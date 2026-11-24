// Bot Telegram di KILLA NEWS: le notizie sul telefono, accessibili con VoiceOver e TalkBack.
// Segreto richiesto: TELEGRAM_BOT_TOKEN (creato dal titolare con @BotFather).
// Il bot non salva nessun dato degli utenti: legge il messaggio, risponde e dimentica.
// Prima configurazione: pagina https://killarecordsgames.github.io/killa-news/telegram/ (il token resta nel browser del titolare).

// Dal segreto si prende solo il token vero e proprio, anche se è stato incollato tutto il messaggio di BotFather
const TOKEN = ((Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "").match(/\d{6,12}:[A-Za-z0-9_-]{35}/) ?? [""])[0];
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
  const piede = "\n\n<i>Tocca un titolo per leggere l'articolo. Per leggere tutto con NVDA sul computer c'è l'app gratuita KILLA NEWS: killarecordsgames.com/killa-news</i>";
  // Telegram accetta messaggi fino a 4096 caratteri: se serve si tolgono le ultime notizie
  while (righe.length > 1 && (`<b>${titolo}</b>\n\n` + righe.join("\n\n") + piede).length > 4000) righe.pop();
  return `<b>${esc(titolo)}</b>\n\n${righe.join("\n\n")}${piede}`;
}

async function sezione(chiave: string) {
  const s = SEZIONI[chiave];
  const liste = await Promise.all(s.feed.map(([g, u]) => leggiFeed(u, g)));
  return elenco(s.nome, unisci(liste, 8));
}

async function cerca(testo: string) {
  const q = testo.slice(0, 80);
  const enc = encodeURIComponent(q);
  // 1) Google News; 2) Bing News se Google non risponde dai server di Supabase; 3) i titoli delle sezioni che contengono la parola
  let notizie = unisci([await leggiFeed(`https://news.google.com/rss/search?q=${enc}+when:3d&hl=it&gl=IT&ceid=IT:it`, "")], 8);
  if (!notizie.length) notizie = unisci([await leggiFeed(`https://www.bing.com/news/search?q=${enc}&format=rss&setlang=it-IT&cc=IT`, "Bing News")], 8);
  if (!notizie.length) {
    const parole = q.toLowerCase().split(/\s+/).filter((p) => p.length > 2);
    const tutte = await Promise.all(Object.values(SEZIONI).flatMap((s) => s.feed.map(([g, u]) => leggiFeed(u, g))));
    notizie = unisci(tutte.map((l) => l.filter((n) => parole.some((p) => n.titolo.toLowerCase().includes(p)))), 8);
  }
  return elenco(`Notizie su «${q}»`, notizie);
}

// Le risposte non partono con una chiamata a Telegram ma tornano nella risposta al webhook
// (Telegram lo permette): così il bot funziona anche quando i server di Supabase sono limitati da Telegram.
function invia(chat: number, testo: string) {
  return { method: "sendMessage", chat_id: chat, text: testo, parse_mode: "HTML", link_preview_options: { is_disabled: true }, reply_markup: TASTIERA };
}

async function giornaleParlato(chat: number) {
  try {
    const p = await (await fetch(PODCAST, { signal: AbortSignal.timeout(8000) })).json();
    if (!p.file) throw new Error("manca il file");
    const audio = `https://killarecordsgames.github.io/killa-news/podcast/${p.file}`;
    return { method: "sendAudio", chat_id: chat, audio, title: p.titolo, performer: "KILLA NEWS", caption: "🎧 " + p.titolo + ". Le notizie principali di oggi, lette ad alta voce.", reply_markup: TASTIERA };
  } catch (e) {
    console.error("giornale parlato", e);
    return invia(chat, "Il giornale parlato di oggi non è ancora pronto. Esce ogni mattina verso le sei e mezza: riprova più tardi.");
  }
}

const AIUTO = "<b>Benvenuto nel bot di KILLA NEWS!</b>\n\n" +
  "Qui trovi le notizie dei giornali italiani, comode da leggere con VoiceOver o TalkBack.\n\n" +
  "• Usa i pulsanti in basso per le sezioni: Prima pagina, Italia, Dal mondo, Economia, Sport, Tecnologia.\n" +
  "• <b>Giornale parlato</b>: ti mando l'audio con le notizie principali di oggi, da ascoltare in pochi minuti.\n" +
  "• Scrivi il nome di una <b>città</b> (per esempio Verona) o un <b>argomento</b> (per esempio Juventus o pensioni) e ti mando le ultime notizie.\n\n" +
  "Il bot è gratuito e non salva i tuoi messaggi. Per ritirare il consenso scrivi /revoca. È un servizio di Killa Records: killarecordsgames.com";

