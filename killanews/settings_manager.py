"""Impostazioni persistenti salvate nella tabella 'settings' (valori JSON)."""
import copy
import json
import logging

from . import config

log = logging.getLogger(__name__)


class SettingsManager:
    def __init__(self, db):
        self.db = db
        self._cache = {}
        self._listeners = []
        self.reload()

    def reload(self):
        self._cache = copy.deepcopy(config.DEFAULT_SETTINGS)
        for row in self.db.query("SELECT key, value FROM settings"):
            if row["key"].startswith("discovery:"):
                continue  # dati interni della ricerca automatica dei feed, non impostazioni
            try:
                self._cache[row["key"]] = json.loads(row["value"])
            except (ValueError, TypeError):
                log.warning("Impostazione non valida ignorata: %s", row["key"])

    def get(self, key, default=None):
        if key in self._cache:
            return copy.deepcopy(self._cache[key])
        return default

    def set(self, key, value, notify=True):
        self._cache[key] = copy.deepcopy(value)
        self.db.set_setting_raw(key, json.dumps(value, ensure_ascii=False))
        if notify:
            for callback in list(self._listeners):
                try:
                    callback(key, value)
                except Exception:  # un ascoltatore difettoso non deve bloccare le impostazioni
                    log.exception("Errore nell'ascoltatore delle impostazioni")

    def update(self, values: dict):
        for key, value in values.items():
            self.set(key, value)

    def add_listener(self, callback):
        self._listeners.append(callback)

    def all(self):
        return copy.deepcopy(self._cache)

    # Valori derivati e validati
    def update_interval_seconds(self) -> int:
        try:
            minutes = int(self.get("update_interval_min", 15))
        except (TypeError, ValueError):
            minutes = 15
        return max(5, min(minutes, 24 * 60)) * 60

    def download_dir(self) -> str:
        return self.get("download_dir") or config.default_download_dir()
