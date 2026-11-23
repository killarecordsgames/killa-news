// Prova del bot Telegram con Telegram finto e feed veri.
Deno.env.set("TELEGRAM_BOT_TOKEN", "123:prova");
// deno-lint-ignore no-explicit-any
(Deno as any).serve = () => {};
const vero = globalThis.fetch;
const inviati: unknown[] = [];
globalThis.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
  const u = String(input);
  if (u.startsWith("https://api.telegram.org/")) { inviati.push({ metodo: u.split("/").pop(), corpo: JSON.parse(String(init?.body ?? "{}")) }); return new Response("{}"); }
  return vero(input, init);
};
const { gestisci } = await import("../supabase/killa-news-telegram/index.ts");
for (const t of ["/start", "📰 Prima pagina", "⚽ Sport", "Verona", "Juventus", "🎧 Giornale parlato", "/giornale"]) {
  // deno-lint-ignore no-explicit-any
  const m: any = await gestisci({ message: { chat: { id: 1 }, text: t } });
  console.log("=== " + t + " -> " + m?.method + " (chiamate dirette a Telegram: " + inviati.length + ")");
  console.log(String(m?.text ?? m?.audio ?? "").slice(0, 600));
}
