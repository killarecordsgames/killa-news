"""Sintesi vocale di KILLA NEWS.

Su Windows usa direttamente SAPI5 tramite COM (oggetto SAPI.SpVoice) in modalità
asincrona: il testo viene letto un paragrafo alla volta, quindi l'interruzione è
immediata anche con articoli lunghissimi (Speak con SVSFPurgeBeforeSpeak svuota la
coda della voce). Sono elencate le voci SAPI5 installate e, se presenti, anche le
voci "OneCore" di Windows 10/11 (per esempio le voci italiane di sistema).

Il gestore non dipende dall'interfaccia grafica: l'interfaccia chiama tick() con un
timer (ogni 100-200 ms) per far avanzare la lettura da un paragrafo al successivo.
"""
import logging
import sys
import time

log = logging.getLogger(__name__)

SVSF_ASYNC = 1
SVSF_PURGE = 2
SVSF_IS_NOT_XML = 16
SRSE_DONE = 1

STATE_STOPPED = "ferma"
STATE_SPEAKING = "in lettura"
STATE_PAUSED = "in pausa"

ONECORE_PATH = r"HKEY_LOCAL_MACHINE\SOFTWARE\Microsoft\Speech_OneCore\Voices"
ITALIAN_LCIDS = ("410", "810")  # italiano (Italia), italiano (Svizzera)


class Voice:
    def __init__(self, voice_id, name, language="", token=None):
        self.id = voice_id
        self.name = name
        self.language = language
        self.token = token

    @property
    def is_italian(self):
        lang = self.language.lower()
        return any(code in lang.split(";") for code in ITALIAN_LCIDS) or "ital" in self.name.lower()

    def __repr__(self):
        return f"Voice({self.name!r})"


class NullBackend:
    """Nessuna sintesi disponibile (sistemi diversi da Windows o SAPI assente)."""
    available = False
    error = "Sintesi vocale di Windows non disponibile su questo sistema."

    def voices(self):
        return []

    def set_voice(self, voice_id):
        return False

    def set_rate(self, rate):
        pass

    def set_volume(self, volume):
        pass

    def speak(self, text):
        pass

    def is_done(self):
        return True

    def pause(self):
        pass

    def resume(self):
        pass

    def purge(self):
        pass


class SapiBackend:
    """SAPI5 tramite COM: pywin32 (win32com) oppure comtypes."""
    available = True
    error = ""

    def __init__(self):
        self._client = None
        try:
            import win32com.client  # type: ignore
            self._client = win32com.client
            self.voice = win32com.client.Dispatch("SAPI.SpVoice")
        except Exception:
            import comtypes.client  # type: ignore
            self._client = comtypes.client
            self.voice = comtypes.client.CreateObject("SAPI.SpVoice")
        self._voices = None

    def _create(self, progid):
        if hasattr(self._client, "Dispatch"):
            return self._client.Dispatch(progid)
        return self._client.CreateObject(progid)

    def voices(self):
        if self._voices is not None:
            return self._voices
        result, seen = [], set()

        def add_tokens(tokens, suffix=""):
            for i in range(tokens.Count):
                token = tokens.Item(i)
                try:
                    name = token.GetDescription()
                except Exception:
                    name = token.Id
                try:
                    lang = token.GetAttribute("Language")
                except Exception:
                    lang = ""
                key = name.lower()
                if key in seen:
                    continue
                seen.add(key)
                result.append(Voice(token.Id, name + suffix, lang or "", token))

        try:
            add_tokens(self.voice.GetVoices())
        except Exception:
            log.exception("Impossibile elencare le voci SAPI5")
        try:
            category = self._create("SAPI.SpObjectTokenCategory")
            category.SetId(ONECORE_PATH, False)
            add_tokens(category.EnumerateTokens(), " (voce di sistema)")
        except Exception:
            log.info("Voci OneCore non disponibili tramite SAPI5")
        self._voices = result
        return result

    def set_voice(self, voice_id):
        for v in self.voices():
            if v.id == voice_id:
                try:
                    self.voice.Voice = v.token
                    return True
                except Exception:
                    log.exception("Voce non utilizzabile: %s", v.name)
                    return False
        return False

    def set_rate(self, rate):
        self.voice.Rate = max(-10, min(10, int(rate)))

    def set_volume(self, volume):
        self.voice.Volume = max(0, min(100, int(volume)))

    def speak(self, text):
        self.voice.Speak(text, SVSF_ASYNC | SVSF_IS_NOT_XML)

    def is_done(self):
        try:
            return self.voice.Status.RunningState == SRSE_DONE
        except Exception:
            return True

    def pause(self):
        self.voice.Pause()

    def resume(self):
        self.voice.Resume()

    def purge(self):
        # Una stringa vuota con PURGE interrompe subito la voce e svuota la coda.
        self.voice.Speak("", SVSF_ASYNC | SVSF_PURGE)


