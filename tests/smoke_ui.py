"""Prova automatica dell'interfaccia (fumo): crea tutte le finestre, carica le sezioni,
esegue ricerca, lettore, voce simulata, scorciatoie e finestre di dialogo.

Non sostituisce le prove con NVDA (vedi CHECKLIST_NVDA.md): verifica che il codice
dell'interfaccia funzioni senza errori. Uso:  python tests/smoke_ui.py
(su Linux senza schermo:  xvfb-run -a python tests/smoke_ui.py)"""
import os
import sys
import tempfile
import traceback

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))
TMP = tempfile.mkdtemp(prefix="killanews_ui_")
os.environ["KILLANEWS_DATA_DIR"] = TMP

import wx  # noqa: E402

from killanews import feed_manager  # noqa: E402
from killanews.core import Core  # noqa: E402
from killanews.speech_manager import FakeBackend  # noqa: E402
import test_core  # noqa: E402  (server di prova e feed di esempio)

STEPS = []
ERRORS = []
UNHANDLED = []


def step(fn):
    STEPS.append(fn)
    return fn


def main():
    def hook(exc_type, exc, tb):
        UNHANDLED.append("".join(traceback.format_exception(exc_type, exc, tb)))
    sys.excepthook = hook
    test_core.TestFeedsAndArticles.start_server()
    base = test_core.TestFeedsAndArticles.base
    app = wx.App(False)
    core = Core(db_path=os.path.join(TMP, "ui.db"), speech_backend=FakeBackend(ms_per_char=0.2))
    core.settings.set("fetch_full_text", False)
    core.settings.set("auto_update", False)
    sid = test_core.add_local_source(core, base, [("/rss.xml", "italia"), ("/dup.xml", "sport"),
                                                 ("/atom.xml", "economia")])
    for f in core.catalog.feeds(sid):
        feed_manager.store_result(core.db, core.catalog, feed_manager.fetch_feed(f))

    from killanews.ui.main_window import MainFrame
    frame = MainFrame(core)
    frame.Show()
    state = {}

    @step
    def views():
        frame.updater.stop()
        sb = frame.sidebar
        assert sb.tree.GetCount() > 30, sb.tree.GetCount()
        for key in ("home", "all", "italia", "sport", "local", "saved", "history", "settings"):
            frame.go_section(key)
        frame.go_section("home")
        frame.load_view({"kind": "home_recent", "title": "Recenti"})
        assert len(frame.list.articles) == 5, len(frame.list.articles)  # 4 recenti + 1 vecchio non ancora rimosso
        frame.load_view({"kind": "category", "category_id": "sport/champions", "title": "Champions"})
        assert len(frame.list.articles) == 1
        corriere = core.db.query_one("SELECT id, site_url FROM sources WHERE key='corriere'")
        frame.load_view({"kind": "source", "source_id": corriere["id"], "title": "Corriere", "site_only": True,
                         "site_url": corriere["site_url"]})
        assert frame.list.list.GetItemCount() == 1 and frame.list.site_view
        frame.load_view({"kind": "local", "region": "Veneto", "title": "Veneto"})
        assert len(frame.list.articles) == 5
        node = sb.find(f"source:{sid}")
        assert node is not None, "testata locale non trovata nell'albero"
        # giornali locali: prima le scelte, poi gli articoli
        frame.go_section("local")
        assert frame.list.choices and frame.list.choices[0][1] == "local_all", frame.list.choices
        assert [k for _, k in frame.list.choices][1:] == ["local_cities", "local_regions", "local_sources"]
        frame.list.list.Select(0)
        frame.open_selected()
        assert frame.current_view["key"] == "local_all" and len(frame.list.articles) == 5
        frame.go_key("local_cities")
        city_keys = [k for _, k in frame.list.choices]
        assert "city:Veneto:Verona:Verona" in city_keys, city_keys
        frame.go_key("city:Veneto:Verona:Verona")
        labels = [t for t, _ in frame.list.choices]
        assert labels[0] == "Tutti gli articoli di Verona" and any("Giornale di Prova" in t for t in labels), labels
        frame.go_key(frame.list.choices[[i for i, (t, _) in enumerate(frame.list.choices) if "Giornale di Prova" in t][0]][1])
        assert len(frame.list.articles) == 5 and frame.current_view["source_id"] == sid
        frame.go_key("local_regions")
        frame.go_key("region:Veneto")
        assert frame.list.choices[0][0].startswith("Tutti gli articoli della regione Veneto")
        assert "prov:Veneto:Verona" in [k for _, k in frame.list.choices]
        frame.go_key("local_sources")
        assert any("Giornale di Prova (Verona)" in t for t, _ in frame.list.choices)

    @step
    def search():
        frame.show_search()
        assert frame.search.IsShown()
        frame.search.text.SetValue("verona")
        frame.on_search()
        assert len(frame.list.articles) == 1, len(frame.list.articles)
        frame.search.period.SetSelection(5)
        frame.search._update_dates()
        frame.search.date_from.SetValue("31/02/2026")
        try:
            frame.search.params()
            raise AssertionError("data non valida accettata")
        except ValueError:
            pass
        frame.search._on_clear(None)
        frame.cycle_pane(1)
        frame.cycle_pane(-1)

    @step
    def favorites_and_menu():
        frame.go_section("home")
        frame.load_view({"kind": "home_recent", "title": "Recenti"})
        frame.list.list.Select(0)
        art = frame.list.selected_article()
        frame.toggle_save()
        assert core.favorites.is_saved(art.id)
        frame.toggle_to_read()
        frame.go_section("saved")
        assert len(frame.list.articles) == 1
        frame.load_view({"kind": "home_recent", "title": "Recenti"})
        frame.list.list.Select(0)
        frame.export_selected = frame.export_selected  # presente
        frame.rebuild_accelerators()
        menubar = frame.GetMenuBar()
        assert menubar.GetMenuCount() == 8
        state["art"] = art

    @step
    def reader():
        from killanews.ui.article_view import ReaderDialog, prepare_article
        article = prepare_article(frame, core, state["art"].id)
        dlg = ReaderDialog(frame, core, article, frame.list.ids())
        dlg.Show()
        assert "Testata:" in dlg.text.GetValue()
        dlg.start_reading()
        assert core.speech.state == "in lettura"
        dlg.toggle_pause()
        assert core.speech.state == "in pausa"
        dlg.stop_reading()
        assert core.speech.state == "ferma"
        dlg.next_par()
        dlg.prev_par()
        dlg.restart()
        dlg.toggle_save()
        dlg.next_article()
        assert dlg.index == 1
        dlg.prev_article()
        assert dlg.index == 0
        import wx.html
        from killanews.download_manager import DownloadManager
        page = DownloadManager.article_as_html(article)
        view = wx.html.HtmlWindow(dlg)
        assert view.SetPage(page)
        printer = wx.html.HtmlEasyPrinting("Stampa", dlg)
        printer.SetStandardFonts(14)
        assert hasattr(dlg, "print_article") and "print" in frame.handlers
        dlg.close()
        assert core.speech.state == "ferma"
        assert core.history.count() >= 1

    @step
    def dialogs():
        from killanews.ui.dialogs import (FoldersDialog, HelpDialog, SourceEditDialog, SourcesDialog,
                                          FeedEditDialog, ShortcutEditDialog)
        from killanews.ui.settings_view import SettingsDialog
        for cls, args in ((SettingsDialog, ()), (SourcesDialog, ()), (FoldersDialog, ()), (HelpDialog, ()),
                          (SourceEditDialog, ()), (SourceEditDialog, (sid,)), (FeedEditDialog, ()),
                          (ShortcutEditDialog, ("search",))):
            d = cls(frame, core, *args)
            d.Show()
            d.Destroy()
        s = SettingsDialog(frame, core)
        s.theme.SetSelection(2)
        s.font_size.SetValue(16)
        s.on_ok = s.on_ok  # nessun ShowModal: applichiamo direttamente
        core.settings.update({"theme": "scuro", "font_size": 16})
        s.Destroy()
        from killanews.ui import common
        common.apply_theme(frame, core.settings)
        core.settings.update({"theme": "alto_contrasto"})
        common.apply_theme(frame, core.settings)
        core.settings.update({"theme": "sistema", "font_size": 12})
        common.apply_theme(frame, core.settings)
        core.keyboard.assign("search", "Ctrl+Shift+Z")
        frame.rebuild_accelerators()
        old = frame.GetMenuBar()
        frame._build_menu()
        old.Destroy()
        core.keyboard.reset()

    @step
    def killa_records():
        import webbrowser
        opened = []
        webbrowser.open = lambda url, *a, **k: opened.append(url) or True
        frame.go_section("killa")
        keys = [k for _, k in frame.list.choices]
        assert keys[0] == "action:report" and "action:site" in keys and "action:check_updates" in keys and len(keys) == 11, keys
        labels = [frame.GetMenuBar().GetMenuLabelText(j) for j in range(frame.GetMenuBar().GetMenuCount())]
        assert "Killa Records" in labels, labels
        frame.list.list.Select(keys.index("action:site"))
        frame.open_selected()
        assert opened == ["https://www.killarecordsgames.com"], opened
        frame.run_action("youtube")
        assert opened[-1].endswith("@KillaRecordsGamesOfficial")
        from killanews.ui.dialogs import ReportProblemDialog, technical_info
        d = ReportProblemDialog(frame)
        d.text.SetValue("La finestra non si chiude")
        assert "La finestra non si chiude" in d.body() and ("KILLA NEWS " + __import__("killanews.config", fromlist=["x"]).APP_VERSION) in d.body()
        assert "Problema o errore" in d.subject()
        d.Destroy()
        assert "Programma: KILLA NEWS" in technical_info()

    @step
    def update_done():
        from killanews.updater import UpdateSummary
        frame.on_update_done(UpdateSummary(new_articles=3, manual=True))
        frame.on_update_done(UpdateSummary(offline=True))
        assert "Ultimo aggiornamento" in frame.GetStatusBar().GetStatusText(1)

    def run_steps(i=0):
        if i >= len(STEPS):
            frame.Close()
            return
        try:
            STEPS[i]()
            print(f"OK   {STEPS[i].__name__}")
        except Exception:
            ERRORS.append(STEPS[i].__name__)
            print(f"ERR  {STEPS[i].__name__}")
            traceback.print_exc()
        wx.CallLater(100, run_steps, i + 1)

    wx.CallLater(800, run_steps)
    app.MainLoop()
    test_core.TestFeedsAndArticles.stop_server()
    if UNHANDLED:
        ERRORS.append("errori non gestiti (anche alla chiusura)")
        print("\n".join(UNHANDLED))
    print("RISULTATO:", "tutto OK" if not ERRORS else f"errori in {ERRORS}")
    return 1 if ERRORS else 0


if __name__ == "__main__":
    sys.exit(main())
