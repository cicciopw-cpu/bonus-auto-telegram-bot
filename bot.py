import os
import re
import json
import hashlib
import datetime
import requests
import feedparser
from bs4 import BeautifulSoup


BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "state.json"

# Lascia False: così il bot non manda notifiche inutili al primo controllo.
SEND_ON_FIRST_RUN = False


SITES = [
    {
        "name": "Ecobonus MIMIT - Cos'è",
        "url": "https://ecobonus.mimit.gov.it/cose",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Auto",
        "url": "https://ecobonus.mimit.gov.it/auto",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Contributi",
        "url": "https://ecobonus.mimit.gov.it/contributi",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Risorse stanziate",
        "url": "https://ecobonus.mimit.gov.it/risorse-stanziate",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Avvisi e notizie",
        "url": "https://ecobonus.mimit.gov.it/avvisi-notizie",
        "important": True,
    },
    {
        "name": "MIMIT - Ecobonus automotive",
        "url": "https://www.mimit.gov.it/it/incentivi/ecobonus-automotive",
        "important": True,
    },
    {
        "name": "MIMIT - Incentivi aggiornamenti",
        "url": "https://www.mimit.gov.it/it/incentivi-aggiornamenti",
        "important": True,
    },
    {
        "name": "Bonus Veicoli Elettrici MASE - Home",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/index.html",
        "important": True,
    },
    {
        "name": "Bonus Veicoli Elettrici MASE - Login Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login",
        "important": True,
    },
    {
        "name": "Regione Campania - Sportello Incentivi",
        "url": "https://sportelloincentivi.regione.campania.it/",
        "important": True,
    },
    {
        "name": "Regione Campania - News",
        "url": "https://www.regione.campania.it/regione-informa/notizie",
        "important": False,
    },
]


NEWS_QUERIES = [
    "bonus auto elettriche 10000 euro",
    "bonus auto elettriche 11000 euro",
    "voucher auto elettriche",
    "voucher veicoli elettrici MASE",
    "incentivi auto elettriche MASE",
    "ecobonus auto elettriche apertura",
    "ecobonus auto elettriche prenotazioni",
    "bonus veicoli elettrici beneficiario",
    "incentivi rottamazione auto elettriche",
    "fondi auto elettriche disponibili",
    "bonus auto elettriche ISEE 40000",
    "bonus auto elettriche ISEE 30000",
    "Leapmotor T03 incentivo",
    "Leapmotor T03 bonus auto elettrica",
    "MIMIT bonus auto elettriche",
    "MASE voucher auto elettriche",
]


KEYWORDS = [
    "auto",
    "automobile",
    "automobili",
    "autovetture",
    "auto elettrica",
    "auto elettriche",
    "elettrica",
    "elettriche",
    "veicoli elettrici",
    "bev",
    "plug-in",
    "plug in",
    "phev",
    "categoria m1",
    "m1",
    "0-20",
    "0 - 20",
    "0/20",
    "g/km",
    "co2",
    "zero emissioni",
    "emissioni zero",
    "ecobonus",
    "incentivo",
    "incentivi",
    "bonus",
    "voucher",
    "rottamazione",
    "prenotazione",
    "prenotazioni",
    "piattaforma",
    "fondi",
    "risorse",
    "disponibile",
    "disponibili",
    "apertura",
    "riapertura",
    "domande",
    "bando",
    "beneficiario",
    "accedi",
    "login",
    "richiedi voucher",
    "richiedi il voucher",
    "voucher disponibile",
    "voucher disponibili",
    "piattaforma attiva",
    "sportello aperto",
    "leapmotor",
    "t03",
]


AVAILABILITY_WORDS = [
    "disponibile",
    "disponibili",
    "attiva",
    "attivo",
    "apertura",
    "riapertura",
    "prenotazioni",
    "prenotazione",
    "domande",
    "fondo",
    "fondi",
    "risorse",
    "bando",
    "sportello",
    "accedi",
    "richiedi",
    "richiedi voucher",
    "richiedi il voucher",
    "piattaforma attiva",
    "sportello aperto",
    "accesso",
    "login",
    "click day",
]


