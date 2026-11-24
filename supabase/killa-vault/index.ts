// KILLA VAULT - funzione Supabase dell'area riservata (si entra solo su invito).
// Azioni pubbliche: richiesta (chiedere di entrare), registrati (con il codice d'invito).
// Azioni dei membri (con accesso fatto): io (tessera, diretta, radio).
// Azioni dell'amministratore (utente nella tabella admins): lista, invita, rifiuta, diretta.
// Segreti: BREVO_API_KEY (già presente). Facoltativo: VAULT_ADMIN_EMAIL (dove arrivano le richieste).
import { createClient } from "npm:@supabase/supabase-js@2";

const DOMINI = ["https://www.killarecordsgames.com", "https://killarecordsgames.com"];
const SITO = "https://www.killarecordsgames.com";
const MITTENTE = { name: "Killa Records", email: "info@killarecordsgames.com" };
const ADMIN_EMAIL = Deno.env.get("VAULT_ADMIN_EMAIL") || "info@killarecordsgames.com";
const RADIO = "https://killarecordsgames.github.io/killa-news/radio/palinsesto.json";
const EMAIL_VALIDA = /^[^\s@<>"]+@[^\s@<>"]+\.[^\s@<>"]{2,}$/;
const NICK_VALIDO = /^[\p{L}\p{N}_.\- ]{3,24}$/u;
const GIORNI_VALIDITA = 7;

const sb = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
  auth: { persistSession: false, autoRefreshToken: false },
});

function cors(origine: string | null) {
  return {
    "Access-Control-Allow-Origin": origine && DOMINI.includes(origine) ? origine : DOMINI[0],
    "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Vary": "Origin",
  };
}
function rispondi(stato: number, dati: unknown, origine: string | null) {
  return new Response(JSON.stringify(dati), { status: stato, headers: { ...cors(origine), "Content-Type": "application/json; charset=utf-8" } });
}
const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

async function sha256(testo: string) {
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(testo));
  return Array.from(new Uint8Array(h)).map((b) => b.toString(16).padStart(2, "0")).join("");
}
function nuovoCodice() {
  const alfabeto = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"; // niente 0/O e 1/I, che si confondono
  const b = crypto.getRandomValues(new Uint8Array(8));
  const c = Array.from(b, (x) => alfabeto[x % alfabeto.length]).join("");
  return `KILLA-${c.slice(0, 4)}-${c.slice(4)}`;
}
const normalizzaCodice = (c: string) => String(c || "").toUpperCase().replace(/[^A-Z0-9]/g, "").replace(/^KILLA/, "");

function paginaEmail(titolo: string, corpo: string) {
  return `<!DOCTYPE html><html lang="it"><head><meta charset="utf-8"><title>${esc(titolo)}</title></head>
<body style="margin:0;background:#0d0b14;font-family:Arial,Helvetica,sans-serif;color:#f2f0f7">
<div style="max-width:560px;margin:0 auto;padding:32px 22px">
<p style="letter-spacing:3px;color:#b48cff;font-size:13px;margin:0 0 6px">KILLA RECORDS · VAULT</p>
<h1 style="font-size:24px;margin:0 0 18px">${esc(titolo)}</h1>${corpo}
<p style="color:#9a94ab;font-size:13px;margin-top:32px">Killa Records · <a href="${SITO}" style="color:#b48cff">killarecordsgames.com</a></p>
</div></body></html>`;
}
async function inviaEmail(a: { email: string; name?: string }, oggetto: string, html: string) {
  const chiave = Deno.env.get("BREVO_API_KEY");
  if (!chiave) throw new Error("manca BREVO_API_KEY");
  const r = await fetch("https://api.brevo.com/v3/smtp/email", {
    method: "POST",
    headers: { "api-key": chiave, "Content-Type": "application/json", accept: "application/json" },
    body: JSON.stringify({ sender: MITTENTE, to: [a], subject: oggetto, htmlContent: html }),
  });
  if (!r.ok) throw new Error("Brevo " + r.status + " " + (await r.text()).slice(0, 200));
}

