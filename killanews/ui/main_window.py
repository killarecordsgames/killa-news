"""Finestra principale di KILLA NEWS."""
import logging
import os
import threading
import time
import webbrowser

import wx

from .. import app_updates, config, database
from ..accessibility import announcer, announce
from ..models import format_date
from . import common
from .article_list import ArticleList
from .article_view import ReaderDialog, prepare_article
from .common import shortcut_hint
from .dialogs import (FoldersDialog, HelpDialog, ReportProblemDialog, SourcesDialog, TextDialog, choose_folder,
                      show_about, show_credits)
from .search_view import SearchPanel
from .settings_view import SettingsDialog
from .sidebar import Sidebar

log = logging.getLogger(__name__)

SECTION_SHORTCUTS = {"home": "home", "all_sources": "all", "history": "history", "favorites": "saved"}


class MainFrame(wx.Frame):
    def __init__(self, core):
        super().__init__(None, title=f"{config.APP_NAME} - {config.SLOGAN}", size=(1200, 800))
        self.core = core
        self.current_view = None
        self.ids = {}
        icon_path = config.asset_file("killa_news.ico")
        if os.path.exists(icon_path):
            self.SetIcon(wx.Icon(icon_path, wx.BITMAP_TYPE_ICO))

        self.CreateStatusBar(2)
        self.SetStatusWidths([-3, -2])
        announcer.fallback = self.set_status

        self.splitter = wx.SplitterWindow(self, style=wx.SP_LIVE_UPDATE | wx.SP_3D)
        self.sidebar = Sidebar(self.splitter, core, self.on_select_view, self.on_activate_view)
        self.right = wx.Panel(self.splitter)
        right_sizer = wx.BoxSizer(wx.VERTICAL)
        self.search = SearchPanel(self.right, core, self.on_search)
        right_sizer.Add(self.search, 0, wx.EXPAND | wx.ALL, 2)
        self.search.Hide()
        self.list = ArticleList(self.right, self.open_selected, self.show_context_menu, self.on_delete_key)
        right_sizer.Add(self.list, 1, wx.EXPAND)
        self.button_row = wx.WrapSizer(wx.HORIZONTAL)
        for label, handler in (("&Apri l'articolo (Invio)", lambda: self.open_selected()),
                               ("Ascolta" + shortcut_hint(core, "read"), lambda: self.open_selected(start_reading=True)),
                               ("Salva o rimuovi dai preferiti" + shortcut_hint(core, "save"), self.toggle_save),
                               ("Scarica offline" + shortcut_hint(core, "download"), self.download_selected),
                               ("Apri l'originale nel browser" + shortcut_hint(core, "open_original"), self.open_original)):
            b = wx.Button(self.right, label=label)
            b.Bind(wx.EVT_BUTTON, lambda e, h=handler: h())
            self.button_row.Add(b, 0, wx.ALL, 2)
        right_sizer.Add(self.button_row, 0, wx.EXPAND | wx.ALL, 2)
        self.right.SetSizer(right_sizer)
        self.splitter.SplitVertically(self.sidebar, self.right, 330)
        self.splitter.SetMinimumPaneSize(200)

        self._build_menu_and_keys()
        self.Bind(wx.EVT_CLOSE, self.on_close)
        self.Bind(wx.EVT_CHAR_HOOK, self.on_char_hook)

        self.speech_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, lambda e: core.speech.tick(), self.speech_timer)
        self.speech_timer.Start(120)

        self.updater = core.create_updater(on_start=lambda manual: wx.CallAfter(self.on_update_start, manual),
                                           on_done=lambda summary: wx.CallAfter(self.on_update_done, summary))
        common.apply_theme(self, core.settings)
        self.SetStatusText(f"Ultimo aggiornamento: {core.last_update_text()}", 1)
        self.Centre()
        wx.CallAfter(self._startup)

    # ================================================================== menu e scorciatoie
    def _id(self, action):
        if action not in self.ids:
            self.ids[action] = wx.NewIdRef()
        return self.ids[action]

    def _build_menu_and_keys(self):
        handlers = {
            "home": lambda: self.go_section("home"), "all_sources": lambda: self.go_section("all"),
            "search": self.show_search, "history": lambda: self.go_section("history"),
            "favorites": lambda: self.go_section("saved"), "refresh": self.refresh_news,
            "refresh_view": self.refresh_view, "next_pane": lambda: self.cycle_pane(1),
            "prev_pane": lambda: self.cycle_pane(-1), "settings": self.open_settings, "sources": self.open_sources,
            "help": self.show_help, "save": self.toggle_save, "read": lambda: self.open_selected(start_reading=True),
            "stop_speech": self.stop_speech, "download": self.download_selected, "open_original": self.open_original,
            "print": self.print_selected,
        }
        extra = {
            "open": lambda: self.open_selected(), "to_read": self.toggle_to_read, "move_folder": self.move_to_folder,
            "remove_offline": self.remove_offline, "copy_link": self.copy_link, "export": self.export_selected,
            "show_to_read": lambda: self.go_section("to_read"), "show_offline": lambda: self.go_section("offline"),
            "folders": self.manage_folders, "failed_sources": self.show_failed, "update_source": self.update_selected_source,
            "backup": self.backup_now, "about": lambda: show_about(self), "exit": self.Close,
            "remove_history": self.remove_from_history, "clear_history": self.clear_history,
            "report": self.report_problem, "credits": lambda: show_credits(self),
            "check_updates": lambda: self.check_app_updates(manual=True),
        }
        for link in config.LINKS:
            extra[link] = lambda link=link: self.open_link(link)
        self.handlers = {**handlers, **extra}
        self.main_actions = set(handlers)
        for action, handler in self.handlers.items():
            self.Bind(wx.EVT_MENU, lambda e, h=handler: h(), id=self._id(action))
        self._build_menu()

    def _build_menu(self):
        core = self.core
        handlers = self.main_actions

        def item(menu, action, label, hint_action=None):
            hint = shortcut_hint(core, hint_action or action) if (hint_action or action) in handlers else ""
            menu.Append(self._id(action), label + hint)

        bar = wx.MenuBar()
        m = wx.Menu()
        item(m, "refresh", "&Aggiorna le notizie da Internet")
        item(m, "refresh_view", "Aggiorna l'&elenco visualizzato")
        m.AppendSeparator()
        item(m, "backup", "Crea un &backup dei dati")
        m.AppendSeparator()
        item(m, "exit", "&Esci (Alt+F4)")
        bar.Append(m, "&File")
        m = wx.Menu()
        item(m, "home", "&Prima pagina")
        item(m, "all_sources", "&Tutti i giornali")
        item(m, "search", "&Cerca")
        item(m, "favorites", "Articoli &salvati")
        item(m, "history", "C&ronologia")
        m.AppendSeparator()
        item(m, "next_pane", "Riquadro &successivo")
        item(m, "prev_pane", "Riquadro &precedente")
        bar.Append(m, "&Visualizza")
        m = wx.Menu()
        item(m, "open", "&Apri l'articolo (Invio)")
        item(m, "read", "A&scolta l'articolo")
        item(m, "stop_speech", "&Interrompi la lettura vocale")
        m.AppendSeparator()
        item(m, "save", "Salva o rimuovi dai &preferiti")
        item(m, "to_read", "Segna o togli «&da leggere»")
        item(m, "move_folder", "Sposta in &cartella...")
        item(m, "download", "Scarica per la lettura &offline")
        item(m, "remove_offline", "Rimuovi dall'archivio o&ffline")
        m.AppendSeparator()
        item(m, "open_original", "Apri l'articolo o&riginale nel browser")
        item(m, "copy_link", "Copia il co&llegamento")
        item(m, "export", "&Esporta come file di testo")
        item(m, "print", "S&tampa")
        item(m, "remove_history", "Rimuovi dalla cro&nologia")
        bar.Append(m, "&Articolo")
        m = wx.Menu()
        item(m, "favorites", "Tutti gli articoli &salvati")
        item(m, "show_to_read", "Articoli &da leggere")
        item(m, "show_offline", "Articoli disponibili &offline")
        item(m, "folders", "Gestisci le &cartelle...")
        m.AppendSeparator()
        item(m, "clear_history", "S&vuota la cronologia")
        bar.Append(m, "&Preferiti")
        m = wx.Menu()
        item(m, "sources", "&Gestione delle fonti...")
        item(m, "failed_sources", "Fonti &non raggiungibili...")
        item(m, "update_source", "&Aggiorna solo la testata selezionata")
        bar.Append(m, "F&onti")
        m = wx.Menu()
        item(m, "settings", "&Impostazioni...")
        bar.Append(m, "&Strumenti")
        m = wx.Menu()
        item(m, "report", "&Segnala un problema...")
        item(m, "credits", "&Chi ha creato KILLA NEWS")
        m.AppendSeparator()
        item(m, "site", "Sito &ufficiale Killa Records")
        item(m, "youtube", "Canale &YouTube")
        item(m, "facebook", "Gruppo &Facebook")
        item(m, "whatsapp", "Canale &WhatsApp")
        item(m, "donate", "Sostieni il progetto con una &donazione")
        m.AppendSeparator()
        item(m, "settings", "&Impostazioni...")
        item(m, "check_updates", "Controlla &aggiornamenti di KILLA NEWS...")
        item(m, "help", "&Guida")
        item(m, "about", "I&nformazioni su KILLA NEWS")
        bar.Append(m, "&Killa Records")
        m = wx.Menu()
        item(m, "help", "&Guida")
        item(m, "check_updates", "Controlla &aggiornamenti...")
        item(m, "about", "&Informazioni su KILLA NEWS")
        bar.Append(m, "A&iuto")
        self.SetMenuBar(bar)
        self.rebuild_accelerators()

    def rebuild_accelerators(self):
        entries = []
        for action, combo in self.core.keyboard.for_scope("main"):
            entry = common.accel_entry(combo, self._id(action))
            if entry:
                entries.append(entry)
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    # ================================================================== avvio e chiusura
    def _startup(self):
        self.sidebar.tree.SetFocus()
        self.load_view(self.sidebar.current_view())
        backup = self.core.daily_backup()
        if self.core.restored_backup:
            common.info(self, "Il backup scelto è stato ripristinato.")
        first_run = self.core.db.query_one("SELECT COUNT(*) FROM articles")[0] == 0
        self.updater.start(initial_delay=1.0)
        if first_run:
            announce("Benvenuto in KILLA NEWS. Sto scaricando le prime notizie: ti avviso quando sono pronte.")
            self.updater.trigger()
        else:
            announce(f"KILLA NEWS pronto. {config.SLOGAN}")
        log.info("Avvio completato (backup: %s)", backup)
        if app_updates.should_check_automatically(self.core.settings):
            wx.CallLater(8000, lambda: self.check_app_updates(manual=False))
        # chi tiene KILLA NEWS aperto per ore riceve comunque l'avviso delle nuove versioni
        self._app_update_timer = wx.Timer(self)
        self.Bind(wx.EVT_TIMER, self._on_app_update_timer, self._app_update_timer)
        self._app_update_timer.Start(app_updates.CHECK_WHILE_OPEN_MS)

    def _on_app_update_timer(self, event):
        if app_updates.should_check_automatically(self.core.settings):
            self.check_app_updates(manual=False)

    # ================================================================== aggiornamenti del programma
    def check_app_updates(self, manual=False):
        """Controlla in background se esiste una nuova versione di KILLA NEWS."""
        if getattr(self, "_checking_app_update", False) or getattr(self, "_app_update_dialog", False):
            return
        self._checking_app_update = True
        if manual:
            announce("Controllo degli aggiornamenti di KILLA NEWS in corso...")

        def lavoro():
            try:
                info, errore = app_updates.check(), None
            except app_updates.UpdateError as exc:
                info, errore = None, str(exc)
            except Exception:
                log.exception("Errore nel controllo degli aggiornamenti")
                info, errore = None, "Errore imprevisto nel controllo degli aggiornamenti."
            wx.CallAfter(self._on_app_update_checked, info, errore, manual)

        threading.Thread(target=lavoro, name="controllo-aggiornamenti", daemon=True).start()

    def _on_app_update_checked(self, info, errore, manual):
        self._checking_app_update = False
        if not self:
            return
        self.core.settings.set("last_app_update_check", time.time(), notify=False)
        if errore:
            if manual:
                common.error(self, errore)
            return
        if info is None:
            if manual:
                common.info(self, f"Hai già l'ultima versione di KILLA NEWS ({config.APP_VERSION}).")
            return
        if not manual and self.core.settings.get("skipped_app_version") == info.version:
            return
        kind = app_updates.install_kind()
        note = info.notes[:1500] + ("…" if len(info.notes) > 1500 else "")
        testo = (f"È disponibile KILLA NEWS {info.version}. Tu hai la versione {config.APP_VERSION}.\n\n"
                 + (f"Novità:\n{note}\n\n" if note else "")
                 + ("Vuoi aggiornare adesso? KILLA NEWS si chiuderà, si aggiornerà e si riaprirà da solo. "
                    "I tuoi preferiti, la cronologia e le impostazioni restano al loro posto."
                    if kind != "sorgente" else
                    "Stai usando KILLA NEWS dal codice sorgente: scarica la nuova versione dal sito."))
        announce(f"È disponibile KILLA NEWS {info.version}")
        if kind == "sorgente":
            common.info(self, testo)
            return
        dlg = wx.MessageDialog(self, testo, "Aggiornamento di KILLA NEWS disponibile",
                               wx.YES_NO | wx.CANCEL | wx.ICON_INFORMATION)
        dlg.SetYesNoCancelLabels("&Aggiorna ora", "&Più tardi", "&Salta questa versione")
        self._app_update_dialog = True
        try:
            scelta = dlg.ShowModal()
        finally:
            self._app_update_dialog = False
            dlg.Destroy()
        if scelta == wx.ID_CANCEL:
            self.core.settings.set("skipped_app_version", info.version, notify=False)
            announce("Questa versione verrà saltata. Puoi sempre aggiornare dal menu Killa Records.")
            return
        if scelta != wx.ID_YES:
            announce("Aggiornamento rimandato.")
            return
        self._install_app_update(info, kind)

    def _install_app_update(self, info, kind):
        progress = wx.ProgressDialog("Aggiornamento di KILLA NEWS", f"Download di KILLA NEWS {info.version} in corso...",
                                     maximum=100, parent=self,
                                     style=wx.PD_APP_MODAL | wx.PD_CAN_ABORT | wx.PD_AUTO_HIDE | wx.PD_ELAPSED_TIME)
        stato = {"annullato": False, "ultimo": -10}

        def avanzamento(fatti, totale):
            percento = int(fatti * 100 / totale) if totale else 0
            if percento >= stato["ultimo"] + 10 or percento == 100:
                stato["ultimo"] = percento
                def aggiorna():
                    if progress:
                        continua, _ = progress.Update(min(percento, 99), f"Download in corso: {percento} per cento")
                        if not continua:
                            stato["annullato"] = True
                wx.CallAfter(aggiorna)
            return not stato["annullato"]

        def lavoro():
            try:
                percorso, errore = app_updates.download(info, kind, avanzamento), None
            except app_updates.UpdateError as exc:
                percorso, errore = None, str(exc)
            except Exception:
                log.exception("Errore nel download dell'aggiornamento")
                percorso, errore = None, "Errore imprevisto durante il download dell'aggiornamento."
            wx.CallAfter(fine, percorso, errore)

        def fine(percorso, errore):
            if progress:
                progress.Destroy()
            if errore:
                common.error(self, errore)
                return
            try:
                app_updates.launch_installer(percorso, kind)
            except Exception:
                log.exception("Avvio dell'aggiornamento non riuscito")
                common.error(self, "Impossibile avviare l'aggiornamento. Puoi scaricare la nuova versione dal sito.")
                return
            announce("Aggiornamento scaricato. KILLA NEWS si chiude e si riapre tra pochi secondi.")
            wx.CallLater(1500, self.Close)

        threading.Thread(target=lavoro, name="download-aggiornamento", daemon=True).start()

    def on_close(self, event):
        try:
            self.sidebar.shutdown()
            self.speech_timer.Stop()
            if getattr(self, "_app_update_timer", None):
                self._app_update_timer.Stop()
            self.core.shutdown()
        except Exception:
            log.exception("Errore durante la chiusura (ignorato)")
        finally:
            announcer.fallback = None
            self.Destroy()
            app = wx.GetApp()
            if app:
                app.ExitMainLoop()  # chiusura garantita anche se resta aperta qualche finestra secondaria

    def set_status(self, text):
        if self:
            self.SetStatusText(text, 0)

    # ================================================================== viste
    def on_select_view(self, view):
        if view.get("kind") == "search_panel":
            self.show_search_panel(True)
            if not self.current_view or self.current_view.get("kind") != "search":
                self.list.set_articles([], "Cerca: scrivi il testo e premi Invio. Premi Invio sul menu per "
                                           "spostarti nel campo di ricerca")
            return
        self.show_search_panel(False)
        self.load_view(view)

    def run_action(self, action):
        handler = self.handlers.get(action)
        if handler:
            handler()

    def open_link(self, key):
        label, url = config.LINKS[key]
        webbrowser.open(url)
        announce(f"Apertura nel browser: {label}")

    def report_problem(self):
        dlg = ReportProblemDialog(self)
        dlg.ShowModal()
        dlg.Destroy()

    def on_activate_view(self, view):
        kind = view.get("kind")
        if kind == "action":
            self.run_action(view["action"])
            return
        if kind == "settings":
            self.open_settings()
        elif kind == "search_panel":
            self.show_search()
        else:
            self.list.focus()

    def load_view(self, view, keep_id=None):
        if not view:
            return
        kind = view.get("kind")
        if kind == "settings":
            self.current_view = view
            self.list.set_articles([], "Impostazioni: premi Invio sul menu per aprirle")
            return
        if kind == "choices":
            self.current_view = view
            self.list.set_choices(view["choices"], view["title"])
            return
        if kind == "action":
            self.current_view = view
            self.list.set_choices([(view["title"], "action:" + view["action"])], view["title"])
            return
        if kind == "source" and view.get("site_only"):
            self.current_view = view
            self.list.set_articles([], view["title"], site_view=view)
            return
        try:
            articles = self.core.news.list_view(view)
        except Exception:
            log.exception("Errore nel caricamento della vista %s", view)
            common.error(self, "Impossibile caricare le notizie di questa sezione. Dettagli nel file di registro.")
            return
        self.current_view = view
        self.list.set_articles(articles, view.get("title", "Notizie"), keep_id=keep_id)

    def refresh_view(self, announce_result=True):
        keep = self.list.selected_article()
        if self.current_view and self.current_view.get("kind") == "search":
            self.on_search(focus_list=False)
        else:
            self.load_view(self.current_view, keep_id=keep.id if keep else None)
        if announce_result:
            announce(f"Elenco aggiornato: {len(self.list.articles)} articoli")

    def go_section(self, key):
        """Scorciatoie Ctrl+1, Ctrl+2, Ctrl+H, Ctrl+D: seleziona la sezione e porta il focus all'elenco."""
        self.show_search_panel(False)
        self.sidebar.select_section(key, focus=False)
        view = self.sidebar.current_view()
        if self.sidebar._pending and self.sidebar._pending.IsRunning():
            self.sidebar._pending.Stop()
        self.load_view(view)
        self.list.focus()
        announce(self.list.heading.GetLabel())

    def show_search_panel(self, show):
        if self.search.IsShown() != show:
            self.search.Show(show)
            self.right.Layout()

    def show_search(self):
        self.sidebar.select_section("search", focus=False)
        if self.sidebar._pending and self.sidebar._pending.IsRunning():
            self.sidebar._pending.Stop()
        self.show_search_panel(True)
        self.search.refresh_choices()
        self.search.focus()

    def on_search(self, focus_list=True):
        try:
            params = self.search.params()
        except ValueError as exc:
            common.error(self, str(exc))
            return
        results = self.core.news.search(**params)
        description = self.search.describe(params)
        self.current_view = {"kind": "search", "params": params, "title": f"Risultati per {description}"}
        self.list.set_articles(results, f"Risultati della ricerca per {description}")
        if results:
            announce(f"{len(results)} risultati")
            if focus_list:
                self.list.focus()
        else:
            announce("Nessun risultato. Prova con altre parole o togli qualche filtro.")

    def cycle_pane(self, direction):
        panes = [self.sidebar.tree]
        if self.search.IsShown():
            panes.append(self.search.text)
        panes.append(self.list.list)
        focused = wx.Window.FindFocus()
        current = 0
        for i, pane in enumerate(panes):
            if focused is pane or (focused and pane.IsDescendant(focused)) or \
                    (pane is self.search.text and focused and self.search.IsDescendant(focused)):
                current = i
        target = panes[(current + direction) % len(panes)]
        if target is self.list.list:
            self.list.focus()
        else:
            target.SetFocus()

    def on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE and not event.HasAnyModifiers():
            if self.core.speech.state != "ferma":
                self.core.speech.stop()
                announce("Lettura interrotta")
                return
            focused = wx.Window.FindFocus()
            if focused and (focused is self.list.list or self.search.IsDescendant(focused)):
                self.sidebar.tree.SetFocus()
                return
        event.Skip()

    # ================================================================== articoli
    def go_key(self, key):
        """Apre una scelta dell'elenco (città, regione, testata...) come se fosse scelta nel menu."""
        self.sidebar.select_section(key, focus=False)
        if self.sidebar._pending and self.sidebar._pending.IsRunning():
            self.sidebar._pending.Stop()
        self.load_view(self.sidebar.current_view())
        self.list.focus()
        announce(self.list.heading.GetLabel())

    def open_selected(self, start_reading=False):
        choice = self.list.selected_choice()
        if choice and choice.startswith("action:"):
            self.run_action(choice.split(":", 1)[1])
            return
        if choice:
            self.go_key(choice)
            return
        if self.list.site_row_selected():
            url = self.list.site_view.get("site_url")
            if url:
                webbrowser.open(url)
                announce("Apertura del sito originale nel browser")
            return
        art = self.list.selected_article()
        if art is None:
            announce("Nessun articolo selezionato")
            return
        article = prepare_article(self, self.core, art.id)
        if article is None:
            common.error(self, "L'articolo non è più disponibile.")
            return
        dlg = ReaderDialog(self, self.core, article, self.list.ids(), start_reading=start_reading)
        dlg.ShowModal()
        last_id = dlg.article.id
        dlg.Destroy()
        if self.current_view and self.current_view.get("kind") != "search":
            self.load_view(self.current_view, keep_id=last_id)
        else:
            self._refresh_rows()
        self.list.focus()

    def _refresh_rows(self):
        for art in list(self.list.articles):
            updated = self.core.news.get_article(art.id)
            if updated:
                self.list.update_article(updated)

    def _selected_or_warn(self):
        art = self.list.selected_article()
        if art is None:
            announce("Nessun articolo selezionato")
        return art

    def toggle_save(self):
        art = self._selected_or_warn()
        if not art:
            return
        saved = self.core.favorites.toggle(art.id)
        announce("Articolo salvato nei preferiti" if saved else "Articolo rimosso dai preferiti")
        if not saved and self.current_view and self.current_view.get("kind") == "saved":
            self.list.remove_article(art.id)
        else:
            self.list.update_article(self.core.news.get_article(art.id))

    def toggle_to_read(self):
        art = self._selected_or_warn()
        if art:
            current = self.core.news.get_article(art.id)
            self.core.favorites.set_to_read(art.id, not current.to_read)
            announce("Segnato da leggere" if not current.to_read else "Tolto da «da leggere»")
            self.list.update_article(self.core.news.get_article(art.id))

    def move_to_folder(self):
        art = self._selected_or_warn()
        if not art:
            return
        ok, folder_id = choose_folder(self, self.core)
        if ok:
            self.core.favorites.move_to_folder(art.id, folder_id)
            self.sidebar.build(keep_key=(self.current_view or {}).get("key"))
            self.list.update_article(self.core.news.get_article(art.id))
            announce("Articolo spostato")
            self.list.focus()

    def download_selected(self):
        art = self._selected_or_warn()
        if not art:
            return
        article = self.core.news.get_article(art.id)
        db_path = self.core.db.path
        settings = self.core.settings

        def work():
            from ..database import Database
            from ..download_manager import DownloadManager
            db = Database(db_path)
            try:
                return DownloadManager(db, settings).download(article)
            finally:
                db.close()

        status, exc, cancelled = common.run_with_wait(self, "Download dell'articolo in corso...", work)
        if cancelled:
            return
        if exc:
            common.error(self, f"Download non riuscito: {exc}")
            return
        self.list.update_article(self.core.news.get_article(art.id))
        announce("Articolo disponibile offline" + ("" if status == "completo" else " (solo l'anteprima del feed)"))
        self.list.focus()

    def remove_offline(self):
        art = self._selected_or_warn()
        if art:
            self.core.downloads.remove(art.id)
            announce("Rimosso dall'archivio offline")
            if self.current_view and self.current_view.get("kind") == "offline":
                self.list.remove_article(art.id)
            else:
                self.list.update_article(self.core.news.get_article(art.id))

    def remove_from_history(self):
        art = self._selected_or_warn()
        if art:
            self.core.history.remove(art.id)
            announce("Rimosso dalla cronologia")
            if self.current_view and self.current_view.get("kind") == "history":
                self.list.remove_article(art.id)

    def clear_history(self):
        if common.confirm(self, "Cancellare tutta la cronologia?"):
            self.core.history.clear()
            if self.current_view and self.current_view.get("kind") == "history":
                self.load_view(self.current_view)
            announce("Cronologia cancellata")

    def on_delete_key(self):
        kind = (self.current_view or {}).get("kind")
        art = self.list.selected_article()
        if not art:
            return
        if kind == "saved":
            if common.confirm(self, f"Rimuovere dai preferiti «{art.title}»?"):
                self.core.favorites.remove(art.id)
                self.list.remove_article(art.id)
                announce("Rimosso dai preferiti")
        elif kind == "history":
            self.remove_from_history()
        elif kind == "offline":
            self.remove_offline()
        else:
            announce("Il tasto Canc rimuove gli articoli solo in Articoli salvati, Disponibili offline e Cronologia.")

    def open_original(self):
        if self.list.site_row_selected():
            webbrowser.open(self.list.site_view.get("site_url"))
            return
        art = self._selected_or_warn()
        if art:
            url = art.link or art.site_url
            if url:
                webbrowser.open(url)
                announce("Apertura dell'articolo originale nel browser")

    def copy_link(self):
        art = self._selected_or_warn()
        if art and art.link and wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(art.link))
            wx.TheClipboard.Close()
            announce("Collegamento copiato negli appunti")

    def export_selected(self):
        art = self._selected_or_warn()
        if art:
            try:
                path = self.core.downloads.export_txt(self.core.news.get_article(art.id),
                                                      self.core.settings.download_dir())
            except OSError as exc:
                common.error(self, f"Esportazione non riuscita: {exc}")
                return
            common.info(self, f"Articolo esportato nel file:\n{path}")

    def print_selected(self):
        art = self._selected_or_warn()
        if art:
            common.print_article(self, self.core, self.core.news.get_article(art.id))

    def stop_speech(self):
        self.core.speech.stop()
        announce("Lettura interrotta")

    def show_context_menu(self):
        if self.list.selected_article() is None and not self.list.site_row_selected():
            return
        menu = wx.Menu()
        kind = (self.current_view or {}).get("kind")
        entries = [("open", "&Apri"), ("read", "A&scolta"), ("save", "Salva o rimuovi dai &preferiti"),
                   ("to_read", "Segna o togli «&da leggere»"), ("move_folder", "Sposta in &cartella..."),
                   ("download", "Scarica &offline"), ("remove_offline", "Rimuovi dall'archivio o&ffline"),
                   ("open_original", "Apri l'o&riginale"), ("copy_link", "Copia il co&llegamento"),
                   ("export", "&Esporta come testo"), ("print", "S&tampa")]
        if kind == "history":
            entries.append(("remove_history", "Rimuovi dalla cro&nologia"))
        for action, label in entries:
            menu.Append(self._id(action), label)
        self.PopupMenu(menu)
        menu.Destroy()

    # ================================================================== aggiornamenti
    def refresh_news(self):
        if self.updater.running:
            announce("Aggiornamento già in corso")
            return
        self.updater.trigger()

    def update_selected_source(self):
        view = self.current_view or {}
        art = self.list.selected_article()
        source_id = view.get("source_id") or (art.source_id if art else None)
        if not source_id:
            announce("Seleziona prima una testata o un suo articolo")
            return
        self.updater.trigger(source_id)

    def on_update_start(self, manual):
        if manual:
            announce("Aggiornamento delle notizie in corso...")
        else:
            self.set_status("Aggiornamento automatico delle notizie in corso...")

    def on_update_done(self, summary):
        if not self:
            return
        self.SetStatusText(f"Ultimo aggiornamento: {self.core.last_update_text()}", 1)
        if summary.offline:
            message = ("Connessione a Internet assente o fonti non raggiungibili: puoi leggere gli articoli già "
                       "scaricati. Riproverò al prossimo aggiornamento.")
        else:
            message = f"Aggiornamento completato: {summary.new_articles} nuove notizie"
            if summary.failed:
                message += f", {len(summary.failed)} feed non raggiungibili (menu Fonti)"
            if summary.discovered:
                names = sorted({name for name, _ in summary.discovered})
                message += f". Trovati nuovi feed per: {', '.join(names)}"
                self.sidebar.build(keep_key=(self.current_view or {}).get("key"))
                self.search.refresh_choices()
            if summary.new_articles and not self.core.settings.get("auto_refresh_view") and not summary.manual:
                message += ". Premi F5 per aggiornare l'elenco"
        refresh = summary.manual or self.core.settings.get("auto_refresh_view")
        if refresh and summary.new_articles and self.current_view and self.current_view.get("kind") not in (
                "settings", "search"):
            self.refresh_view(announce_result=False)
        if summary.manual or summary.offline or (summary.new_articles and self.core.settings.get("notify_new")):
            announce(message)
        else:
            self.set_status(message)
        if summary.new_articles and self.core.settings.get("notify_windows"):
            try:
                import wx.adv
                note = wx.adv.NotificationMessage(config.APP_NAME, message, self)
                note.Show(timeout=6)
            except Exception:
                log.exception("Notifica di Windows non disponibile")

    def show_failed(self):
        summary = self.updater.last_summary
        if summary is None:
            text = "Nessun aggiornamento eseguito in questa sessione. Premi Ctrl+R per aggiornare."
        elif not summary.failed:
            text = "Tutte le fonti hanno risposto correttamente all'ultimo aggiornamento."
        else:
            text = "\n".join(f"{name}: {err}\n   {url}" for name, url, err in summary.failed)
            text = (f"Ultimo aggiornamento: {format_date(summary.finished_at)}. Feed non raggiungibili: "
                    f"{len(summary.failed)}\n\n" + text)
        dlg = TextDialog(self, "Fonti non raggiungibili - " + config.APP_NAME, text, "&Elenco:")
        dlg.ShowModal()
        dlg.Destroy()

    # ================================================================== finestre
    def open_settings(self):
        dlg = SettingsDialog(self, self.core)
        result = dlg.ShowModal()
        shortcuts_changed, data_changed = dlg.shortcuts_changed, dlg.data_changed
        dlg.Destroy()
        if result == wx.ID_OK or shortcuts_changed:
            self.rebuild_accelerators()
            common.apply_theme(self, self.core.settings)
            self.updater.reschedule()
        if shortcuts_changed:
            old = self.GetMenuBar()
            self._build_menu()
            if old:
                old.Destroy()
        if data_changed:
            self.sidebar.build(keep_key="settings")
        announce("Impostazioni salvate" if result == wx.ID_OK else "Impostazioni non modificate")

    def open_sources(self):
        dlg = SourcesDialog(self, self.core)
        dlg.ShowModal()
        changed = dlg.changed
        dlg.Destroy()
        if changed:
            key = (self.current_view or {}).get("key")
            self.sidebar.build(keep_key=key)
            self.search.refresh_choices()
            if common.confirm(self, "Le fonti sono cambiate. Vuoi aggiornare subito le notizie?"):
                self.updater.trigger()

    def manage_folders(self):
        dlg = FoldersDialog(self, self.core)
        dlg.ShowModal()
        changed = dlg.changed
        dlg.Destroy()
        if changed:
            self.sidebar.build(keep_key=(self.current_view or {}).get("key"))

    def show_help(self):
        dlg = HelpDialog(self, self.core)
        dlg.ShowModal()
        dlg.Destroy()

    def backup_now(self):
        try:
            path = database.backup_database(self.core.db)
        except Exception as exc:
            common.error(self, f"Backup non riuscito: {exc}")
            return
        common.info(self, f"Backup creato:\n{path}")
