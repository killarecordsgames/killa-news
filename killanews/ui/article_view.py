"""Lettore degli articoli: testo navigabile con le frecce, lettura vocale a paragrafi,
salvataggio, download offline, esportazione e apertura della fonte originale."""
import webbrowser

import wx

from .. import article_reader, config
from ..accessibility import announce
from ..database import Database
from ..speech_manager import STATE_PAUSED, STATE_SPEAKING, STATE_STOPPED
from . import common
from .common import shortcut_hint


def prepare_article(parent, core, article_id):
    """Carica l'articolo e, se consentito, recupera il testo integrale dalla pagina pubblica
    mostrando una finestra di attesa annullabile. Restituisce l'articolo aggiornato."""
    article = core.news.get_article(article_id)
    if article is None:
        return None
    needs_fetch = (article.content_status != "completo" and article.fulltext_allowed and article.link
                   and core.settings.get("fetch_full_text", True))
    if needs_fetch:
        db_path = core.db.path

        def work():
            result = article_reader.fetch_full_text(article.link, article.description)
            db = Database(db_path)
            try:
                article_reader.save_extract(db, article.id, result)
            finally:
                db.close()
            return result

        result, exc, cancelled = common.run_with_wait(
            parent, f"Caricamento del testo completo dell'articolo «{article.title[:80]}» in corso...", work)
        article = core.news.get_article(article_id)
        if result is not None and result.status != "completo":
            article.extra["partial_reason"] = result.reason
    core.history.record(article_id)
    return article