// ---- Informativa privacy da accettare al primo messaggio ----
const ACCETTO = "✅ Accetto l'informativa";
const INFORMATIVA = "<b>Prima di iniziare: informativa privacy</b>\n\n" +
  "Il bot di KILLA NEWS è un servizio gratuito di Killa Records (titolare del trattamento, contatto: info@killarecordsgames.com).\n\n" +
  "• <b>Cosa trattiamo</b>: i messaggi che scrivi al bot, solo per risponderti. Non li salviamo.\n" +
  "• <b>Cosa conserviamo</b>: solo un codice cifrato ricavato dal tuo account Telegram e la data in cui accetti, per ricordare che hai già accettato. Non conserviamo nome, numero di telefono o messaggi.\n" +
  "• <b>Dove</b>: su Supabase, che lo gestisce per nostro conto. Telegram tratta i tuoi dati secondo la sua informativa.\n" +
  "• <b>Per quanto</b>: finché usi il bot. Con /revoca lo cancelliamo subito.\n" +
  "• <b>I tuoi diritti</b>: accesso, cancellazione, opposizione e reclamo al Garante privacy. Informativa completa: killarecordsgames.com/privacy\n\n" +
  "Le notizie sono titoli pubblici dei giornali indicati: per l'articolo completo si va sul sito del giornale.\n\n" +
  "Per usare il bot tocca il pulsante <b>" + ACCETTO + "</b> qui sotto.";
const TASTIERA_CONSENSO = { keyboard: [[{ text: ACCETTO }]], resize_keyboard: true, is_persistent: true, one_time_keyboard: true };

const SB_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SB_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";
async function codiceUtente(id: number) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode("killa-news-consenso:" + id + ":" + SB_KEY.slice(-24)));
  return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, "0")).join("");
}
async function db(metodo: string, query: string, corpo?: unknown) {
  return await fetch(`${SB_URL}/rest/v1/telegram_consensi${query}`, {
    method: metodo,
    headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json", Prefer: "resolution=merge-duplicates,return=minimal" },
    body: corpo ? JSON.stringify(corpo) : undefined,
  });
}
async function haAccettato(codice: string) {
  const r = await db("GET", `?codice=eq.${codice}&select=codice`);
  if (!r.ok) throw new Error("consensi " + r.status);
  return (await r.json()).length > 0;
}


// ---- Gruppo Killa Radio: post del mattino e comandi dell'amministratore ----
async function tg(metodo: string, dati: unknown) {
  const r = await fetch(`${API}/${metodo}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(dati) });
  return await r.json();
}
async function config(chiave: string): Promise<string> {
  const r = await fetch(`${SB_URL}/rest/v1/telegram_config?chiave=eq.${chiave}&select=valore`, { headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}` } });
  const j = r.ok ? await r.json() : [];
  return j[0]?.valore ?? "";
}
async function salvaConfig(chiave: string, valore: string) {
  await fetch(`${SB_URL}/rest/v1/telegram_config`, {
    method: "POST",
    headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json", Prefer: "resolution=merge-duplicates,return=minimal" },
    body: JSON.stringify({ chiave, valore }),
  });
}
async function statoVault(attiva: boolean, link: string, titolo: string) {
  await fetch(`${SB_URL}/rest/v1/vault_stato?id=eq.1`, {
    method: "PATCH",
    headers: { apikey: SB_KEY, Authorization: `Bearer ${SB_KEY}`, "Content-Type": "application/json", Prefer: "return=minimal" },
    body: JSON.stringify({ in_diretta: attiva, link_diretta: attiva ? link : "", titolo_diretta: titolo.slice(0, 120), aggiornato_il: new Date().toISOString() }),
  });
}
// È amministratore chi è proprietario o amministratore del gruppo Killa Radio
async function eAdminRadio(userId: number) {
  const gruppo = await config("gruppo_id");
  if (!gruppo || !userId) return false;
  const r = await tg("getChatMember", { chat_id: gruppo, user_id: userId });
  return r.ok && ["creator", "administrator"].includes(r.result?.status);
}
const COMANDI_ADMIN = "<b>Comandi per te (solo amministratore)</b>\n\n" +
  "• <b>annuncia la diretta</b>: avvisa il gruppo Killa Radio e ferma la radio del Vault. Puoi aggiungere il titolo, per esempio: annuncia la diretta Quiz del venerdì\n" +
  "• <b>fine diretta</b>: avvisa che la diretta è finita e fa ripartire la musica nel Vault\n" +
  "• <b>annuncia</b> seguito da un testo: lo pubblico nel gruppo così com'è\n" +
  "• <b>giornale nel gruppo</b>: pubblico adesso il giornale parlato di oggi nel gruppo";

