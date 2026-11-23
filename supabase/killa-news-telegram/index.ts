// Bot Telegram di KILLA NEWS: le notizie sul telefono, accessibili con VoiceOver e TalkBack.
// Segreto richiesto: TELEGRAM_BOT_TOKEN (creato dal titolare con @BotFather).
// Il bot non salva nessun dato degli utenti: legge il messaggio, risponde e dimentica.
// Prima configurazione: aprire una volta l'indirizzo della funzione con ?configura=1.

const TOKEN = Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "";
const API = `https://api.telegram.org/bot${TOKEN}`;
const UA = "KillaNews-Telegram/1.0 (+https://www.killarecordsgames.com/killa-news)";
const PODCAST = "https://killarecordsgames.github.io/killa-news/podcast/ultima.json";

const SEZIONI: Record<string, { nome: string; feed: [string, string][] }> = {
  prima: { nome: "Prima pagina", feed: [["ANSA", "https://www.ansa.it/sito/notizie/topnews/topnews_rss.xml"], ["Rai News", "https://www.rainews.it/rss/ultimora"]] },
  italia: { nome: "Italia", feed: [["ANSA", "https://www.ansa.it/sito/notizie/politica/politica_rss.xml"], ["ANSA", "https://www.ansa.it/sito/notizie/cronaca/cronaca_rss.xml"]] },
  mondo: { nome: "Dal mondo", feed: [["ANSA", "https://www.ansa.it/sito/notizie/mondo/mondo_rss.xml"], ["Rai News", "https://www.rainews.it/rss/esteri"]] },
  economia: { nome: "Economia", feed: [["ANSA", "https://www.ansa.it/sito/notizie/economia/economia_rss.xml"], ["Il Sole 24 Ore", "https://www.ilsole24ore.com/rss/italia.xml"]] },
  sport: { nome: "Sport", feed: [["ANSA", "https://www.ansa.it/sito/notizie/sport/sport_rss.xml"], ["Rai News", "https://www.rainews.it/rss/sport"]] },
  tecnologia: { nome: "Tecnologia", feed: [["HWUpgrade", "http://feeds.hwupgrade.it/rss_hwup.xml"]] },
};
// Pulsanti fissi in basso: con VoiceOver si trovano subito, senza scrivere comandi
const TASTIERA = {
  keyboard: [
    [{ text: "📰 Prima pagina" }, { text: "🇮🇹 Italia" }],
    [{ text: "🌍 Dal mondo" }, { text: "💶 Economia" }],
    [{ text: "⚽ Sport" }, { text: "💻 Tecnologia" }],
    [{ text: "🎧 Giornale parlato" }, { text: "❓ Aiuto" }],
  ],
  resize_keyboard: true,
  is_persistent: true,
  input_field_placeholder: "Scrivi una città o un argomento",
};
const PAROLE: [RegExp, string][] = [
  [/prima pagina|^\/?prima|^\/?notizie/i, "prima"], [/italia/i, "italia"], [/mondo|esteri/i, "mondo"],
  [/economia/i, "economia"], [/sport/i, "sport"], [/tecnologia/i, "tecnologia"],
];

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const decodifica = (s: string) =>
  s.replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1").replace(/<[^>]+>/g, " ")
    .replace(/&amp;/g, "&").replace(/&quot;/g, '"').replace(/&#39;|&apos;/g, "'").replace(/&lt;/g, "<").replace(/&gt;/g, ">")
    .replace(/&#(\d+);/g, (_, n) => String.fromCharCode(Number(n))).replace(/\s+/g, " ").trim();

type Notizia = { titolo: string; link: string; giornale: string; data: number };

async function leggiFeed(url: string, giornale: string): Promise<Notizia[]> {
  try {
    const r = await fetch(url, { headers: { "User-Agent": UA }, signal: AbortSignal.timeout(8000) });
    if (!r.ok) return [];
    const xml = await r.text();
    const out: Notizia[] = [];
    for (const m of xml.matchAll(/<item\b[\s\S]*?<\/item>/g)) {
      const it = m[0];
      const t = decodifica((it.match(/<title\b[^>]*>([\s\S]*?)<\/title>/) ?? [])[1] ?? "");
      const l = decodifica((it.match(/<link\b[^>]*>([\s\S]*?)<\/link>/) ?? [])[1] ?? "");
      const d = Date.parse(decodifica((it.match(/<pubDate>([\s\S]*?)<\/pubDate>/) ?? [])[1] ?? "")) || 0;
      let g = giornale;
      let titolo = t;
      const src = it.match(/<source\b[^>]*>([\s\S]*?)<\/source>/);
      if (src) { g = decodifica(src[1]); titolo = t.replace(new RegExp(`\\s+-\\s+${g.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}$`), ""); }
      if (titolo.length > 15 && l.startsWith("http")) out.push({ titolo, link: l, giornale: g, data: d });
      if (out.length >= 20) break;
    }
    return out;
  } catch {
    return [];
  }
}

function unisci(liste: Notizia[][], quante: number): Notizia[] {
  const visti = new Set<string>();
  const tutte = liste.flat().sort((a, b) => b.data - a.data);
  const out: Notizia[] = [];
  for (const n of tutte) {
    const k = n.titolo.toLowerCase().replace(/\W+/g, " ").slice(0, 60);
    if (visti.has(k)) continue;
    visti.add(k);
    out.push(n);
    if (out.length >= quante) break;
  }
  return out;
}

function elenco(titolo: string, notizie: Notizia[]): string {
  if (!notizie.length) return `<b>${esc(titolo)}</b>\n\nNon ho trovato notizie in questo momento. Riprova tra poco.`;
  const righe = notizie.map((n, i) => `${i + 1}. <a href="${esc(n.link)}">${esc(n.titolo)}</a>, ${esc(n.giornale)}`);
  return `<b>${esc(titolo)}</b>\n\n${righe.join("\n\n")}\n\n<i>Tocca un titolo per leggere l'articolo. Per leggere tutto con NVDA sul computer c'è l'app gratuita KILLA NEWS: killarecordsgames.com/killa-news</i>`;
}

async function sezione(chiave: string) {
  const s = SEZIONI[chiave];
  const liste = await Promise.all(s.feed.map(([g, u]) => leggiFeed(u, g)));
  return elenco(s.nome, unisci(liste, 8));
}

async function cerca(testo: string) {
  const q = testo.slice(0, 80);
  const url = `https://news.google.com/rss/search?q=${encodeURIComponent(q)}+when:3d&hl=it&gl=IT&ceid=IT:it`;
  const notizie = unisci([await leggiFeed(url, "")], 8);
  return elenco(`Notizie su «${q}»`, notizie);
}

async function invia(chat: number, testo: string) {
  await fetch(`${API}/sendMessage`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ chat_id: chat, text: testo, parse_mode: "HTML", link_preview_options: { is_disabled: true }, reply_markup: TASTIERA }),
  });
}