class ReaderDialog(wx.Dialog):
    def __init__(self, parent, core, article, article_ids=None, start_reading=False):
        super().__init__(parent, title=article.title + " - " + config.APP_NAME,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER | wx.MAXIMIZE_BOX)
        self.core = core
        self.article = article
        self.article_ids = list(article_ids or [article.id])
        self.index = self.article_ids.index(article.id) if article.id in self.article_ids else 0
        self.spoken = []
        self.offsets = []
        self.changed = False
        speech = core.speech

        main = wx.BoxSizer(wx.VERTICAL)
        main.Add(wx.StaticText(self, label="&Testo dell'articolo (usa le frecce per leggerlo):"), 0, wx.ALL, 6)
        self.text = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2 | wx.TE_AUTO_URL
                                | wx.TE_NOHIDESEL)
        main.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        main.Add(wx.StaticText(self, label="Stato della &lettura vocale:"), 0, wx.ALL, 6)
        self.status = wx.TextCtrl(self, style=wx.TE_READONLY)
        main.Add(self.status, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)

        def button(label, handler, sizer):
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, lambda e: handler())
            sizer.Add(b, 0, wx.ALL, 3)
            return b

        voice_row = wx.WrapSizer(wx.HORIZONTAL)
        self.b_read = button("Inizia lettura" + shortcut_hint(core, "read"), self.start_reading, voice_row)
        self.b_pause = button("Pausa o riprendi" + shortcut_hint(core, "pause"), self.toggle_pause, voice_row)
        self.b_stop = button("Interrompi" + shortcut_hint(core, "stop_speech"), self.stop_reading, voice_row)
        button("Torna all'inizio" + shortcut_hint(core, "restart"), self.restart, voice_row)
        button("Paragrafo precedente" + shortcut_hint(core, "prev_par"), self.prev_par, voice_row)
        button("Paragrafo successivo" + shortcut_hint(core, "next_par"), self.next_par, voice_row)
        main.Add(voice_row, 0, wx.EXPAND | wx.ALL, 3)

        art_row = wx.WrapSizer(wx.HORIZONTAL)
        self.b_prev = button("Articolo precedente" + shortcut_hint(core, "prev_article"), self.prev_article, art_row)
        self.b_next = button("Articolo successivo" + shortcut_hint(core, "next_article"), self.next_article, art_row)
        self.b_save = button("Salva nei preferiti", self.toggle_save, art_row)
        self.b_offline = button("Scarica per la lettura offline" + shortcut_hint(core, "download"), self.download,
                                art_row)
        button("Apri articolo originale" + shortcut_hint(core, "open_original"), self.open_original, art_row)
        button("Esporta come testo" + shortcut_hint(core, "export"), self.export, art_row)
        button("Stampa" + shortcut_hint(core, "print"), self.print_article, art_row)
        close = wx.Button(self, wx.ID_CLOSE, "&Chiudi (Esc)")
        art_row.Add(close, 0, wx.ALL, 3)
        main.Add(art_row, 0, wx.EXPAND | wx.ALL, 3)
        self.SetSizer(main)
        self.SetSize(self.FromDIP(wx.Size(900, 680)))
        self.CentreOnParent()

        close.Bind(wx.EVT_BUTTON, lambda e: self.close())
        self.Bind(wx.EVT_CLOSE, lambda e: self.close())
        self.Bind(wx.EVT_CHAR_HOOK, self._on_char_hook)
        self._bind_accelerators()
        self._prev_state_cb = speech.on_state_change
        speech.on_state_change = self._on_speech_state
        speech.on_finished = self._on_speech_finished
        self.show_article(article)
        common.apply_theme(self, core.settings)
        if start_reading:
            wx.CallAfter(self.start_reading)

    # ------------------------------------------------------------------ scorciatoie
    def _bind_accelerators(self):
        handlers = {
            "read": self.start_reading, "pause": self.toggle_pause, "stop_speech": self.stop_reading,
            "restart": self.restart, "next_par": self.next_par, "prev_par": self.prev_par,
            "next_article": self.next_article, "prev_article": self.prev_article, "save": self.toggle_save,
            "download": self.download, "open_original": self.open_original, "export": self.export,
            "help": self.show_help, "print": self.print_article,
        }
        entries = []
        for action, combo in self.core.keyboard.for_scope("reader"):
            if action not in handlers:
                continue
            cmd = wx.NewIdRef()
            self.Bind(wx.EVT_MENU, lambda e, h=handlers[action]: h(), id=cmd)
            entry = common.accel_entry(combo, cmd)
            if entry:
                entries.append(entry)
        self.SetAcceleratorTable(wx.AcceleratorTable(entries))

    def _on_char_hook(self, event):
        if event.GetKeyCode() == wx.WXK_ESCAPE:
            if self.core.speech.state != STATE_STOPPED:
                self.stop_reading()
                announce("Lettura interrotta")
            else:
                self.close()
            return
        event.Skip()

    # ------------------------------------------------------------------ contenuto
    def show_article(self, article):
        self.article = article
        self.SetTitle(article.title + " - " + config.APP_NAME)
        cat = self.core.catalog.category_name(article.category_id) if article.category_id else article.category_name
        text, self.spoken, self.offsets = article_reader.build_reader_text(article, cat)
        if article.extra.get("partial_reason") and article.is_partial:
            text += "\n" + "Motivo: " + article.extra["partial_reason"]
        self.text.SetValue(text)
        self.text.SetInsertionPoint(0)
        self.text.ShowPosition(0)
        self.core.speech.load(self.spoken)
        self._refresh_buttons()
        self._set_status(f"ferma. Articolo {self.index + 1} di {len(self.article_ids)}. "
                         + ("Testo parziale: apri l'articolo originale per leggerlo tutto."
                            if article.is_partial else "Testo completo."))
        self.text.SetFocus()

    def _refresh_buttons(self):
        a = self.core.news.get_article(self.article.id) or self.article
        self.article.saved, self.article.offline = a.saved, a.offline
        self.b_save.SetLabel(("Rimuovi dai preferiti" if a.saved else "Salva nei preferiti")
                             + shortcut_hint(self.core, "save"))
        self.b_offline.SetLabel(("Disponibile offline (scarica di nuovo)" if a.offline
                                 else "Scarica per la lettura offline") + shortcut_hint(self.core, "download"))
        self.b_prev.Enable(self.index > 0)
        self.b_next.Enable(self.index < len(self.article_ids) - 1)
        self.b_read.Enable(self.core.speech.available)
        self.Layout()

    def _set_status(self, text):
        self.status.SetValue(text)

    def _current_paragraph(self):
        pos = common.ui_pos_to_index(self.text, self.text.GetInsertionPoint())
        for i, (start, end) in enumerate(self.offsets):
            if pos <= end:
                return i
        return max(0, len(self.offsets) - 1)

    # ------------------------------------------------------------------ voce
    def _check_speech(self):
        if not self.core.speech.available:
            common.error(self, self.core.speech.backend.error + "\n\nPuoi comunque leggere il testo con NVDA "
                         "(per esempio con NVDA+Freccia giù per la lettura continua).")
            return False
        return True

    def start_reading(self):
        if self._check_speech():
            self.core.speech.start(self._current_paragraph())

    def toggle_pause(self):
        if self._check_speech():
            if self.core.speech.state == STATE_STOPPED:
                self.core.speech.start(self._current_paragraph())
            else:
                self.core.speech.toggle_pause()

    def stop_reading(self):
        self.core.speech.stop()

    def restart(self):
        if self._check_speech():
            self.core.speech.restart()

    def next_par(self):
        if self._check_speech():
            sp = self.core.speech
            if sp.state == STATE_STOPPED:
                sp.start(min(self._current_paragraph() + 1, len(self.spoken) - 1))
            elif not sp.next_paragraph():
                announce("Ultimo paragrafo")

    def prev_par(self):
        if self._check_speech():
            sp = self.core.speech
            if sp.state == STATE_STOPPED:
                sp.start(max(self._current_paragraph() - 1, 0))
            else:
                sp.previous_paragraph()

    def _on_speech_state(self, state, index, total):
        if not self:
            return
        if state == STATE_SPEAKING:
            text = f"in lettura, paragrafo {index + 1} di {total}"
        elif state == STATE_PAUSED:
            text = f"in pausa al paragrafo {index + 1} di {total}"
        else:
            text = "ferma"
        self._set_status(text)
        if state == STATE_SPEAKING and self.core.settings.get("follow_reading_caret", False) and index < len(self.offsets):
            pos = common.index_to_ui_pos(self.text, self.offsets[index][0])
            self.text.SetInsertionPoint(pos)
            self.text.ShowPosition(pos)

    def _on_speech_finished(self):
        if self:
            self._set_status("lettura terminata")

    # ------------------------------------------------------------------ articoli
    def _go(self, delta):
        new = self.index + delta
        if not (0 <= new < len(self.article_ids)):
            announce("Non ci sono altri articoli in questa direzione")
            return
        self.core.speech.stop()
        article = prepare_article(self, self.core, self.article_ids[new])
        if article is None:
            return
        self.index = new
        self.show_article(article)
        announce(article.title)

    def next_article(self):
        self._go(1)

    def prev_article(self):
        self._go(-1)

    def toggle_save(self):
        saved = self.core.favorites.toggle(self.article.id)
        self.changed = True
        self._refresh_buttons()
        announce("Articolo salvato nei preferiti" if saved else "Articolo rimosso dai preferiti")

    def download(self):
        art = self.core.news.get_article(self.article.id)
        db_path = self.core.db.path

        def work():
            from ..download_manager import DownloadManager
            db = Database(db_path)
            try:
                return DownloadManager(db, self.core.settings).download(art)
            finally:
                db.close()

        status, exc, cancelled = common.run_with_wait(self, "Download dell'articolo in corso...", work)
        if cancelled:
            return
        if exc:
            common.error(self, f"Download non riuscito: {exc}")
            return
        self.changed = True
        updated = self.core.news.get_article(self.article.id)
        if updated.content != self.article.content:
            self.show_article(updated)
        self._refresh_buttons()
        announce("Articolo disponibile offline" + ("" if status == "completo" else " (solo l'anteprima del feed)"))

    def open_original(self):
        url = self.article.link or self.article.site_url
        if url:
            webbrowser.open(url)
            announce("Apertura dell'articolo originale nel browser")
        else:
            common.info(self, "Per questo articolo non è disponibile un collegamento alla fonte.")

    def export(self):
        folder = self.core.settings.download_dir()
        try:
            path = self.core.downloads.export_txt(self.article, folder)
        except OSError as exc:
            common.error(self, f"Impossibile salvare il file nella cartella {folder}:\n{exc}")
            return
        common.info(self, f"Articolo esportato nel file:\n{path}")

    def print_article(self):
        self.core.speech.stop()
        common.print_article(self, self.core, self.core.news.get_article(self.article.id) or self.article)

    def show_help(self):
        from .dialogs import HelpDialog
        HelpDialog(self, self.core).ShowModal()

    def close(self):
        self.core.speech.stop()
        self.core.speech.on_state_change = self._prev_state_cb
        self.core.speech.on_finished = None
        if self.IsModal():
            self.EndModal(wx.ID_CLOSE)
        else:
            self.Destroy()
