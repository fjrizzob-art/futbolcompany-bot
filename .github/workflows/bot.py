import os, csv, datetime, traceback, sys
import tweepy

# Carga facts con columnas: text, tag, md (md = "MM-DD" opcional)
def load_facts(path="facts.csv"):
    facts = []
    with open(path, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        # Validar cabecera
        expected = ["text","tag","md"]
        if [h.strip().lower() for h in rd.fieldnames or []] != expected:
            raise RuntimeError("Cabecera CSV inválida. Debe ser exactamente: text,tag,md")
        for row in rd:
            text = (row.get("text") or "").strip()
            tag  = (row.get("tag")  or "").strip()
            md   = (row.get("md")   or "").strip()  # ej: 07-16
            if text:
                if len(text) > 280:
                    text = text[:279] + "…"
                facts.append({"text": text, "tag": tag, "md": md})
    if not facts:
        raise RuntimeError("facts.csv no tiene filas válidas (revisa que haya contenido debajo de la cabecera).")
    return facts

# Rotación de temas por franja (puedes ajustarlas)
MORNING_ORDER   = ["Mundial", "Champions", "Libertadores", "Eliminatorias", "Historia"]
AFTERNOON_ORDER = ["Libertadores", "Mundial", "Champions", "Eliminatorias", "Historia"]

def pick_today(facts):
    today = datetime.datetime.utcnow().date()
    md_today = today.strftime("%m-%d")

    # Índice determinístico por día
    base = datetime.date(2025, 1, 1)
    day_idx = (today - base).days  # 0,1,2,...

    # Bucket horario (mañana/tarde en UTC; 13 y 21 UTC ≈ 08 y 16 GYE)
    hour = datetime.datetime.utcnow().hour
    morning = hour < 17

    # 1) Efemérides primero
    efes = [f for f in facts if f.get("md") == md_today]
    if efes:
        idx = day_idx % len(efes)
        return efes[idx]["text"]

    # 2) Rotación por tema (si no hay efemérides)
    order = MORNING_ORDER if morning else AFTERNOON_ORDER
    theme = order[day_idx % len(order)]
    themed = [f for f in facts if (f.get("tag") or "").lower() == theme.lower()]
    if themed:
        idx = (day_idx // len(order)) % len(themed)
        return themed[idx]["text"]

    # 3) Fallback total: round-robin global (2 tuits por día)
    idx_global = (day_idx * 2 + (0 if morning else 1)) % len(facts)
    return facts[idx_global]["text"]

def post_to_x(text):
    required = ["X_API_KEY","X_API_SECRET","X_ACCESS_TOKEN","X_ACCESS_TOKEN_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Faltan secrets: {', '.join(missing)} (crea/pega en Settings → Secrets → Actions)")

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"]
    )
    try:
        resp = client.create_tweet(text=text)
        print("Publicado:", resp)
    except Exception as e:
        # Mostrar info útil del error
        print("::error ::Error al publicar en X")
        if hasattr(e, "response") and getattr(e.response, "text", None):
            print("Respuesta de X:", e.response.text)
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    try:
        facts = load_facts()
        tweet = pick_today(facts)
        print("Tweet seleccionado:", tweet)
        post_to_x(tweet)
    except Exception as e:
        print("::error ::Fallo en bot.py:", repr(e))
        traceback.print_exc()
        sys.exit(1)