async function giornaleParlato(chat: number) {
  try {
    const p = await (await fetch(PODCAST, { signal: AbortSignal.timeout(8000) })).json();
    const audio = `https://killarecordsgames.github.io/killa-news/podcast/${p.file}`;
    const r = await fetch(`${API}/sendAudio`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: chat, audio, title: p.titolo, performer: "KILLA NEWS", caption: "🎧 " + p.titolo + ". Le notizie principali di oggi, lette ad alta voce.", reply_markup: TASTIERA }),
    });
    if (!r.ok) throw new Error(await r.text());
  } catch (e) {
    console.error("giornale parlato", e);
    await invia(chat, "Il giornale parlato di oggi non è ancora pronto. Esce ogni mattina verso le sei e mezza: riprova più tardi.");
  }
}

const AIUTO = "<b>Benvenuto nel bot di KILLA NEWS!</b>\n\n" +
  "Qui trovi le notizie dei giornali italiani, comode da leggere con VoiceOver o TalkBack.\n\n" +
  "• Usa i pulsanti in basso per le sezioni: Prima pagina, Italia, Dal mondo, Economia, Sport, Tecnologia.\n" +
  "• <b>Giornale parlato</b>: ti mando l'audio con le notizie principali di oggi, da ascoltare in pochi minuti.\n" +
  "• Scrivi il nome di una <b>città</b> (per esempio Verona) o un <b>argomento</b> (per esempio Juventus o pensioni) e ti mando le ultime notizie.\n\n" +
  "Il bot è gratuito e non salva i tuoi messaggi. È un servizio di Killa Records: killarecordsgames.com";

async function gestisci(update: any) {
  const msg = update.message;
  if (!msg?.chat?.id || typeof msg.text !== "string") return;
  const chat = msg.chat.id;
  const testo = msg.text.replace(/[^\p{L}\p{N}\s'’.,-]/gu, " ").replace(/\s+/g, " ").trim();
  if (/^\/?(start|aiuto|help)\b/i.test(msg.text.trim()) || /^aiuto$/i.test(testo)) return invia(chat, AIUTO);
  if (/giornale parlato|^\/?(podcast|ascolta|giornale)/i.test(testo)) return giornaleParlato(chat);
  for (const [re, k] of PAROLE) if (re.test(testo) && testo.split(" ").length <= 3) return invia(chat, await sezione(k));
  if (testo.length < 2) return invia(chat, AIUTO);
  return invia(chat, await cerca(testo));
}

async function segretoWebhook() {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("killa-news-telegram:" + TOKEN));
  return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, "0")).join("").slice(0, 48);
}

Deno.serve(async (req) => {
  if (!TOKEN) return new Response("Manca il segreto TELEGRAM_BOT_TOKEN", { status: 500 });
  const url = new URL(req.url);
  if (req.method === "GET" && url.searchParams.get("configura") === "1") {
    const indirizzo = `https://${url.host}/functions/v1/killa-news-telegram`;
    const segreto = await segretoWebhook();
    const r1 = await fetch(`${API}/setWebhook`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url: indirizzo, secret_token: segreto, allowed_updates: ["message"], drop_pending_updates: true }),
    });
    await fetch(`${API}/setMyCommands`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ commands: [
        { command: "notizie", description: "Prima pagina" }, { command: "giornale", description: "Giornale parlato di oggi" },
        { command: "sport", description: "Notizie di sport" }, { command: "aiuto", description: "Come funziona" },
      ] }),
    });
    await fetch(`${API}/setMyDescription`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ description: "Le notizie dei giornali italiani sul telefono, accessibili con VoiceOver e TalkBack, e ogni mattina il giornale parlato. Un servizio gratuito di KILLA NEWS, di Killa Records." }),
    });
    return new Response(r1.ok ? "Bot configurato: ora puoi scrivergli su Telegram." : "Configurazione non riuscita: " + await r1.text(),
      { headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  if (req.method !== "POST") return new Response("ok");
  if (req.headers.get("X-Telegram-Bot-Api-Secret-Token") !== await segretoWebhook()) return new Response("no", { status: 401 });
  try {
    await gestisci(await req.json());
  } catch (e) {
    console.error("errore", e);
  }
  return new Response("ok");
});
export { gestisci };
