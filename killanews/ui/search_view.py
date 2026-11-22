"""Pannello della ricerca universale con filtri per categoria, testata, continente, nazione e periodo."""
import wx

from ..news_manager import parse_italian_date

PERIODS = [("", "Qualsiasi data"), ("oggi", "Oggi"), ("24h", "Ultime 24 ore"), ("7g", "Ultimi 7 giorni"),
           ("30g", "Ultimi 30 giorni"), ("range", "Intervallo di date indicato sotto")]


class SearchPanel(wx.Panel):
    def __init__(self, parent, core, on_search):
        super().__init__(parent)
        self.core = core
        self.on_search = on_search
        box = wx.StaticBoxSizer(wx.VERTICAL, self, "Ricerca universale")
        parent_box = box.GetStaticBox()
        grid = wx.FlexGridSizer(cols=2, vgap=4, hgap=8)
        grid.AddGrowableCol(1)

        def row(label, factory):
            grid.Add(wx.StaticText(parent_box, label=label), 0, wx.ALIGN_CENTER_VERTICAL)
            ctrl = factory()
            grid.Add(ctrl, 1, wx.EXPAND)
            return ctrl

        self.text = row("&Testo da cercare (titoli, testi, persone, città, argomenti, testate):",
                        lambda: wx.TextCtrl(parent_box, style=wx.TE_PROCESS_ENTER))
        self.category = row("&Categoria:", lambda: wx.Choice(parent_box))
        self.source = row("T&estata:", lambda: wx.Choice(parent_box))
        self.continent = row("C&ontinente:", lambda: wx.Choice(parent_box))
        self.country = row("&Nazione:", lambda: wx.Choice(parent_box))
        self.period = row("Pe&riodo di pubblicazione:", lambda: wx.Choice(parent_box, choices=[p[1] for p in PERIODS]))
        self.date_from = row("&Dal giorno (gg/mm/aaaa):", lambda: wx.TextCtrl(parent_box, style=wx.TE_PROCESS_ENTER))
        self.date_to = row("&Al giorno (gg/mm/aaaa):", lambda: wx.TextCtrl(parent_box, style=wx.TE_PROCESS_ENTER))
        box.Add(grid, 0, wx.EXPAND | wx.ALL, 4)
        buttons = wx.BoxSizer(wx.HORIZONTAL)
        self.go = wx.Button(parent_box, label="&Cerca")
        self.clear = wx.Button(parent_box, label="Azzera i &filtri")
        buttons.Add(self.go, 0, wx.RIGHT, 8)
        buttons.Add(self.clear, 0)
        box.Add(buttons, 0, wx.ALL, 4)
        self.SetSizer(box)
        self.period.SetSelection(0)
        self.refresh_choices()
        self._update_dates()
        for ctrl in (self.text, self.date_from, self.date_to):
            ctrl.Bind(wx.EVT_TEXT_ENTER, self._on_go)
        self.go.Bind(wx.EVT_BUTTON, self._on_go)
        self.clear.Bind(wx.EVT_BUTTON, self._on_clear)
        self.period.Bind(wx.EVT_CHOICE, lambda e: self._update_dates())

    def refresh_choices(self):
        self._cats = [("", "Tutte le categorie")]
        for top, subs in self.core.catalog.categories_tree():
            self._cats.append((top["id"], top["name"]))
            for sub in subs:
                self._cats.append((sub["id"], f"{top['name']} - {sub['name']}"))
        self._sources = [(None, "Tutte le testate")] + [(s["id"], s["name"]) for s in self.core.catalog.sources()]
        self._continents = [("", "Tutti i continenti")] + [(c, c) for c in self.core.news.continents()]
        self._countries = [("", "Tutte le nazioni")] + [(c, c) for c in self.core.news.countries()]
        for ctrl, items in ((self.category, self._cats), (self.source, self._sources),
                            (self.continent, self._continents), (self.country, self._countries)):
            current = ctrl.GetSelection()
            ctrl.Set([label for _, label in items])
            ctrl.SetSelection(current if 0 <= current < len(items) else 0)

    def _update_dates(self):
        enabled = PERIODS[self.period.GetSelection()][0] == "range"
        self.date_from.Enable(enabled)
        self.date_to.Enable(enabled)

    def _on_clear(self, event):
        self.text.SetValue("")
        for ctrl in (self.category, self.source, self.continent, self.country, self.period):
            ctrl.SetSelection(0)
        self.date_from.SetValue("")
        self.date_to.SetValue("")
        self._update_dates()
        self.text.SetFocus()

    def params(self):
        """Parametri della ricerca; solleva ValueError con un messaggio comprensibile."""
        period = PERIODS[self.period.GetSelection()][0]
        date_from = date_to = ""
        if period == "range":
            date_from = parse_italian_date(self.date_from.GetValue())
            date_to = parse_italian_date(self.date_to.GetValue())
            if date_from and date_to and date_from > date_to:
                raise ValueError("La data iniziale è successiva alla data finale.")
            period = ""
        return {
            "text": self.text.GetValue().strip(),
            "category_id": self._cats[self.category.GetSelection()][0],
            "source_id": self._sources[self.source.GetSelection()][0],
            "country": self._countries[self.country.GetSelection()][0],
            "continent": self._continents[self.continent.GetSelection()][0],
            "period": period, "date_from": date_from, "date_to": date_to,
        }

    def describe(self, params):
        parts = []
        if params["text"]:
            parts.append(f"«{params['text']}»")
        for key, items, ctrl in (("category_id", self._cats, self.category), ("source_id", self._sources, self.source),
                                 ("continent", self._continents, self.continent),
                                 ("country", self._countries, self.country)):
            if params[key]:
                parts.append(items[ctrl.GetSelection()][1])
        if self.period.GetSelection():
            parts.append(PERIODS[self.period.GetSelection()][1].lower())
        return ", ".join(parts) or "tutti gli articoli"

    def _on_go(self, event):
        self.on_search()

    def focus(self):
        self.text.SetFocus()
        self.text.SelectAll()