async function comandoAdmin(msg: any): Promise<Record<string, unknown> | null> {
  const t = msg.text.trim();
  const chat = msg.chat.id;
  const m1 = t.match(/^\/?(annuncia|avvia)\s+(la\s+)?diretta\s*[:,-]?\s*(.*)$/i);
  const m2 = /^\/?(fine|chiudi|termina)\s+(la\s+)?diretta\b/i.test(t);
  const m3 = t.match(/^\/?annuncia\s+([\s\S]+)$/i);
  const m4 = /^\/?(giornale nel gruppo|mattino)\b/i.test(t);
  const m5 = /^\/?(comandi|admin)$/i.test(t);
  if (!m1 && !m2 && !m3 && !m4 && !m5) return null;
  if (!(await eAdminRadio(msg.from?.id))) return null; // per gli altri sono messaggi normali
  const gruppo = await config("gruppo_id");
  const link = await config("gruppo_link");
  if (m5) return invia(chat, COMANDI_ADMIN);
  if (m1) {
    const titolo = (m1[3] || "").trim();
    const testo = "🔴 <b>KILLA È IN DIRETTA ADESSO!</b>" + (titolo ? "\n\n🎙 " + esc(titolo) : "") +
      "\n\nEntra nella diretta qui nel gruppo: tocca la barra della diretta in alto, oppure apri il gruppo e scegli Partecipa." +
      "\nVuoi parlare? Alza la mano. Per i quiz scrivi la risposta qui in chat.";
    const r = await tg("sendMessage", { chat_id: gruppo, text: testo, parse_mode: "HTML" });
    await statoVault(true, link, titolo || "Diretta di Killa");
    return invia(chat, r.ok ? "Fatto! Ho avvisato il gruppo Killa Radio e nel Vault la musica si è fermata con l'avviso della diretta. Quando finisci scrivimi: fine diretta" : "Non riesco a scrivere nel gruppo: controlla che io sia ancora nel gruppo. Errore: " + esc(r.description || ""));
  }
  if (m2) {
    await tg("sendMessage", { chat_id: gruppo, text: "✅ La diretta è finita. Grazie a tutti! La registrazione arriverà presto nella Killa Radio del Vault." });
    await statoVault(false, "", "");
    return invia(chat, "Diretta chiusa: ho avvisato il gruppo e nel Vault la musica è ripartita.");
  }
  if (m4) {
    const esito = await postMattino(true);
    return invia(chat, esito);
  }
  if (m3) {
    const r = await tg("sendMessage", { chat_id: gruppo, text: m3[1].slice(0, 4000) });
    return invia(chat, r.ok ? "Pubblicato nel gruppo Killa Radio." : "Non riesco a scrivere nel gruppo. Errore: " + esc(r.description || ""));
  }
  return null;
}

// Post del mattino nel gruppo: il giornale parlato di oggi, una volta sola al giorno
async function postMattino(forza = false): Promise<string> {
  const gruppo = await config("gruppo_id");
  if (!gruppo) return "Il gruppo non è ancora collegato: scrivi /collega nel gruppo Killa Radio.";
  const p = await (await fetch(PODCAST + "?t=" + Date.now(), { signal: AbortSignal.timeout(8000) })).json();
  const oggi = new Date().toLocaleDateString("sv-SE", { timeZone: "Europe/Rome" });
  if (p.data !== oggi) return "Il giornale parlato di oggi non è ancora pronto.";
  if (!forza && (await config("ultimo_mattino")) === oggi) return "Già pubblicato oggi.";
  const audio = `https://killarecordsgames.github.io/killa-news/podcast/${p.file}`;
  const r = await tg("sendAudio", {
    chat_id: gruppo, audio, title: p.titolo, performer: "KILLA NEWS",
    caption: "☀️ Buongiorno Killa Family! Ecco " + p.titolo.charAt(0).toLowerCase() + p.titolo.slice(1) + ": le notizie principali di oggi in pochi minuti.\n\nLe notizie quando vuoi: @KillaFlowBot · La radio 24 ore su 24: killarecordsgames.com/vault",
  });
  if (r.ok) await salvaConfig("ultimo_mattino", oggi);
  return r.ok ? "Giornale parlato pubblicato nel gruppo." : "Errore Telegram: " + (r.description || "");
}

