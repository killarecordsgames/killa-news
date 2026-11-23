import sys, logging
sys.path.insert(0, '.')
logging.basicConfig(level=logging.WARNING)
from killanews import translator
fr = ("Le gouvernement français a annoncé mardi une série de mesures pour soutenir l'économie, après une année marquée par une inflation élevée.\n" * 12)
for lingua in ("fr", ""):
    try:
        t, l = translator.translate_text(fr, lingua)
        print("OK", repr(lingua), "->", l, len(t), t[:110].encode("ascii", "replace").decode())
    except Exception as e:
        print("ERRORE", repr(e), repr(e.__cause__))
print("pause:", translator._PAUSA)
