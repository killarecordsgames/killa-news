/* Classifiche dei giochi Killa Records: Il Mio Bar e Global Manager */
(function () {
  "use strict";
  var URL_GIOCHI = "https://dsfzjqxbvnasxyuwyyca.supabase.co";
  var CHIAVE_PUBBLICA = "sb_publishable_9enEQSCr2Tv8Z4KK51RZXA_SkxBZw98";
  var NOMI = { bar: "Il Mio Bar", gm: "Global Manager" };
  var db = window.supabase.createClient(URL_GIOCHI, CHIAVE_PUBBLICA, {
    auth: { storageKey: "kr-classifiche-auth", persistSession: true }
  });
  var $ = function (id) { return document.getElementById(id); };
  var EN = (document.documentElement.lang || "").indexOf("en") === 0;
  var LOC = EN ? "en-GB" : "it-IT";
  var TR = {
    "Non è stato possibile caricare i vincitori. Riprova più tardi.": "The winners could not be loaded. Please try again later.",
    "La prima settimana di sfida è in corso: il primo vincitore sarà pubblicato lunedì a mezzanotte.": "The first week of the challenge is under way: the first winner will be published on Monday at midnight.",
    "Settimana dal ": "Week from ",
    " al ": " to ",
    ", con ": ", with ",
    " guadagnati in una settimana.": " earned in one week.",
    "Albo d'oro": "Hall of fame",
    "Non è stato possibile caricare la classifica. Riprova più tardi.": "The leaderboard could not be loaded. Please try again later.",
    ". Si chiude lunedì a mezzanotte.": ". It closes on Monday at midnight.",
    "Ancora nessun giocatore in classifica. Partecipa tu per primo!": "No players on the leaderboard yet. Be the first to join!",
    "Classifica della settimana di ": "This week's leaderboard for ",
    "Posizione": "Position", "Nickname": "Nickname", "Guadagnato in settimana": "Earned this week", "Totale": "Total",
    "Sei in classifica come «": "You are on the leaderboard as “",
    "». Puoi cambiare nickname qui sotto.": "”. You can change your nickname below.",
    "Cambia nickname": "Change nickname",
    "Non sei ancora in classifica. Scegli un nickname per partecipare.": "You are not on the leaderboard yet. Choose a nickname to join.",
    "Partecipa alla classifica": "Join the leaderboard",
    "Email o password non corrette.": "Wrong email or password.",
    "Prima conferma la tua email con il messaggio che ti abbiamo inviato.": "Please confirm your email first, using the message we sent you.",
    "Questo nickname è già usato da un altro giocatore. Scegline un altro.": "This nickname is already used by another player. Please choose another one.",
    "Il nickname deve avere da 3 a 20 caratteri: lettere, numeri, spazio, punto o trattino.": "The nickname must be 3 to 20 characters: letters, numbers, space, dot or hyphen.",
    "Si è verificato un errore. Riprova.": "Something went wrong. Please try again.",
    "Accesso in corso…": "Signing in…", "Accesso eseguito.": "Signed in.",
    "Il nickname deve avere almeno 3 caratteri.": "The nickname must have at least 3 characters.",
    "Salvataggio…": "Saving…",
    "Fatto! Sei in classifica come «": "Done! You are on the leaderboard as “",
    "».": "”.",
    "Vuoi davvero uscire dalla classifica? Il tuo nickname non comparirà più.": "Do you really want to leave the leaderboard? Your nickname will no longer appear.",
    "Sei uscito dalla classifica.": "You have left the leaderboard.",
    "Sei uscito dall'account.": "You have signed out.",
    "Questo nickname non è consentito. Scegline un altro.": "This nickname is not allowed. Please choose another one."
  };
  function T(s) { return EN && TR[s] ? TR[s] : s; }

  function euro(n) {
    return Math.round(Number(n) || 0).toLocaleString(LOC) + " €";
  }
  function giorno(d) {
    return new Date(d + "T12:00:00").toLocaleDateString(LOC, { day: "numeric", month: "long", year: "numeric" });
  }
  function fineSettimana(d) {
    var x = new Date(d + "T12:00:00"); x.setDate(x.getDate() + 6);
    return x.toLocaleDateString(LOC, { day: "numeric", month: "long", year: "numeric" });
  }
  function el(tag, testo) {
    var e = document.createElement(tag);
    if (testo !== undefined) e.textContent = testo;
    return e;
  }
  function messaggio(t) { $("cl-messaggio").textContent = t; }

  async function caricaVincitori() {
    var box = $("cl-vincitori");
    var r = await db.from("classifica_vincitori").select("settimana,gioco,nickname,punteggio").order("settimana", { ascending: false }).limit(40);
    box.textContent = "";
    if (r.error) { box.appendChild(el("p", T("Non è stato possibile caricare i vincitori. Riprova più tardi."))); return; }
    if (!r.data.length) {
      box.appendChild(el("p", T("La prima settimana di sfida è in corso: il primo vincitore sarà pubblicato lunedì a mezzanotte.")));
      return;
    }
    var ultima = r.data[0].settimana;
    var h = el("h3", T("Settimana dal ") + giorno(ultima) + T(" al ") + fineSettimana(ultima));
    box.appendChild(h);
    var ul = el("ul"); ul.className = "cl-vincitori";
    r.data.filter(function (v) { return v.settimana === ultima; }).forEach(function (v) {
      var li = el("li");
      li.appendChild(el("strong", NOMI[v.gioco] + ": " + v.nickname));
      li.appendChild(document.createTextNode(T(", con ") + euro(v.punteggio) + T(" guadagnati in una settimana.")));
      ul.appendChild(li);
    });
    box.appendChild(ul);
    var vecchi = r.data.filter(function (v) { return v.settimana !== ultima; });
    if (vecchi.length) {
      box.appendChild(el("h3", T("Albo d'oro")));
      var ul2 = el("ul");
      vecchi.forEach(function (v) {
        ul2.appendChild(el("li", T("Settimana dal ") + giorno(v.settimana) + ", " + NOMI[v.gioco] + ": " + v.nickname + " (" + euro(v.punteggio) + ")"));
      });
      box.appendChild(ul2);
    }
  }

  async function caricaClassifica() {
    var box = $("cl-tabelle");
    var r = await db.rpc("classifica_corrente");
    box.textContent = "";
    if (r.error) { box.appendChild(el("p", T("Non è stato possibile caricare la classifica. Riprova più tardi."))); return; }
    var sett = r.data.length ? r.data[0].settimana : null;
    if (sett) $("cl-periodo").textContent = T("Settimana dal ") + giorno(sett) + T(" al ") + fineSettimana(sett) + T(". Si chiude lunedì a mezzanotte.");
    ["bar", "gm"].forEach(function (g) {
      var righe = r.data.filter(function (x) { return x.gioco === g; });
      box.appendChild(el("h3", NOMI[g]));
      if (!righe.length) {
        box.appendChild(el("p", T("Ancora nessun giocatore in classifica. Partecipa tu per primo!")));
        return;
      }
      var t = el("table"); t.className = "cl-tabella";
      t.appendChild(el("caption", T("Classifica della settimana di ") + NOMI[g]));
      var th = el("thead"); var tr = el("tr");
      ["Posizione", "Nickname", "Guadagnato in settimana", "Totale"].forEach(function (c) {
        var x = el("th", T(c)); x.scope = "col"; tr.appendChild(x);
      });
      th.appendChild(tr); t.appendChild(th);
      var tb = el("tbody");
      righe.forEach(function (x) {
        var row = el("tr");
        var p = el("td", EN ? "#" + x.posizione : x.posizione + "°");
        var n = el("th", x.nickname); n.scope = "row";
        row.appendChild(p); row.appendChild(n);
        row.appendChild(el("td", euro(x.punteggio)));
        row.appendChild(el("td", euro(x.totale)));
        tb.appendChild(row);
      });
      t.appendChild(tb); box.appendChild(t);
    });
  }

  async function aggiornaAccount() {
    var s = await db.auth.getSession();
    var utente = s.data && s.data.session ? s.data.session.user : null;
    $("cl-accesso").hidden = !!utente;
    $("cl-nick").hidden = !utente;
    if (!utente) return;
    var r = await db.from("classifica_iscritti").select("nickname").eq("user_id", utente.id).maybeSingle();
    if (r.data) {
      $("cl-stato").textContent = T("Sei in classifica come «") + r.data.nickname + T("». Puoi cambiare nickname qui sotto.");
      $("cl-nickname").value = r.data.nickname;
      $("cl-salva").textContent = T("Cambia nickname");
      $("cl-esci-classifica").hidden = false;
    } else {
      $("cl-stato").textContent = T("Non sei ancora in classifica. Scegli un nickname per partecipare.");
      $("cl-salva").textContent = T("Partecipa alla classifica");
      $("cl-esci-classifica").hidden = true;
    }
  }

  function erroreLeggibile(e) {
    var m = (e && e.message) || "";
    if (/Invalid login/i.test(m)) return T("Email o password non corrette.");
    if (/Email not confirmed/i.test(m)) return T("Prima conferma la tua email con il messaggio che ti abbiamo inviato.");
    if (/non è consentito/.test(m)) return T("Questo nickname non è consentito. Scegline un altro.");
    if (/duplicate|unique/i.test(m)) return T("Questo nickname è già usato da un altro giocatore. Scegline un altro.");
    if (/nickname_formato|check constraint/i.test(m)) return T("Il nickname deve avere da 3 a 20 caratteri: lettere, numeri, spazio, punto o trattino.");
    return T("Si è verificato un errore. Riprova.");
  }

  $("cl-accesso").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    messaggio(T("Accesso in corso…"));
    var r = await db.auth.signInWithPassword({ email: $("cl-email").value.trim(), password: $("cl-password").value });
    $("cl-password").value = "";
    if (r.error) { messaggio(erroreLeggibile(r.error)); $("cl-email").focus(); return; }
    messaggio(T("Accesso eseguito."));
    await aggiornaAccount();
    $("cl-nickname").focus();
  });

  $("cl-nick").addEventListener("submit", async function (ev) {
    ev.preventDefault();
    var nick = $("cl-nickname").value.trim().replace(/\s+/g, " ");
    if (nick.length < 3) { messaggio(T("Il nickname deve avere almeno 3 caratteri.")); $("cl-nickname").focus(); return; }
    var s = await db.auth.getSession();
    var id = s.data.session.user.id;
    messaggio(T("Salvataggio…"));
    var r = await db.from("classifica_iscritti").upsert({ user_id: id, nickname: nick }, { onConflict: "user_id" });
    if (r.error) { messaggio(erroreLeggibile(r.error)); $("cl-nickname").focus(); return; }
    messaggio(T("Fatto! Sei in classifica come «") + nick + T("»."));
    await aggiornaAccount();
    caricaClassifica();
  });

  $("cl-esci-classifica").addEventListener("click", async function () {
    if (!window.confirm(T("Vuoi davvero uscire dalla classifica? Il tuo nickname non comparirà più."))) return;
    var s = await db.auth.getSession();
    var r = await db.from("classifica_iscritti").delete().eq("user_id", s.data.session.user.id);
    if (r.error) { messaggio(erroreLeggibile(r.error)); return; }
    $("cl-nickname").value = "";
    messaggio(T("Sei uscito dalla classifica."));
    await aggiornaAccount();
    caricaClassifica();
  });

  $("cl-logout").addEventListener("click", async function () {
    await db.auth.signOut();
    messaggio(T("Sei uscito dall'account."));
    await aggiornaAccount();
    $("cl-email").focus();
  });

  caricaVincitori();
  caricaClassifica();
  aggiornaAccount();
})();
