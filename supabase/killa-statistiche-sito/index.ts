// Statistiche del sito (GoatCounter) per la pagina privata: risponde solo agli amministratori.
// Serve il segreto GOATCOUNTER_TOKEN (chiave API di GoatCounter con permesso di lettura).
import { createClient } from "jsr:@supabase/supabase-js@2";

const CORS = {
  "Access-Control-Allow-Origin": "https://www.killarecordsgames.com",
  "Access-Control-Allow-Headers": "authorization, content-type, apikey, x-client-info",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};
const GC = "https://killarecords.goatcounter.com/api/v0";

function risposta(stato: number, dati: unknown) {
  return new Response(JSON.stringify(dati), { status: stato, headers: { ...CORS, "Content-Type": "application/json" } });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return risposta(405, { errore: "Usa POST" });
  const jwt = (req.headers.get("Authorization") ?? "").replace(/^Bearer\s+/i, "");
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });
  const { data: u, error: e1 } = await db.auth.getUser(jwt);
  if (e1 || !u?.user) return risposta(401, { errore: "Accesso richiesto" });
  const { data: adm } = await db.from("admins").select("user_id").eq("user_id", u.user.id).maybeSingle();
  if (!adm) return risposta(403, { errore: "Solo per gli amministratori" });

  const token = Deno.env.get("GOATCOUNTER_TOKEN");
  if (!token) return risposta(200, { configurato: false });

  let giorni = 30;
  try {
    const b = await req.json();
    giorni = Math.max(1, Math.min(365, Math.floor(Number(b.giorni) || 30)));
  } catch { /* corpo vuoto: 30 giorni */ }
  // GoatCounter vuole data e ora (RFC 3339) arrotondate all'ora
  const fine = new Date(Math.ceil(Date.now() / 3600000) * 3600000);
  const inizio = new Date(fine.getTime() - giorni * 86400000);
  inizio.setUTCMinutes(0, 0, 0);
  const iso = (d: Date) => d.toISOString().replace(/\.\d{3}Z$/, "Z");
  const periodo = "start=" + encodeURIComponent(iso(inizio)) + "&end=" + encodeURIComponent(iso(fine));
  const leggi = async (percorso: string) => {
    const r = await fetch(GC + percorso, {
      headers: { Authorization: "Bearer " + token, "Content-Type": "application/json" },
    });
    if (!r.ok) throw new Error(percorso.split("?")[0] + ": " + r.status);
    return await r.json();
  };
  // Il totale non si chiede più a /stats/total (sul nostro GoatCounter risponde 404):
  // i visitatori sono la somma dei paesi (ogni visitatore ha un solo paese) e i clic
  // sono la somma degli eventi tra le pagine.
  const nomi = ["pagine", "provenienza", "paesi", "sistemi"];
  // una richiesta alla volta: GoatCounter limita le richieste troppo ravvicinate
  const percorsi = [
    "/stats/hits?" + periodo + "&limit=100",
    "/stats/toprefs?" + periodo + "&limit=15",
    "/stats/locations?" + periodo + "&limit=100",
    "/stats/systems?" + periodo + "&limit=10",
  ];
  const risultati: PromiseSettledResult<unknown>[] = [];
  for (const p of percorsi) {
    try {
      risultati.push({ status: "fulfilled", value: await leggi(p) });
    } catch (e) {
      risultati.push({ status: "rejected", reason: e });
    }
    await new Promise((r) => setTimeout(r, 300));
  }
  const out: Record<string, unknown> = { configurato: true, giorni, errori: [] as string[] };
  risultati.forEach((r, i) => {
    if (r.status === "fulfilled") out[nomi[i]] = r.value;
    else (out.errori as string[]).push(String(r.reason));
  });
  // deno-lint-ignore no-explicit-any
  const somma = (lista: any[] | undefined, filtro: (x: any) => boolean = () => true) =>
    (lista ?? []).filter(filtro).reduce((t, x) => t + (Number(x.count) || 0), 0);
  // deno-lint-ignore no-explicit-any
  const pagine = out.pagine as any, paesi = out.paesi as any;
  out.totale = {
    total: somma(paesi?.stats),
    total_events: somma(pagine?.hits, (h) => h.event === true),
  };
  if (pagine?.hits) pagine.hits = pagine.hits.slice(0, 30);
  if (paesi?.stats) paesi.stats = paesi.stats.slice(0, 15);
  return risposta(200, out);
});
