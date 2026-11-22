"""Annunci per i lettori di schermo.

Se nella cartella del programma è presente la libreria ufficiale di NVDA
'nvdaControllerClient.dll' (64 bit) - oppure 'nvdaControllerClient64.dll' /
'nvdaControllerClient32.dll' - i messaggi di stato vengono pronunciati da NVDA
senza spostare il focus. In alternativa il messaggio viene scritto nella barra di
stato (NVDA lo legge con NVDA+Fine) tramite la funzione di ripiego impostata
dall'interfaccia."""
import ctypes
import logging
import os
import struct
import sys

from . import config

log = logging.getLogger(__name__)


class Announcer:
    def __init__(self):
        self._nvda = None
        self.fallback = None   # funzione(testo) impostata dall'interfaccia
        self._load_nvda()

    def _load_nvda(self):
        if not sys.platform.startswith("win"):
            return
        bits = struct.calcsize("P") * 8
        names = ["nvdaControllerClient.dll", f"nvdaControllerClient{bits}.dll"]
        folders = [config.program_dir(), config.resource_dir(), os.path.join(config.resource_dir(), "lib")]
        for folder in folders:
            for name in names:
                path = os.path.join(folder, name)
                if os.path.exists(path):
                    try:
                        self._nvda = ctypes.windll.LoadLibrary(path)
                        log.info("Libreria di NVDA caricata: %s", path)
                        return
                    except OSError:
                        log.warning("Impossibile caricare %s (architettura diversa?)", path)

    @property
    def nvda_library_loaded(self):
        return self._nvda is not None

    def nvda_running(self) -> bool:
        if self._nvda is None:
            return False
        try:
            return self._nvda.nvdaController_testIfRunning() == 0
        except Exception:
            return False

    def announce(self, text: str, interrupt: bool = False):
        """Pronuncia un messaggio di stato tramite NVDA (se disponibile) e lo mostra nella barra di stato."""
        if not text:
            return
        if self.fallback:
            try:
                self.fallback(text)
            except Exception:
                log.exception("Errore nel messaggio di stato")
        if self.nvda_running():
            try:
                if interrupt:
                    self._nvda.nvdaController_cancelSpeech()
                self._nvda.nvdaController_speakText(ctypes.c_wchar_p(text))
            except Exception:
                log.exception("Errore nell'annuncio a NVDA")

    def silence(self):
        if self.nvda_running():
            try:
                self._nvda.nvdaController_cancelSpeech()
            except Exception:
                pass


announcer = Announcer()


def announce(text, interrupt=False):
    announcer.announce(text, interrupt)