async function utenteDa(req: Request) {
  const jwt = (req.headers.get("authorization") || "").replace(/^Bearer\s+/i, "");
  if (!jwt) return null;
  const { data } = await sb.auth.getUser(jwt);
  return data?.user ?? null;
}
async function eAdmin(userId: string) {
  const { data } = await sb.from("admins").select("user_id").eq("user_id", userId).maybeSingle();
  return !!data;
}

// ---------- azioni pubbliche ----------
async function richiesta(c: Record<string, unknown>, origine: string | null) {
  if (c.sito) return rispondi(200, { ok: true }, origine); // campo trappola per i programmi automatici
  const nickname = String(c.nickname || "").trim().replace(/\s+/g, " ");
  const email = String(c.email || "").trim().toLowerCase();
  if (!NICK_VALIDO.test(nickname)) return rispondi(400, { errore: "Il nickname deve avere da 3 a 24 caratteri: lettere, numeri, spazio, punto, trattino o trattino basso." }, origine);
  if (!EMAIL_VALIDA.test(email) || email.length > 254) return rispondi(400, { errore: "L'indirizzo email non sembra corretto. Controllalo e riprova." }, origine);
  if (c.privacy !== true) return rispondi(400, { errore: "Per chiedere di entrare devi accettare l'informativa privacy." }, origine);

  const { data: esiste } = await sb.from("vault_richieste").select("id, stato").ilike("email", email).maybeSingle();
  if (esiste) {
    const msg = esiste.stato === "iscritto" ? "Sei già nella Killa Family: entra con la tua email e la tua password." :
      "Abbiamo già la tua richiesta. Riceverai l'invito per email appena viene approvata.";
    return rispondi(200, { ok: true, messaggio: msg }, origine);
  }
  // Freno contro chi prova a riempire il modulo di richieste: al massimo 30 nuove richieste all'ora in tutto
  const unOraFa = new Date(Date.now() - 3600000).toISOString();
  const { count } = await sb.from("vault_richieste").select("id", { count: "exact", head: true }).gte("creata_il", unOraFa);
  if ((count ?? 0) >= 30) return rispondi(429, { errore: "In questo momento arrivano troppe richieste. Riprova tra un'ora." }, origine);
  const { data: stessoNick } = await sb.from("vault_membri").select("user_id").ilike("nickname", nickname).maybeSingle();
  if (stessoNick) return rispondi(400, { errore: "Questo nickname è già usato da un membro. Scegline un altro." }, origine);

  const { data: nuova, error } = await sb.from("vault_richieste").insert({ nickname, email }).select("id").single();
  if (error) return rispondi(500, { errore: "Non riesco a salvare la richiesta. Riprova tra poco." }, origine);

  try {
    await inviaEmail({ email: ADMIN_EMAIL }, `Vault: nuova richiesta da ${nickname}`, paginaEmail("Nuova richiesta per il Vault",
      `<p>Nickname: <strong>${esc(nickname)}</strong><br>Email: <strong>${esc(email)}</strong></p>
<p>Per mandare l'invito apri la gestione del Vault:</p>
<p><a href="${SITO}/admin-vault" style="display:inline-block;background:#8b5cf6;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold">Apri la gestione del Vault</a></p>`));
    await inviaEmail({ email, name: nickname }, "Abbiamo ricevuto la tua richiesta per il KILLA VAULT", paginaEmail(`Ciao ${nickname}!`,
      `<p>Abbiamo ricevuto la tua richiesta di entrare nel <strong>KILLA VAULT</strong>, l'area riservata della Killa Family.</p>
<p>Le richieste vengono approvate a mano. Se vieni scelto, ti arriva un'email con il tuo <strong>codice d'invito personale</strong>.</p>
<p>Se non sei stato tu a fare questa richiesta, ignora questa email: i tuoi dati verranno cancellati.</p>`));
  } catch (e) {
    console.error("email richiesta", nuova?.id, e);
  }
  return rispondi(200, { ok: true, messaggio: "Richiesta inviata! Ti abbiamo mandato un'email di conferma. Se vieni scelto riceverai il codice d'invito." }, origine);
}

