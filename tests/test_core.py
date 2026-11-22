"""Test automatici del nucleo di KILLA NEWS (senza interfaccia grafica).

Esecuzione:  python -m unittest discover -s tests -v
Usano un server HTTP locale con feed di prova: non serve Internet."""
import datetime
import http.server
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import threading
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

TMP = tempfile.mkdtemp(prefix="killanews_test_")
os.environ["KILLANEWS_DATA_DIR"] = TMP

from killanews import article_reader, config, database, feed_manager  # noqa: E402
from killanews.core import Core  # noqa: E402
from killanews.keyboard_manager import KeyboardManager, ShortcutError, normalize  # noqa: E402
from killanews.news_manager import parse_italian_date  # noqa: E402
from killanews.speech_manager import FakeBackend, SpeechManager, STATE_PAUSED, STATE_SPEAKING, STATE_STOPPED  # noqa: E402


def rfc822(dt):
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")


NOW = datetime.datetime.now(datetime.timezone.utc)

RSS = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<title>Giornale di Prova</title><link>http://localhost/</link><description>prova</description>
<item><title>Verona, nuovo parcheggio in centro</title><link>http://localhost/a1?utm_source=rss</link>
<guid>a1</guid><pubDate>{rfc822(NOW - datetime.timedelta(minutes=30))}</pubDate>
<description>&lt;p&gt;Il consiglio comunale di Verona ha approvato il progetto.&lt;/p&gt;</description></item>
<item><title>La Juventus vince in Champions League</title><link>http://localhost/a2</link>
<guid>a2</guid><pubDate>{rfc822(NOW - datetime.timedelta(hours=2))}</pubDate>
<description>Partita decisa nel secondo tempo.</description></item>
<item><title>Articolo con testo completo nel feed</title><link>http://localhost/a3</link>
<guid>a3</guid><pubDate>{rfc822(NOW - datetime.timedelta(hours=5))}</pubDate>
<description>Breve sommario.</description>
<content:encoded><![CDATA[{"<p>" + "Paragrafo di prova completo. " * 30 + "</p>" + "<p>" + "Secondo paragrafo. " * 40 + "</p>"}]]></content:encoded></item>
<item><title>Notizia vecchia</title><link>http://localhost/old</link><guid>old</guid>
<pubDate>{rfc822(NOW - datetime.timedelta(days=90))}</pubDate><description>vecchia</description></item>
</channel></rss>"""

RSS_DUP = RSS.replace("<guid>a1</guid>", "<guid>a1-bis</guid>").replace("?utm_source=rss", "?utm_medium=x")

ATOM = f"""<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom"><title>Atom di prova</title>
<entry><title>Borsa di Milano in rialzo</title><link href="http://localhost/b1"/><id>b1</id>
<updated>{NOW.strftime('%Y-%m-%dT%H:%M:%SZ')}</updated><summary>Piazza Affari chiude positiva.</summary>
<author><name>Mario Rossi</name></author></entry></feed>"""

LONG_BODY = " ".join(["Questo è il testo integrale dell'articolo pubblicato sulla pagina."] * 25)
ARTICLE_PAGE = f"""<html><head><title>Articolo</title>
<meta property="og:description" content="Sottotitolo dalla pagina">
<script type="application/ld+json">{json.dumps({"@context": "https://schema.org", "@type": "NewsArticle",
 "headline": "Verona", "articleBody": LONG_BODY, "author": {"@type": "Person", "name": "Giulia Bianchi"},
 "isAccessibleForFree": True})}</script></head><body><article><p>{LONG_BODY}</p></article></body></html>"""

PAYWALL_PAGE = """<html><head><script type="application/ld+json">{"@type":"NewsArticle","isAccessibleForFree":false,
"articleBody":"segreto"}</script></head><body><p>Abbonati per leggere.</p></body></html>"""

SITE_PAGE = """<html><head><link rel="alternate" type="application/rss+xml" title="Feed ufficiale" href="/rss.xml">
<link rel="alternate" type="application/rss+xml" title="Rotto" href="/rotto.xml"></head><body>Sito</body></html>"""


class Handler(http.server.BaseHTTPRequestHandler):
    routes = {}

    def log_message(self, *args):
        pass

    def do_GET(self):
        path = self.path.split("?")[0]
        if path == "/rss.xml" and self.headers.get("If-None-Match") == '"v1"':
            self.send_response(304)
            self.end_headers()
            return
        if path not in self.routes:
            self.send_response(404)
            self.end_headers()
            return
        body, ctype = self.routes[path]
        data = body.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        if path == "/rss.xml":
            self.send_header("ETag", '"v1"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class ServerMixin:
    @classmethod
    def start_server(cls):
        Handler.routes = {
            "/rss.xml": (RSS, "application/rss+xml"),
            "/dup.xml": (RSS_DUP, "application/rss+xml"),
            "/atom.xml": (ATOM, "application/atom+xml"),
            # i collegamenti dei feed puntano a "http://localhost": sostituiti con l'indirizzo reale qui sotto
            "/a1": (ARTICLE_PAGE, "text/html; charset=utf-8"),
            "/paywall": (PAYWALL_PAGE, "text/html; charset=utf-8"),
            "/sito": (SITE_PAGE, "text/html; charset=utf-8"),
            "/nonfeed.xml": ("<html>non sono un feed</html>", "text/html"),
        }
        cls.httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.port = cls.httpd.server_address[1]
        cls.base = f"http://127.0.0.1:{cls.port}"
        for key, (body, ctype) in list(Handler.routes.items()):
            Handler.routes[key] = (body.replace("http://localhost", cls.base), ctype)
        threading.Thread(target=cls.httpd.serve_forever, daemon=True).start()

    @classmethod
    def stop_server(cls):
        cls.httpd.shutdown()
        cls.httpd.server_close()


def new_core(name):
    path = os.path.join(TMP, name + ".db")
    for suffix in ("", "-wal", "-shm"):
        if os.path.exists(path + suffix):
            os.remove(path + suffix)
    return Core(db_path=path, speech_backend=FakeBackend())


def add_local_source(core, base, feeds, name="Giornale di Prova", region="Veneto", city="Verona"):
    for s in core.catalog.sources():
        core.catalog.set_source_enabled(s["id"], False)
    return core.catalog.save_source(
        {"name": name, "country": "Italia", "region": region, "province": "Verona", "city": city,
         "group_name": "Locali", "site_url": base + "/sito", "fulltext_allowed": True},
        feeds=[{"url": base + path, "category_id": cat, "is_main": True} for path, cat in feeds])


class TestDatabaseCatalog(unittest.TestCase):
    def test_schema_and_catalog(self):
        core = new_core("schema")
        self.assertEqual(core.db.schema_version(), config.DB_SCHEMA_VERSION)
        for table in ("sources", "categories", "articles", "favorites", "history", "folders",
                      "settings", "downloads", "feeds"):
            self.assertTrue(core.db._has_table(table), table)
        with open(config.data_file("sources.json"), encoding="utf-8") as fh:
            catalog = json.load(fh)
        self.assertEqual(len(core.catalog.sources()), len(catalog["fonti"]))
        n_feeds = sum(len(s["feed"]) for s in catalog["fonti"])
        self.assertEqual(len(core.catalog.feeds()), n_feeds)
        for f in core.catalog.feeds():
            self.assertTrue(f["url"].startswith("http"))
            self.assertIn(f["verification"], ("feeder", "feedspot", "github-actions 22/11/2026"))
            self.assertIsNotNone(core.db.query_one("SELECT 1 FROM categories WHERE id = ?", (f["category_id"],)),
                                 f"categoria inesistente {f['category_id']}")
        tree = core.catalog.categories_tree()
        self.assertEqual([t["name"] for t, _ in tree][:2], ["Italia", "Notizie dal mondo"])
        self.assertIn("Veneto", core.catalog.local_tree())
        # nuova apertura: il catalogo non viene duplicato
        core.db.close()
        core2 = Core(db_path=core.db.path, speech_backend=FakeBackend())
        self.assertEqual(len(core2.catalog.sources()), len(catalog["fonti"]))
        core2.db.close()

    def test_add_remove_sources(self):
        core = new_core("sources")
        before = len(core.catalog.sources())
        sid = core.catalog.save_source({"name": "Testata Nuova", "region": "Sicilia", "province": "Palermo",
                                        "city": "Palermo", "site_url": "https://example.org"},
                                       feeds=[{"url": "https://example.org/rss", "category_id": "cronaca"}])
        self.assertEqual(len(core.catalog.sources()), before + 1)
        self.assertIn("Sicilia", core.catalog.local_tree())
        with self.assertRaises(Exception):
            core.catalog.save_source({"name": ""})
        with self.assertRaises(Exception):
            core.catalog.save_source({"name": "x"}, feeds=[{"url": "ftp://bad"}])
        core.catalog.delete_source(sid)
        self.assertEqual(len(core.catalog.sources()), before)
        ansa = core.db.query_one("SELECT id FROM sources WHERE key = 'ansa'")["id"]
        core.catalog.delete_source(ansa)   # fonte del catalogo: nascosta, non reinserita
        core.catalog.load_sources()
        self.assertEqual(len(core.catalog.sources()), before - 1)
        core.catalog.restore_catalog()
        self.assertEqual(len(core.catalog.sources()), before)

    def test_backup(self):
        core = new_core("backup")
        path = database.backup_database(core.db)
        self.assertTrue(os.path.exists(path))
        conn = sqlite3.connect(path)
        self.assertGreater(conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0], 10)
        conn.close()
        self.assertIn(path, database.list_backups())

    def test_classify(self):
        core = new_core("classify")
        cats = core.catalog.classify("sport", "La Juventus vince in Champions League", "")
        self.assertIn("sport/champions", cats)
        self.assertIn("sport/serie_a", cats)
        self.assertNotIn("esteri/europa", cats)
        self.assertEqual(core.catalog.classify("generale", "Francia", ""), {"generale"})


class TestFeedsAndArticles(ServerMixin, unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.start_server()

    @classmethod
    def tearDownClass(cls):
        cls.stop_server()

    def test_fetch_store_dedup(self):
        core = new_core("fetch")
        sid = add_local_source(core, self.base, [("/rss.xml", "italia"), ("/dup.xml", "sport"),
                                                 ("/atom.xml", "economia")])
        feeds = core.catalog.feeds(sid)
        total = 0
        for f in feeds:
            result = feed_manager.fetch_feed(f)
            self.assertTrue(result.ok, result.error)
            total += feed_manager.store_result(core.db, core.catalog, result)
        # 4 dal primo feed + 1 Atom; il secondo feed contiene gli stessi articoli (link normalizzati)
        self.assertEqual(total, 5)
        self.assertEqual(core.db.query_one("SELECT COUNT(*) FROM articles")[0], 5)
        # secondo giro: nessun duplicato; il feed principale risponde 304
        again = 0
        for f in core.catalog.feeds(sid):
            r = feed_manager.fetch_feed(f)
            if f["url"].endswith("/rss.xml"):
                self.assertTrue(r.not_modified)
            again += feed_manager.store_result(core.db, core.catalog, r)
        self.assertEqual(again, 0)
        art = core.db.query_one("SELECT * FROM articles WHERE title LIKE 'Articolo con testo completo%'")
        self.assertEqual(art["content_status"], "completo")
        atom = core.db.query_one("SELECT * FROM articles WHERE title LIKE 'Borsa%'")
        self.assertEqual(atom["author"], "Mario Rossi")
        # categorie multiple: articolo sulla Juventus anche in sport/champions (feed sport)
        juve = core.db.query_one("SELECT id FROM articles WHERE title LIKE '%Juventus%'")["id"]
        cats = {r[0] for r in core.db.query("SELECT category_id FROM article_categories WHERE article_id = ?", (juve,))}
        self.assertTrue({"italia", "sport", "sport/champions"} <= cats, cats)
        # stato dei feed e pulizia degli articoli vecchi
        self.assertTrue(all(f["status"] == "ok" for f in core.catalog.feeds(sid)))
        removed = feed_manager.prune_old_articles(core.db, 30)
        self.assertEqual(removed, 1)

        # viste e ricerca
        news = core.news
        self.assertTrue(any("Verona" in a.title for a in news.list_view({"kind": "home_latest"})))
        self.assertEqual(len(news.list_view({"kind": "category", "category_id": "sport/champions"})), 1)
        self.assertEqual(len(news.list_view({"kind": "local", "region": "Veneto", "city": "Verona"})), 4)
        self.assertEqual(len(news.search(text="verona")), 1)
        self.assertEqual(len(news.search(text="consiglio comunale")), 1)
        self.assertEqual(len(news.search(text="Rossi")), 1)          # autore
        self.assertEqual(len(news.search(text="Giornale di Prova")), 4)  # testata
        self.assertEqual(len(news.search(text="juventus", category_id="economia")), 0)
        self.assertEqual(len(news.search(text="", period="oggi", source_id=sid)) >= 1, True)
        self.assertEqual(len(news.search(text="", country="Italia")), 4)
        today = datetime.date.today().isoformat()
        self.assertGreaterEqual(len(news.search(date_from=today, date_to=today)), 1)
        core.db.fts = False   # ricerca di ripiego senza FTS5
        self.assertEqual(len(news.search(text="Verona")), 1)
        core.db.fts = True

        # preferiti, cartelle, cronologia
        aid = core.db.query_one("SELECT id FROM articles WHERE title LIKE 'Verona%'")["id"]
        self.assertTrue(core.favorites.toggle(aid))
        folder = core.favorites.create_folder("Da approfondire")
        core.favorites.move_to_folder(aid, folder)
        core.favorites.set_to_read(aid, True)
        with self.assertRaises(Exception):
            core.favorites.create_folder("Da approfondire")
        self.assertEqual(len(news.list_view({"kind": "saved", "folder_id": folder})), 1)
        self.assertEqual(len(news.list_view({"kind": "saved", "to_read": True})), 1)
        core.history.record(aid)
        core.history.record(aid)
        h = news.list_view({"kind": "history"})
        self.assertEqual(len(h), 1)
        self.assertTrue(h[0].last_viewed)
        self.assertEqual(core.db.query_one("SELECT view_count FROM history")[0], 2)

        # testo integrale dalla pagina pubblica, quindi archivio offline
        article = news.get_article(aid)
        status = core.downloads.download(article)
        self.assertEqual(status, "completo")
        article = news.get_article(aid)
        self.assertTrue(article.offline)
        self.assertIn("testo integrale", article.content)
        self.assertEqual(article.author, "Giulia Bianchi")
        n, size = core.downloads.stats()
        self.assertEqual(n, 1)
        self.assertGreater(size, 0)
        exported = core.downloads.export_txt(article, os.path.join(TMP, "export"))
        self.assertTrue(os.path.exists(exported))

        # persistenza dopo la riapertura
        path = core.db.path
        core.db.close()
        core2 = Core(db_path=path, speech_backend=FakeBackend())
        a2 = core2.news.get_article(aid)
        self.assertTrue(a2.saved and a2.offline and a2.to_read)
        self.assertEqual(a2.folder_name, "Da approfondire")
        # la pulizia non cancella gli articoli salvati
        core2.db.execute("UPDATE articles SET published = '2000-01-01T00:00:00+00:00' WHERE id = ?", (aid,))
        core2.db.commit()
        feed_manager.prune_old_articles(core2.db, 30)
        self.assertIsNotNone(core2.news.get_article(aid))
        core2.favorites.delete_folder(folder)
        self.assertEqual(core2.news.get_article(aid).folder_name, "")
        core2.history.clear()
        self.assertEqual(core2.history.count(), 0)
        core2.db.close()

    def test_errors_and_discovery(self):
        core = new_core("errors")
        sid = add_local_source(core, self.base, [("/manca.xml", "italia"), ("/nonfeed.xml", "italia")])
        for f in core.catalog.feeds(sid):
            r = feed_manager.fetch_feed(f)
            self.assertFalse(r.ok)
            feed_manager.store_result(core.db, core.catalog, r)
        statuses = sorted(f["status"] for f in core.catalog.feeds(sid))
        self.assertTrue(all(s.startswith("errore") for s in statuses), statuses)
        # server inesistente: errore di rete
        dead = {"id": 0, "source_id": sid, "url": "http://127.0.0.1:9/rss", "etag": "", "modified": ""}
        r = feed_manager.fetch_feed(dead)
        self.assertTrue(r.network_error)
        # scoperta del feed dichiarato dal sito: solo quello valido
        found = feed_manager.discover_feeds(self.base + "/sito")
        self.assertEqual([u for u, _ in found], [self.base + "/rss.xml"])
        ok, msg, n = feed_manager.test_feed_url(self.base + "/atom.xml")
        self.assertTrue(ok)
        self.assertEqual(n, 1)

    def test_paywall_and_extraction(self):
        r = article_reader.fetch_full_text(self.base + "/paywall", "anteprima")
        self.assertEqual(r.status, "anteprima")
        self.assertIn("abbonati", r.reason)
        r = article_reader.fetch_full_text(self.base + "/a1", "breve")
        self.assertEqual(r.status, "completo")
        r = article_reader.fetch_full_text("http://127.0.0.1:9/x", "")
        self.assertEqual(r.status, "anteprima")

    def test_updater_background_and_offline(self):
        core = new_core("updater")
        add_local_source(core, self.base, [("/rss.xml", "italia"), ("/atom.xml", "economia")])
        done = threading.Event()
        results = []
        updater = core.create_updater(on_done=lambda s: (results.append(s), done.set()))
        updater.start(initial_delay=0.1)
        self.assertTrue(done.wait(20), "l'aggiornamento automatico non è partito")
        updater.stop()
        self.assertEqual(results[0].new_articles, 5)   # il vecchio viene salvato e poi rimosso dalla pulizia
        self.assertEqual(results[0].removed_old, 1)
        self.assertFalse(results[0].offline)
        # "Internet assente": tutti i feed irraggiungibili
        core2 = new_core("updater_off")
        add_local_source(core2, "http://127.0.0.1:9", [("/a.xml", "italia")])
        s = core2.create_updater().run_once(manual=True)
        self.assertTrue(s.offline)
        self.assertEqual(len(s.failed), 1)


    def test_automatic_feed_discovery(self):
        core = new_core("discovery")
        add_local_source(core, self.base, [("/atom.xml", "economia")])
        sid = core.catalog.save_source({"name": "La Stampa Prova", "region": "Piemonte", "province": "Cuneo",
                                        "city": "Cuneo", "site_url": self.base + "/sito"}, feeds=[])
        s = core.create_updater().run_once(manual=True)
        self.assertEqual(s.discovered, [("La Stampa Prova", self.base + "/rss.xml")])
        feeds = core.catalog.feeds(sid)
        self.assertEqual(len(feeds), 1)
        self.assertEqual(feeds[0]["category_id"], "italia/cronaca_locale")
        self.assertGreaterEqual(core.db.query_one("SELECT COUNT(*) FROM articles WHERE source_id = ?", (sid,))[0], 3)
        # una testata senza feed dichiarati viene riprovata solo dopo una settimana
        other = core.catalog.save_source({"name": "Senza feed", "site_url": self.base + "/a1"}, feeds=[])
        s2 = core.create_updater().run_once(manual=True)
        self.assertEqual(s2.discovered, [])
        self.assertIsNotNone(core.db.get_setting_raw(f"discovery:{other}"))
        s3 = core.create_updater().run_once(manual=True)
        self.assertEqual(s3.discovered, [])


class TestSpeech(unittest.TestCase):
    def wait(self, sm, cond, timeout=3):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            sm.tick()
            if cond():
                return True
            time.sleep(0.02)
        return False

    def test_reading_pause_stop(self):
        backend = FakeBackend(ms_per_char=0.5)
        sm = SpeechManager(backend)
        states = []
        sm.on_state_change = lambda st, i, n: states.append((st, i))
        finished = threading.Event()
        sm.on_finished = finished.set
        sm.load(["Primo paragrafo breve.", "Secondo.", "Terzo e ultimo."])
        self.assertTrue(sm.start())
        self.assertEqual(sm.state, STATE_SPEAKING)
        self.assertTrue(self.wait(sm, finished.is_set), "la lettura non è arrivata alla fine")
        self.assertEqual(backend.spoken, ["Primo paragrafo breve.", "Secondo.", "Terzo e ultimo."])
        self.assertEqual(sm.state, STATE_STOPPED)

        # articolo lunghissimo: pausa, ripresa e arresto immediato
        long_par = "parola " * 20000
        sm.load([long_par, "fine"])
        sm.start()
        sm.pause()
        self.assertEqual(sm.state, STATE_PAUSED)
        time.sleep(0.2)
        sm.tick()
        self.assertEqual(sm.index, 0, "in pausa non deve avanzare")
        sm.resume()
        self.assertEqual(sm.state, STATE_SPEAKING)
        purged = backend.purged
        t0 = time.monotonic()
        sm.stop()
        self.assertLess(time.monotonic() - t0, 0.05)
        self.assertEqual(sm.state, STATE_STOPPED)
        self.assertGreater(backend.purged, purged)
        self.assertTrue(backend.is_done(), "la voce deve essere zittita subito")
        # arresto mentre è in pausa
        sm.start()
        sm.pause()
        sm.stop()
        self.assertEqual(sm.state, STATE_STOPPED)
        self.assertTrue(backend.is_done())
        # navigazione tra paragrafi
        sm.load(["a", "b", "c"])
        sm.start(1)
        sm.next_paragraph()
        self.assertEqual(sm.index, 2)
        self.assertFalse(sm.next_paragraph())
        sm.previous_paragraph()
        self.assertEqual(sm.index, 1)
        sm.restart()
        self.assertEqual(sm.index, 0)
        sm.stop()

    def test_italian_voice_default(self):
        sm = SpeechManager(FakeBackend())
        sm.apply_settings("", 3, 80)
        self.assertTrue(sm.voices()[0].is_italian)


class TestKeyboardAndText(unittest.TestCase):
    def test_shortcuts(self):
        self.assertEqual(normalize("ctrl+maiusc+f"), "Ctrl+Shift+F")
        self.assertEqual(normalize("Alt + freccia giù"), "Alt+Down")
        self.assertEqual(normalize("f5"), "F5")
        for bad in ("a", "Shift+A", "Ctrl+Insert", "Ctrl+", "", "Ctrl+A+B", "Ctrl+Pippo"):
            with self.assertRaises(ShortcutError, msg=bad):
                normalize(bad)
        core = new_core("keys")
        km = KeyboardManager(core.settings)
        self.assertEqual(km.get("search"), "Ctrl+F")
        with self.assertRaises(ShortcutError):
            km.assign("search", "Ctrl+H")        # già usata da Cronologia
        with self.assertRaises(ShortcutError):
            km.assign("search", "Alt+F4")        # riservata a Windows
        with self.assertRaises(ShortcutError):
            km.assign("search", "Ctrl+Alt+N")    # riservata a NVDA
        km.assign("pause", "Ctrl+Shift+Z")
        self.assertEqual(km.get("pause"), "Ctrl+Shift+Z")
        # stessa combinazione ammessa in ambiti diversi? 'export' (lettore) contro 'sources' (principale)
        km.assign("export", "Ctrl+Shift+F")
        self.assertEqual(km.get("export"), "Ctrl+Shift+F")
        km.reset()
        self.assertEqual(km.get("pause"), "Ctrl+Shift+P")
        actions = dict(km.for_scope("main"))
        self.assertIn("home", actions)
        self.assertNotIn("pause", actions)
        # tutte le predefinite sono valide e senza conflitti
        for action, label, combo, scope in km.all():
            km.check(action, combo)

    def test_reader_text_and_dates(self):
        from killanews.models import Article
        art = Article(id=1, title="Titolo", source_name="ANSA", source_id=1, published=NOW.isoformat(),
                      category_name="Italia", description="Primo.\n\nSecondo.", link="https://x", content_status="anteprima")
        text, spoken, offsets = article_reader.build_reader_text(art)
        self.assertEqual(len(spoken), len(offsets))
        for (start, end), par in zip(offsets, spoken):
            self.assertEqual(text[start:end], par)
        self.assertTrue(any("estratto" in p for p in spoken))
        from killanews.download_manager import DownloadManager
        page = DownloadManager.article_as_html(art)
        self.assertIn("<b>Titolo</b>", page)
        self.assertIn("<p>Secondo.</p>", page)
        self.assertIn("estratto", page)
        art.title = "A <b> & C"
        self.assertIn("A &lt;b&gt; &amp; C", DownloadManager.article_as_html(art))
        self.assertEqual(parse_italian_date("20/11/2026"), "2026-11-20")
        with self.assertRaises(ValueError):
            parse_italian_date("31/02/2026")
        self.assertEqual(feed_manager.normalize_link("https://www.Sito.it/a/?utm_source=x#c"), "sito.it/a")
        self.assertEqual(feed_manager.html_to_text("<p>Uno &amp; due</p><p>Tre</p>"), "Uno & due\n\nTre")


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


if __name__ == "__main__":
    unittest.main(verbosity=2)


class TestAggiornamentiProgramma(unittest.TestCase):
    def test_confronto_versioni(self):
        from killanews import app_updates
        self.assertTrue(app_updates.is_newer("v1.1.0", "1.0.0"))
        self.assertTrue(app_updates.is_newer("v1.0.10", "1.0.9"))
        self.assertFalse(app_updates.is_newer("v1.0.0", "1.0.0"))
        self.assertFalse(app_updates.is_newer("1.0", "1.0.0"))
        self.assertFalse(app_updates.is_newer("v0.9.9", "1.0.0"))
        self.assertEqual(app_updates.parse_version("v2.3.4"), (2, 3, 4))

    def test_repository_non_configurato(self):
        from killanews import app_updates, config
        if config.GITHUB_REPO.startswith("__"):
            self.assertFalse(app_updates.configured())


class TestGiornaliInternazionali(unittest.TestCase):
    def test_continenti_e_albero(self):
        from killanews import world
        self.assertEqual(world.continent_of("Giappone"), "Asia e Medio Oriente")
        self.assertEqual(world.continent_of("Ghana"), "Africa")
        self.assertEqual(world.continent_of("Marocco"), "Africa")
        self.assertEqual(world.continent_of("Italia"), "")
        core = new_core("internazionali")
        tree = core.catalog.international_tree()
        for cont in ("Europa", "Asia e Medio Oriente", "Africa", "America del Nord", "America Latina", "Oceania"):
            self.assertIn(cont, tree)
        for country in ("Giappone", "Cina", "Francia", "Marocco", "Ghana"):
            cont = world.continent_of(country)
            self.assertIn(country, tree[cont], country)
            self.assertTrue(tree[cont][country])
        # nessuna testata italiana o locale tra le internazionali
        for cs in tree.values():
            for lst in cs.values():
                for src in lst:
                    self.assertNotEqual(src["country"], "Italia")
                    self.assertEqual(src["region"], "")
        self.assertIn("Africa", core.news.continents())
        self.assertIn("Ghana", core.news.countries(international=True))
        self.assertNotIn("Italia", core.news.countries(international=True))
        core.db.close()

    def test_viste_e_ricerca_per_nazione(self):
        core = new_core("intviste")
        db = core.db
        jp = db.query_one("SELECT id FROM sources WHERE country = 'Giappone' LIMIT 1")["id"]
        it = db.query_one("SELECT id FROM sources WHERE country = 'Italia' AND region = '' LIMIT 1")["id"]
        now = database.now_iso()
        for i, (sid, title) in enumerate(((jp, "Tokyo news test"), (it, "Notizia italiana di prova"))):
            db.execute("INSERT INTO articles(source_id, uid, title, link, norm_link, published, fetched, category_id) "
                       "VALUES (?, ?, ?, ?, ?, ?, ?, 'esteri')", (sid, f"g{i}", title, f"http://x/{i}", f"x/{i}", now, now))
        db.commit()
        titles = lambda arts: {a.title for a in arts}
        self.assertEqual(titles(core.news.list_view({"kind": "international", "country": "Giappone"})),
                         {"Tokyo news test"})
        self.assertIn("Tokyo news test",
                      titles(core.news.list_view({"kind": "international", "continent": "Asia e Medio Oriente"})))
        self.assertNotIn("Notizia italiana di prova", titles(core.news.list_view({"kind": "international"})))
        self.assertEqual(titles(core.news.search(continent="Asia e Medio Oriente")), {"Tokyo news test"})
        self.assertEqual(titles(core.news.search(country="Giappone")), {"Tokyo news test"})
        self.assertEqual(titles(core.news.list_view({"kind": "international", "continent": "Oceania"})), set())
        # la prima pagina resta in italiano
        recent = titles(core.news.list_view({"kind": "home_recent"}))
        self.assertIn("Notizia italiana di prova", recent)
        self.assertNotIn("Tokyo news test", recent)
        core.db.close()


class TestTraduzione(unittest.TestCase):
    def test_blocchi_e_rilevamento(self):
        from killanews import translator
        long_text = "\n".join(["Paragraph number %d. " % i * 20 for i in range(40)])
        chunks = translator._chunks(long_text)
        self.assertTrue(all(len(c) <= translator._MAX_CHUNK for c in chunks))
        self.assertEqual("".join(c.replace("\n", "") for c in chunks).replace(" ", ""),
                         long_text.replace("\n", "").replace(" ", ""))
        self.assertTrue(translator.looks_italian("Il governo ha approvato la legge di bilancio per il prossimo anno, "
                                                 "con le misure per le famiglie e per le imprese della regione."))
        self.assertFalse(translator.looks_italian("The government approved the budget law for next year, "
                                                  "with measures for families and businesses."))
        self.assertEqual(translator.language_name("ja"), "giapponese")

    def test_traduzione_con_servizio_finto_e_cache(self):
        from killanews import translator
        from killanews.models import Article

        class FakeResp:
            def __init__(self, data):
                self.data = data

            def raise_for_status(self):
                pass

            def json(self):
                return self.data

        class FakeSession:
            headers = {}
            calls = 0

            def get(self, url, params=None, timeout=None):
                FakeSession.calls += 1
                q = params["q"]
                return FakeResp([[["IT:" + line, line] for line in q.split("\n")], None, "en"])

        core = new_core("traduzione")
        sid = core.db.query_one("SELECT id FROM sources LIMIT 1")["id"]
        now = database.now_iso()
        cur = core.db.execute("INSERT INTO articles(source_id, uid, title, link, norm_link, published, fetched, "
                              "category_id, content) VALUES (?, 't1', 'Hello', 'http://x/t', 'x/t', ?, ?, 'esteri', ?)",
                              (sid, now, now, "First line\nSecond line"))
        core.db.commit()
        art = core.news.get_article(cur.lastrowid)
        store = translator.TranslationStore(core.db)
        res = translator.translate_article(art, store, session=FakeSession())
        self.assertEqual(res["title"], "IT:Hello")
        self.assertIn("IT:Second line", res["body"])
        self.assertEqual(res["source_lang"], "en")
        calls = FakeSession.calls
        again = translator.translate_article(art, store, session=FakeSession())
        self.assertEqual(again["body"], res["body"])
        self.assertEqual(FakeSession.calls, calls)  # seconda volta dalla memoria, senza rete
        core.db.close()


class TestMigrazione(unittest.TestCase):
    def test_database_della_versione_1(self):
        path = os.path.join(TMP, "vecchio.db")
        conn = sqlite3.connect(path)
        conn.executescript(database._SCHEMA_V1.replace(",\n    language TEXT NOT NULL DEFAULT ''", ""))
        conn.execute("INSERT INTO schema_version(version) VALUES (1)")
        conn.commit()
        conn.close()
        db = database.Database(path)
        self.assertEqual(db.schema_version(), config.DB_SCHEMA_VERSION)
        cols = [r[1] for r in db.query("PRAGMA table_info(sources)")]
        self.assertIn("language", cols)
        self.assertTrue(db._has_table("translations"))
        db.close()


class TestVoceNVDA(unittest.TestCase):
    class FakeNvda:
        def __init__(self, running=True):
            self.running = running
            self.texts = []
            self.cancelled = 0

        def nvdaController_testIfRunning(self):
            return 0 if self.running else 1

        def nvdaController_speakSsml(self, ssml, level, prio, asynchronous):
            self.texts.append(ssml.value)
            time.sleep(0.05)
            return 0

        def nvdaController_speakText(self, text):
            self.texts.append(text.value)
            return 0

        def nvdaController_cancelSpeech(self):
            self.cancelled += 1
            return 0

    def _wait(self, sm, state, limit=3.0):
        end = time.monotonic() + limit
        while time.monotonic() < end and sm.state != state:
            sm.tick()
            time.sleep(0.01)

    def test_lettura_con_nvda(self):
        from killanews.speech_manager import MultiBackend, NvdaBackend, NVDA_VOICE_ID
        fake = self.FakeNvda()
        backend = MultiBackend(FakeBackend(), NvdaBackend(fake))
        self.assertEqual(backend.voices()[0].id, NVDA_VOICE_ID)
        sm = SpeechManager(backend)
        sm.apply_settings(NVDA_VOICE_ID)
        sm.load(["Primo paragrafo & <prova>", "Secondo paragrafo"])
        sm.start()
        self._wait(sm, STATE_STOPPED)
        self.assertEqual(len(fake.texts), 2)
        self.assertIn("&amp; &lt;prova&gt;", fake.texts[0])
        self.assertEqual(backend.sapi.spoken, [])
        # pausa = la voce di NVDA si ferma; ripresa = rilegge il paragrafo
        sm.load(["Uno", "Due"])
        sm.start()
        sm.pause()
        self.assertEqual(sm.state, STATE_PAUSED)
        self.assertGreaterEqual(fake.cancelled, 1)
        sm.resume()
        self._wait(sm, STATE_STOPPED)
        sm.stop()

    def test_nvda_spento_o_vecchio(self):
        from killanews.speech_manager import MultiBackend, NvdaBackend, NVDA_VOICE_ID
        fake = self.FakeNvda(running=False)
        backend = MultiBackend(FakeBackend(), NvdaBackend(fake))
        sm = SpeechManager(backend)
        sm.apply_settings(NVDA_VOICE_ID)
        sm.load(["Testo letto dalla voce di Windows"])
        sm.start()
        self._wait(sm, STATE_STOPPED)
        self.assertEqual(backend.sapi.spoken, ["Testo letto dalla voce di Windows"])
        self.assertEqual(fake.texts, [])
        old = self.FakeNvda()
        old.nvdaController_speakSsml = lambda *a: 1717  # NVDA troppo vecchio: funzione sconosciuta al server
        nb = NvdaBackend(old)
        nb.MS_PER_CHAR = 1
        sm2 = SpeechManager(MultiBackend(FakeBackend(), nb))
        sm2.apply_settings(NVDA_VOICE_ID)
        sm2.load(["Versione vecchia di NVDA"])
        sm2.start()
        self._wait(sm2, STATE_STOPPED)
        self.assertEqual(old.texts, ["Versione vecchia di NVDA"])


class TestNovita(unittest.TestCase):
    def test_elenco_delle_novita(self):
        from killanews import changelog
        sections = changelog.load()
        self.assertEqual(sections[0][0], config.APP_VERSION)  # la versione in uso ha le sue novità
        for version, date, items in sections:
            self.assertTrue(items, version)
            for item in items:
                if version != "1.0.0":
                    self.assertTrue(item.split(":")[0] in changelog.KINDS, item)
        mid = changelog.between(sections, "1.2.0", "1.3.0")
        self.assertEqual([s[0] for s in mid], ["1.3.0", "1.2.1"])
        text = changelog.as_text(mid, "1.3.0", "1.2.0")
        self.assertIn("Versione nuova: 1.3.0", text)
        self.assertIn("Versione precedente: 1.2.0", text)

    def test_cartella_scrivibile(self):
        from killanews import app_updates
        self.assertTrue(app_updates.folder_is_writable(TMP))
        self.assertFalse(app_updates.folder_is_writable(os.path.join(TMP, "non-esiste")))
