"""Nucleo dell'applicazione: crea e collega tutti i gestori (senza interfaccia grafica)."""
import datetime
import logging
import logging.handlers

from . import config, database
from .catalog import Catalog
from .download_manager import DownloadManager
from .favorites_manager import FavoritesManager
from .history_manager import HistoryManager
from .keyboard_manager import KeyboardManager
from .news_manager import NewsManager
from .settings_manager import SettingsManager
from .stats import Stats
from .speech_manager import SpeechManager
from .updater import Updater

log = logging.getLogger(__name__)


def setup_logging():
    handler = logging.handlers.RotatingFileHandler(config.log_path(), maxBytes=1_000_000, backupCount=2,
                                                   encoding="utf-8")
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.addHandler(handler)


class Core:
    def __init__(self, db_path=None, speech_backend=None):
        restored = database.apply_pending_restore()
        self.db = database.Database(db_path)
        if not self.db.integrity_ok():
            log.error("Controllo di integrità del database non superato")
        self.settings = SettingsManager(self.db)
        self.catalog = Catalog(self.db)
        self.catalog.ensure_loaded(self.settings)
        self.news = NewsManager(self.db, self.settings)
        self.favorites = FavoritesManager(self.db)
        self.history = HistoryManager(self.db, self.settings)
        self.downloads = DownloadManager(self.db, self.settings)
        self.keyboard = KeyboardManager(self.settings)
        self.speech = SpeechManager(speech_backend)
        self.stats = Stats(self.settings)
        self.apply_speech_settings()
        self.updater = None
        self.restored_backup = restored

    def apply_speech_settings(self):
        self.speech.apply_settings(self.settings.get("voice_id", ""), self.settings.get("speech_rate", 0),
                                   self.settings.get("speech_volume", 100))

    def create_updater(self, on_start=None, on_done=None):
        self.updater = Updater(
            self.db.path,
            interval_seconds=self.settings.update_interval_seconds,
            auto_enabled=lambda: bool(self.settings.get("auto_update", True)),
            retention_days=lambda: int(self.settings.get("retention_days", 30) or 0),
            on_start=on_start, on_done=on_done)
        return self.updater

    def daily_backup(self):
        """Un backup automatico al giorno, all'avvio."""
        today = datetime.date.today().isoformat()
        if self.settings.get("last_backup", "") == today:
            return None
        try:
            path = database.backup_database(self.db)
            self.settings.set("last_backup", today, notify=False)
            return path
        except Exception:
            log.exception("Backup automatico non riuscito")
            return None

    def last_update_text(self):
        row = self.db.query_one("SELECT MAX(last_success) AS t FROM feeds")
        from .models import format_date
        return format_date(row["t"]) if row and row["t"] else "mai"

    def shutdown(self):
        try:
            self.speech.stop()
        except Exception:
            pass
        if self.updater:
            self.updater.stop()
        self.db.close()
