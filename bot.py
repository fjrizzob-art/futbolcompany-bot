import os, csv, datetime
import tweepy

# ========
# CONFIG
# ========

# Firma fija al final de TODOS los tuits
SIGNATURE = " — ⚽️ FútbolCompany"

# Rotación de temas por franja (se usan para elegir, no para mostrar)
MORNING_ORDER   = ["Mundial", "Champions", "Libertadores", "Eliminatorias", "Historia"]
AFTERNOON_ORDER = ["Libertadores", "Mundial", "Champions", "Eliminatorias", "Historia"]


# =========
# CARGA CSV
# =========

# CSV con cabecera EXACTA: text,tag,md   (md = "MM-DD" opcional)
def load_facts(path="facts.csv"):
    facts = []
    with open(path, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        expected = ["text","tag","md"]
        if [h.strip().lower() for h in (rd.fieldnames or [])] != expected:
            raise RuntimeError("Cabecera CSV inválida. Debe ser exactamente: text,tag,md")
        for row in rd:
            text = (row.get("text") or "").strip()
            tag  = (row.get("tag")  or "").strip()  # usado para seleccionar, NO para mostrar
            md   = (row.get("md")   or "").strip()  # ej: 07-16
            if text:
                facts.append({"text": text, "tag": tag, "md": md})
    if not facts:
        raise RuntimeError("facts.csv no tiene filas válidas (revisa que haya contenido bajo la cabecera).")
    return facts


# =================
# SELECCIÓN DIARIA
# =================

def pick_today(facts):
    """Devuelve el dict del fact seleccionado usando 2 slots diarios (08:00 y 10:00 GYE)."""
    import datetime
    today = datetime.datetime.utcnow().date()
    md_today = today.strftime("%m-%d")

    # Índice determinístico por día
    base = datetime.date(2025, 1, 1)
    day_idx = (today - base).days  # 0,1,2,...

    # Slots en UTC que usa tu workflow: 13 (08:00 GYE) y 15 (10:00 GYE)
    SLOTS_UTC = [13, 15]
    hour = datetime.datetime.utcnow().hour
    # slot = 0 para 13 UTC, slot = 1 para 15 UTC (si se dispara manualmente, aproximamos)
    slot = SLOTS_UTC.index(hour) if hour in SLOTS_UTC else (0 if hour < SLOTS_UTC[-1] else 1)

    # 1) Efemérides primero (rota entre varias usando slot)
    efes = [f for f in facts if f.get("md") == md_today]
    if efes:
        idx = (day_idx * 2 + slot) % len(efes)
        return efes[idx]

    # 2) Rotación por tema (si no hay efemérides)
    MORNING_ORDER   = ["Mundial", "Champions", "Libertadores", "Eliminatorias", "Historia"]
    AFTERNOON_ORDER = MORNING_ORDER  # mismo orden; no usamos “tarde” con estos horarios
    order = MORNING_ORDER  # ambos disparos están en la mañana UTC
    theme = order[(day_idx * 2 + slot) % len(order)]
    themed = [f for f in facts if (f.get("tag") or "").lower() == theme.lower()]
    if themed:
        idx = (day_idx * 2 + slot) % len(themed)
        return themed[idx]

    # 3) Fallback total: round-robin global en 2 pasos diarios
    idx_global = (day_idx * 2 + slot) % len(facts)
    return facts[idx_global]



# ===================
# FORMATEO DEL TUIT
# ===================

def format_tweet(text, is_efemeride=False):
    """
    Sin mostrar el tag. Si es efeméride, antepone '📅 Un día como hoy — '.
    Siempre añade la firma final. Máximo 280 caracteres.
    """
    header = "📅 Un día como hoy — " if is_efemeride else ""
    allowed = 280 - len(header) - len(SIGNATURE)
    if allowed < 0:
        allowed = 0
    main = text
    if len(main) > allowed:
        ell = "…"
        main = main[:max(0, allowed - len(ell))] + (ell if allowed > 0 else "")
    return f"{header}{main}{SIGNATURE}"


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

    tweet = format_tweet(fact["text"], is_efemeride=is_efe)
    print("Tweet seleccionado:", tweet)
    post_to_x(tweet)
