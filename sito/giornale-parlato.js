/* Il giornale parlato di KILLA NEWS: ultima puntata e archivio */
(function () {
  "use strict";
  var BASE = "https://killarecordsgames.github.io/killa-news/podcast/";
  var MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
  function el(tag, testo) { var e = document.createElement(tag); if (testo !== undefined) e.textContent = testo; return e; }
  function minuti(s) { var m = Math.round(s / 60); return m <= 1 ? "1 minuto" : m + " minuti"; }
  function data(iso) { var p = iso.split("-"); return +p[2] + " " + MESI[+p[1] - 1] + " " + p[0]; }

  fetch(BASE + "episodi.json?t=" + Date.now()).then(function (r) { return r.json(); }).then(function (ep) {
    var box = document.getElementById("gp-ultima"); box.textContent = "";
    if (!ep.length) { box.appendChild(el("p", "La prima puntata arriva domani mattina.")); return; }
    var u = ep[0];
    box.appendChild(el("h3", u.titolo + " (" + minuti(u.durata) + ")"));
    var a = el("audio"); a.controls = true; a.preload = "none"; a.src = BASE + u.file;
    a.setAttribute("aria-label", "Ascolta " + u.titolo);
    box.appendChild(a);
    var dl = el("p"); var link = el("a", "Scarica la puntata (MP3)"); link.href = BASE + u.file; link.setAttribute("download", u.file);
    dl.appendChild(link); box.appendChild(dl);
    if (u.scaletta) {
      box.appendChild(el("h3", "I titoli di questa puntata"));
      u.scaletta.forEach(function (s) {
        box.appendChild(el("h4", s[0]));
        var ul = el("ul"); s[1].forEach(function (t) { ul.appendChild(el("li", t)); }); box.appendChild(ul);
      });
    }
    var arc = document.getElementById("gp-archivio"); arc.textContent = "";
    var vecchie = ep.slice(1, 15);
    if (!vecchie.length) { arc.appendChild(el("p", "Ancora nessuna puntata precedente.")); return; }
    var ul = el("ul"); ul.className = "gp-lista";
    vecchie.forEach(function (e) {
      var li = el("li"); var l = el("a", "Giornale parlato del " + data(e.data)); l.href = BASE + e.file;
      li.appendChild(l); li.appendChild(document.createTextNode(" (" + minuti(e.durata) + ", MP3)")); ul.appendChild(li);
    });
    arc.appendChild(ul);
  }).catch(function () {
    document.getElementById("gp-ultima").textContent = "Non è stato possibile caricare la puntata. Riprova più tardi.";
    document.getElementById("gp-archivio").textContent = "";
  });
})();
