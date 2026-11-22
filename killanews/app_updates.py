"""Aggiornamenti automatici di KILLA NEWS stesso (non delle notizie).

Le nuove versioni vengono create da GitHub Actions e pubblicate come "release" su GitHub.
Il programma controlla l'ultima release, la confronta con la propria versione e, se l'utente
accetta, scarica il file giusto, ne verifica l'impronta SHA-256 e lo installa:

- versione installata (cartella con unins000.exe): esegue l'installatore in modo silenzioso,
  che chiude il programma, lo aggiorna e lo riavvia;
- eseguibile singolo (KillaNews.exe portatile): scarica il nuovo .exe, chiude il programma e
  un piccolo script sostituisce il file e riavvia KILLA NEWS.

Nessun dato personale viene inviato: solo una richiesta pubblica all'API di GitHub.
"""
import hashlib
import logging
import os
import re
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field

import requests

from . import config

log = logging.getLogger(__name__)

API_LATEST = "https://api.github.com/repos/{repo}/releases/latest"
INSTALLER_ASSET = "KillaNews_Installazione.exe"
SINGLE_EXE_ASSET = "KillaNews.exe"
CHECKSUMS_ASSET = "SHA256SUMS.txt"
CHECK_EVERY_SECONDS = 20 * 3600  # al massimo un controllo automatico al giorno circa


def parse_version(text: str) -> tuple:
    """'v1.2.3' oppure '1.2' -> (1, 2, 3). Testo non valido -> (0,)."""
    numbers = re.findall(r"\d+", str(text or ""))[:4]
    return tuple(int(n) for n in numbers) or (0,)


def is_newer(remote: str, local: str = config.APP_VERSION) -> bool:
    r, l = parse_version(remote), parse_version(local)
    width = max(len(r), len(l))
    return r + (0,) * (width - len(r)) > l + (0,) * (width - len(l))


def install_kind() -> str:
    """'installata', 'eseguibile' (KillaNews.exe singolo) oppure 'sorgente' (avviato da main.py)."""
    if not getattr(sys, "frozen", False):
        return "sorgente"
    folder = config.program_dir()
    if any(name.lower().startswith("unins") and name.lower().endswith(".exe") for name in os.listdir(folder)):
        return "installata"
    return "eseguibile"


@dataclass
class UpdateInfo:
    version: str
    title: str
    notes: str
    page_url: str
    assets: dict = field(default_factory=dict)  # nome file -> indirizzo di download

    def asset_for(self, kind: str):
        name = INSTALLER_ASSET if kind == "installata" else SINGLE_EXE_ASSET
        return name, self.assets.get(name)


class UpdateError(Exception):
    """Errore spiegato in italiano, da mostrare all'utente."""


def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update({"User-Agent": config.USER_AGENT, "Accept": "application/vnd.github+json"})
    return s


def check(timeout: float = 15) -> "UpdateInfo | None":
    """Restituisce le informazioni sulla nuova versione, oppure None se si usa già l'ultima."""
    if not configured():
        raise UpdateError("Il controllo degli aggiornamenti non è configurato in questa versione.")
    try:
        resp = _session().get(API_LATEST.format(repo=config.GITHUB_REPO), timeout=timeout)
    except requests.RequestException as exc:
        raise UpdateError("Impossibile contattare il server degli aggiornamenti. Controlla la connessione a Internet.") from exc
    if resp.status_code == 404:
        return None  # nessuna versione pubblicata ancora
    if resp.status_code != 200:
        raise UpdateError(f"Il server degli aggiornamenti ha risposto con un errore ({resp.status_code}). Riprova più tardi.")
    data = resp.json()
    tag = data.get("tag_name") or ""
    if data.get("draft") or data.get("prerelease") or not is_newer(tag):
        return None
    assets = {a.get("name"): a.get("browser_download_url") for a in data.get("assets", []) if a.get("name")}
    return UpdateInfo(
        version=".".join(str(n) for n in parse_version(tag)),
        title=data.get("name") or f"{config.APP_NAME} {tag}",
        notes=(data.get("body") or "").strip(),
        page_url=data.get("html_url") or "",
        assets=assets,
    )


def configured() -> bool:
    return bool(config.GITHUB_REPO) and not config.GITHUB_REPO.startswith("__")


