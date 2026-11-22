"""Condivisione di un articolo: WhatsApp, email o appunti."""
import os
import sys
import urllib.parse
import webbrowser

import wx

from ..accessibility import announce

INVITO = "Letto con KILLA NEWS, l'edicola digitale accessibile: https://www.killarecordsgames.com/killa-news"

CHOICES = [
    ("whatsapp", "Invia su WhatsApp"),
    ("email", "Invia per email"),
    ("copy_text", "Copia titolo e collegamento negli appunti"),
    ("copy_link", "Copia solo il collegamento negli appunti"),
]


def share_text(article):
    parts = [article.title]
    if article.source_name:
        parts[0] += f" ({article.source_name})"
    if article.link or article.site_url:
        parts.append(article.link or article.site_url)
    parts += ["", INVITO]
    return "\n".join(parts)


def _whatsapp_app_installed():
    if not sys.platform.startswith("win"):
        return False
    try:
        import winreg
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "whatsapp"))
        return True
    except OSError:
        return False


def _open(url):
    if sys.platform.startswith("win"):
        try:
            os.startfile(url)  # programma predefinito (WhatsApp, posta)
            return True
        except OSError:
            pass
    return webbrowser.open(url)


def _copy(text):
    if wx.TheClipboard.Open():
        try:
            wx.TheClipboard.SetData(wx.TextDataObject(text))
        finally:
            wx.TheClipboard.Close()
        return True
    return False


def do_share(article, how):
    """Esegue la condivisione scelta. Restituisce il messaggio da annunciare."""
    text = share_text(article)
    if how == "whatsapp":
        q = urllib.parse.quote(text)
        if _whatsapp_app_installed():
            _open("whatsapp://send?text=" + q)
            return "Apertura di WhatsApp: scegli a chi mandare l'articolo"
        webbrowser.open("https://wa.me/?text=" + q)
        return "Apertura di WhatsApp nel browser: scegli a chi mandare l'articolo"
    if how == "email":
        subject = urllib.parse.quote(article.title)
        _open(f"mailto:?subject={subject}&body={urllib.parse.quote(text)}")
        return "Apertura del programma di posta con l'articolo già scritto"
    if how == "copy_link":
        link = article.link or article.site_url
        if not link:
            return "Questo articolo non ha un collegamento"
        return "Collegamento copiato negli appunti" if _copy(link) else "Impossibile usare gli appunti"
    return "Titolo e collegamento copiati negli appunti" if _copy(text) else "Impossibile usare gli appunti"


def share_article(parent, core, article):
    """Chiede come condividere l'articolo e lo condivide."""
    if article is None:
        return False
    dlg = wx.SingleChoiceDialog(parent, f"Come vuoi condividere l'articolo «{article.title[:120]}»?",
                                "Condividi l'articolo", [label for _, label in CHOICES])
    dlg.SetSelection(0)
    try:
        if dlg.ShowModal() != wx.ID_OK:
            return False
        how = CHOICES[dlg.GetSelection()][0]
    finally:
        dlg.Destroy()
    announce(do_share(article, how))
    stats = getattr(core, "stats", None)
    if stats:
        stats.count("condivisioni")
    return True
