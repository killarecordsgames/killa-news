"""Configurazione generale di KILLA NEWS: identità, percorsi e valori predefiniti."""
import os
import sys

APP_NAME = "KILLA NEWS"
APP_VERSION = "1.6.1"
PRODUCER = "Killa Records"
SLOGAN = "L'informazione, senza barriere."
APP_ID = "KillaNews"
CREATOR = "Abdu Killa"
CONTACT_EMAIL = "info@killarecordsgames.com"
LINKS = {
    "site": ("Sito ufficiale Killa Records", "https://www.killarecordsgames.com"),
    "youtube": ("Canale YouTube Killa Records", "https://www.youtube.com/@KillaRecordsGamesOfficial"),
    "facebook": ("Gruppo Facebook Killa Records Games", "https://www.facebook.com/groups/971706109130060/"),
    "whatsapp": ("Canale WhatsApp Killa Records", "https://whatsapp.com/channel/0029VbD8ArhJJhzdFghGyT3F"),
    "donate": ("Sostieni il progetto con una donazione (PayPal)", "https://paypal.me/abdukilla"),
}
USER_AGENT = f"KillaNews/{APP_VERSION} (lettore di notizie accessibile; Windows)"
DB_SCHEMA_VERSION = 2
# Repository GitHub da cui arrivano le nuove versioni ("utente/repository"); vuoto = aggiornamenti disattivati
GITHUB_REPO = "__GITHUB_REPO__"
DOWNLOAD_PAGE = "https://www.killarecordsgames.com/killa-news"


def resource_dir() -> str:
    """Cartella delle risorse in sola lettura (data/, assets/).

    Funziona sia dal sorgente sia dall'eseguibile creato con PyInstaller."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(sys.executable))
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def program_dir() -> str:
    """Cartella in cui si trova il programma (eseguibile o main.py)."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def is_portable() -> bool:
    """Modalità portatile: se accanto al programma esiste il file 'portable.flag'
    i dati personali vengono salvati nella sottocartella 'dati' del programma."""
    return os.path.exists(os.path.join(program_dir(), "portable.flag"))


def user_data_dir() -> str:
    """Cartella dei dati personali (database, backup, registro)."""
    override = os.environ.get("KILLANEWS_DATA_DIR")
    if override:
        path = override
    elif is_portable():
        path = os.path.join(program_dir(), "dati")
    elif sys.platform.startswith("win"):
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
        path = os.path.join(base, APP_ID)
    else:
        path = os.path.join(os.path.expanduser("~"), ".killanews")
    os.makedirs(path, exist_ok=True)
    return path


def db_path() -> str:
    return os.path.join(user_data_dir(), "killanews.db")


def backup_dir() -> str:
    path = os.path.join(user_data_dir(), "backup")
    os.makedirs(path, exist_ok=True)
    return path


def log_path() -> str:
    return os.path.join(user_data_dir(), "killanews.log")


def default_download_dir() -> str:
    docs = os.path.join(os.path.expanduser("~"), "Documents")
    if not os.path.isdir(docs):
        docs = os.path.expanduser("~")
    return os.path.join(docs, "KILLA NEWS")


def data_file(name: str) -> str:
    return os.path.join(resource_dir(), "data", name)


def asset_file(name: str) -> str:
    return os.path.join(resource_dir(), "assets", name)


# Valori predefiniti delle impostazioni (chiave -> valore).
DEFAULT_SETTINGS = {
    "theme": "sistema",              # sistema | chiaro | scuro | alto_contrasto
    "font_size": 12,
    "font_face": "Segoe UI",
    "voice_id": "",                   # vuoto = voce predefinita di Windows (preferibilmente italiana)
    "speech_rate": 0,                 # da -10 a 10 (SAPI5)
    "speech_volume": 100,             # da 0 a 100
    "auto_update": True,
    "update_interval_min": 15,
    "notify_new": True,               # annuncio a NVDA / barra di stato
    "notify_windows": False,          # notifiche di Windows
    "auto_refresh_view": False,       # aggiorna l'elenco visualizzato da solo (sconsigliato con lettori di schermo)
    "download_dir": "",               # vuoto = Documenti\\KILLA NEWS
    "fetch_full_text": True,          # recupera il testo integrale dalle pagine pubbliche autorizzate
    "retention_days": 30,             # gli articoli non salvati e non scaricati più vecchi vengono rimossi
    "history_enabled": True,
    "max_list_items": 500,
    "follow_reading_caret": False,    # sposta il cursore sul paragrafo letto dalla sintesi
    "announce_on_open": True,
    "shortcuts": {},                  # personalizzazioni delle scorciatoie
    "last_backup": "",
    "catalog_version": 0,
    "check_app_updates": True,        # controlla da solo se esiste una nuova versione di KILLA NEWS
    "last_app_update_check": 0,
    "skipped_app_version": "",
    "auto_translate": False,
    "last_run_version": "",
    "pending_update": "",
    "send_usage_stats": True,         # statistiche anonime d'uso (nessun dato personale)
    "stats_id": "",                   # identificativo casuale dell'installazione
    "stats_pending": "",              # conteggi non ancora inviati             # versione che si stava installando (per accorgersi se l'aggiornamento non è riuscito)           # versione usata l'ultima volta (per mostrare le novità dopo un aggiornamento)          # traduce da solo in italiano gli articoli scritti in altre lingue
}
