"""Menu laterale: albero standard di Windows (SysTreeView32), pienamente leggibile da NVDA.

Frecce su/giù: spostamento; destra/sinistra: apre/chiude le sottosezioni;
Invio: porta il focus all'elenco delle notizie (o apre Cerca/Impostazioni)."""
import wx

SECTION_ORDER = [
    ("home", "Prima pagina"), ("all", "Tutti i giornali"), ("italia", "Italia"), ("international", "Giornali internazionali"),
    ("cronaca", "Cronaca"), ("economia", "Economia e finanza"), ("sport", "Sport"), ("tecnologia", "Tecnologia"),
    ("cultura", "Cultura e spettacolo"), ("salute", "Salute e benessere"), ("local", "Giornali locali"),
    ("saved", "Articoli salvati"), ("history", "Cronologia"), ("search", "Cerca"), ("settings", "Impostazioni"),
    ("killa", "Killa Records"),
]

# Voci della sezione Killa Records: (azione, testo)
KILLA_ITEMS = [
    ("report", "Segnala un problema"), ("credits", "Chi ha creato KILLA NEWS"),
    ("site", "Sito ufficiale Killa Records"), ("youtube", "Canale YouTube Killa Records"),
    ("facebook", "Gruppo Facebook Killa Records Games"), ("whatsapp", "Canale WhatsApp Killa Records"),
    ("donate", "Sostieni il progetto con una donazione"), ("settings", "Impostazioni"),
    ("check_updates", "Controlla aggiornamenti di KILLA NEWS"), ("whats_new", "Novità di KILLA NEWS"),
    ("help", "Guida"), ("about", "Informazioni su KILLA NEWS"),
]