async function gestisci(update: any): Promise<Record<string, unknown> | null> {
  const msg = update.message;
  if (!msg?.chat?.id || typeof msg.text !== "string") return null;
  const chat = msg.chat.id;
  // Nei gruppi rispondo solo a /collega (per collegare il gruppo Killa Radio)
  if (msg.chat.type !== "private") {
    if (/^\/collega(@\w+)?\b/i.test(msg.text.trim())) {
      const r = await tg("getChatMember", { chat_id: chat, user_id: msg.from?.id });
      if (!(r.ok && r.result?.status === "creator")) return null;
      await salvaConfig("gruppo_id", String(chat));
      const link = (msg.text.match(/https:\/\/t\.me\/\S+/) || [""])[0];
      if (link) await salvaConfig("gruppo_link", link);
      return { method: "sendMessage", chat_id: chat, text: "✅ Gruppo Killa Radio collegato al bot. Ogni mattina pubblicherò qui il giornale parlato." };
    }
    return null;
  }
  const admin = await comandoAdmin(msg);
  if (admin) return admin;
  const testo = msg.text.replace(/[^\p{L}\p{N}\s'’.,-]/gu, " ").replace(/\s+/g, " ").trim();
  const codice = await codiceUtente(msg.from?.id ?? chat);
  if (/^\/?revoca\b/i.test(msg.text.trim())) {
    await db("DELETE", `?codice=eq.${codice}`);
    return { method: "sendMessage", chat_id: chat, text: "Fatto: ho cancellato il tuo consenso e il codice che lo ricordava. Se vuoi usare di nuovo il bot, scrivimi qualcosa e ti ripropongo l'informativa.", reply_markup: { remove_keyboard: true } };
  }
  if (msg.text.trim() === ACCETTO) {
    await db("POST", "", { codice, accettato_il: new Date().toISOString(), versione: "2026-11-24" });
    return invia(chat, "Grazie! " + AIUTO);
  }
  if (!(await haAccettato(codice))) {
    return { method: "sendMessage", chat_id: chat, text: INFORMATIVA, parse_mode: "HTML", link_preview_options: { is_disabled: true }, reply_markup: TASTIERA_CONSENSO };
  }
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
  if (req.method === "GET" && url.searchParams.get("stato") === "1") {
    const me = await (await fetch(`${API}/getMe`)).json();
    const wh = await (await fetch(`${API}/getWebhookInfo`)).json();
    const r = wh.result || {};
    return new Response(JSON.stringify({
      token_trovato: TOKEN !== "", segreto_con_testo_in_piu: (Deno.env.get("TELEGRAM_BOT_TOKEN") ?? "").trim() !== TOKEN,
      bot: me.ok ? me.result.username : me, webhook: r.url || "(nessuno)", in_attesa: r.pending_update_count,
      ultimo_errore: r.last_error_message || "", data_errore: r.last_error_date ? new Date(r.last_error_date * 1000).toISOString() : "",
    }, null, 1), { headers: { "Content-Type": "application/json; charset=utf-8" } });
  }
  if (req.method === "GET" && url.searchParams.get("mattino") === "1") {
    // Chiamato ogni mattina dopo l'uscita del giornale parlato: pubblica una sola volta al giorno
    return new Response(await postMattino(false), { headers: { "Content-Type": "text/plain; charset=utf-8" } });
  }
  if (req.method === "GET" && url.searchParams.get("configura") === "1") {
    const indirizzo = `https://${url.host}/functions/v1/killa-news-telegram`;
    const segreto = await segretoWebhook();
    const info = await (await fetch(`${API}/getWebhookInfo`)).json();
    if (info.ok && info.result?.url === indirizzo) {
      return new Response("Bot già collegato a questo indirizzo.", { headers: { "Content-Type": "text/plain; charset=utf-8" } });
    }
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
    const risposta = await gestisci(await req.json());
    if (risposta) return new Response(JSON.stringify(risposta), { headers: { "Content-Type": "application/json" } });
  } catch (e) {
    console.error("errore", e);
  }
  return new Response("ok");
});
export { gestisci };
