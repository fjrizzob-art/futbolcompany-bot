import os, csv, random, hashlib, datetime, sys
import tweepy

def load_facts(path="facts.csv"):
    facts = []
    with open(path, encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for row in rd:
            txt = (row.get("text") or "").strip()
            if txt:
                facts.append(txt[:280])  # límite de 280
    if not facts:
        raise RuntimeError("facts.csv vacío o mal formateado (primera fila debe ser 'text').")
    return facts

def pick_today(facts):
    today = datetime.datetime.utcnow().date().isoformat()
    seed = int(hashlib.sha256(today.encode()).hexdigest(), 16)
    rng = random.Random(seed)
    pair = rng.sample(facts, k=2 if len(facts) >= 2 else 1)
    hour = datetime.datetime.utcnow().hour
    bucket = 0 if hour < 17 else 1  # <17 UTC = “mañana” GYE, >=17 = “tarde”
    return pair[0] if len(pair) == 1 or bucket == 0 else pair[1]

def post_to_x(text):
    # Chequeo previo: que existan secrets
    required = ["X_API_KEY","X_API_SECRET","X_ACCESS_TOKEN","X_ACCESS_TOKEN_SECRET"]
    missing = [k for k in required if not os.environ.get(k)]
    if missing:
        raise RuntimeError(f"Faltan secrets: {', '.join(missing)}")

    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"]
    )
    try:
        resp = client.create_tweet(text=text)
        print("Respuesta de X (create_tweet):", resp)
    except tweepy.TweepyException as e:
        msg = getattr(e, "response", None)
        if msg is not None and hasattr(msg, "text"):
            print("ERROR Tweepy response text:", msg.text)
        print("ERROR Tweepy:", repr(e))
        raise

if __name__ == "__main__":
    print("Iniciando bot…")
    facts = load_facts()
    tweet = pick_today(facts)
    print("Tweet seleccionado:", tweet)
    post_to_x(tweet)
    print("Publicado:", tweet)
