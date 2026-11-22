"""KILLA NEWS 1.0.0 - Killa Records - L'informazione, senza barriere.

Avvio:  python main.py
"""
import logging
import sys
import traceback


def main():
    from killanews import config
    from killanews.core import Core, setup_logging

    setup_logging()
    log = logging.getLogger("killanews")
    log.info("Avvio di %s %s", config.APP_NAME, config.APP_VERSION)

    try:
        import wx
    except ImportError:
        print("Manca wxPython. Installa le dipendenze con:  pip install -r requirements.txt")
        return 1

    if sys.platform.startswith("win"):
        try:  # testo nitido su schermi ad alta risoluzione
            import ctypes
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

    app = wx.App(False)
    app.SetAppName(config.APP_ID)
    with wx.LogNull():  # testi standard (OK, Annulla...) in italiano, se disponibili
        locale = wx.Locale(wx.LANGUAGE_ITALIAN)  # noqa: F841

    checker = wx.SingleInstanceChecker(config.APP_ID + "-" + wx.GetUserId())
    if checker.IsAnotherRunning():
        wx.MessageBox("KILLA NEWS è già aperto. Usa Alt+Tab per passare alla finestra.", config.APP_NAME,
                      wx.OK | wx.ICON_INFORMATION)
        return 0

    def excepthook(exc_type, exc, tb):
        if exc_type is RuntimeError and "has been deleted" in str(exc):
            # evento arrivato a un controllo già chiuso (per esempio durante la chiusura): innocuo
            log.warning("Evento ignorato su un controllo chiuso: %s", exc)
            return
        log.error("Errore non gestito:\n%s", "".join(traceback.format_exception(exc_type, exc, tb)))
        try:
            wx.MessageBox(f"Si è verificato un errore imprevisto: {exc}\n\nIl programma continua a funzionare. "
                          f"I dettagli sono nel file {config.log_path()}", config.APP_NAME, wx.OK | wx.ICON_ERROR)
        except Exception:
            pass

    sys.excepthook = excepthook

    try:
        core = Core()
    except Exception as exc:
        log.exception("Impossibile aprire il database")
        wx.MessageBox(f"Impossibile aprire i dati di KILLA NEWS:\n{exc}\n\nPuoi ripristinare un backup dalla "
                      f"cartella {config.backup_dir()}", config.APP_NAME, wx.OK | wx.ICON_ERROR)
        return 1

    from killanews.ui.main_window import MainFrame
    frame = MainFrame(core)
    frame.Show()
    app.MainLoop()
    del checker
    return 0


if __name__ == "__main__":
    sys.exit(main())
