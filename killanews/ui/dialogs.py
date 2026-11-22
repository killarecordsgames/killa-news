"""Finestre di dialogo: guida, informazioni, gestione delle fonti, cartelle dei preferiti."""
import webbrowser

import wx

from .. import config, feed_manager
from ..catalog import CatalogError
from ..favorites_manager import FavoritesError
from ..keyboard_manager import ACTIONS, to_italian
from ..models import format_date
from . import common


# ====================================================================== testo semplice
class TextDialog(wx.Dialog):
    """Testo in sola lettura navigabile con le frecce (guida, elenchi di errori, dettagli)."""

    def __init__(self, parent, title, text, label="Testo:"):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=label), 0, wx.ALL, 6)
        self.text = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2)
        sizer.Add(self.text, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        close = wx.Button(self, wx.ID_CANCEL, "&Chiudi")
        sizer.Add(close, 0, wx.ALL | wx.ALIGN_RIGHT, 6)
        self.SetSizer(sizer)
        self.SetSize(self.FromDIP(wx.Size(760, 560)))
        self.CentreOnParent()
        self.text.SetInsertionPoint(0)
        self.text.SetFocus()


def guide_text(core):
    lines = [
        f"{config.APP_NAME} {config.APP_VERSION} - {config.PRODUCER}", config.SLOGAN, "",
        "COME È FATTA LA FINESTRA",
        "A sinistra c'è il menu delle sezioni, a destra l'elenco delle notizie. Con F6 (o Tab) passi da un "
        "riquadro all'altro. Nel menu usa le frecce su e giù per scegliere una sezione, la freccia destra "
        "per aprire le sottosezioni e la freccia sinistra per chiuderle. Premi Invio per spostarti "
        "sull'elenco delle notizie.",
        "Nell'elenco ogni riga contiene titolo, testata, data, categoria, stato e descrizione. Premi Invio "
        "per aprire l'articolo. Il tasto Applicazioni (o Maiusc+F10) apre il menu contestuale. Il tasto Canc "
        "rimuove l'articolo dai salvati, dalla cronologia o dall'archivio offline, a seconda della sezione.",
        "",
        "IL LETTORE DEGLI ARTICOLI",
        "Il testo si legge con le frecce come in un documento; con NVDA puoi usare anche la lettura "
        "continua (NVDA+Freccia giù). La lettura vocale di KILLA NEWS legge un paragrafo alla volta, parte "
        "dal paragrafo in cui si trova il cursore e si interrompe subito con Ctrl+K o con Esc. Se il feed "
        "fornisce solo un estratto, il lettore lo dice chiaramente e offre il collegamento alla fonte originale.",
        "Esc nel lettore: se la voce sta parlando la interrompe, altrimenti chiude la finestra.",
        "",
        "AGGIORNAMENTO DELLE NOTIZIE",
        "Le fonti si aggiornano da sole in background (impostazione predefinita: ogni 15 minuti). "
        "L'elenco che stai leggendo non viene mai ricaricato da solo, per non spostare il focus: quando "
        "arrivano nuove notizie viene annunciato un messaggio e puoi aggiornare la vista con F5.",
        "",
        "SCORCIATOIE DA TASTIERA (modificabili in Impostazioni, scheda Scorciatoie)",
    ]
    for action, label, combo, scope in core.keyboard.all():
        where = {"main": "finestra principale", "reader": "lettore", "both": "ovunque"}[scope]
        lines.append(f"{to_italian(combo)}: {label} ({where})")
    lines += [
        "Esc: torna indietro, chiude la ricerca o la finestra secondaria",
        "F6 e Maiusc+F6: spostamento tra menu delle sezioni, ricerca ed elenco",
        "Alt: barra dei menu (File, Visualizza, Articolo, Preferiti, Fonti, Strumenti, Killa Records, Aiuto)",
        "",
        "KILLA RECORDS",
        "Nel menu Killa Records e nell'ultima sezione del menu laterale trovi: Segnala un problema (la "
        f"segnalazione arriva a {config.CONTACT_EMAIL}), Chi ha creato KILLA NEWS, i collegamenti al sito, al "
        "canale YouTube, al gruppo Facebook e al canale WhatsApp di Killa Records, la donazione, le "
        "impostazioni e la guida.",
        "",
        "FONTI E TESTATE",
        "Le testate senza feed pubblico sono indicate come «solo sito»: premendo Invio si apre il sito "
        "originale. Dal menu Fonti puoi aggiungere testate, regioni, province e città, verificare i feed e "
        "cercare il feed ufficiale dichiarato dal sito della testata. KILLA NEWS non aggira paywall o "
        "abbonamenti: per gli articoli riservati mostra l'anteprima e il collegamento alla fonte.",
        "",
        "DATI PERSONALI",
        f"Preferiti, cronologia, archivio offline e impostazioni sono salvati in: {config.user_data_dir()}. "
        "Ogni giorno viene creato un backup automatico del database (menu File > Backup).",
    ]
    return "\n".join(lines)


class HelpDialog(TextDialog):
    def __init__(self, parent, core):
        super().__init__(parent, f"Guida di {config.APP_NAME}", guide_text(core), "&Guida (usa le frecce per leggerla):")


def show_about(parent):
    text = (f"{config.APP_NAME}\nVersione {config.APP_VERSION}\n\nIdeato e realizzato da {config.CREATOR}\n"
            f"Prodotto da {config.PRODUCER}\n"
            f"{config.SLOGAN}\n\nEdicola digitale accessibile per persone non vedenti e ipovedenti.\n"
            "Gratuito. Le notizie appartengono alle rispettive testate: KILLA NEWS mostra ciò che i feed "
            "pubblicano e rimanda sempre alla fonte originale.")
    wx.MessageBox(text, f"Informazioni su {config.APP_NAME}", wx.OK | wx.ICON_INFORMATION, parent)


# ====================================================================== cartelle
class FoldersDialog(wx.Dialog):
    def __init__(self, parent, core):
        super().__init__(parent, title="Cartelle dei preferiti - " + config.APP_NAME)
        self.core = core
        self.changed = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Cartelle:"), 0, wx.ALL, 6)
        self.listbox = wx.ListBox(self, size=self.FromDIP(wx.Size(380, 220)))
        sizer.Add(self.listbox, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("&Nuova cartella...", self.on_new), ("&Rinomina...", self.on_rename),
                               ("&Elimina", self.on_delete)):
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            row.Add(b, 0, wx.ALL, 4)
        row.Add(wx.Button(self, wx.ID_CANCEL, "&Chiudi"), 0, wx.ALL, 4)
        sizer.Add(row, 0, wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.reload()
        self.listbox.SetFocus()

    def reload(self, select_id=None):
        self.folders = list(self.core.favorites.folders())
        self.listbox.Set([f"{f['name']} ({f['items']} articoli)" for f in self.folders]
                         or ["Nessuna cartella. Usa il pulsante Nuova cartella."])
        idx = 0
        for i, f in enumerate(self.folders):
            if f["id"] == select_id:
                idx = i
        self.listbox.SetSelection(idx)

    def _current(self):
        i = self.listbox.GetSelection()
        return self.folders[i] if self.folders and 0 <= i < len(self.folders) else None

    def on_new(self, event):
        name = common.ask_text(self, "Nome della nuova cartella:", "Nuova cartella")
        if name:
            try:
                fid = self.core.favorites.create_folder(name)
            except FavoritesError as exc:
                common.error(self, str(exc))
                return
            self.changed = True
            self.reload(fid)

    def on_rename(self, event):
        f = self._current()
        if not f:
            return
        name = common.ask_text(self, "Nuovo nome della cartella:", "Rinomina cartella", f["name"])
        if name:
            try:
                self.core.favorites.rename_folder(f["id"], name)
            except FavoritesError as exc:
                common.error(self, str(exc))
                return
            self.changed = True
            self.reload(f["id"])

    def on_delete(self, event):
        f = self._current()
        if f and common.confirm(self, f"Eliminare la cartella «{f['name']}»? Gli articoli restano tra i salvati."):
            self.core.favorites.delete_folder(f["id"])
            self.changed = True
            self.reload()


def choose_folder(parent, core):
    """Restituisce (ok, folder_id o None)."""
    folders = list(core.favorites.folders())
    choices = ["(Nessuna cartella)"] + [f["name"] for f in folders] + ["Nuova cartella..."]
    dlg = wx.SingleChoiceDialog(parent, "Scegli la cartella in cui spostare l'articolo:", "Sposta in cartella",
                                choices)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return False, None
        i = dlg.GetSelection()
    finally:
        dlg.Destroy()
    if i == 0:
        return True, None
    if i == len(choices) - 1:
        name = common.ask_text(parent, "Nome della nuova cartella:", "Nuova cartella")
        if not name:
            return False, None
        try:
            return True, core.favorites.create_folder(name)
        except FavoritesError as exc:
            common.error(parent, str(exc))
            return False, None
    return True, folders[i - 1]["id"]


# ====================================================================== fonti
def category_choices(core):
    items = [("generale", "Notizie generali (prima pagina)")]
    for top, subs in core.catalog.categories_tree():
        items.append((top["id"], top["name"]))
        for sub in subs:
            items.append((sub["id"], f"{top['name']} - {sub['name']}"))
    return items


class FeedEditDialog(wx.Dialog):
    def __init__(self, parent, core, feed=None):
        super().__init__(parent, title=("Modifica feed" if feed else "Aggiungi feed") + " - " + config.APP_NAME)
        self.core = core
        self.cats = category_choices(core)
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.url = common.labeled(self, sizer, "&Indirizzo del feed RSS o Atom (https://...):",
                                  lambda: wx.TextCtrl(self, value=(feed or {}).get("url", ""),
                                                      size=self.FromDIP(wx.Size(520, -1))))
        self.cat = common.labeled(self, sizer, "&Categoria:", lambda: wx.Choice(self, choices=[c[1] for c in self.cats]))
        current = (feed or {}).get("category_id", "generale")
        self.cat.SetSelection(next((i for i, c in enumerate(self.cats) if c[0] == current), 0))
        self.main = wx.CheckBox(self, label="Mostra in &Prima pagina tra le notizie principali")
        self.main.SetValue(bool((feed or {}).get("is_main", True)))
        sizer.Add(self.main, 0, wx.ALL, 6)
        self.highlight = wx.CheckBox(self, label="Mostra tra le notizie in &evidenza (ultima ora)")
        self.highlight.SetValue(bool((feed or {}).get("highlight", False)))
        sizer.Add(self.highlight, 0, wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        test = wx.Button(self, label="&Verifica il feed")
        test.Bind(wx.EVT_BUTTON, self.on_test)
        row.Add(test, 0, wx.ALL, 4)
        ok = wx.Button(self, wx.ID_OK, "&OK")
        ok.SetDefault()
        row.Add(ok, 0, wx.ALL, 4)
        row.Add(wx.Button(self, wx.ID_CANCEL, "&Annulla"), 0, wx.ALL, 4)
        sizer.Add(row, 0, wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.url.SetFocus()

    def value(self):
        return {"url": self.url.GetValue().strip(), "category_id": self.cats[self.cat.GetSelection()][0],
                "is_main": self.main.GetValue(), "highlight": self.highlight.GetValue()}

    def on_test(self, event):
        url = self.url.GetValue().strip()
        if not url.startswith(("http://", "https://")):
            common.error(self, "Scrivi un indirizzo che inizi con http:// o https://")
            return
        res, exc, cancelled = common.run_with_wait(self, "Verifica del feed in corso...",
                                                   lambda: feed_manager.test_feed_url(url))
        if res:
            (common.info if res[0] else common.error)(self, res[1])

    def on_ok(self, event):
        if not self.url.GetValue().strip().startswith(("http://", "https://")):
            common.error(self, "L'indirizzo del feed deve iniziare con http:// o https://")
            self.url.SetFocus()
            return
        self.EndModal(wx.ID_OK)


class SourceEditDialog(wx.Dialog):
    def __init__(self, parent, core, source_id=None):
        super().__init__(parent, title=("Modifica testata" if source_id else "Aggiungi testata") + " - "
                         + config.APP_NAME, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.core = core
        self.source_id = source_id
        src = core.catalog.source(source_id) if source_id else None
        self.feeds = [dict(category_id=f["category_id"], url=f["url"], is_main=bool(f["is_main"]),
                           highlight=bool(f["highlight"]), verification=f["verification"])
                      for f in core.catalog.feeds(source_id)] if source_id else []
        outer = wx.BoxSizer(wx.VERTICAL)
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1)

        def field(label, value, factory=None):
            grid.Add(wx.StaticText(self, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = factory() if factory else wx.TextCtrl(self, value=value or "")
            grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        g = lambda k: (src[k] if src else "")  # noqa: E731
        self.name = field("&Nome della testata:", g("name"))
        self.group = field("&Gruppo (per esempio Quotidiani nazionali, Locali):", "",
                           lambda: wx.ComboBox(self, value=g("group_name") or "Locali", choices=core.catalog.groups()))
        self.country = field("&Paese:", g("country") or "Italia")
        self.region = field("&Regione (per i giornali locali):", g("region"))
        self.province = field("Pro&vincia:", g("province"))
        self.city = field("Ci&ttà:", g("city"))
        self.site = field("Indirizzo del &sito (https://...):", g("site_url"))
        outer.Add(grid, 0, wx.EXPAND | wx.ALL, 6)
        self.fulltext = wx.CheckBox(self, label="Consenti il recupero del testo &integrale dalla pagina pubblica "
                                                "(solo per testate senza abbonamento o paywall)")
        self.fulltext.SetValue(bool(src["fulltext_allowed"]) if src else False)
        outer.Add(self.fulltext, 0, wx.ALL, 6)
        self.enabled = wx.CheckBox(self, label="Testata &attiva (aggiornata automaticamente)")
        self.enabled.SetValue(bool(src["enabled"]) if src else True)
        outer.Add(self.enabled, 0, wx.ALL, 6)
        outer.Add(wx.StaticText(self, label="&Feed della testata:"), 0, wx.ALL, 6)
        self.feed_list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=self.FromDIP(wx.Size(640, 160)))
        self.feed_list.SetLabel("Feed della testata")
        for i, (col, w) in enumerate((("Indirizzo", 360), ("Categoria", 180), ("Prima pagina", 90))):
            self.feed_list.InsertColumn(i, col, width=w)
        outer.Add(self.feed_list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        for label, handler in (("Aggiungi &feed...", self.on_add_feed), ("&Modifica feed...", self.on_edit_feed),
                               ("Rim&uovi feed", self.on_remove_feed), ("&Cerca feed sul sito", self.on_discover)):
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            row.Add(b, 0, wx.ALL, 3)
        outer.Add(row, 0, wx.ALL, 3)
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
        self.refresh_feeds()
        self.name.SetFocus()

    def refresh_feeds(self, select=0):
        names = dict(category_choices(self.core))
        self.feed_list.DeleteAllItems()
        for i, f in enumerate(self.feeds):
            self.feed_list.InsertItem(i, f["url"])
            self.feed_list.SetItem(i, 1, names.get(f["category_id"], f["category_id"]))
            self.feed_list.SetItem(i, 2, "sì" if f.get("is_main") else "no")
        if self.feeds:
            self.feed_list.Select(min(select, len(self.feeds) - 1))

    def _sel(self):
        i = self.feed_list.GetFirstSelected()
        return i if 0 <= i < len(self.feeds) else None

    def on_add_feed(self, event):
        dlg = FeedEditDialog(self, self.core)
        if dlg.ShowModal() == wx.ID_OK:
            self.feeds.append(dlg.value())
            self.refresh_feeds(len(self.feeds) - 1)
        dlg.Destroy()
        self.feed_list.SetFocus()

    def on_edit_feed(self, event):
        i = self._sel()
        if i is None:
            return
        dlg = FeedEditDialog(self, self.core, self.feeds[i])
        if dlg.ShowModal() == wx.ID_OK:
            self.feeds[i].update(dlg.value())
            self.refresh_feeds(i)
        dlg.Destroy()
        self.feed_list.SetFocus()

    def on_remove_feed(self, event):
        i = self._sel()
        if i is not None and common.confirm(self, f"Rimuovere il feed {self.feeds[i]['url']}?"):
            del self.feeds[i]
            self.refresh_feeds(i)

    def on_discover(self, event):
        site = self.site.GetValue().strip()
        if not site.startswith(("http://", "https://")):
            common.error(self, "Scrivi prima l'indirizzo del sito (https://...).")
            self.site.SetFocus()
            return
        found = discover_and_choose(self, site)
        for url in found:
            if url not in [f["url"] for f in self.feeds]:
                self.feeds.append({"url": url, "category_id": "generale", "is_main": True, "highlight": False,
                                   "verification": "trovato sul sito"})
        self.refresh_feeds(len(self.feeds) - 1)

    def on_ok(self, event):
        data = {"name": self.name.GetValue(), "group_name": self.group.GetValue(), "country": self.country.GetValue(),
                "region": self.region.GetValue(), "province": self.province.GetValue(), "city": self.city.GetValue(),
                "site_url": self.site.GetValue(), "fulltext_allowed": self.fulltext.GetValue(),
                "enabled": self.enabled.GetValue()}
        try:
            self.source_id = self.core.catalog.save_source(data, self.source_id, feeds=self.feeds)
        except CatalogError as exc:
            common.error(self, str(exc))
            return
        self.EndModal(wx.ID_OK)


def discover_and_choose(parent, site_url):
    """Cerca i feed dichiarati dal sito e lascia scegliere quali usare. Restituisce gli URL scelti."""
    found, exc, cancelled = common.run_with_wait(parent, f"Ricerca dei feed dichiarati dal sito {site_url}...",
                                                 lambda: feed_manager.discover_feeds(site_url))
    if cancelled:
        return []
    if exc:
        common.error(parent, f"Impossibile leggere il sito: {exc}")
        return []
    if not found:
        common.info(parent, "Il sito non dichiara feed RSS o Atom validi. La testata resterà consultabile "
                            "aprendo il sito originale.")
        return []
    dlg = wx.MultiChoiceDialog(parent, "Il sito dichiara questi feed (già verificati). Seleziona con la barra "
                                       "spaziatrice quelli da aggiungere:", "Feed trovati",
                               [f"{title} - {url}" for url, title in found])
    dlg.SetSelections([0])
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return []
        return [found[i][0] for i in dlg.GetSelections()]
    finally:
        dlg.Destroy()


class SourcesDialog(wx.Dialog):
    COLS = (("Testata", 220), ("Gruppo", 150), ("Paese", 100), ("Zona", 160), ("Stato", 260),
            ("Ultimo aggiornamento", 200))

    def __init__(self, parent, core):
        super().__init__(parent, title="Gestione delle fonti - " + config.APP_NAME,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        self.core = core
        self.changed = False
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label="&Testate:"), 0, wx.ALL, 6)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL, size=self.FromDIP(wx.Size(1000, 360)))
        self.list.SetLabel("Testate")
        for i, (c, w) in enumerate(self.COLS):
            self.list.InsertColumn(i, c, width=w)
        sizer.Add(self.list, 1, wx.EXPAND | wx.LEFT | wx.RIGHT, 6)
        rows = [wx.WrapSizer(wx.HORIZONTAL), wx.WrapSizer(wx.HORIZONTAL)]
        actions = [
            (0, "&Aggiungi testata...", self.on_add), (0, "&Modifica...", self.on_edit), (0, "&Elimina", self.on_delete),
            (0, "Attiva o &disattiva", self.on_toggle), (0, "&Verifica i feed", self.on_test),
            (0, "&Cerca feed sul sito", self.on_discover), (0, "Apri il &sito", self.on_open_site),
            (1, "Dettagli degli &errori", self.on_errors), (1, "&Importa catalogo...", self.on_import),
            (1, "Es&porta catalogo...", self.on_export), (1, "&Ripristina il catalogo originale", self.on_restore),
        ]
        for r, label, handler in actions:
            b = wx.Button(self, label=label)
            b.Bind(wx.EVT_BUTTON, handler)
            rows[r].Add(b, 0, wx.ALL, 3)
        rows[1].Add(wx.Button(self, wx.ID_CANCEL, "&Chiudi"), 0, wx.ALL, 3)
        for r in rows:
            sizer.Add(r, 0, wx.EXPAND | wx.ALL, 3)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.on_edit)
        self.reload()
        self.list.SetFocus()

    @staticmethod
    def status_text(src):
        if not src["enabled"]:
            return "disattivata"
        if not src["feed_count"]:
            return "solo sito (nessun feed pubblico)"
        if src["feed_errors"]:
            return f"{src['feed_count']} feed, {src['feed_errors']} con errori"
        if not src["last_success"]:
            return f"{src['feed_count']} feed, non ancora aggiornata"
        return f"{src['feed_count']} feed funzionanti"

    def reload(self, select_id=None):
        self.sources = list(self.core.catalog.sources())
        self.list.DeleteAllItems()
        target = 0
        for i, s in enumerate(self.sources):
            zone = ", ".join(x for x in (s["city"], s["province"], s["region"]) if x)
            values = (s["name"], s["group_name"], s["country"], zone, self.status_text(s),
                      format_date(s["last_success"]) if s["last_success"] else "mai")
            self.list.InsertItem(i, values[0])
            for c, v in enumerate(values[1:], start=1):
                self.list.SetItem(i, c, v)
            if s["id"] == select_id:
                target = i
        if self.sources:
            self.list.SetItemState(target, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                   wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            self.list.EnsureVisible(target)

    def _current(self):
        i = self.list.GetFirstSelected()
        return self.sources[i] if 0 <= i < len(self.sources) else None

    def on_add(self, event):
        dlg = SourceEditDialog(self, self.core)
        if dlg.ShowModal() == wx.ID_OK:
            self.changed = True
            self.reload(dlg.source_id)
        dlg.Destroy()
        self.list.SetFocus()

    def on_edit(self, event):
        s = self._current()
        if not s:
            return
        dlg = SourceEditDialog(self, self.core, s["id"])
        if dlg.ShowModal() == wx.ID_OK:
            self.changed = True
            self.reload(s["id"])
        dlg.Destroy()
        self.list.SetFocus()

    def on_delete(self, event):
        s = self._current()
        if s and common.confirm(self, f"Eliminare la testata «{s['name']}»? Gli articoli salvati vengono conservati."):
            self.core.catalog.delete_source(s["id"])
            self.changed = True
            self.reload()

    def on_toggle(self, event):
        s = self._current()
        if s:
            self.core.catalog.set_source_enabled(s["id"], not s["enabled"])
            self.changed = True
            self.reload(s["id"])

    def on_test(self, event):
        s = self._current()
        if not s:
            return
        feeds = list(self.core.catalog.feeds(s["id"]))
        if not feeds:
            common.info(self, f"«{s['name']}» non ha feed: si consulta aprendo il sito originale "
                              "(oppure prova Cerca feed sul sito).")
            return
        res, exc, cancelled = common.run_with_wait(
            self, f"Verifica dei feed di {s['name']}...",
            lambda: [(f["url"],) + feed_manager.test_feed_url(f["url"]) for f in feeds])
        if res:
            text = "\n".join(f"{'FUNZIONANTE' if ok else 'NON FUNZIONANTE'}: {url}\n   {msg}"
                             for url, ok, msg, n in res)
            TextDialog(self, f"Verifica dei feed di {s['name']}", text, "&Risultato:").ShowModal()

    def on_discover(self, event):
        s = self._current()
        if not s or not s["site_url"]:
            return
        urls = discover_and_choose(self, s["site_url"])
        for url in urls:
            self.core.catalog.add_feed(s["id"], url, "generale", "trovato sul sito della testata")
        if urls:
            self.changed = True
            self.reload(s["id"])
            common.info(self, f"Aggiunti {len(urls)} feed. Verranno letti al prossimo aggiornamento (Ctrl+R).")

    def on_open_site(self, event):
        s = self._current()
        if s and s["site_url"]:
            webbrowser.open(s["site_url"])

    def on_errors(self, event):
        lines = []
        for f in self.core.catalog.feeds():
            if f["last_error"]:
                when = format_date(f["last_checked"]) if f["last_checked"] else ""
                lines.append(f"{f['source_name']}: {f['last_error']}\n   {f['url']}\n   controllato: {when}")
        TextDialog(self, "Fonti non raggiungibili o con errori",
                   "\n".join(lines) or "Nessun errore registrato dall'ultimo aggiornamento.",
                   "&Elenco degli errori:").ShowModal()

    def on_import(self, event):
        dlg = wx.FileDialog(self, "Importa un catalogo di fonti (file JSON)", wildcard="Catalogo JSON (*.json)|*.json",
                            style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                n = self.core.catalog.import_sources_file(dlg.GetPath())
            except (OSError, ValueError, CatalogError) as exc:
                common.error(self, f"Catalogo non valido: {exc}")
            else:
                self.changed = True
                self.reload()
                common.info(self, f"Importate {n} testate.")
        dlg.Destroy()

    def on_export(self, event):
        dlg = wx.FileDialog(self, "Esporta il catalogo delle fonti", defaultFile="fonti_killa_news.json",
                            wildcard="Catalogo JSON (*.json)|*.json", style=wx.FD_SAVE | wx.FD_OVERWRITE_PROMPT)
        if dlg.ShowModal() == wx.ID_OK:
            try:
                self.core.catalog.export_sources(dlg.GetPath())
                common.info(self, "Catalogo esportato.")
            except OSError as exc:
                common.error(self, str(exc))
        dlg.Destroy()

    def on_restore(self, event):
        if common.confirm(self, "Ripristinare tutte le testate del catalogo originale, annullando eliminazioni "
                                "e modifiche? Le testate aggiunte da te restano."):
            self.core.catalog.restore_catalog()
            self.changed = True
            self.reload()


class ShortcutEditDialog(wx.Dialog):
    def __init__(self, parent, core, action):
        super().__init__(parent, title="Modifica scorciatoia - " + config.APP_NAME)
        self.core = core
        self.action = action
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=f"Azione: {ACTIONS[action][0]}. Combinazione attuale: "
                                            f"{to_italian(core.keyboard.get(action))}."), 0, wx.ALL, 6)
        self.combo = common.labeled(self, sizer, "&Nuova combinazione (per esempio Ctrl+Maiusc+N, Alt+Freccia giù, F7):",
                                    lambda: wx.TextCtrl(self, value=to_italian(core.keyboard.get(action))))
        buttons = wx.StdDialogButtonSizer()
        ok = wx.Button(self, wx.ID_OK, "&OK")
        ok.SetDefault()
        buttons.AddButton(ok)
        buttons.AddButton(wx.Button(self, wx.ID_CANCEL, "&Annulla"))
        buttons.Realize()
        sizer.Add(buttons, 0, wx.ALL | wx.ALIGN_RIGHT, 6)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        self.Bind(wx.EVT_BUTTON, self.on_ok, id=wx.ID_OK)
        self.combo.SetFocus()
        self.combo.SelectAll()

    def on_ok(self, event):
        from ..keyboard_manager import ShortcutError
        try:
            self.result = self.core.keyboard.assign(self.action, self.combo.GetValue())
        except ShortcutError as exc:
            common.error(self, str(exc))
            self.combo.SetFocus()
            return
        self.EndModal(wx.ID_OK)


def show_credits(parent):
    text = (f"{config.APP_NAME} è stato ideato e realizzato da {config.CREATOR} per {config.PRODUCER}.\n\n"
            f"{config.SLOGAN}\n\nPer domande, suggerimenti e segnalazioni: {config.CONTACT_EMAIL}\n"
            f"Sito: {config.LINKS['site'][1]}")
    wx.MessageBox(text, f"Chi ha creato {config.APP_NAME}", wx.OK | wx.ICON_INFORMATION, parent)


REPORT_TYPES = ["Problema o errore del programma", "Problema con NVDA o con l'accessibilità",
                "Testata da aggiungere o notizie che non arrivano", "Suggerimento o nuova idea", "Altro"]


def technical_info(max_log_lines=15):
    import platform
    lines = [f"Programma: {config.APP_NAME} {config.APP_VERSION}",
             f"Sistema: {platform.platform()}", f"Python: {platform.python_version()}"]
    try:
        with open(config.log_path(), encoding="utf-8", errors="replace") as fh:
            tail = fh.read().splitlines()[-max_log_lines:]
        if tail:
            lines += ["", "Ultime righe del registro:"] + [t[:200] for t in tail]
    except OSError:
        pass
    return "\n".join(lines)


class ReportProblemDialog(wx.Dialog):
    """Segnalazione di un problema a Killa Records tramite il programma di posta."""

    def __init__(self, parent):
        super().__init__(parent, title="Segnala un problema - " + config.APP_NAME,
                         style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        sizer.Add(wx.StaticText(self, label=f"La segnalazione arriva a {config.PRODUCER} all'indirizzo "
                                            f"{config.CONTACT_EMAIL}."), 0, wx.ALL, 6)
        self.kind = common.labeled(self, sizer, "&Tipo di segnalazione:", lambda: wx.Choice(self, choices=REPORT_TYPES))
        self.kind.SetSelection(0)
        self.text = common.labeled(self, sizer, "&Descrivi il problema (cosa stavi facendo e cosa è successo):",
                                   lambda: wx.TextCtrl(self, style=wx.TE_MULTILINE, size=self.FromDIP(wx.Size(560, 180))),
                                   proportion=1)
        self.tech = wx.CheckBox(self, label="Allega le &informazioni tecniche (versione, Windows e ultime righe "
                                            "del registro degli errori, senza dati personali)")
        self.tech.SetValue(True)
        sizer.Add(self.tech, 0, wx.ALL, 6)
        row = wx.BoxSizer(wx.HORIZONTAL)
        send = wx.Button(self, label="&Invia con il programma di posta")
        copy = wx.Button(self, label="&Copia il testo negli appunti")
        row.Add(send, 0, wx.ALL, 4)
        row.Add(copy, 0, wx.ALL, 4)
        row.Add(wx.Button(self, wx.ID_CANCEL, "&Annulla"), 0, wx.ALL, 4)
        sizer.Add(row, 0, wx.ALL, 4)
        self.SetSizerAndFit(sizer)
        self.CentreOnParent()
        send.Bind(wx.EVT_BUTTON, self.on_send)
        copy.Bind(wx.EVT_BUTTON, self.on_copy)
        self.kind.SetFocus()

    def subject(self):
        return f"{config.APP_NAME} {config.APP_VERSION} - {REPORT_TYPES[self.kind.GetSelection()]}"

    def body(self):
        text = self.text.GetValue().strip()
        parts = [text]
        if self.tech.GetValue():
            parts += ["", "-----", technical_info()]
        return "\n".join(parts)

    def _check(self):
        if not self.text.GetValue().strip():
            common.error(self, "Scrivi una breve descrizione del problema.")
            self.text.SetFocus()
            return False
        return True

    def on_send(self, event):
        if not self._check():
            return
        import urllib.parse
        body = self.body()
        if len(body) > 1800:  # limite pratico degli indirizzi mailto
            body = body[:1800] + "\n[testo accorciato]"
        url = (f"mailto:{config.CONTACT_EMAIL}?subject={urllib.parse.quote(self.subject())}"
               f"&body={urllib.parse.quote(body)}")
        webbrowser.open(url)
        common.info(self, "Si è aperto il programma di posta con la segnalazione già scritta: controlla e premi "
                          f"Invia. Se non si apre nulla, usa «Copia il testo negli appunti» e incollalo in una "
                          f"e-mail a {config.CONTACT_EMAIL}.")
        self.EndModal(wx.ID_OK)

    def on_copy(self, event):
        if not self._check():
            return
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(f"A: {config.CONTACT_EMAIL}\nOggetto: {self.subject()}\n\n"
                                                      + self.body()))
            wx.TheClipboard.Close()
            common.info(self, f"Testo copiato. Incollalo in una nuova e-mail a {config.CONTACT_EMAIL}.")


class ChangesDialog(wx.Dialog):
    """Finestra con le novità in un campo di testo leggibile con le frecce.

    buttons: [(id, etichetta)]. Il primo pulsante è quello predefinito.
    ShowModal() restituisce l'id del pulsante premuto (Esc = l'ultimo)."""

    def __init__(self, parent, title, intro, text, buttons):
        super().__init__(parent, title=title, style=wx.DEFAULT_DIALOG_STYLE | wx.RESIZE_BORDER)
        sizer = wx.BoxSizer(wx.VERTICAL)
        if intro:
            sizer.Add(wx.StaticText(self, label=intro), 0, wx.ALL, 8)
        sizer.Add(wx.StaticText(self, label="&Novità (usa le frecce per leggerle):"), 0, wx.LEFT | wx.RIGHT, 8)
        self.text = wx.TextCtrl(self, value=text, style=wx.TE_MULTILINE | wx.TE_READONLY | wx.TE_RICH2
                                | wx.TE_NOHIDESEL)
        sizer.Add(self.text, 1, wx.EXPAND | wx.ALL, 8)
        row = wx.BoxSizer(wx.HORIZONTAL)
        self._buttons = []
        for i, (bid, label) in enumerate(buttons):
            b = wx.Button(self, bid, label)
            b.Bind(wx.EVT_BUTTON, lambda e, bid=bid: self.EndModal(bid))
            row.Add(b, 0, wx.ALL, 4)
            self._buttons.append(b)
            if i == 0:
                b.SetDefault()
        sizer.Add(row, 0, wx.ALIGN_RIGHT | wx.ALL, 4)
        self.SetSizer(sizer)
        self.SetEscapeId(buttons[-1][0])
        self.SetSize(self.FromDIP(wx.Size(700, 520)))
        self.CentreOnParent()
        self.text.SetInsertionPoint(0)
        self.text.SetFocus()
