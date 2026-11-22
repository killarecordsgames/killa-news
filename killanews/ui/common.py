"""Funzioni comuni dell'interfaccia: temi, caratteri, acceleratori e finestre di messaggio.

Regola di accessibilità seguita in tutta l'interfaccia: ogni controllo è preceduto
da un'etichetta (wx.StaticText) creata subito prima, così Windows e NVDA associano
automaticamente il nome al controllo; i pulsanti hanno sempre un testo."""
import threading

import wx

from .. import config
from ..keyboard_manager import to_italian

THEMES = {
    "sistema": None,
    "chiaro": (wx.Colour(255, 255, 255), wx.Colour(0, 0, 0)),
    "scuro": (wx.Colour(30, 30, 30), wx.Colour(240, 240, 240)),
    "alto_contrasto": (wx.Colour(0, 0, 0), wx.Colour(255, 255, 0)),
}
THEME_LABELS = [("sistema", "Colori di sistema (consigliato, rispetta il contrasto elevato di Windows)"),
                ("chiaro", "Tema chiaro"), ("scuro", "Tema scuro"),
                ("alto_contrasto", "Contrasto elevato (giallo su nero)")]

_KEYS = {
    "Up": wx.WXK_UP, "Down": wx.WXK_DOWN, "Left": wx.WXK_LEFT, "Right": wx.WXK_RIGHT,
    "Home": wx.WXK_HOME, "End": wx.WXK_END, "PageUp": wx.WXK_PAGEUP, "PageDown": wx.WXK_PAGEDOWN,
    "Delete": wx.WXK_DELETE, "Back": wx.WXK_BACK, "Space": wx.WXK_SPACE, "Enter": wx.WXK_RETURN,
    "Escape": wx.WXK_ESCAPE, ".": ord("."), ",": ord(","),
}


def accel_entry(combo: str, cmd_id: int):
    """'Ctrl+Shift+F' -> wx.AcceleratorEntry."""
    if not combo:
        return None
    parts = combo.split("+")
    key = parts[-1]
    flags = wx.ACCEL_NORMAL
    for mod in parts[:-1]:
        flags |= {"Ctrl": wx.ACCEL_CTRL, "Alt": wx.ACCEL_ALT, "Shift": wx.ACCEL_SHIFT}[mod]
    if key in _KEYS:
        code = _KEYS[key]
    elif key.startswith("F") and key[1:].isdigit():
        code = wx.WXK_F1 + int(key[1:]) - 1
    else:
        code = ord(key.upper())
    return wx.AcceleratorEntry(flags, code, cmd_id)


def shortcut_hint(core, action):
    """Testo da mostrare nelle etichette: ' (Ctrl+F)'."""
    combo = core.keyboard.get(action)
    return f" ({to_italian(combo)})" if combo else ""


def make_font(settings):
    size = int(settings.get("font_size", 12) or 12)
    face = settings.get("font_face", "") or ""
    font = wx.Font(wx.FontInfo(max(8, min(size, 40))).FaceName(face) if face else wx.FontInfo(max(8, min(size, 40))))
    return font


def apply_theme(window, settings):
    """Applica tema e caratteri a una finestra e a tutti i suoi controlli."""
    theme = THEMES.get(settings.get("theme", "sistema"))
    font = make_font(settings)

    def visit(win):
        try:
            if isinstance(win, (wx.ListCtrl, wx.TreeCtrl, wx.TextCtrl, wx.StaticText, wx.ListBox,
                                wx.Choice, wx.ComboBox, wx.CheckBox, wx.Button, wx.SpinCtrl)):
                win.SetFont(font)
            if theme is None:
                win.SetBackgroundColour(wx.NullColour)
                win.SetForegroundColour(wx.NullColour)
            else:
                bg, fg = theme
                win.SetBackgroundColour(bg)
                win.SetForegroundColour(fg)
                if isinstance(win, wx.ListCtrl):
                    win.SetTextColour(fg)
            if isinstance(win, wx.TextCtrl) and win.IsMultiLine():
                attr = wx.TextAttr(theme[1] if theme else wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOWTEXT),
                                   theme[0] if theme else wx.SystemSettings.GetColour(wx.SYS_COLOUR_WINDOW), font)
                win.SetDefaultStyle(attr)
                win.SetStyle(0, win.GetLastPosition(), attr)
        except RuntimeError:
            return
        for child in win.GetChildren():
            visit(child)

    visit(window)
    window.Layout()
    window.Refresh()


def labeled(parent, sizer, label, ctrl_factory, expand=True, proportion=0):
    """Crea un'etichetta e SUBITO DOPO il controllo (ordine necessario per i lettori di schermo)."""
    lbl = wx.StaticText(parent, label=label)
    sizer.Add(lbl, 0, wx.LEFT | wx.RIGHT | wx.TOP, 6)
    ctrl = ctrl_factory()
    sizer.Add(ctrl, proportion, (wx.EXPAND if expand else 0) | wx.ALL, 6)
    return ctrl