AUTO_FOCUS_WORDS = [
    "auto",
    "automobile",
    "automobili",
    "autovetture",
    "auto elettrica",
    "auto elettriche",
    "categoria m1",
    "m1",
    "0-20",
    "0 - 20",
    "0/20",
    "g/km",
    "co2",
    "elettrica",
    "elettriche",
    "bev",
    "zero emissioni",
    "emissioni zero",
    "leapmotor",
    "t03",
]


EXCLUDE_WORDS = [
    "motocicli",
    "ciclomotori",
    "due ruote",
    "scooter",
    "bici elettriche",
    "biciclette elettriche",
    "monopattini",
    "veicoli commerciali",
    "installatori",
    "colonnine",
    "wallbox",
]


AMOUNT_PATTERNS = [
    r"10\.000\s*€",
    r"10000\s*€",
    r"10 mila",
    r"11\.000\s*€",
    r"11000\s*€",
    r"12\.000\s*€",
    r"12000\s*€",
    r"13\.000\s*€",
    r"13000\s*€",
    r"13\.750\s*€",
    r"13750\s*€",
    r"14\.000\s*€",
    r"14000\s*€",
    r"15\.000\s*€",
    r"15000\s*€",
    r"20\.000\s*€",
    r"20000\s*€",
    r"22\.000\s*€",
    r"22000\s*€",
]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}

    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    return text


def get_page_text(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36 BonusAutoTelegramBot/1.0"
        )
    }

    response = requests.get(url, headers=headers, timeout=45)
    response.raise_for_status()

    return clean_text(response.text)


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contains_any(text, words):
    text_lower = text.lower()
    return any(word.lower() in text_lower for word in words)


def contains_amount_10000_or_more(text):
    text_lower = text.lower()

    for pattern in AMOUNT_PATTERNS:
        if re.search(pattern, text_lower):
            return True

    euro_amounts = re.findall(r"(\d{1,3}(?:\.\d{3})+|\d{5,})\s*€", text_lower)

    for amount in euro_amounts:
        try:
            value = int(amount.replace(".", ""))
            if value >= 10000:
                return True
        except Exception:
            pass

    return False


def make_snippet(text):
    text_lower = text.lower()
    positions = []

    for word in KEYWORDS + AVAILABILITY_WORDS:
        pos = text_lower.find(word.lower())
        if pos != -1:
            positions.append(pos)

    if not positions:
        return text[:700]

    start = max(0, min(positions) - 250)
    end = min(len(text), start + 900)

    return text[start:end]


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }

    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()


def should_alert(text, changed, first_run, site_important):
    text_lower = text.lower()

    has_auto_focus = any(word in text_lower for word in AUTO_FOCUS_WORDS)
    has_excluded_topic = any(word in text_lower for word in EXCLUDE_WORDS)

    has_bonus_words = contains_any(text, KEYWORDS)
    has_availability = contains_any(text, AVAILABILITY_WORDS)
    has_big_amount = contains_amount_10000_or_more(text)

    if first_run and not SEND_ON_FIRST_RUN:
        return False

    if not changed:
        return False

    # Se parla solo di moto/scooter/colonnine e non di auto, non avvisare.
    if has_excluded_topic and not has_auto_focus:
        return False

    # Deve avere focus su auto elettriche, M1 o Leapmotor T03.
    if not has_auto_focus:
        return False

    # Avviso se pagina importante + parole bonus + parole di apertura/disponibilità.
    if site_important and has_bonus_words and has_availability:
        return True

    # Avviso se trova importi da 10.000 euro in su + parole bonus.
    if has_big_amount and has_bonus_words:
        return True

    return False


def google_news_rss_url(query):
    encoded_query = requests.utils.quote(query)
    return f"https://news.google.com/rss/search?q={encoded_query}&hl=it&gl=IT&ceid=IT:it"


