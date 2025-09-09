import os, csv, datetime
import tweepy

# =========
# CONFIG
# =========

# Prefijos por tag (EMOJIS + abreviaturas) — sin hashtags
STYLES = {
    "Mundial":       {"prefix": "🌍 WC"},
    "Champions":     {"prefix": "⭐️ UCL"},
    "Libertadores":  {"prefix": "🏆 LIB"},
    "Eliminatorias": {"prefix": "🛤️ ELIM"},
    "Historia":      {"prefix": "📚 HIST"},
    "_default":      {"prefix": "⚽️ Fútbol"},
}

# Firma fija al final de TODOS los tuits
SIGNATURE = " — ⚽️ FútbolCompany"

# Rotación de temas por franja (ajustable)
MORNING_ORDER   = ["Mundial", "Champions", "Libertadores", "Eliminatorias", "Historia"]
AFTERNOON_ORDER = ["Libertadores", "Mundial", "Champions", "Eliminatorias", "Historia"]


# =========
# CARGA CSV
# =========

# CSV con cabecera: text,tag,md   (md = "MM-DD" opcional)
def load_facts(path="facts.csv"):
    facts = []
    with open(path, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        expected = ["text","tag","md"]
        if [h.strip().lower() for h in (rd.fieldnames or [])] != expected:
            raise RuntimeError("Cabecera CSV inválida. Debe ser exactamente: text,tag,md")
        for row in rd:
            text = (row.get("text") or "").strip()
            tag  = (row.get("tag")  or "").strip()
            md   = (row.get("md")   or "").strip()  # ej: 07-16
            if text:
                facts.append({"text": text, "tag": tag, "md": md})
    if not facts:
        raise RuntimeError("facts.csv no tiene filas válidas (revisa que haya contenido debajo de la cabecera).")
    return facts


# =================
# SELECCIÓN DIARIA
# =================

def pick_today(facts):
    """Devuelve el dict del fact seleccionado (no solo el texto)."""
    today = datetime.datetime.utcnow().date()
    md_today = today.strftime("%m-%d")

    # Índice determinístico por día (sin estado)
    base = datetime.date(2025, 1, 1)
    day_idx = (today - base).days  # 0,1,2,...

    # Bucket horario: mañana (<17 UTC) o tarde (>=17 UTC)
    hour = datetime.datetime.utcnow().hour
    morning = hour < 17

    # 1) Efemérides primero
    efes = [f for f in facts if f.get("md") == md_today]
    if efes:
        idx = day_idx % len(efes)
        return efes[idx]

    # 2) Rotación por tema si no hay efemérides
    order = MORNING_ORDER if morning else AFTERNOON_ORDER
    theme = order[day_idx % len(order)]
    themed = [f for f in facts if (f.get("tag") or "").lower() == theme.lower()]
    if themed:
        idx = (day_idx // len(order)) % len(themed)
        return themed[idx]

    # 3) Fallback total: round-robin global (dos tuits por día)
    idx_global = (day_idx * 2 + (0 if morning else 1)) % len(facts)
    return facts[idx_global]


# ===================
# FORMATEO DEL TUIT
# ===================

def format_tweet(text, tag, is_efemeride=False):
    """
    [Prefijo por tag (+ '· 📅 Un día como hoy' si aplica)] — [texto] [firma]
    Sin hashtags. Se respeta límite de 280 caracteres.
    """
    style  = STYLES.get(tag, STYLES["_default"])
    prefix = style["prefix"] + (" · 📅 Un día como hoy" if is_efemeride else "")
    sep    = " — "
    tail   = SIGNATURE

    # Espacio disponible para el cuerpo
    allowed = 280 - len(prefix) - len(sep) - len(tail)
    if allowed < 0:
        allowed = 0

    main = text
    if len(main) > allowed:
        ell = "…"
        main = main[:max(0, allowed - len(ell))] + (ell if allowed > 0 else "")

    return f"{prefix}{sep}{main}{tail}"


# ================
# PUBLICAR EN X
# ================

def post_to_x(text):
    required = ["X_API_KEY","X_API_SECRET","X_ACCESS_TOKEN","X_ACCESS_TOKEN_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Faltan secrets: {', '.join(missing)} (Settings → Secrets → Actions)")

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"]
    )
    resp = client.create_tweet(text=text)
    print("Publicado:", resp)


# ==========
# MAIN
# ==========

if __name__ == "__main__":
    facts = load_facts()
    fact  = pick_today(facts)

    # Detectar si es efeméride (por el campo md)
    today_md = datetime.datetime.utcnow().strftime("%m-%d")
    is_efe   = (fact.get("md") or "") == today_md

    tweet = format_tweet(fact["text"], fact.get("tag",""), is_efemeride=is_efe)
    print("Tweet seleccionado:", tweet)
    post_to_x(tweet)