async function registrati(c: Record<string, unknown>, origine: string | null) {
  if (c.sito) return rispondi(200, { ok: true }, origine);
  const email = String(c.email || "").trim().toLowerCase();
  const password = String(c.password || "");
  const codice = normalizzaCodice(String(c.codice || ""));
  if (!EMAIL_VALIDA.test(email)) return rispondi(400, { errore: "Scrivi la stessa email a cui ti è arrivato l'invito." }, origine);
  if (codice.length !== 8) return rispondi(400, { errore: "Il codice d'invito non è completo. Ha questa forma: KILLA-ABCD-EFGH." }, origine);
  if (password.length < 8) return rispondi(400, { errore: "La password deve avere almeno 8 caratteri." }, origine);
  if (c.privacy !== true) return rispondi(400, { errore: "Per entrare devi accettare l'informativa privacy e il regolamento del Vault." }, origine);

  const { data: r } = await sb.from("vault_richieste").select("*").ilike("email", email).maybeSingle();
  const hash = await sha256("vault:" + email + ":" + codice);
  if (!r || r.stato !== "invitato" || r.codice_hash !== hash) {
    return rispondi(400, { errore: "Codice non valido per questa email. Controlla di aver scritto la stessa email dell'invito e il codice giusto." }, origine);
  }
  if (!r.codice_scade || new Date(r.codice_scade) < new Date()) {
    return rispondi(400, { errore: "Questo codice è scaduto. Scrivici a info@killarecordsgames.com e te ne mandiamo uno nuovo." }, origine);
  }

  let userId = "";
  const crea = await sb.auth.admin.createUser({ email, password, email_confirm: true, user_metadata: { nickname: r.nickname } });
  if (crea.data?.user) {
    userId = crea.data.user.id;
  } else {
    // Esiste già un account con questa email (per esempio quello dei giochi): serve la sua password
    const { data: login } = await createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_ANON_KEY")!, { auth: { persistSession: false } })
      .auth.signInWithPassword({ email, password });
    if (!login?.user) return rispondi(400, { errore: "Hai già un account con questa email: scrivi la password che usi già per entrare." }, origine);
    userId = login.user.id;
  }
  const { data: membro, error } = await sb.from("vault_membri").insert({ user_id: userId, nickname: r.nickname }).select("tessera").single();
  if (error && !String(error.message).includes("duplicate")) return rispondi(500, { errore: "Non riesco a completare l'iscrizione. Riprova tra poco." }, origine);
  await sb.from("vault_richieste").update({ stato: "iscritto", codice_hash: null, codice_scade: null }).eq("id", r.id);
  return rispondi(200, { ok: true, tessera: membro?.tessera, nickname: r.nickname }, origine);
}

// ---------- membri ----------
async function io(utente: { id: string } | null, origine: string | null) {
  if (!utente) return rispondi(401, { errore: "Devi entrare con la tua email e la tua password." }, origine);
  const { data: m } = await sb.from("vault_membri").select("nickname, tessera, entrato_il").eq("user_id", utente.id).maybeSingle();
  const admin = await eAdmin(utente.id);
  if (!m && !admin) return rispondi(403, { errore: "Questo account non è ancora nella Killa Family. Chiedi di entrare con il modulo." }, origine);
  const { data: stato } = await sb.from("vault_stato").select("in_diretta, titolo_diretta, link_diretta, aggiornato_il").eq("id", 1).single();
  return rispondi(200, { membro: m ?? { nickname: "Killa", tessera: 0 }, admin, diretta: stato, radio: RADIO }, origine);
}

