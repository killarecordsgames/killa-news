/* KILLA VAULT: accesso, richiesta d'ingresso, tessera e Killa Radio */
(function () {
  "use strict";
  var client = window.supabase.createClient(window.KILLA_SUPABASE_URL, window.KILLA_SUPABASE_KEY);
  var FUNZ = window.KILLA_SUPABASE_URL + "/functions/v1/killa-vault";
  var $ = function (id) { return document.getElementById(id); };

  async function chiama(dati) {
    var h = { "Content-Type": "application/json", apikey: window.KILLA_SUPABASE_KEY };
    var s = (await client.auth.getSession()).data.session;
    if (s) h.Authorization = "Bearer " + s.access_token;
    var r = await fetch(FUNZ, { method: "POST", headers: h, body: JSON.stringify(dati) });
    var j = {};
    try { j = await r.json(); } catch (e) { /* risposta vuota */ }
    j._stato = r.status;
    return j;
  }
  function mostra(id) {
    ["v-caricamento", "v-fuori", "v-dentro", "v-nuova"].forEach(function (x) { $(x).hidden = x !== id; });
  }

  // ---------- chi non è dentro ----------
  $("f-richiesta").addEventListener("submit", async function (e) {
    e.preventDefault();
    var esito = $("r-esito");
    if (!$("r-privacy").checked) { esito.textContent = "Per chiedere di entrare devi spuntare la casella dell'informativa privacy."; $("r-privacy").focus(); return; }
    esito.textContent = "Invio la richiesta…";
    var j = await chiama({ azione: "richiesta", nickname: $("r-nick").value, email: $("r-email").value, privacy: true, sito: $("r-sito").value });
    esito.textContent = j.messaggio || j.errore || "Richiesta inviata.";
    if (j.ok) this.reset();
  });

  $("f-accesso").addEventListener("submit", async function (e) {
    e.preventDefault();
    var esito = $("a-esito");
    esito.textContent = "Entro…";
    var r = await client.auth.signInWithPassword({ email: $("a-email").value.trim(), password: $("a-pass").value });
    if (r.error) { esito.textContent = "Email o password non corrette."; return; }
    esito.textContent = "";
    avvia();
  });

  $("a-dimenticata").addEventListener("click", async function () {
    var email = $("a-email").value.trim();
    var esito = $("a-esito");
    if (!email) { esito.textContent = "Scrivi prima la tua email nel campo Email, poi premi di nuovo questo pulsante."; $("a-email").focus(); return; }
    await client.auth.resetPasswordForEmail(email, { redirectTo: location.origin + "/vault" });
    esito.textContent = "Se l'email è iscritta, ti abbiamo mandato un link per scegliere una nuova password.";
  });

  client.auth.onAuthStateChange(function (evento) {
    if (evento === "PASSWORD_RECOVERY") { mostra("v-nuova"); $("n-pass").focus(); }
  });
  $("f-nuova").addEventListener("submit", async function (e) {
    e.preventDefault();
    var p = $("n-pass").value;
    if (p.length < 8) { $("n-esito").textContent = "La password deve avere almeno 8 caratteri."; return; }
    var r = await client.auth.updateUser({ password: p });
    $("n-esito").textContent = r.error ? "Non riesco a salvare la password. Riprova." : "Password salvata!";
    if (!r.error) setTimeout(avvia, 1200);
  });

  $("v-esci").addEventListener("click", async function () {
    ferma();
    await client.auth.signOut();
    location.reload();
  });

  // ---------- Killa Radio ----------
  var audio = $("v-audio"), palinsesto = null, giornale = null, accesa = false, inDiretta = false, attuale = null;

  function rng(seme) { // generatore pseudocasuale con seme: stessa sequenza per tutti nello stesso giorno
    return function () {
      seme |= 0; seme = seme + 0x6D2B79F5 | 0;
      var t = Math.imul(seme ^ seme >>> 15, 1 | seme);
      t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t;
      return ((t ^ t >>> 14) >>> 0) / 4294967296;
    };
  }
  function scaletta(giorno) {
    var r = rng(giorno * 7919), seq = [], tot = 0, blocco = 0, P = palinsesto;
    while (tot < 86400 + 600) {
      var j = P.jingle[blocco % 2 === 0 ? 0 : 2];
      if (giornale && blocco % 6 === 0) { j = P.jingle[1]; }
      seq.push({ titolo: j.titolo, url: P.base + j.file, durata: j.durata }); tot += j.durata;
      if (giornale && blocco % 6 === 0) {
        seq.push({ titolo: giornale.titolo, url: giornale.url, durata: giornale.durata }); tot += giornale.durata;
      }
      if (P.spot && P.spot.length && blocco % 2 === 1) {
        var sp = P.spot[Math.floor(blocco / 2) % P.spot.length];
        seq.push({ titolo: sp.titolo, url: P.base + sp.file, durata: sp.durata }); tot += sp.durata;
      }
      var brani = P.brani.slice();
      for (var i = brani.length - 1; i > 0; i--) { var k = Math.floor(r() * (i + 1)); var x = brani[i]; brani[i] = brani[k]; brani[k] = x; }
      brani.slice(0, 4).forEach(function (b) { seq.push({ titolo: b.titolo + ", " + b.artista, url: P.base + b.file, durata: b.durata }); tot += b.durata; });
      blocco++;
    }
    return seq;
  }
  function cosaSuona() {
    var ora = Date.now() / 1000, giorno = Math.floor(ora / 86400), t = ora - giorno * 86400;
    var seq = scaletta(giorno), inizio = 0;
    for (var i = 0; i < seq.length; i++) {
      if (t < inizio + seq[i].durata) return { voce: seq[i], offset: t - inizio };
      inizio += seq[i].durata;
    }
    return { voce: seq[0], offset: 0 };
  }
  async function caricaPalinsesto(url) {
    palinsesto = await (await fetch(url + "?t=" + Math.floor(Date.now() / 600000))).json();
    try {
      var g = await (await fetch(palinsesto.giornale + "?t=" + Math.floor(Date.now() / 600000))).json();
      giornale = { titolo: g.titolo, url: palinsesto.giornale.replace(/ultima\.json$/, "") + g.file, durata: g.durata };
    } catch (e) { giornale = null; }
  }
  function sintonizza() {
    if (!accesa || inDiretta || !palinsesto) return;
    var c = cosaSuona();
    attuale = c.voce;
    $("v-in-onda").textContent = c.voce.titolo;
    if (audio.src !== c.voce.url) { audio.preload = "auto"; audio.src = c.voce.url; audio.load(); }
    var parti = function () {
      try { audio.currentTime = Math.max(0, c.offset - 0.5); } catch (e) { /* alcuni browser non lo permettono subito */ }
      audio.play().catch(function () { /* il browser vuole un clic */ });
    };
    if (audio.readyState >= 1) parti(); else audio.addEventListener("loadedmetadata", parti, { once: true });
  }
  function ferma() { audio.pause(); }
  audio.addEventListener("ended", function () { setTimeout(sintonizza, 200); });
  audio.addEventListener("error", function () { setTimeout(sintonizza, 3000); });
  $("v-play").addEventListener("click", function () {
    accesa = !accesa;
    this.setAttribute("aria-pressed", accesa ? "true" : "false");
    this.textContent = accesa ? "Ferma Killa Radio" : "Ascolta Killa Radio";
    if (accesa) sintonizza(); else { ferma(); $("v-in-onda").textContent = "radio ferma"; }
  });
  $("v-volume").addEventListener("input", function () { audio.volume = this.value / 100; });

  function aggiornaDiretta(d) {
    var box = $("v-diretta");
    if (d && d.in_diretta && d.link_diretta) {
      if (!inDiretta) {
        inDiretta = true;
        ferma();
        box.innerHTML = "";
        var p = document.createElement("p");
        p.innerHTML = "<strong>🔴 Killa è in diretta adesso!</strong> " ;
        p.appendChild(document.createTextNode(d.titolo_diretta ? d.titolo_diretta + ". " : ""));
        p.appendChild(document.createTextNode("La musica della radio è in pausa."));
        var a = document.createElement("a");
        a.href = d.link_diretta; a.target = "_blank"; a.rel = "noopener";
        a.textContent = "Entra nella diretta su Telegram";
        box.appendChild(p); box.appendChild(a);
        box.hidden = false;
        $("v-in-onda").textContent = "diretta su Telegram";
      }
    } else if (inDiretta) {
      inDiretta = false;
      box.hidden = true; box.innerHTML = "";
      sintonizza();
    }
  }

  // ---------- avvio ----------
  async function avvia() {
    var s = (await client.auth.getSession()).data.session;
    if (!s) { mostra("v-fuori"); return; }
    var j = await chiama({ azione: "io" });
    if (j._stato !== 200) {
      mostra("v-fuori");
      $("a-esito").textContent = j.errore || "Accesso non riuscito.";
      return;
    }
    $("v-tessera").textContent = j.membro.tessera
      ? "Ciao " + j.membro.nickname + "! Tessera Killa Family numero " + String(j.membro.tessera).padStart(3, "0")
      : "Ciao " + j.membro.nickname + "! Sei l'amministratore del Vault.";
    $("v-admin").hidden = !j.admin;
    mostra("v-dentro");
    await caricaPalinsesto(j.radio);
    aggiornaDiretta(j.diretta);
    setInterval(async function () {
      var k = await chiama({ azione: "io" });
      if (k._stato === 200) aggiornaDiretta(k.diretta);
    }, 30000);
    setInterval(function () { if (palinsesto) caricaPalinsesto(j.radio); }, 3600000);
  }
  if (!/type=recovery/.test(location.hash)) avvia();
})();