def info(parent, message, title=config.APP_NAME):
    wx.MessageBox(message, title, wx.OK | wx.ICON_INFORMATION, parent)


def error(parent, message, title="Errore - " + config.APP_NAME):
    wx.MessageBox(message, title, wx.OK | wx.ICON_ERROR, parent)


def confirm(parent, message, title=config.APP_NAME) -> bool:
    dlg = wx.MessageDialog(parent, message, title, wx.YES_NO | wx.NO_DEFAULT | wx.ICON_QUESTION)
    dlg.SetYesNoLabels("&Sì", "&No")
    try:
        return dlg.ShowModal() == wx.ID_YES
    finally:
        dlg.Destroy()


def ask_text(parent, message, title, value=""):
    dlg = wx.TextEntryDialog(parent, message, title, value)
    try:
        if dlg.ShowModal() == wx.ID_OK:
            return dlg.GetValue().strip()
        return None
    finally:
        dlg.Destroy()


class WaitDialog(wx.Dialog):
    """Finestra di attesa accessibile: esegue `work()` in un thread e si chiude da sola.
    Il pulsante Annulla ha il focus, così NVDA legge subito il messaggio."""

    def __init__(self, parent, message, work, title="Attendere - " + config.APP_NAME):
        super().__init__(parent, title=title)
        self.result = None
        self.error = None
        self.cancelled = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.text = wx.StaticText(self, label=message)
        sizer.Add(self.text, 0, wx.ALL, 12)
        self.cancel = wx.Button(self, wx.ID_CANCEL, "&Annulla")
        sizer.Add(self.cancel, 0, wx.ALL | wx.ALIGN_CENTER, 12)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self._on_cancel, id=wx.ID_CANCEL)
        self.Bind(wx.EVT_CLOSE, self._on_cancel)
        self._work = work
        self.cancel.SetFocus()

    def run(self):
        def target():
            try:
                res = self._work()
                wx.CallAfter(self._finish, res, None)
            except Exception as exc:  # comunicato all'interfaccia
                wx.CallAfter(self._finish, None, exc)

        threading.Thread(target=target, daemon=True).start()
        self.ShowModal()
        self.Destroy()
        return self.result

    def _finish(self, result, exc):
        if self.cancelled:
            return
        self.result, self.error = result, exc
        if self.IsModal():
            self.EndModal(wx.ID_OK)

    def _on_cancel(self, event):
        self.cancelled = True
        if self.IsModal():
            self.EndModal(wx.ID_CANCEL)


def run_with_wait(parent, message, work):
    """Esegue `work` in background mostrando la finestra di attesa.
    Restituisce (risultato, eccezione, annullato)."""
    dlg = WaitDialog(parent, message, work)
    res = dlg.run()
    return res, dlg.error, dlg.cancelled


def ui_pos_to_index(ctrl, pos: int) -> int:
    """Converte una posizione del controllo di testo in indice della stringa Python.
    (Nei controlli multilinea di Windows a volte l'a capo conta come due caratteri.)"""
    value = ctrl.GetValue()
    if ctrl.GetLastPosition() == len(value):
        return pos
    index, ui = 0, 0
    while index < len(value) and ui < pos:
        ui += 2 if value[index] == "\n" else 1
        index += 1
    return index


def index_to_ui_pos(ctrl, index: int) -> int:
    value = ctrl.GetValue()
    if ctrl.GetLastPosition() == len(value):
        return index
    return index + value.count("\n", 0, index)


def print_article(parent, core, article):
    """Apre la finestra di stampa standard di Windows per l'articolo."""
    import wx.html
    from ..download_manager import DownloadManager
    from ..accessibility import announce
    html_text = DownloadManager.article_as_html(article, core.settings.get("font_size", 12))
    printer = wx.html.HtmlEasyPrinting("Stampa - " + config.APP_NAME, parent)
    size = max(10, min(int(core.settings.get("font_size", 12) or 12), 28))
    printer.SetStandardFonts(size)
    printer.SetHeader(f"{config.APP_NAME} - {article.source_name}", wx.html.PAGE_ALL)
    printer.SetFooter("Pagina @PAGENUM@ di @PAGESCNT@", wx.html.PAGE_ALL)
    if printer.PrintText(html_text, article.title):
        announce("Articolo inviato alla stampante")
    else:
        err = wx.Printer.GetLastError()
        if err == wx.PRINTER_ERROR:
            error(parent, "Stampa non riuscita. Controlla che la stampante sia accesa e collegata.")
        else:
            announce("Stampa annullata")
