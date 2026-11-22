"""Scorciatoie da tastiera personalizzabili e controllo dei conflitti.

Le combinazioni sono stringhe canoniche come 'Ctrl+Shift+F'. L'interfaccia le
converte nelle tabelle di acceleratori di wxPython. Il modulo non dipende da wx."""

# id azione: (descrizione, combinazione predefinita, ambito)  ambito: main | reader | both
ACTIONS = {
    "home":          ("Prima pagina", "Ctrl+1", "main"),
    "all_sources":   ("Tutti i giornali", "Ctrl+2", "main"),
    "search":        ("Ricerca", "Ctrl+F", "main"),
    "history":       ("Cronologia", "Ctrl+H", "main"),
    "favorites":     ("Articoli salvati (preferiti)", "Ctrl+D", "main"),
    "refresh":       ("Aggiorna notizie da Internet", "Ctrl+R", "main"),
    "refresh_view":  ("Aggiorna l'elenco visualizzato", "F5", "main"),
    "next_pane":     ("Passa al riquadro successivo", "F6", "main"),
    "prev_pane":     ("Passa al riquadro precedente", "Shift+F6", "main"),
    "settings":      ("Impostazioni", "Ctrl+Shift+I", "main"),
    "sources":       ("Gestione delle fonti", "Ctrl+Shift+F", "main"),
    "help":          ("Guida", "F1", "both"),
    "save":          ("Salva o rimuovi dai preferiti", "Ctrl+S", "both"),
    "read":          ("Avvia la lettura vocale", "Ctrl+P", "both"),
    "stop_speech":   ("Interrompi la lettura vocale", "Ctrl+K", "both"),
    "download":      ("Scarica per la lettura offline", "Ctrl+Shift+S", "both"),
    "open_original": ("Apri l'articolo originale nel browser", "Ctrl+O", "both"),
    "print":         ("Stampa l'articolo", "Ctrl+Shift+T", "both"),
    "pause":         ("Metti in pausa o riprendi la lettura", "Ctrl+Shift+P", "reader"),
    "restart":       ("Leggi dall'inizio", "Alt+Home", "reader"),
    "next_par":      ("Leggi il paragrafo successivo", "Alt+Down", "reader"),
    "prev_par":      ("Leggi il paragrafo precedente", "Alt+Up", "reader"),
    "next_article":  ("Articolo successivo", "Ctrl+PageDown", "reader"),
    "prev_article":  ("Articolo precedente", "Ctrl+PageUp", "reader"),
    "export":        ("Esporta l'articolo come file di testo", "Ctrl+E", "reader"),
    "translate":     ("Traduci l'articolo in italiano o torna alla lingua originale", "Ctrl+T", "reader"),
}

MODIFIERS = ("Ctrl", "Alt", "Shift")
_MOD_ALIASES = {"ctrl": "Ctrl", "control": "Ctrl", "controllo": "Ctrl", "alt": "Alt",
                "shift": "Shift", "maiusc": "Shift", "maiuscolo": "Shift", "maiuscole": "Shift"}

_KEY_ALIASES = {
    "esc": "Escape", "escape": "Escape", "invio": "Enter", "enter": "Enter", "return": "Enter",
    "spazio": "Space", "space": "Space", "su": "Up", "up": "Up", "freccia su": "Up",
    "giù": "Down", "giu": "Down", "down": "Down", "freccia giù": "Down",
    "sinistra": "Left", "left": "Left", "destra": "Right", "right": "Right",
    "inizio": "Home", "home": "Home", "fine": "End", "end": "End",
    "pagsu": "PageUp", "pag su": "PageUp", "pageup": "PageUp", "pgup": "PageUp",
    "paggiù": "PageDown", "paggiu": "PageDown", "pag giù": "PageDown", "pagedown": "PageDown", "pgdn": "PageDown",
    "canc": "Delete", "delete": "Delete", "del": "Delete", "backspace": "Back", "back": "Back",
    "punto": ".", "virgola": ",", ".": ".", ",": ",",
}

ITALIAN_NAMES = {"Shift": "Maiusc", "Escape": "Esc", "Enter": "Invio", "Space": "Spazio",
                 "Up": "Freccia su", "Down": "Freccia giù", "Left": "Freccia sinistra",
                 "Right": "Freccia destra", "Home": "Inizio", "End": "Fine", "PageUp": "Pagina su",
                 "PageDown": "Pagina giù", "Delete": "Canc", "Back": "Backspace"}

# Combinazioni riservate a Windows o a NVDA, che non possono essere assegnate.
RESERVED = {
    "Alt+F4": "chiude la finestra (Windows)",
    "Alt+Tab": "cambia applicazione (Windows)",
    "Ctrl+Escape": "apre il menu Start (Windows)",
    "Ctrl+Alt+Delete": "sicurezza di Windows",
    "Ctrl+Alt+N": "avvia NVDA",
    "Alt+Space": "menu di sistema della finestra (Windows)",
    "Ctrl+Shift+Escape": "Gestione attività (Windows)",
    "F10": "attiva la barra dei menu (Windows)",
    "Escape": "torna indietro o chiude la finestra (KILLA NEWS)",
    "Enter": "apre l'elemento selezionato (KILLA NEWS)",
    "Tab": "spostamento tra i controlli",
    "Shift+Tab": "spostamento tra i controlli",
}