class Sidebar(wx.Panel):
    def __init__(self, parent, core, on_select, on_activate):
        super().__init__(parent)
        self.core = core
        self.on_select = on_select
        self.on_activate = on_activate
        self._pending = None
        self.closing = False
        self.section_items = {}
        sizer = wx.BoxSizer(wx.VERTICAL)
        self.label = wx.StaticText(self, label="Menu delle sezioni")
        sizer.Add(self.label, 0, wx.ALL, 4)
        self.tree = wx.TreeCtrl(self, style=wx.TR_HAS_BUTTONS | wx.TR_HIDE_ROOT | wx.TR_LINES_AT_ROOT
                                | wx.TR_SINGLE)
        self.tree.SetLabel("Menu delle sezioni")
        sizer.Add(self.tree, 1, wx.EXPAND | wx.ALL, 4)
        self.SetSizer(sizer)
        self.tree.Bind(wx.EVT_TREE_SEL_CHANGED, self._on_sel_changed)
        self.tree.Bind(wx.EVT_TREE_ITEM_ACTIVATED, self._on_activated)
        self.build()

    # ------------------------------------------------------------------ costruzione
    def _add(self, parent, label, view):
        item = self.tree.AppendItem(parent, label)
        self.tree.SetItemData(item, view)
        return item

    def build(self, keep_key=None):
        """(Ri)costruisce l'albero. keep_key: chiave della vista da riselezionare."""
        self.tree.Freeze()
        try:
            self.tree.DeleteAllItems()
            root = self.tree.AddRoot("KILLA NEWS")
            self.section_items = {}
            tree = {t["id"]: subs for t, subs in self.core.catalog.categories_tree()}
            names = {t["id"]: t["name"] for t, _ in self.core.catalog.categories_tree()}
            for key, label in SECTION_ORDER:
                if key == "home":
                    item = self._add(root, label, {"kind": "home_main", "title": "Prima pagina - Notizie principali", "key": "home"})
                    for kind, sub in (("home_latest", "Ultime notizie (ultime 3 ore)"),
                                      ("home_recent", "Notizie più recenti"),
                                      ("home_highlight", "In evidenza (ultima ora delle agenzie)"),
                                      ("home_deep", "Approfondimenti")):
                        self._add(item, sub, {"kind": kind, "title": f"Prima pagina - {sub}", "key": kind})
                elif key == "all":
                    item = self._add(root, label, {"kind": "all", "title": "Tutti i giornali - tutte le notizie", "key": "all"})
                    groups = {}
                    for src in self.core.catalog.sources(include_disabled=False):
                        groups.setdefault(src["group_name"] or "Altre testate", []).append(src)
                    for group in sorted(groups):
                        g_item = self._add(item, group, {"kind": "group", "group": group, "title": group,
                                                         "key": "group:" + group})
                        for src in groups[group]:
                            self._add(g_item, self.source_label(src), self.source_view(src))
                elif key in tree:
                    item = self._add(root, names.get(key, label),
                                     {"kind": "category", "category_id": key, "title": names.get(key, label), "key": key})
                    for sub in tree[key]:
                        self._add(item, sub["name"], {"kind": "category", "category_id": sub["id"],
                                                      "title": f"{names.get(key, label)} - {sub['name']}", "key": sub["id"]})
                elif key == "local":
                    item = self._build_local(root, label)
                elif key == "international":
                    item = self._build_international(root, label, tree.get("esteri"), names.get("esteri"))
                elif key == "saved":
                    item = self._add(root, label, {"kind": "saved", "title": "Articoli salvati - tutti", "key": "saved"})
                    self._add(item, "Da leggere", {"kind": "saved", "to_read": True, "title": "Articoli da leggere",
                                                   "key": "to_read"})
                    self._add(item, "Disponibili offline", {"kind": "offline", "title": "Articoli disponibili offline",
                                                            "key": "offline"})
                    for folder in self.core.favorites.folders():
                        self._add(item, f"Cartella {folder['name']}", {
                            "kind": "saved", "folder_id": folder["id"], "title": f"Cartella {folder['name']}",
                            "key": f"folder:{folder['id']}"})
                elif key == "history":
                    item = self._add(root, label, {"kind": "history", "title": "Cronologia", "key": "history"})
                elif key == "search":
                    item = self._add(root, label, {"kind": "search_panel", "title": "Cerca", "key": "search"})
                elif key == "settings":
                    item = self._add(root, label, {"kind": "settings", "title": "Impostazioni", "key": "settings"})
                elif key == "killa":
                    item, kview = self._choices_node(root, label, "Killa Records", "killa")
                    for action, text in KILLA_ITEMS:
                        self._add(item, text, {"kind": "action", "action": action, "title": text,
                                               "key": f"killa:{action}"})
                        kview["choices"].append((text, f"action:{action}"))
                else:
                    continue
                self.section_items[key] = item
        finally:
            self.tree.Thaw()
        target = self.find(keep_key) if keep_key else None
        self.tree.SelectItem(target or self.section_items["home"])

    # ------------------------------------------------------------------ giornali locali
    def _choices_node(self, parent, label, title, key):
        view = {"kind": "choices", "title": title, "key": key, "choices": []}
        return self._add(parent, label, view), view

    def _build_local(self, root, label):
        """Giornali locali: prima si sceglie il luogo o la testata, poi si leggono gli articoli.
        Ogni livello offre anche «Tutti gli articoli» di quel luogo."""
        tree = self.core.catalog.local_tree()
        sources = [s for provs in tree.values() for cities in provs.values() for lst in cities.values() for s in lst]
        top, top_view = self._choices_node(root, label, "Giornali locali: scegli cosa leggere", "local")

        def leaf(parent, parent_view, text, view):
            self._add(parent, text, view)
            parent_view["choices"].append((text, view["key"]))

        def source_leaf(parent, parent_view, src, branch, place=""):
            text = self.source_label(src) + (f" ({place})" if place else "")
            view = dict(self.source_view(src), key=f"loc-{branch}:{src['id']}")
            leaf(parent, parent_view, text, view)

        leaf(top, top_view, f"Tutti gli articoli locali ({len(sources)} testate)",
             {"kind": "local", "title": "Giornali locali - tutti gli articoli", "key": "local_all"})

        # per città
        cities = sorted({(city, region, prov) for region, provs in tree.items() for prov, cs in provs.items()
                         for city in cs if city}, key=lambda c: c[0].lower())
        c_node, c_view = self._choices_node(top, "Scegli per città", "Giornali locali - scegli la città",
                                            "local_cities")
        top_view["choices"].append(("Scegli per città", "local_cities"))
        for city, region, prov in cities:
            ckey = f"city:{region}:{prov}:{city}"
            n, v = self._choices_node(c_node, f"{city} ({region})", f"Giornali locali - {city}", ckey)
            c_view["choices"].append((f"{city} ({region})", ckey))
            leaf(n, v, f"Tutti gli articoli di {city}", {"kind": "local", "region": region, "province": prov,
                                                         "city": city, "title": f"Locali - {city}, tutti gli articoli",
                                                         "key": f"cityall:{region}:{prov}:{city}"})
            for src in tree[region][prov][city]:
                source_leaf(n, v, src, "c")

        # per regione e provincia
        r_node, r_view = self._choices_node(top, "Scegli per regione e provincia",
                                            "Giornali locali - scegli la regione", "local_regions")
        top_view["choices"].append(("Scegli per regione e provincia", "local_regions"))
        for region in sorted(tree, key=str.lower):
            rkey = f"region:{region}"
            n, v = self._choices_node(r_node, region, f"Giornali locali - {region}", rkey)
            r_view["choices"].append((region, rkey))
            leaf(n, v, f"Tutti gli articoli della regione {region}",
                 {"kind": "local", "region": region, "title": f"Locali - {region}, tutti gli articoli",
                  "key": f"regionall:{region}"})
            for prov in sorted(tree[region], key=str.lower):
                if not prov:
                    for city_sources in tree[region][prov].values():
                        for src in city_sources:
                            source_leaf(n, v, src, "r")
                    continue
                pkey = f"prov:{region}:{prov}"
                pn, pv = self._choices_node(n, f"Provincia di {prov}", f"Giornali locali - provincia di {prov}", pkey)
                v["choices"].append((f"Provincia di {prov}", pkey))
                leaf(pn, pv, f"Tutti gli articoli della provincia di {prov}",
                     {"kind": "local", "region": region, "province": prov,
                      "title": f"Locali - provincia di {prov}, tutti gli articoli", "key": f"provall:{region}:{prov}"})
                for city in sorted(tree[region][prov], key=str.lower):
                    for src in tree[region][prov][city]:
                        source_leaf(pn, pv, src, "p", city)

        # per testata
        s_node, s_view = self._choices_node(top, "Scegli per testata", "Giornali locali - scegli la testata",
                                            "local_sources")
        top_view["choices"].append(("Scegli per testata", "local_sources"))
        for src in sorted(sources, key=lambda s: s["name"].lower()):
            place = src["city"] or src["region"]
            source_leaf(s_node, s_view, src, "s", place)
        return top

    # ------------------------------------------------------------------ giornali internazionali
    def _build_international(self, root, label, world_subs=None, world_name=None):
        """Giornali internazionali: si sceglie per continente, per nazione o per testata.
        Scelto il luogo compaiono prima le testate; ogni livello offre anche «Tutti gli articoli»."""
        tree = self.core.catalog.international_tree()
        countries = sorted(((country, cont) for cont, cs in tree.items() for country in cs),
                           key=lambda c: c[0].lower())
        sources = [s for cs in tree.values() for lst in cs.values() for s in lst]
        top, top_view = self._choices_node(root, label, "Giornali internazionali: scegli cosa leggere",
                                           "international")

        def leaf(parent, parent_view, text, view):
            self._add(parent, text, view)
            parent_view["choices"].append((text, view["key"]))

        def source_leaf(parent, parent_view, src, branch, place=""):
            text = self.source_label(src) + (f" ({place})" if place else "")
            leaf(parent, parent_view, text, dict(self.source_view(src), key=f"int-{branch}:{src['id']}"))

        def country_node(parent, parent_view, country, cont, branch, with_continent=False):
            ckey = f"intcountry-{branch}:{country}"
            text = f"{country} ({cont})" if with_continent else country
            n, v = self._choices_node(parent, f"{text}, {len(tree[cont][country])} testate",
                                      f"Giornali internazionali - {country}", ckey)
            parent_view["choices"].append((f"{text}, {len(tree[cont][country])} testate", ckey))
            for src in tree[cont][country]:
                source_leaf(n, v, src, branch + "c")
            leaf(n, v, f"Tutti gli articoli di {country} (testate mescolate)",
                 {"kind": "international", "country": country, "key": f"intcountryall-{branch}:{country}",
                  "title": f"Internazionali - {country}, tutti gli articoli"})

        leaf(top, top_view, f"Tutti gli articoli internazionali ({len(sources)} testate)",
             {"kind": "international", "title": "Giornali internazionali - tutti gli articoli",
              "key": "international_all"})

        # per continente
        k_node, k_view = self._choices_node(top, "Scegli per continente",
                                            "Giornali internazionali - scegli il continente", "int_continents")
        top_view["choices"].append(("Scegli per continente", "int_continents"))
        for cont, cs in tree.items():
            n_src = sum(len(lst) for lst in cs.values())
            ckey = f"intcont:{cont}"
            n, v = self._choices_node(k_node, f"{cont}, {len(cs)} paesi", f"Giornali internazionali - {cont}", ckey)
            k_view["choices"].append((f"{cont}, {len(cs)} paesi", ckey))
            for country in sorted(cs, key=str.lower):
                country_node(n, v, country, cont, "k")
            leaf(n, v, f"Tutti gli articoli di {cont} ({n_src} testate mescolate)",
                 {"kind": "international", "continent": cont, "key": f"intcontall:{cont}",
                  "title": f"Internazionali - {cont}, tutti gli articoli"})

        # per nazione
        c_node, c_view = self._choices_node(top, "Scegli per nazione",
                                            "Giornali internazionali - scegli la nazione", "int_countries")
        top_view["choices"].append(("Scegli per nazione", "int_countries"))
        for country, cont in countries:
            country_node(c_node, c_view, country, cont, "n", with_continent=True)

        # per testata
        s_node, s_view = self._choices_node(top, "Scegli per testata",
                                            "Giornali internazionali - scegli la testata", "int_sources")
        top_view["choices"].append(("Scegli per testata", "int_sources"))
        for src in sorted(sources, key=lambda s: s["name"].lower()):
            source_leaf(s_node, s_view, src, "s", src["country"])

        # le notizie dal mondo di tutti i giornali, divise per argomento (la vecchia sezione Esteri)
        if world_subs is not None:
            w_node, w_view = self._choices_node(top, "Notizie dal mondo per area (anche dai giornali italiani)",
                                                "Notizie dal mondo per area", "int_world")
            top_view["choices"].append(("Notizie dal mondo per area (anche dai giornali italiani)", "int_world"))
            leaf(w_node, w_view, "Tutte le notizie dal mondo",
                 {"kind": "category", "category_id": "esteri", "title": world_name or "Notizie dal mondo",
                  "key": "esteri"})
            for sub in world_subs:
                leaf(w_node, w_view, sub["name"], {"kind": "category", "category_id": sub["id"],
                                                    "title": f"Notizie dal mondo - {sub['name']}", "key": sub["id"]})
        return top

    @staticmethod
    def source_label(src):
        if not src["feed_count"]:
            return f"{src['name']} (solo sito, nessun feed)"
        return src["name"]

    @staticmethod
    def source_view(src):
        return {"kind": "source", "source_id": src["id"], "title": src["name"], "key": f"source:{src['id']}",
                "site_only": not src["feed_count"], "site_url": src["site_url"]}

    def find(self, key):
        def walk(item):
            while item.IsOk():
                data = self.tree.GetItemData(item)
                if data and data.get("key") == key:
                    return item
                child, _ = self.tree.GetFirstChild(item)
                if child.IsOk():
                    found = walk(child)
                    if found:
                        return found
                item = self.tree.GetNextSibling(item)
            return None
        first, _ = self.tree.GetFirstChild(self.tree.GetRootItem())
        return walk(first)

    # ------------------------------------------------------------------ eventi
    def current_view(self):
        item = self.tree.GetSelection()
        return self.tree.GetItemData(item) if item.IsOk() else None

    def select_section(self, key, focus=True):
        item = self.section_items.get(key) or self.find(key)
        if item:
            self.tree.SelectItem(item)
            self.tree.EnsureVisible(item)
            if focus:
                self.tree.SetFocus()

    def shutdown(self):
        """Da chiamare prima di distruggere la finestra: Windows, eliminando l'albero,
        genera eventi di selezione che non devono più essere gestiti."""
        self.closing = True
        if self._pending and self._pending.IsRunning():
            self._pending.Stop()
        try:
            self.tree.Unbind(wx.EVT_TREE_SEL_CHANGED)
            self.tree.Unbind(wx.EVT_TREE_ITEM_ACTIVATED)
        except RuntimeError:
            pass

    def _safe_call(self, view):
        if not self.closing and self:
            self.on_select(view)

    def _on_sel_changed(self, event):
        if self.closing:
            return
        try:
            item = event.GetItem()
            view = self.tree.GetItemData(item) if item.IsOk() else None
        except RuntimeError:  # albero in fase di distruzione
            return
        if view is None:
            return
        if self._pending and self._pending.IsRunning():
            self._pending.Stop()
        # breve ritardo: scorrendo con le frecce non si ricarica l'elenco a ogni tasto
        self._pending = wx.CallLater(250, self._safe_call, view)

    def _on_activated(self, event):
        if self.closing:
            return
        try:
            view = self.tree.GetItemData(event.GetItem())
        except RuntimeError:
            return
        if view:
            if self._pending and self._pending.IsRunning():
                self._pending.Stop()
                self.on_select(view)
            self.on_activate(view)
