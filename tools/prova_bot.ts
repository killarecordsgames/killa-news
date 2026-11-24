// Prova del bot Telegram con Telegram finto e feed veri.
Deno.env.set("TELEGRAM_BOT_TOKEN", "1234567890:AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA");
Deno.env.set("SUPABASE_URL", "https://sb.test");
Deno.env.set("SUPABASE_SERVICE_ROLE_KEY", "chiave-di-prova-lunga-abbastanza");
const consensi = new Set<string>();
// deno-lint-ignore no-explicit-any
(Deno as any).serve = () => {};
const vero = globalThis.fetch;
const inviati: unknown[] = [];
globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const u = String(input);
  if (u.startsWith("https://sb.test/")) {
    const m = u.match(/codice=eq\.([0-9a-f]+)/);
    if (init?.method === "POST") { consensi.add(JSON.parse(String(init.body)).codice); return new Response(""); }
    if (init?.method === "DELETE") { if (m) consensi.delete(m[1]); return new Response(""); }
    return new Response(JSON.stringify(m && consensi.has(m[1]) ? [{ codice: m[1] }] : []));
  }
  if (u.startsWith("https://api.telegram.org/")) { inviati.push({ metodo: u.split("/").pop(), corpo: JSON.parse(String(init?.body ?? "{}")) }); return new Response("{}"); }
  return vero(input, init);
};
const { gestisci } = await import("../supabase/killa-news-telegram/index.ts");
for (const t of ["/start", "✅ Accetto l'informativa", "/start", "📰 Prima pagina", "⚽ Sport", "Verona", "Juventus", "🎧 Giornale parlato", "/giornale"]) {
  // deno-lint-ignore no-explicit-any
  const m: any = await gestisci({ message: { chat: { id: 1 }, from: { id: 1 }, text: t } });
  console.log("=== " + t + " -> " + m?.method + " (chiamate dirette a Telegram: " + inviati.length + ")");
  console.log(String(m?.text ?? m?.audio ?? "").slice(0, 600));
}

// deno-lint-ignore no-explicit-any
const r: any = await gestisci({ message: { chat: { id: 1 }, from: { id: 1 }, text: "/revoca" } });
console.log("=== /revoca -> " + r.text);
// deno-lint-ignore no-explicit-any
const r2: any = await gestisci({ message: { chat: { id: 1 }, from: { id: 1 }, text: "Sport" } });
console.log("=== dopo revoca, Sport -> " + String(r2.text).slice(0, 60));