FORBIDDEN_KEYS = ("Insert", "Ins", "CapsLock", "Win", "Windows", "BlocMaiusc")


class ShortcutError(ValueError):
    pass


def _valid_key(key: str) -> bool:
    if len(key) == 1 and (key.isalnum() or key in ".,"):
        return True
    if key.startswith("F") and key[1:].isdigit() and 1 <= int(key[1:]) <= 12:
        return True
    return key in set(_KEY_ALIASES.values())


def normalize(text: str) -> str:
    """Converte una combinazione scritta dall'utente nella forma canonica.
    Esempi: 'ctrl+maiusc+f' -> 'Ctrl+Shift+F'; 'alt + freccia giù' -> 'Alt+Down'."""
    if not text or not text.strip():
        raise ShortcutError("Scrivi una combinazione di tasti, per esempio Ctrl+Maiusc+N.")
    parts = [p.strip() for p in text.replace(" + ", "+").split("+")]
    if any(not p for p in parts):
        raise ShortcutError("Combinazione non valida: controlla i segni +.")
    mods, key = set(), None
    for part in parts:
        low = part.lower()
        if low in _MOD_ALIASES:
            mods.add(_MOD_ALIASES[low])
            continue
        if key is not None:
            raise ShortcutError("Indica un solo tasto oltre ai modificatori (Ctrl, Alt, Maiusc).")
        if part in FORBIDDEN_KEYS or low in ("insert", "ins", "capslock", "win", "windows", "bloc maiusc"):
            raise ShortcutError("I tasti Insert, Bloc Maiusc e Windows sono riservati a NVDA e a Windows.")
        if low in _KEY_ALIASES:
            key = _KEY_ALIASES[low]
        elif len(part) == 1:
            key = part.upper()
        elif low.startswith("f") and low[1:].isdigit():
            key = "F" + low[1:]
        else:
            key = part[:1].upper() + part[1:]
        if not _valid_key(key):
            raise ShortcutError(f"Tasto non riconosciuto: {part}")
    if key is None:
        raise ShortcutError("Manca il tasto principale (per esempio una lettera).")
    if not mods and not (key.startswith("F") and key[1:].isdigit()):
        raise ShortcutError("Usa almeno un modificatore (Ctrl o Alt) oppure un tasto funzione F1-F12, "
                            "per non interferire con la digitazione e con la navigazione di NVDA.")
    if mods == {"Shift"} and not key.startswith("F"):
        raise ShortcutError("Maiusc da solo con una lettera serve a scrivere: aggiungi Ctrl o Alt.")
    ordered = [m for m in MODIFIERS if m in mods]
    return "+".join(ordered + [key])


def to_italian(combo: str) -> str:
    """Forma leggibile in italiano, per menu e guida: 'Ctrl+Shift+F' -> 'Ctrl+Maiusc+F'."""
    return "+".join(ITALIAN_NAMES.get(p, p) for p in combo.split("+")) if combo else "nessuna"


class KeyboardManager:
    def __init__(self, settings=None):
        self.settings = settings

    def overrides(self) -> dict:
        if self.settings is None:
            return {}
        value = self.settings.get("shortcuts", {}) or {}
        return value if isinstance(value, dict) else {}

    def get(self, action: str) -> str:
        if action not in ACTIONS:
            raise KeyError(action)
        return self.overrides().get(action, ACTIONS[action][1])

    def label(self, action: str) -> str:
        return ACTIONS[action][0]

    def scope(self, action: str) -> str:
        return ACTIONS[action][2]

    def all(self):
        return [(a, ACTIONS[a][0], self.get(a), ACTIONS[a][2]) for a in ACTIONS]

    def for_scope(self, scope: str):
        """Coppie (azione, combinazione) attive nella finestra principale o nel lettore."""
        return [(a, self.get(a)) for a, (_, _, sc) in ACTIONS.items()
                if self.get(a) and (sc == scope or sc == "both")]

    def check(self, action: str, combo: str):
        """Verifica una nuova combinazione per l'azione. Restituisce la forma canonica
        oppure solleva ShortcutError con la spiegazione del conflitto."""
        canonical = normalize(combo)
        if canonical in RESERVED:
            raise ShortcutError(f"{to_italian(canonical)} è riservata: {RESERVED[canonical]}.")
        my_scope = self.scope(action)
        for other, label, current, scope in self.all():
            if other == action or current != canonical:
                continue
            if scope == "both" or my_scope == "both" or scope == my_scope:
                raise ShortcutError(f"{to_italian(canonical)} è già usata per «{label}».")
        return canonical

    def assign(self, action: str, combo: str):
        canonical = self.check(action, combo)
        values = self.overrides()
        if canonical == ACTIONS[action][1]:
            values.pop(action, None)
        else:
            values[action] = canonical
        if self.settings is not None:
            self.settings.set("shortcuts", values)
        return canonical

    def reset(self):
        if self.settings is not None:
            self.settings.set("shortcuts", {})
