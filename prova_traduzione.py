import sys, time
sys.path.insert(0, ".")
from killanews import translator
for txt in ["The government approved a new budget on Tuesday.\nOpposition parties criticised the plan.",
            "東京で新しい地下鉄の駅が開業しました。",
            "Le président a annoncé de nouvelles mesures pour l'économie.",
            "أعلنت الحكومة المغربية عن خطة جديدة للتعليم.",
            ("Long paragraph about football. " * 120)]:
    t0 = time.time()
    out, lang = translator.translate_text(txt)
    print("LINGUA", lang, "TEMPO %.1fs" % (time.time() - t0), "->", out[:160].replace("\n", " | "))