// ---------- amministratore ----------
async function admin(azione: string, c: Record<string, unknown>, origine: string | null) {
  if (azione === "lista") {
    const { data: richieste } = await sb.from("vault_richieste").select("id, nickname, email, creata_il, stato, invitata_il, codice_scade").order("creata_il", { ascending: false }).limit(500);
    const { data: membri } = await sb.from("vault_membri").select("nickname, tessera, entrato_il").order("tessera");
    const { data: stato } = await sb.from("vault_stato").select("*").eq("id", 1).single();
    return rispondi(200, { richieste, membri, diretta: stato }, origine);
  }
  if (azione === "invita") {
    const { data: r } = await sb.from("vault_richieste").select("*").eq("id", String(c.id || "")).maybeSingle();
    if (!r) return rispondi(404, { errore: "Richiesta non trovata." }, origine);
    if (r.stato === "iscritto") return rispondi(400, { errore: `${r.nickname} è già nel Vault.` }, origine);
    const codice = nuovoCodice();
    const scade = new Date(Date.now() + GIORNI_VALIDITA * 86400000);
    const link = `${SITO}/vault-entra?email=${encodeURIComponent(r.email)}`;
    await inviaEmail({ email: r.email, name: r.nickname }, "Il tuo invito per il KILLA VAULT", paginaEmail(`${r.nickname}, sei dentro!`,
      `<p>La tua richiesta è stata approvata: puoi entrare nel <strong>KILLA VAULT</strong>, l'area riservata della Killa Family.</p>
<p>Il tuo codice d'invito personale è:</p>
<p style="font-size:26px;font-weight:bold;letter-spacing:3px;background:#1c1828;padding:14px 18px;border-radius:8px;text-align:center">${codice}</p>
<p>Il codice vale <strong>una sola volta</strong>, solo con questa email, e scade tra ${GIORNI_VALIDITA} giorni. Non condividerlo.</p>
<p><a href="${link}" style="display:inline-block;background:#8b5cf6;color:#fff;padding:12px 20px;border-radius:8px;text-decoration:none;font-weight:bold">Entra nel Vault</a></p>
<p>Nella pagina scrivi il codice e scegli una password. Riceverai la tua tessera numerata della Killa Family.</p>`));
    await sb.from("vault_richieste").update({
      stato: "invitato", codice_hash: await sha256("vault:" + r.email.toLowerCase() + ":" + normalizzaCodice(codice)),
      codice_scade: scade.toISOString(), invitata_il: new Date().toISOString(),
    }).eq("id", r.id);
    return rispondi(200, { ok: true, messaggio: `Invito mandato a ${r.nickname}. Il codice scade il ${scade.toLocaleDateString("it-IT")}.` }, origine);
  }
  if (azione === "rifiuta") {
    // Una richiesta rifiutata si cancella: non teniamo dati che non servono
    await sb.from("vault_richieste").delete().eq("id", String(c.id || "")).neq("stato", "iscritto");
    return rispondi(200, { ok: true, messaggio: "Richiesta cancellata." }, origine);
  }
  if (azione === "diretta") {
    const attiva = c.attiva === true;
    const link = String(c.link || "").trim();
    if (attiva && !/^https:\/\/(t\.me|telegram\.me)\//.test(link)) return rispondi(400, { errore: "Incolla il link della diretta Telegram, che inizia con https://t.me/" }, origine);
    await sb.from("vault_stato").update({ in_diretta: attiva, titolo_diretta: String(c.titolo || "").slice(0, 120), link_diretta: attiva ? link : "", aggiornato_il: new Date().toISOString() }).eq("id", 1);
    return rispondi(200, { ok: true, messaggio: attiva ? "Diretta attivata: la radio del Vault si ferma e avvisa tutti." : "Diretta chiusa: la musica riparte." }, origine);
  }
  return rispondi(400, { errore: "Azione sconosciuta." }, origine);
}

Deno.serve(async (req) => {
  const origine = req.headers.get("origin");
  if (req.method === "OPTIONS") return new Response(null, { status: 204, headers: cors(origine) });
  if (req.method !== "POST") return rispondi(405, { errore: "Metodo non consentito." }, origine);
  if (!origine || !DOMINI.includes(origine)) return rispondi(403, { errore: "Il Vault funziona solo dal sito di Killa Records." }, origine);
  let c: Record<string, unknown>;
  try { c = await req.json(); } catch { return rispondi(400, { errore: "Richiesta non valida." }, origine); }
  const azione = String(c.azione || "");
  try {
    if (azione === "richiesta") return await richiesta(c, origine);
    if (azione === "registrati") return await registrati(c, origine);
    const utente = await utenteDa(req);
    if (azione === "io") return await io(utente, origine);
    if (!utente || !(await eAdmin(utente.id))) return rispondi(403, { errore: "Solo l'amministratore può farlo." }, origine);
    return await admin(azione, c, origine);
  } catch (e) {
    console.error("vault", azione, e);
    return rispondi(500, { errore: "Si è verificato un errore. Riprova tra poco." }, origine);
  }
});