class FakeBackend(NullBackend):
    """Backend simulato per i test automatici: ogni testo 'dura' 2 ms per carattere."""
    available = True
    error = ""

    def __init__(self, ms_per_char=2.0):
        self.ms_per_char = ms_per_char
        self.spoken = []
        self._end = 0.0
        self._paused_at = None
        self.purged = 0

    def voices(self):
        return [Voice("fake-it", "Voce di prova italiana", "410")]

    def set_voice(self, voice_id):
        return voice_id == "fake-it"

    def speak(self, text):
        self.spoken.append(text)
        self._end = time.monotonic() + len(text) * self.ms_per_char / 1000.0

    def is_done(self):
        if self._paused_at is not None:
            return False
        return time.monotonic() >= self._end

    def pause(self):
        self._paused_at = time.monotonic()

    def resume(self):
        if self._paused_at is not None:
            self._end += time.monotonic() - self._paused_at
            self._paused_at = None

    def purge(self):
        self.purged += 1
        self._end = 0.0


def create_backend():
    if not sys.platform.startswith("win"):
        return NullBackend()
    try:
        return SapiBackend()
    except Exception as exc:
        log.exception("SAPI5 non disponibile")
        backend = NullBackend()
        backend.error = f"Impossibile avviare la sintesi vocale di Windows: {exc}"
        return backend


class SpeechManager:
    """Lettura a paragrafi con pausa, ripresa, arresto immediato e navigazione."""

    def __init__(self, backend=None):
        self.backend = backend or create_backend()
        self.paragraphs = []
        self.index = 0
        self.state = STATE_STOPPED
        self.on_state_change = None      # callback(state, index, total)
        self.on_finished = None          # callback()
        self._started_at = 0.0

    @property
    def available(self):
        return self.backend.available

    # --- configurazione --------------------------------------------------
    def voices(self):
        return self.backend.voices()

    def apply_settings(self, voice_id="", rate=0, volume=100):
        if not self.available:
            return
        try:
            chosen = voice_id
            if not chosen:
                italian = [v for v in self.voices() if v.is_italian]
                chosen = italian[0].id if italian else ""
            if chosen:
                self.backend.set_voice(chosen)
            self.backend.set_rate(rate)
            self.backend.set_volume(volume)
        except Exception:
            log.exception("Impostazioni della voce non applicate")

    # --- controllo -------------------------------------------------------
    def _notify(self):
        if self.on_state_change:
            try:
                self.on_state_change(self.state, self.index, len(self.paragraphs))
            except Exception:
                log.exception("Errore nella notifica dello stato della voce")

    def load(self, paragraphs, index=0):
        self.stop()
        self.paragraphs = [p for p in paragraphs if p and p.strip()]
        self.index = max(0, min(index, max(0, len(self.paragraphs) - 1)))

    def start(self, index=None):
        if not self.available or not self.paragraphs:
            return False
        if index is not None:
            self.index = max(0, min(index, len(self.paragraphs) - 1))
        self._hard_stop()
        self.state = STATE_SPEAKING
        self._speak_current()
        self._notify()
        return True

    def _speak_current(self):
        self._started_at = time.monotonic()
        try:
            self.backend.speak(self.paragraphs[self.index])
        except Exception:
            log.exception("Errore della sintesi vocale")
            self.state = STATE_STOPPED

    def _hard_stop(self):
        try:
            if self.state == STATE_PAUSED:
                self.backend.purge()
                self.backend.resume()
            self.backend.purge()
        except Exception:
            log.exception("Errore durante l'arresto della voce")

    def pause(self):
        if self.state == STATE_SPEAKING:
            self.backend.pause()
            self.state = STATE_PAUSED
            self._notify()

    def resume(self):
        if self.state == STATE_PAUSED:
            self.backend.resume()
            self.state = STATE_SPEAKING
            self._notify()
        elif self.state == STATE_STOPPED:
            self.start()

    def toggle_pause(self):
        if self.state == STATE_SPEAKING:
            self.pause()
        else:
            self.resume()

    def stop(self):
        was_active = self.state != STATE_STOPPED
        self._hard_stop()
        self.state = STATE_STOPPED
        if was_active:
            self._notify()

    def next_paragraph(self):
        if self.index < len(self.paragraphs) - 1:
            return self.start(self.index + 1)
        return False

    def previous_paragraph(self):
        if self.index > 0:
            return self.start(self.index - 1)
        return self.start(0)

    def restart(self):
        return self.start(0)

    def tick(self):
        """Da chiamare periodicamente dall'interfaccia: passa al paragrafo successivo."""
        if self.state != STATE_SPEAKING:
            return
        if time.monotonic() - self._started_at < 0.15:
            return  # lascia alla voce il tempo di iniziare
        if self.backend.is_done():
            if self.index < len(self.paragraphs) - 1:
                self.index += 1
                self._speak_current()
                self._notify()
            else:
                self.state = STATE_STOPPED
                self._notify()
                if self.on_finished:
                    self.on_finished()

    def speak_text(self, text):
        """Legge un testo breve (per esempio un titolo) senza cambiare articolo."""
        self.load([text])
        self.start()