def should_check_automatically(settings) -> bool:
    if not configured() or not settings.get("check_app_updates", True) or install_kind() == "sorgente":
        return False
    try:
        last = float(settings.get("last_app_update_check", 0) or 0)
    except (TypeError, ValueError):
        last = 0
    return time.time() - last > CHECK_EVERY_SECONDS


def _expected_hash(info: UpdateInfo, name: str, session: requests.Session) -> str:
    url = info.assets.get(CHECKSUMS_ASSET)
    if not url:
        raise UpdateError("La nuova versione non contiene il file di controllo. Per sicurezza l'aggiornamento è stato annullato.")
    text = session.get(url, timeout=20).text
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 2 and parts[-1].lstrip("*") == name:
            return parts[0].lower()
    raise UpdateError("Impossibile verificare il file scaricato. Per sicurezza l'aggiornamento è stato annullato.")


def download(info: UpdateInfo, kind: str, progress=None) -> str:
    """Scarica il file della nuova versione in una cartella temporanea e ne verifica l'impronta.

    progress(scaricati, totale) può restituire False per annullare."""
    name, url = info.asset_for(kind)
    if not url:
        raise UpdateError("In questa versione manca il file per il tuo tipo di installazione. Scaricala dal sito.")
    session = _session()
    expected = _expected_hash(info, name, session)
    folder = tempfile.mkdtemp(prefix="KillaNews_aggiornamento_")
    path = os.path.join(folder, name)
    digest = hashlib.sha256()
    try:
        with session.get(url, stream=True, timeout=30) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("Content-Length") or 0)
            done = 0
            with open(path, "wb") as fh:
                for chunk in resp.iter_content(chunk_size=256 * 1024):
                    if not chunk:
                        continue
                    fh.write(chunk)
                    digest.update(chunk)
                    done += len(chunk)
                    if progress and progress(done, total) is False:
                        raise UpdateError("Aggiornamento annullato.")
    except requests.RequestException as exc:
        raise UpdateError("Il download della nuova versione si è interrotto. Riprova più tardi.") from exc
    if digest.hexdigest().lower() != expected:
        try:
            os.remove(path)
        except OSError:
            pass
        raise UpdateError("Il file scaricato non corrisponde a quello pubblicato. Per sicurezza non è stato installato.")
    log.info("Nuova versione %s scaricata e verificata: %s", info.version, path)
    return path


def launch_installer(path: str, kind: str) -> None:
    """Avvia l'installazione. Il chiamante deve poi chiudere KILLA NEWS subito."""
    flags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)
    if kind == "installata":
        # Inno Setup: installazione silenziosa che chiude e poi riavvia il programma (vedi [Run] nel file .iss).
        subprocess.Popen([path, "/SILENT", "/SUPPRESSMSGBOXES", "/NORESTART", "/CLOSEAPPLICATIONS",
                          "/AGGIORNAMENTO"], close_fds=True, creationflags=flags)
        return
    # Eseguibile singolo: uno script aspetta che KILLA NEWS si chiuda, sostituisce il file e lo riavvia.
    target = sys.executable
    script = os.path.join(os.path.dirname(path), "aggiorna_killa_news.cmd")
    pid = os.getpid()
    lines = [
        "@echo off",
        "chcp 65001 >nul",
        "set TENTATIVI=0",
        ":attendi",
        f'tasklist /FI "PID eq {pid}" 2>nul | find "{pid}" >nul',
        "if not errorlevel 1 (",
        "  timeout /t 1 /nobreak >nul",
        "  goto attendi",
        ")",
        ":copia",
        f'copy /y "{path}" "{target}" >nul',
        "if errorlevel 1 (",
        "  set /a TENTATIVI+=1",
        "  if %TENTATIVI% GEQ 30 goto fine",
        "  timeout /t 1 /nobreak >nul",
        "  goto copia",
        ")",
        ":fine",
        f'start "" "{target}"',
        'del "%~f0"',
    ]
    with open(script, "w", encoding="utf-8", newline="\r\n") as fh:
        fh.write("\r\n".join(lines) + "\r\n")
    subprocess.Popen(["cmd.exe", "/c", script], close_fds=True,
                     creationflags=flags | getattr(subprocess, "CREATE_NO_WINDOW", 0))