def is_relevant_news(title, summary):
    text = f"{title} {summary}".lower()

    main_topics = [
        "auto elettrica",
        "auto elettriche",
        "veicoli elettrici",
        "ecobonus",
        "bonus",
        "voucher",
        "incentivi",
        "incentivo",
        "rottamazione",
        "mase",
        "mimit",
        "leapmotor",
        "t03",
    ]

    good_signals = [
        "apertura",
        "riapertura",
        "prenotazioni",
        "domande",
        "piattaforma",
        "fondi",
        "disponibili",
        "disponibile",
        "10.000",
        "10000",
        "11.000",
        "11000",
        "isee",
        "beneficiario",
        "sportello",
        "click day",
        "voucher",
    ]

    bad_topics = [
        "moto",
        "motocicli",
        "scooter",
        "bici elettriche",
        "biciclette elettriche",
        "monopattini",
        "colonnine",
        "wallbox",
    ]

    has_main_topic = any(word in text for word in main_topics)
    has_good_signal = any(word in text for word in good_signals)
    has_bad_topic = any(word in text for word in bad_topics)
    has_auto_word = any(word in text for word in AUTO_FOCUS_WORDS)

    if has_bad_topic and not has_auto_word:
        return False

    return has_main_topic and has_good_signal


def check_news(state):
    alerts = []
    seen_news = state.get("_seen_news", {})

    for query in NEWS_QUERIES:
        try:
            feed_url = google_news_rss_url(query)
            feed = feedparser.parse(feed_url)

            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                published = entry.get("published", "Data non disponibile")

                if not title or not link:
                    continue

                news_id = hashlib.sha256(link.encode("utf-8")).hexdigest()

                if news_id in seen_news:
                    continue

                if not is_relevant_news(title, summary):
                    continue

                message = (
                    "📰 NUOVA NOTIZIA BONUS AUTO ELETTRICHE\n\n"
                    f"Ricerca: {query}\n"
                    f"Titolo: {title}\n"
                    f"Data: {published}\n"
                    f"Link: {link}\n\n"
                    "Motivo: nuova notizia collegata a bonus, voucher, incentivi, fondi, "
                    "apertura piattaforma o auto elettriche."
                )

                alerts.append(message)

                seen_news[news_id] = {
                    "title": title,
                    "link": link,
                    "query": query,
                    "published": published,
                    "saved_at": datetime.datetime.now().strftime("%d/%m/%Y %H:%M"),
                }

        except Exception as e:
            print(f"Errore controllo news per ricerca '{query}': {e}")

    state["_seen_news"] = seen_news

    return alerts


def check_sites(state):
    alerts = []
    errors = []

    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

    for site in SITES:
        name = site["name"]
        url = site["url"]

        try:
            text = get_page_text(url)
            current_hash = text_hash(text)

            old_hash = state.get(url, {}).get("hash")
            first_run = old_hash is None
            changed = old_hash != current_hash

            if should_alert(text, changed, first_run, site.get("important", False)):
                snippet = make_snippet(text)

                message = (
                    "🚗 POSSIBILE BONUS AUTO ELETTRICHE DISPONIBILE / AGGIORNATO\n\n"
                    f"Fonte: {name}\n"
                    f"Controllo: {now}\n"
                    f"Link: {url}\n\n"
                    "Motivo: la pagina è cambiata e contiene parole collegate ad auto elettriche, "
                    "bonus, incentivi, fondi, voucher, rottamazione o apertura piattaforma.\n\n"
                    f"Anteprima:\n{snippet[:1200]}"
                )

                alerts.append(message)

            state[url] = {
                "hash": current_hash,
                "last_checked": now,
                "name": name,
            }

        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    # Non mandiamo errori temporanei su Telegram, così non ti spammiamo.
    # Se un sito istituzionale non risponde, lo vedrai solo nei log GitHub.
    if errors:
        print("Errori durante il controllo siti:")
        for error in errors[:10]:
            print(error)

    return alerts


def main():
    state = load_state()

    alerts = []

    site_alerts = check_sites(state)
    alerts.extend(site_alerts)

    news_alerts = check_news(state)
    alerts.extend(news_alerts)

    save_state(state)

    for alert in alerts:
        send_telegram(alert)


if __name__ == "__main__":
    main()
