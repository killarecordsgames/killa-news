// Statistiche anonime di KILLA NEWS.
// Il programma invia: un identificativo casuale dell'installazione (non legato a nessuna persona),
// la versione, il tipo (installata/portatile) e quante volte sono state aperte le sezioni.
// Non vengono salvati indirizzi IP, nomi, email o contenuti letti.
import { createClient } from "jsr:@supabase/supabase-js@2";

const SEZIONI = new Set([
  "prima_pagina", "tutti_i_giornali", "italia", "cronaca", "economia", "sport", "tecnologia", "cultura",
  "salute", "giornali_locali", "giornali_internazionali", "notizie_dal_mondo", "articoli_salvati",
  "cronologia", "cerca", "killa_records", "articoli_letti", "traduzioni", "condivisioni", "voce_nvda",
]);
const TIPI = new Set(["installata", "eseguibile", "sorgente"]);
const CORS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "content-type",
  "Access-Control-Allow-Methods": "POST, OPTIONS",
};

function risposta(stato: number, dati: unknown) {
  return new Response(JSON.stringify(dati), { status: stato, headers: { ...CORS, "Content-Type": "application/json" } });
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") return new Response("ok", { headers: CORS });
  if (req.method !== "POST") return risposta(405, { errore: "Usa POST" });
  let b: Record<string, unknown>;
  try {
    const testo = await req.text();
    if (testo.length > 4000) return risposta(413, { errore: "Richiesta troppo grande" });
    b = JSON.parse(testo);
  } catch {
    return risposta(400, { errore: "JSON non valido" });
  }
  const id = String(b.installazione ?? "");
  const versione = String(b.versione ?? "");
  const tipo = String(b.tipo ?? "");
  if (!/^[0-9a-f]{32}$/.test(id)) return risposta(400, { errore: "Identificativo non valido" });
  if (!/^\d{1,3}\.\d{1,3}\.\d{1,3}$/.test(versione)) return risposta(400, { errore: "Versione non valida" });
  if (!TIPI.has(tipo)) return risposta(400, { errore: "Tipo non valido" });
  const num = (v: unknown) => Math.max(0, Math.min(10000, Math.floor(Number(v) || 0)));
  const sezioni: Record<string, number> = {};
  const ingresso = (b.sezioni && typeof b.sezioni === "object") ? b.sezioni as Record<string, unknown> : {};
  for (const [k, v] of Object.entries(ingresso)) {
    if (SEZIONI.has(k) && num(v) > 0) sezioni[k] = num(v);
  }
  const db = createClient(Deno.env.get("SUPABASE_URL")!, Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!, {
    auth: { persistSession: false },
  });
  const { error } = await db.rpc("killa_news_registra", {
    p_inst: id, p_versione: versione, p_tipo: tipo, p_sezioni: sezioni, p_aperture: num(b.aperture),
  });
  if (error) {
    console.error("Errore nel salvataggio delle statistiche", error.message);
    return risposta(500, { errore: "Salvataggio non riuscito" });
  }
  return risposta(200, { ok: true });
});
