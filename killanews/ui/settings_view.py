"""Impostazioni: schede Generale, Aspetto, Voce, Scorciatoie, Dati personali.
Le schede si cambiano con Ctrl+Tab (comportamento standard di Windows)."""
import os

import wx

from .. import config, database
from ..keyboard_manager import to_italian
from ..models import format_size
from . import common
from .dialogs import FoldersDialog, ShortcutEditDialog


class SettingsDialog(wx.Dialog):
    def __init__(self, parent, core):
        super().__init__(parent, title="Impostazioni - " + config.APP_NAME,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.core = core
        s = core.settings
        self.shortcuts_changed = False
        self.data_changed = False
        outer = wx.BoxSizer(wx.VERTICAL)
        self.book = wx.Notebook(self)
        outer.Add(self.book, 1, wx.EXPAND | wx.ALL, 6)

        # ---------------------------------------------------------------- Generale
        p = wx.Panel(self.book)
        sz = wx.BoxSizer(wx.VERTICAL)
        self.auto_update = wx.CheckBox(p, label="&Aggiorna automaticamente le notizie")
        self.auto_update.SetValue(bool(s.get("auto_update")))
        sz.Add(self.auto_update, 0, wx.ALL, 6)
        self.interval = common.labeled(p, sz, "&Frequenza degli aggiornamenti in minuti (da 5 a 1440):",
                                       lambda: wx.SpinCtrl(p, min=5, max=1440, initial=int(s.get("update_interval_min", 15))),
                                       expand=False)
        self.notify_new = wx.CheckBox(p, label="&Annuncia le nuove notizie con NVDA e nella barra di stato")
        self.notify_new.SetValue(bool(s.get("notify_new")))
        sz.Add(self.notify_new, 0, wx.ALL, 6)
        self.notify_windows = wx.CheckBox(p, label="Mostra anche le &notifiche di Windows")
        self.notify_windows.SetValue(bool(s.get("notify_windows")))
        sz.Add(self.notify_windows, 0, wx.ALL, 6)
        self.auto_refresh = wx.CheckBox(p, label="Ricarica da solo l'&elenco visualizzato dopo ogni aggiornamento "
                                                 "(sconsigliato con i lettori di schermo)")
        self.auto_refresh.SetValue(bool(s.get("auto_refresh_view")))
        sz.Add(self.auto_refresh, 0, wx.ALL, 6)
        self.fulltext = wx.CheckBox(p, label="Recupera il &testo integrale dalle pagine pubbliche quando è consentito")
        self.fulltext.SetValue(bool(s.get("fetch_full_text")))
        sz.Add(self.fulltext, 0, wx.ALL, 6)
        self.app_updates = wx.CheckBox(p, label="Controlla da solo se esiste una nuova &versione di KILLA NEWS")
        self.app_updates.SetValue(bool(s.get("check_app_updates", True)))
        sz.Add(self.app_updates, 0, wx.ALL, 6)
        self.retention = common.labeled(p, sz, "&Conserva gli articoli non salvati per giorni (da 1 a 365):",
                                        lambda: wx.SpinCtrl(p, min=1, max=365, initial=int(s.get("retention_days", 30))),
                                        expand=False)
        self.max_items = common.labeled(p, sz, "Numero &massimo di notizie per elenco (da 50 a 5000):",
                                        lambda: wx.SpinCtrl(p, min=50, max=5000, initial=int(s.get("max_list_items", 500))),
                                        expand=False)
        dl_row = wx.BoxSizer(wx.HORIZONTAL)
        self.download_dir = common.labeled(p, sz, "Cartella dei &download (articoli esportati in testo):",
                                           lambda: wx.TextCtrl(p, value=s.download_dir()))
        browse = wx.Button(p, label="&Sfoglia...")
        browse.Bind(wx.EVT_BUTTON, self.on_browse)
        dl_row.Add(browse, 0, wx.ALL, 6)
        sz.Add(dl_row)
        p.SetSizer(sz)
        self.book.AddPage(p, "Generale")

        # ---------------------------------------------------------------- Aspetto
        p = wx.Panel(self.book)
        sz = wx.BoxSizer(wx.VERTICAL)
        self.theme = common.labeled(p, sz, "&Tema e contrasto:",
                                    lambda: wx.Choice(p, choices=[label for _, label in common.THEME_LABELS]))
        keys = [k for k, _ in common.THEME_LABELS]
        self.theme.SetSelection(keys.index(s.get("theme", "sistema")) if s.get("theme") in keys else 0)
        self.font_size = common.labeled(p, sz, "&Dimensione dei caratteri (da 8 a 40):",
                                        lambda: wx.SpinCtrl(p, min=8, max=40, initial=int(s.get("font_size", 12))),
                                        expand=False)
        faces = sorted(set(wx.FontEnumerator.GetFacenames()))
        preferred = [f for f in ("Segoe UI", "Arial", "Verdana", "Tahoma", "Calibri", "Atkinson Hyperlegible")
                     if f in faces]
        self.faces = preferred + [f for f in faces if f not in preferred and not f.startswith("@")]
        self.font_face = common.labeled(p, sz, "Tipo di &carattere:", lambda: wx.Choice(p, choices=self.faces))
        cur = s.get("font_face", "Segoe UI")
        self.font_face.SetSelection(self.faces.index(cur) if cur in self.faces else 0)
        p.SetSizer(sz)
        self.book.AddPage(p, "Aspetto")

        # ---------------------------------------------------------------- Voce
        p = wx.Panel(self.book)
        sz = wx.BoxSizer(wx.VERTICAL)
        self.voices = core.speech.voices()
        names = ["Voce italiana predefinita di Windows"] + [v.name + (" - italiano" if v.is_italian else "")
                                                            for v in self.voices]
        self.voice = common.labeled(p, sz, "&Voce:", lambda: wx.Choice(p, choices=names))
        ids = [v.id for v in self.voices]
        self.voice.SetSelection(ids.index(s.get("voice_id")) + 1 if s.get("voice_id") in ids else 0)
        self.rate = common.labeled(p, sz, "Velocità di &lettura (da -10 lenta a 10 veloce, 0 normale):",
                                   lambda: wx.SpinCtrl(p, min=-10, max=10, initial=int(s.get("speech_rate", 0))),
                                   expand=False)
        self.volume = common.labeled(p, sz, "V&olume (da 0 a 100):",
                                     lambda: wx.SpinCtrl(p, min=0, max=100, initial=int(s.get("speech_volume", 100))),
                                     expand=False)
        self.follow = wx.CheckBox(p, label="&Sposta il cursore sul paragrafo letto dalla voce")
        self.follow.SetValue(bool(s.get("follow_reading_caret")))
        sz.Add(self.follow, 0, wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        test = wx.Button(p, label="&Prova la voce")
        test.Bind(wx.EVT_BUTTON, self.on_test_voice)
        stop = wx.Button(p, label="&Ferma la prova")
        stop.Bind(wx.EVT_BUTTON, lambda e: core.speech.stop())
        row.Add(test, 0, wx.ALL, 6)
        row.Add(stop, 0, wx.ALL, 6)
        sz.Add(row)
        if not core.speech.available:
            sz.Add(wx.StaticText(p, label=core.speech.backend.error), 0, wx.ALL, 6)
            test.Disable()
        p.SetSizer(sz)
        self.book.AddPage(p, "Voce")

        # ---------------------------------------------------------------- Scorciatoie
        p = wx.Panel(self.book)
        sz = wx.BoxSizer(wx.VERTICAL)
        self.keys = common.labeled(p, sz, "&Scorciatoie (premi Invio per modificarla):",
                                   lambda: wx.ListCtrl(p, style=wx.LC_REPORT | wx.LC_SINGLE_SEL,
                                                       size=p.FromDIP(wx.Size(620, 300))), proportion=1)
        self.keys.SetLabel("Scorciatoie")
        for i, (c, w) in enumerate((("Azione", 330), ("Combinazione", 160), ("Dove", 120))):
            self.keys.InsertColumn(i, c, width=w)
        row = wx.BoxSizer(wx.HORIZONTAL)
        edit = wx.Button(p, label="&Modifica...")
        edit.Bind(wx.EVT_BUTTON, self.on_edit_key)
        reset = wx.Button(p, label="&Ripristina tutte le predefinite")
        reset.Bind(wx.EVT_BUTTON, self.on_reset_keys)
        row.Add(edit, 0, wx.ALL, 6)
        row.Add(reset, 0, wx.ALL, 6)
        sz.Add(row)
        sz.Add(wx.StaticText(p, label="Le combinazioni con Insert, Bloc Maiusc o il tasto Windows non sono "
                                      "ammesse perché riservate a NVDA e a Windows."), 0, wx.ALL, 6)
        self.keys.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit_key)
        p.SetSizer(sz)
        self.book.AddPage(p, "Scorciatoie")
        self.reload_keys()

        # ---------------------------------------------------------------- Dati
        p = wx.Panel(self.book)
        sz = wx.BoxSizer(wx.VERTICAL)
        self.history_enabled = wx.CheckBox(p, label="Registra la &cronologia degli articoli letti")
        self.history_enabled.SetValue(bool(s.get("history_enabled")))
        sz.Add(self.history_enabled, 0, wx.ALL, 6)
        self.data_info = common.labeled(p, sz, "&Riepilogo dei dati:",
                                        lambda: wx.TextCtrl(p, style=wx.TE_MULTILINE | wx.TE_READONLY,
                                                            size=p.FromDIP(wx.Size(620, 130))))
        grid = wx.WrapSizer(wx.HORIZONTAL)
        for label, handler in (("Gestisci le &cartelle dei preferiti...", self.on_folders),
                               ("Svuota la cr&onologia", self.on_clear_history),
                               ("Elimina articoli offline più vecchi di &30 giorni", self.on_offline_old),
                               ("Svuota l'&archivio offline", self.on_offline_clear),
                               ("Crea un &backup ora", self.on_backup),
                               ("Ri&pristina un backup...", self.on_restore),
                               ("Apri la cartella dei &dati", self.on_open_data)):
            b = wx.Button(p, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            grid.Add(b, 0, wx.ALL, 4)
        sz.Add(grid, 0, wx.EXPAND)
        p.SetSizer(sz)
        self.book.AddPage(p, "Dati personali")
        self.refresh_data_info()

        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, "&OK")
        ok.SetDefault()
        buttons.AddButton(ok)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL, "&Annulla"))
        buttons.Realize()
        outer.Add(buttons, 0, wx.ALL | wx.ALIGN_RIGHT, 6)
        self.SetSizerAndFit(outer)
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.Bind(wx.EVT_BUTTON, self.on_cancel, id=wx.ID_CANCEL)
        self.book.SetFocus()

    # ------------------------------------------------------------------ dati
    def refresh_data_info(self):
        n_off, size = self.core.downloads.stats()
        lines = [
            f"Articoli salvati: {self.core.favorites.count()}",
            f"Articoli nella cronologia: {self.core.history.count()}",
            f"Articoli disponibili offline: {n_off} (circa {format_size(size)})",
            f"Dimensione totale del database: {format_size(self.core.db.size_bytes())}",
            f"Cartella dei dati: {config.user_data_dir()}",
        ]
        self.data_info.SetValue("\n".join(lines))

    def on_folders(self, event):
        dlg = FoldersDialog(self, self.core)
        dlg.ShowModal()
        self.data_changed = self.data_changed or dlg.changed
        dlg.Destroy()
        self.refresh_data_info()

    def on_clear_history(self, event):
        if common.confirm(self, "Cancellare tutta la cronologia?"):
            self.core.history.clear()
            self.data_changed = True
            self.refresh_data_info()

    def on_offline_old(self, event):
        n = self.core.downloads.remove_older_than(30)
        self.data_changed = True
        self.refresh_data_info()
        common.info(self, f"Rimossi dall'archivio offline {n} articoli.")

    def on_offline_clear(self, event):
        if common.confirm(self, "Rimuovere tutti gli articoli dall'archivio offline? Gli articoli salvati restano "
                                "tra i preferiti."):
            n = self.core.downloads.clear()
            self.data_changed = True
            self.refresh_data_info()
            common.info(self, f"Rimossi {n} articoli dall'archivio offline.")

    def on_backup(self, event):
        try:
            path = database.backup_database(self.core.db)
        except Exception as exc:
            common.error(self, f"Backup non riuscito: {exc}")
            return
        common.info(self, f"Backup creato:\n{path}")

    def on_restore(self, event):
        backups = database.list_backups()
        if not backups:
            common.info(self, "Non ci sono backup disponibili.")
            return
        dlg = wx.SingleChoiceDialog(self, "Scegli il backup da ripristinare. Il ripristino avviene al prossimo "
                                          "avvio del programma.", "Ripristina backup",
                                    [os.path.basename(b) for b in backups])
        if dlg.ShowModal() == wx.ID_OK:
            database.schedule_restore(backups[dlg.GetSelection()])
            common.info(self, "Il backup verrà ripristinato quando riavvii KILLA NEWS.")
        dlg.Destroy()

    def on_open_data(self, event):
        try:
            os.startfile(config.user_data_dir())  # type: ignore[attr-defined]
        except (AttributeError, OSError):
            common.info(self, config.user_data_dir())

    def on_browse(self, event):
        dlg = wx.DirDialog(self, "Scegli la cartella dei download", self.download_dir.GetValue())
        if dlg.ShowModal() == wx.ID_OK:
            self.download_dir.SetValue(dlg.GetPath())
        dlg.Destroy()

    # ------------------------------------------------------------------ scorciatoie
    def reload_keys(self, select=0):
        self.keys.DeleteAllItems()
        self.key_actions = []
        for i, (action, label, combo, scope) in enumerate(self.core.keyboard.all()):
            self.keys.InsertItem(i, label)
            self.keys.SetItem(i, 1, to_italian(combo))
            self.keys.SetItem(i, 2, {"main": "finestra principale", "reader": "lettore", "both": "ovunque"}[scope])
            self.key_actions.append(action)
        self.keys.Select(select)

    def on_edit_key(self, event):
        i = self.keys.GetFirstSelected()
        if i < 0:
            return
        dlg = ShortcutEditDialog(self, self.core, self.key_actions[i])
        if dlg.ShowModal() == wx.ID_OK:
            self.shortcuts_changed = True
            self.reload_keys(i)
        dlg.Destroy()
        self.keys.SetFocus()

    def on_reset_keys(self, event):
        if common.confirm(self, "Ripristinare tutte le scorciatoie predefinite?"):
            self.core.keyboard.reset()
            self.shortcuts_changed = True
            self.reload_keys()

    # ------------------------------------------------------------------ voce
    def _voice_id(self):
        i = self.voice.GetSelection()
        return self.voices[i - 1].id if i > 0 else ""

    def on_test_voice(self, event):
        self.core.speech.apply_settings(self._voice_id(), self.rate.GetValue(), self.volume.GetValue())
        self.core.speech.speak_text("Benvenuto in KILLA NEWS. L'informazione, senza barriere.")

    # ------------------------------------------------------------------ conferma
    def on_ok(self, event):
        folder = self.download_dir.GetValue().strip()
        values = {
            "auto_update": self.auto_update.GetValue(), "update_interval_min": self.interval.GetValue(),
            "notify_new": self.notify_new.GetValue(), "notify_windows": self.notify_windows.GetValue(),
            "auto_refresh_view": self.auto_refresh.GetValue(), "fetch_full_text": self.fulltext.GetValue(),
            "check_app_updates": self.app_updates.GetValue(),
            "retention_days": self.retention.GetValue(), "max_list_items": self.max_items.GetValue(),
            "download_dir": "" if folder == config.default_download_dir() else folder,
            "theme": common.THEME_LABELS[self.theme.GetSelection()][0], "font_size": self.font_size.GetValue(),
            "font_face": self.faces[self.font_face.GetSelection()] if self.faces else "",
            "voice_id": self._voice_id(), "speech_rate": self.rate.GetValue(),
            "speech_volume": self.volume.GetValue(), "follow_reading_caret": self.follow.GetValue(),
            "history_enabled": self.history_enabled.GetValue(),
        }
        self.core.settings.update(values)
        self.core.speech.stop()
        self.core.apply_speech_settings()
        self.EndModal(wx.ID_OK)

    def on_cancel(self, event):
        self.core.speech.stop()
        self.core.apply_speech_settings()
        self.EndModal(wx.ID_CANCEL)
