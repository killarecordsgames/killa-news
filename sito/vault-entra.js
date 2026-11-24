/* KILLA VAULT: attivazione dell'invito con il codice personale */
(function () {
  "use strict";
  var client = window.supabase.createClient(window.KILLA_SUPABASE_URL, window.KILLA_SUPABASE_KEY);
  var FUNZ = window.KILLA_SUPABASE_URL + "/functions/v1/killa-vault";
  var $ = function (id) { return document.getElementById(id); };
  var q = new URLSearchParams(location.search);
  if (q.get("email")) $("e-email").value = q.get("email");
  if (q.get("codice")) $("e-codice").value = q.get("codice");

  $("f-entra").addEventListener("submit", async function (e) {
    e.preventDefault();
    var esito = $("e-esito");
    var email = $("e-email").value.trim(), pass = $("e-pass").value;
    if (pass !== $("e-pass2").value) { esito.textContent = "Le due password non sono uguali. Riscrivile."; $("e-pass2").focus(); return; }
    if (!$("e-privacy").checked) { esito.textContent = "Per entrare devi spuntare la casella dell'informativa."; $("e-privacy").focus(); return; }
    esito.textContent = "Controllo il codice…";
    var r = await fetch(FUNZ, {
      method: "POST",
      headers: { "Content-Type": "application/json", apikey: window.KILLA_SUPABASE_KEY },
      body: JSON.stringify({ azione: "registrati", email: email, codice: $("e-codice").value, password: pass, privacy: true, sito: $("e-sito").value }),
    });
    var j = {};
    try { j = await r.json(); } catch (x) { /* vuota */ }
    if (!j.ok) { esito.textContent = j.errore || "Qualcosa non è andato. Riprova."; return; }
    esito.textContent = "Benvenuto nella Killa Family, " + j.nickname + "! La tua tessera è la numero " + String(j.tessera || "").padStart(3, "0") + ". Ti porto nel Vault…";
    await client.auth.signInWithPassword({ email: email, password: pass });
    setTimeout(function () { location.href = "/vault"; }, 2500);
  });
})();
