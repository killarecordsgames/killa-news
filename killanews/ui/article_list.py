"""Elenco delle notizie: controllo elenco standard di Windows (SysListView32) in modalità report.

NVDA legge ogni riga con le colonne Titolo, Testata, Data, Categoria, Stato e Descrizione.
Lo stato (salvato, da leggere, offline) è scritto come testo, mai solo con colori o icone."""
import wx

from ..models import format_date_short

COLUMNS = [("Titolo", 420), ("Testata", 160), ("Data", 130), ("Categoria", 170), ("Stato", 150),
           ("Descrizione", 400)]
SITE_ROW_ID = -1


class ArticleList(wx.Panel):
    def __init__(self, parent, on_open, on_context_menu, on_delete):
        super().__init__(parent)
        self.on_open = on_open
        self.on_context_menu = on_context_menu
        self.on_delete = on_delete
        self.articles = []
        self.site_view = None
        self.choices = None   # [(testo, chiave)] quando l'elenco mostra delle scelte
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.heading = wx.StaticText(self, label="Elenco delle notizie")
        sizer.Add(self.heading, 0, wx.ALL, 4)
        self.list = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.list.SetLabel("Elenco delle notizie")
        for i, (name, width) in enumerate(COLUMNS):
            self.list.InsertColumn(i, name, width=width)
        sizer.Add(self.list, 1, wx.EXPAND | wx.ALL, 4)
        self.empty_text = wx.StaticText(self, label="")
        sizer.Add(self.empty_text, 0, wx.ALL, 4)
        self.SetSizer(sizer)
        self.list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self._on_activated)
        self.list.Bind(wx.EVT_CONTEXT_MENU, self._on_context)
        self.list.Bind(wx.EVT_KEY_DOWN, self._on_key)

    # ------------------------------------------------------------------ contenuto
    def set_title(self, title, count=None):
        text = title if count is None else f"{title}: {count} articoli"
        self.heading.SetLabel(text)
        self.list.SetLabel(text)

    def set_articles(self, articles, title, keep_id=None, site_view=None):
        """Popola l'elenco. keep_id: articolo da mantenere selezionato (nessun salto del focus)."""
        self.site_view = site_view
        self.choices = None
        self.articles = list(articles)
        had_focus = self.list.HasFocus()
        self.list.Freeze()
        try:
            self.list.DeleteAllItems()
            if site_view is not None:
                idx = self.list.InsertItem(0, f"{site_view['title']}: questa testata non offre un feed pubblico. "
                                              f"Premi Invio per aprire il sito originale nel browser.")
                self.list.SetItem(idx, 1, site_view["title"])
                self.list.SetItem(idx, 5, site_view.get("site_url", ""))
            for i, art in enumerate(self.articles):
                row = i + (1 if site_view is not None else 0)
                self.list.InsertItem(row, art.title)
                self.list.SetItem(row, 1, art.source_name)
                self.list.SetItem(row, 2, format_date_short(art.published))
                self.list.SetItem(row, 3, art.category_name)
                self.list.SetItem(row, 4, art.status_label() or ("testo completo" if not art.is_partial else ""))
                desc = (art.subtitle or art.description or "").replace("\n", " ")
                self.list.SetItem(row, 5, desc[:220] + ("…" if len(desc) > 220 else ""))
        finally:
            self.list.Thaw()
        count = len(self.articles)
        self.set_title(title, None if site_view is not None and not count else count)
        if not count and site_view is None:
            self.empty_text.SetLabel("Nessun articolo in questa sezione. Premi Ctrl+R per aggiornare le notizie.")
        else:
            self.empty_text.SetLabel("")
        target = 0
        if keep_id is not None:
            for i, art in enumerate(self.articles):
                if art.id == keep_id:
                    target = i + (1 if site_view is not None else 0)
                    break
        if self.list.GetItemCount():
            self.list.SetItemState(target, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                   wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            self.list.EnsureVisible(target)
        if had_focus:
            self.list.SetFocus()
        self.Layout()

    def set_choices(self, choices, title):
        """Mostra un elenco di scelte (per esempio città o testate): Invio apre la scelta."""
        self.articles = []
        self.site_view = None
        self.choices = list(choices)
        had_focus = self.list.HasFocus()
        self.list.Freeze()
        try:
            self.list.DeleteAllItems()
            for i, (text, _key) in enumerate(self.choices):
                self.list.InsertItem(i, text)
                self.list.SetItem(i, 5, "premi Invio per aprire")
        finally:
            self.list.Thaw()
        label = f"{title}: {len(self.choices)} scelte, premi Invio per aprire"
        self.heading.SetLabel(label)
        self.list.SetLabel(label)
        self.empty_text.SetLabel("")
        if self.choices:
            self.list.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                   wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        if had_focus:
            self.list.SetFocus()
        self.Layout()

    def selected_choice(self):
        if not self.choices:
            return None
        row = self.list.GetFirstSelected()
        if row < 0:
            row = self.list.GetFocusedItem()
        return self.choices[row][1] if 0 <= row < len(self.choices) else None

    def update_article(self, article):
        """Aggiorna la riga di un articolo senza ricostruire l'elenco."""
        for i, art in enumerate(self.articles):
            if art.id == article.id:
                self.articles[i] = article
                row = i + (1 if self.site_view is not None else 0)
                self.list.SetItem(row, 4, article.status_label() or ("testo completo" if not article.is_partial else ""))
                return

    def remove_article(self, article_id):
        for i, art in enumerate(self.articles):
            if art.id == article_id:
                row = i + (1 if self.site_view is not None else 0)
                del self.articles[i]
                self.list.DeleteItem(row)
                if self.list.GetItemCount():
                    new = min(row, self.list.GetItemCount() - 1)
                    self.list.SetItemState(new, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                           wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
                    self.list.EnsureVisible(new)
                self.set_title(self.heading.GetLabel().split(":")[0], len(self.articles))
                return

    # ------------------------------------------------------------------ selezione
    def selected_index(self):
        row = self.list.GetFirstSelected()
        if row < 0:
            row = self.list.GetFocusedItem()
        if row < 0:
            return None
        if self.site_view is not None:
            row -= 1
        return row

    def selected_article(self):
        idx = self.selected_index()
        if idx is None or idx < 0 or idx >= len(self.articles):
            return None
        return self.articles[idx]

    def site_row_selected(self):
        return self.site_view is not None and self.list.GetFirstSelected() == 0

    def ids(self):
        return [a.id for a in self.articles]

    def focus(self):
        self.list.SetFocus()
        if self.list.GetItemCount() and self.list.GetFirstSelected() < 0:
            self.list.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED,
                                   wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)

    # ------------------------------------------------------------------ eventi
    def _on_activated(self, event):
        self.on_open()

    def _on_context(self, event):
        self.on_context_menu()

    def _on_key(self, event):
        if event.GetKeyCode() == wx.WXK_DELETE:
            self.on_delete()
            return
        event.Skip()
