/* KILLA VAULT: gestione delle richieste, degli inviti e della diretta (solo amministratore) */
(function () {
  "use strict";
  var client = window.supabase.createClient(window.KILLA_SUPABASE_URL, window.KILLA_SUPABASE_KEY);
  var FUNZ = window.KILLA_SUPABASE_URL + "/functions/v1/killa-vault";
  var $ = function (id) { return document.getElementById(id); };
  var STATI = { in_attesa: "in attesa", invitato: "invito mandato", iscritto: "entrato", rifiutato: "rifiutata" };

  async function chiama(dati) {
    var s = (await client.auth.getSession()).data.session;
    var r = await fetch(FUNZ, {
      method: "POST",
      headers: { "Content-Type": "application/json", apikey: window.KILLA_SUPABASE_KEY, Authorization: "Bearer " + (s ? s.access_token : "") },
      body: JSON.stringify(dati),
    });
    var j = {};
    try { j = await r.json(); } catch (e) { /* vuota */ }
    j._stato = r.status;
    return j;
  }
  function data(d) { return d ? new Date(d).toLocaleString("it-IT", { dateStyle: "short", timeStyle: "short" }) : ""; }
  function el(tag, testo) { var e = document.createElement(tag); if (testo !== undefined) e.textContent = testo; return e; }

  async function carica() {
    var j = await chiama({ azione: "lista" });
    if (j._stato !== 200) {
      $("g-stato").textContent = j._stato === 403 ? "Questa pagina è solo per l'amministratore. Entra prima dalla pagina Gestione notizie." : (j.errore || "Errore.");
      return;
    }
    $("g-stato").textContent = "";
    $("g-pannello").hidden = false;

    var d = j.diretta || {};
    $("g-dir-ora").textContent = d.in_diretta ? "Adesso sei IN DIRETTA: " + (d.titolo_diretta || "") + " " + d.link_diretta : "Adesso la radio suona la musica automatica.";
    if (d.link_diretta) $("g-link").value = d.link_diretta;

    mostraRadio(j.radio);

    var box = $("g-richieste"); box.innerHTML = "";
    var aperte = (j.richieste || []).filter(function (r) { return r.stato !== "iscritto"; });
    if (!aperte.length) box.appendChild(el("p", "Nessuna richiesta in attesa."));
    var ul = el("ul");
    aperte.forEach(function (r) {
      var li = el("li");
      li.appendChild(el("strong", r.nickname));
      li.appendChild(document.createTextNode(", " + r.email + ", " + STATI[r.stato] + ", richiesta del " + data(r.creata_il) + (r.stato === "invitato" ? ", codice valido fino al " + data(r.codice_scade) : "") + ". "));
      var inv = el("button", r.stato === "invitato" ? "Manda un nuovo codice a " + r.nickname : "Invita " + r.nickname);
      inv.type = "button";
      inv.addEventListener("click", async function () {
        inv.disabled = true;
        var k = await chiama({ azione: "invita", id: r.id });
        $("g-ric-esito").textContent = k.messaggio || k.errore;
        carica();
      });
      var rif = el("button", "Rifiuta e cancella " + r.nickname);
      rif.type = "button"; rif.className = "v-link";
      rif.addEventListener("click", async function () {
        if (!window.confirm("Cancellare la richiesta di " + r.nickname + "?")) return;
        var k = await chiama({ azione: "rifiuta", id: r.id });
        $("g-ric-esito").textContent = k.messaggio || k.errore;
        carica();
      });
      li.appendChild(inv); li.appendChild(rif);
      ul.appendChild(li);
    });
    box.appendChild(ul);

    var mbox = $("g-membri"); mbox.innerHTML = "";
    var membri = j.membri || [];
    mbox.appendChild(el("p", membri.length ? "Membri: " + membri.length : "Ancora nessun membro."));
    var ol = el("ul");
    membri.forEach(function (m) { ol.appendChild(el("li", "Tessera " + String(m.tessera).padStart(3, "0") + ": " + m.nickname + ", entrato il " + data(m.entrato_il))); });
    mbox.appendChild(ol);
  }

  // ---------- ascoltatori della Killa Radio ----------
  function mostraRadio(r) {
    var sez = $("g-radio");
    if (!sez) {
      sez = document.createElement("section");
      sez.className = "v-box"; sez.id = "g-radio"; sez.setAttribute("aria-labelledby", "g-radio-t");
      var h = el("h2", "Ascoltatori della Killa Radio"); h.id = "g-radio-t";
      var ora = el("p"); ora.id = "g-radio-ora"; ora.setAttribute("role", "status"); ora.setAttribute("aria-live", "polite");
      var giorni = el("div"); giorni.id = "g-radio-giorni";
      sez.appendChild(h); sez.appendChild(ora); sez.appendChild(giorni);
      var dopo = $("g-ric-t") ? $("g-ric-t").closest("section") : null;
      $("g-pannello").insertBefore(sez, dopo);
    }
    if (!r) { $("g-radio-ora").textContent = "Il contatore non è ancora attivo."; return; }
    $("g-radio-ora").textContent = "In ascolto adesso: " + r.ora + (r.ora === 1 ? " persona." : " persone.");
    var box = $("g-radio-giorni"); box.innerHTML = "";
    var lista = r.giorni || [];
    if (!lista.length) { box.appendChild(el("p", "Ancora nessun ascolto registrato negli ultimi 7 giorni.")); return; }
    var ul = el("ul");
    lista.forEach(function (g) {
      var giorno = new Date(g.giorno + "T12:00:00").toLocaleDateString("it-IT", { weekday: "long", day: "numeric", month: "long" });
      var ore = Math.floor(g.minuti / 60), min = g.minuti % 60;
      ul.appendChild(el("li", giorno + ": " + g.persone + (g.persone === 1 ? " ascoltatore" : " ascoltatori") +
        ", picco di " + g.picco + " insieme alle " + g.ora_picco + ", " + (ore ? ore + " ore e " : "") + min + " minuti di ascolto in tutto."));
    });
    box.appendChild(ul);
  }
  setInterval(async function () {
    if ($("g-pannello").hidden) return;
    var j = await chiama({ azione: "lista" });
    if (j._stato === 200) mostraRadio(j.radio);
  }, 60000);

  $("f-diretta").addEventListener("submit", async function (e) {
    e.preventDefault();
    var k = await chiama({ azione: "diretta", attiva: true, link: $("g-link").value, titolo: $("g-titolo").value });
    $("g-dir-esito").textContent = k.messaggio || k.errore;
    carica();
  });
  $("g-chiudi").addEventListener("click", async function () {
    var k = await chiama({ azione: "diretta", attiva: false });
    $("g-dir-esito").textContent = k.messaggio || k.errore;
    carica();
  });

  (async function () {
    var s = (await client.auth.getSession()).data.session;
    if (!s) { $("g-stato").innerHTML = 'Devi prima entrare come amministratore dalla pagina <a href="/admin">Gestione notizie</a>.'; return; }
    carica();
  })();
})();
