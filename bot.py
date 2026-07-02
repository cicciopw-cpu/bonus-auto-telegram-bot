import os
import re
import json
import hashlib
import datetime
import requests
import feedparser
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright


BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "state.json"

SEND_ON_FIRST_RUN = False

SUMMARY_EVERY_HOURS = 12
ALIVE_MESSAGE_HOUR = 9

NEWS_KEEP_DAYS = 30
MAX_SEEN_NEWS = 500

MIN_MASE_TEXT_LENGTH = 350
SUSPICIOUS_PAGE_ALERT_AFTER = 3
SUSPICIOUS_PAGE_ALERT_COOLDOWN_HOURS = 6

MAX_API_BODY_CHARS = 25000
MAX_API_ENDPOINTS_IN_STATE = 80

API_DISCOVERY_ENABLED = True


MASE_SOLD_OUT_PHRASES = [
    "tutte le risorse risultano al momento prenotate",
    "risorse risultano al momento prenotate",
    "risorse al momento prenotate",
    "risorse prenotate",
    "fondi prenotati",
    "plafond esaurito",
    "fondi esauriti",
    "risorse esaurite",
    "non sono disponibili risorse",
    "non risultano risorse disponibili",
    "non è possibile presentare domanda",
    "non e possibile presentare domanda",
    "non è possibile richiedere il voucher",
    "non e possibile richiedere il voucher",
    "le risorse sono terminate",
    "plafond non disponibile",
    "fondi non disponibili",
    "sportello chiuso",
    "piattaforma non attiva",
    "voucher non disponibile",
    "voucher non disponibili",
]


MASE_AVAILABLE_PHRASES = [
    "voucher disponibili",
    "voucher disponibile",
    "fondi disponibili",
    "fondo disponibile",
    "risorse disponibili",
    "risorsa disponibile",
    "plafond disponibile",
    "disponibilità plafond",
    "disponibilita plafond",
    "sportello aperto",
    "sportello riaperto",
    "piattaforma aperta",
    "piattaforma attiva",
    "piattaforma riattivata",
    "piattaforma riaperta",
    "prenotazioni aperte",
    "domande aperte",
    "presenta domanda",
    "presentare domanda",
    "è possibile presentare domanda",
    "e possibile presentare domanda",
    "puoi presentare domanda",
    "richiedi il voucher",
    "richiedere il voucher",
    "puoi richiedere il voucher",
    "è possibile richiedere il voucher",
    "e possibile richiedere il voucher",
    "richiesta voucher attiva",
    "richiesta voucher",
    "genera voucher",
    "generare voucher",
    "voucher generabile",
    "procedi con la richiesta",
    "accedi per richiedere",
    "sono disponibili risorse",
    "sono disponibili fondi",
    "nuova disponibilità",
    "nuova disponibilita",
    "ulteriori risorse",
    "riapertura dello sportello",
    "riattivazione dello sportello",
    "riapertura piattaforma",
    "riaperti i termini",
]


MASE_IMPORTANT_PHRASES = [
    "avviso importante",
    "plafond",
    "risorse",
    "voucher",
    "beneficiario",
    "fua",
    "isee",
    "rottamazione",
    "veicoli elettrici",
    "categoria m1",
    "bonus veicoli elettrici",
    "pnrr",
    "click day",
]


JAVASCRIPT_SUSPICIOUS_WORDS = [
    "loading",
    "caricamento",
    "app-root",
    "javascript",
    "enable javascript",
    "abilita javascript",
    "webpack",
    "runtime",
]


API_URL_HINTS = [
    "api",
    "rest",
    "graphql",
    "json",
    "plafond",
    "voucher",
    "beneficiario",
    "esercente",
    "disponibil",
    "fondo",
    "fondi",
    "risorse",
    "config",
    "domanda",
    "prenot",
]


SITES = [
    {
        "name": "MASE - Home Bonus Veicoli Elettrici",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/index.html",
        "type": "mase",
        "important": True,
    },
    {
        "name": "MASE - Login Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login",
        "type": "mase",
        "important": True,
    },
    {
        "name": "MASE - Home Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/home",
        "type": "mase",
        "important": True,
    },
    {
        "name": "MASE - Plafond",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond",
        "type": "mase",
        "important": True,
    },
    {
        "name": "MASE - Esercente / Concessionari",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciEsercente/",
        "type": "mase",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Cos'è",
        "url": "https://ecobonus.mimit.gov.it/cose",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Auto",
        "url": "https://ecobonus.mimit.gov.it/auto",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Contributi",
        "url": "https://ecobonus.mimit.gov.it/contributi",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Risorse stanziate",
        "url": "https://ecobonus.mimit.gov.it/risorse-stanziate",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "Ecobonus MIMIT - Avvisi e notizie",
        "url": "https://ecobonus.mimit.gov.it/avvisi-notizie",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "MIMIT - Ecobonus Automotive",
        "url": "https://www.mimit.gov.it/it/incentivi/ecobonus-automotive",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "MIMIT - Incentivi Aggiornamenti",
        "url": "https://www.mimit.gov.it/it/incentivi-aggiornamenti",
        "type": "mimit",
        "important": True,
    },
    {
        "name": "MASE - Comunicati ufficiali",
        "url": "https://www.mase.gov.it/portale/comunicati",
        "type": "mase_news",
        "important": True,
    },
    {
        "name": "Regione Campania - Sportello Incentivi",
        "url": "https://sportelloincentivi.regione.campania.it/",
        "type": "regione",
        "important": True,
    },
    {
        "name": "Regione Campania - News",
        "url": "https://www.regione.campania.it/regione-informa/notizie",
        "type": "regione",
        "important": False,
    },
]


NEWS_QUERIES = [
    "bonus veicoli elettrici MASE voucher disponibili",
    "bonus veicoli elettrici MASE fondi disponibili",
    "voucher auto elettriche MASE disponibili",
    "bonus auto elettriche voucher disponibile",
    "bonus auto elettriche fondi disponibili",
    "MASE bonus veicoli elettrici riapertura piattaforma",
    "MASE voucher auto elettriche sportello aperto",
    "bonus veicoli elettrici beneficiario plafond",
    "ecobonus auto elettriche apertura prenotazioni",
    "incentivi auto elettriche 10000 euro",
    "incentivi auto elettriche 11000 euro",
    "Leapmotor T03 incentivo bonus elettrica",
    "Leapmotor T03 bonus 11000 euro",
    "Leapmotor T03 voucher MASE",
]


AUTO_WORDS = [
    "auto",
    "automobile",
    "automobili",
    "autovetture",
    "auto elettrica",
    "auto elettriche",
    "veicoli elettrici",
    "categoria m1",
    "m1",
    "bev",
    "elettrica",
    "elettriche",
    "0-20",
    "0 - 20",
    "g/km",
    "co2",
    "emissioni zero",
    "zero emissioni",
    "leapmotor",
    "t03",
    "citycar elettrica",
]


BAD_TOPICS = [
    "motocicli",
    "ciclomotori",
    "scooter",
    "due ruote",
    "bici elettriche",
    "biciclette elettriche",
    "monopattini",
    "colonnine",
    "wallbox",
    "installatori",
]


IMPORTANT_NEWS_WORDS = [
    "disponibili",
    "disponibile",
    "riapertura",
    "apertura",
    "sportello aperto",
    "sportello riaperto",
    "piattaforma aperta",
    "piattaforma attiva",
    "voucher",
    "fondi",
    "risorse",
    "plafond",
    "prenotazioni",
    "domande",
    "click day",
    "isee",
    "rottamazione",
    "mase",
    "mimit",
    "ecobonus",
    "10.000",
    "10000",
    "11.000",
    "11000",
    "9.000",
    "9000",
]


def now_italy():
    return datetime.datetime.now(ZoneInfo("Europe/Rome"))


def now_string():
    return now_italy().strftime("%d/%m/%Y %H:%M")


def today_italy():
    return now_italy().date()


def today_string():
    return today_italy().strftime("%Y-%m-%d")


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


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }

    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()


def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    text = re.sub(r"\s+", " ", text)

    return text


def text_hash(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def contains_any(text, words):
    text_lower = text.lower()
    return any(word.lower() in text_lower for word in words)


def find_matching_phrases(text, phrases):
    text_lower = text.lower()
    return [phrase for phrase in phrases if phrase.lower() in text_lower]


def is_mase_like(site):
    return site["type"] in ["mase", "mase_news"]


def page_is_suspicious(site, text):
    if not is_mase_like(site):
        return False, []

    reasons = []
    text_clean = text.strip()
    text_lower = text_clean.lower()

    if len(text_clean) < MIN_MASE_TEXT_LENGTH:
        reasons.append(f"testo troppo corto ({len(text_clean)} caratteri)")

    if contains_any(text_lower, JAVASCRIPT_SUSPICIOUS_WORDS):
        reasons.append("possibile pagina JavaScript/loading")

    useful_words = MASE_SOLD_OUT_PHRASES + MASE_AVAILABLE_PHRASES + MASE_IMPORTANT_PHRASES

    if not contains_any(text_lower, useful_words):
        reasons.append("mancano parole utili come voucher/plafond/risorse/beneficiario")

    return len(reasons) > 0, reasons


def make_snippet(text, phrases=None):
    text_lower = text.lower()
    phrases = phrases or []

    positions = []

    for word in phrases + MASE_AVAILABLE_PHRASES + MASE_SOLD_OUT_PHRASES + IMPORTANT_NEWS_WORDS + AUTO_WORDS:
        pos = text_lower.find(word.lower())
        if pos != -1:
            positions.append(pos)

    if not positions:
        return text[:900]

    start = max(0, min(positions) - 300)
    end = min(len(text), start + 1300)

    return text[start:end]


def parse_saved_at(saved_at):
    try:
        return datetime.datetime.strptime(saved_at, "%d/%m/%Y %H:%M").replace(tzinfo=ZoneInfo("Europe/Rome"))
    except Exception:
        return None


def hours_since(timestamp_string):
    parsed = parse_saved_at(timestamp_string)

    if parsed is None:
        return 999999

    return (now_italy() - parsed).total_seconds() / 3600


def alert_allowed(state, key, cooldown_hours):
    cooldowns = state.get("_alert_cooldowns", {})
    last = cooldowns.get(key)

    if last is None:
        return True

    return hours_since(last) >= cooldown_hours


def mark_alert_sent(state, key):
    cooldowns = state.get("_alert_cooldowns", {})
    cooldowns[key] = now_string()
    state["_alert_cooldowns"] = cooldowns


def add_alert(alerts, state, key, cooldown_hours, message):
    if alert_allowed(state, key, cooldown_hours):
        alerts.append(message)
        mark_alert_sent(state, key)


# ----------------------------
# LETTURA PAGINE: REQUESTS + PLAYWRIGHT + API HUNTER
# ----------------------------

def get_page_text_requests(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36 BonusAutoBot/6.0"
        )
    }

    response = requests.get(url, headers=headers, timeout=45)
    response.raise_for_status()

    return clean_text(response.text)


def response_is_interesting(response):
    try:
        url = response.url.lower()
        content_type = response.headers.get("content-type", "").lower()

        if "json" in content_type:
            return True

        if any(hint in url for hint in API_URL_HINTS):
            return True

        return False
    except Exception:
        return False


def body_looks_useful(body):
    if not body:
        return False

    body_lower = body.lower().strip()

    if body_lower.startswith("{") or body_lower.startswith("["):
        return True

    useful_words = (
        MASE_SOLD_OUT_PHRASES
        + MASE_AVAILABLE_PHRASES
        + MASE_IMPORTANT_PHRASES
        + ["plafond", "voucher", "risorse", "fondi", "beneficiario"]
    )

    return contains_any(body_lower, useful_words)


def normalize_api_body(body):
    if not body:
        return ""

    body = re.sub(r"\s+", " ", body).strip()

    if len(body) > MAX_API_BODY_CHARS:
        body = body[:MAX_API_BODY_CHARS]

    return body


def get_page_text_playwright(site):
    api_results = []
    url = site["url"]

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
            ],
        )

        page = browser.new_page(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0 Safari/537.36 BonusAutoBot/6.0"
            ),
            viewport={"width": 1366, "height": 900},
        )

        def on_response(response):
            if not API_DISCOVERY_ENABLED:
                return

            try:
                if not response_is_interesting(response):
                    return

                status = response.status
                if status < 200 or status >= 400:
                    return

                response_url = response.url
                content_type = response.headers.get("content-type", "")

                body = response.text()
                body = normalize_api_body(body)

                if not body_looks_useful(body):
                    return

                api_results.append({
                    "url": response_url,
                    "status": status,
                    "content_type": content_type,
                    "body": body,
                    "hash": text_hash(body),
                })

            except Exception:
                return

        page.on("response", on_response)

        page.goto(url, wait_until="domcontentloaded", timeout=60000)

        try:
            page.wait_for_load_state("networkidle", timeout=20000)
        except Exception:
            pass

        page.wait_for_timeout(5000)

        try:
            text = page.locator("body").inner_text(timeout=15000)
        except Exception:
            text = ""

        if not text.strip():
            try:
                html = page.content()
                text = clean_text(html)
            except Exception:
                text = ""

        browser.close()

        text = re.sub(r"\s+", " ", text).strip()

        unique = {}
        for item in api_results:
            unique[item["url"]] = item

        api_results = list(unique.values())[:25]

        return text, api_results


def get_page_text(site):
    text = get_page_text_requests(site["url"])
    read_method = "requests"
    api_results = []

    suspicious, _ = page_is_suspicious(site, text)

    if is_mase_like(site) and suspicious:
        try:
            rendered_text, discovered_api = get_page_text_playwright(site)
            rendered_suspicious, _ = page_is_suspicious(site, rendered_text)

            api_results = discovered_api

            if rendered_text and (len(rendered_text) > len(text) or not rendered_suspicious):
                text = rendered_text
                read_method = "playwright"
            else:
                read_method = "requests_playwright_no_text_improvement"

        except Exception as e:
            print(f"Errore Playwright su {site['name']}: {e}")
            read_method = "requests_playwright_failed"

    return text, read_method, api_results


# ----------------------------
# API DISCOVERY / API HUNTER
# ----------------------------

def api_endpoint_id(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def analyze_api_results(state, site, api_results):
    alerts = []

    if not api_results:
        return alerts

    inventory = state.get("_api_inventory", {})
    if not isinstance(inventory, dict):
        inventory = {}

    discovered_count = state.get("_api_discovered_count", 0)

    for api in api_results:
        url = api.get("url", "")
        body = api.get("body", "")
        status = api.get("status", "")
        content_type = api.get("content_type", "")

        if not url or not body:
            continue

        endpoint_id = api_endpoint_id(url)
        previous = inventory.get(endpoint_id, {})

        old_hash = previous.get("hash")
        old_sold_out = previous.get("sold_out")
        old_available = previous.get("available")

        body_hash = text_hash(body)

        sold_out_matches = find_matching_phrases(body, MASE_SOLD_OUT_PHRASES)
        available_matches = find_matching_phrases(body, MASE_AVAILABLE_PHRASES)
        important_matches = find_matching_phrases(body, MASE_IMPORTANT_PHRASES)

        sold_out_now = len(sold_out_matches) > 0
        available_now = len(available_matches) > 0
        important_now = len(important_matches) > 0

        is_new_endpoint = old_hash is None
        changed = old_hash is not None and old_hash != body_hash

        inventory[endpoint_id] = {
            "url": url,
            "source_page": site["name"],
            "source_page_url": site["url"],
            "status": status,
            "content_type": content_type,
            "hash": body_hash,
            "sold_out": sold_out_now,
            "available": available_now,
            "important": important_now,
            "sold_out_matches": sold_out_matches,
            "available_matches": available_matches,
            "important_matches": important_matches,
            "last_seen": now_string(),
            "body_preview": body[:800],
        }

        if is_new_endpoint:
            discovered_count += 1

        if available_now and old_available is not True:
            snippet = make_snippet(body, available_matches)

            add_alert(
                alerts,
                state,
                f"api_available::{endpoint_id}",
                0.5,
                "🚨🚨 API HUNTER - POSSIBILE DISPONIBILITÀ TROVATA 🚨🚨\n\n"
                f"Fonte pagina: {site['name']}\n"
                f"Endpoint API/JSON rilevato:\n{url}\n\n"
                "Frasi trovate:\n"
                + "\n".join([f"- {p}" for p in available_matches[:10]])
                + "\n\n"
                "Cosa significa:\n"
                "Il bot ha intercettato una risposta API/JSON che contiene parole compatibili con fondi/voucher disponibili.\n\n"
                "Cosa fare subito:\n"
                "Apri il portale MASE e prova ad accedere con SPID/CIE.\n\n"
                "Link rapidi:\n"
                "Login: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login\n"
                "Plafond: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond\n\n"
                f"Anteprima API:\n{snippet[:1200]}"
            )

        if old_sold_out is True and sold_out_now is False:
            add_alert(
                alerts,
                state,
                f"api_soldout_disappeared::{endpoint_id}",
                0.5,
                "🚨🚨 API HUNTER - STATO ESAURITO/PRENOTATO SPARITO 🚨🚨\n\n"
                f"Fonte pagina: {site['name']}\n"
                f"Endpoint API/JSON:\n{url}\n\n"
                "Cosa è successo:\n"
                "Prima questa API conteneva frasi compatibili con risorse/fondi prenotati o esauriti.\n"
                "Ora quelle frasi non risultano più presenti.\n\n"
                "Cosa fare subito:\n"
                "Controlla immediatamente il portale MASE."
            )

        if changed and important_now:
            add_alert(
                alerts,
                state,
                f"api_changed::{endpoint_id}",
                6,
                "⚠️ API HUNTER - ENDPOINT IMPORTANTE CAMBIATO\n\n"
                f"Fonte pagina: {site['name']}\n"
                f"Endpoint API/JSON:\n{url}\n\n"
                "L’endpoint è cambiato e contiene riferimenti importanti a voucher, plafond, risorse o beneficiario.\n"
                "Non è una conferma di fondi disponibili, ma va controllato.\n\n"
                f"Anteprima API:\n{body[:1200]}"
            )

    if len(inventory) > MAX_API_ENDPOINTS_IN_STATE:
        items = list(inventory.items())
        items = items[-MAX_API_ENDPOINTS_IN_STATE:]
        inventory = dict(items)

    state["_api_inventory"] = inventory
    state["_api_discovered_count"] = discovered_count

    return alerts


# ----------------------------
# NEWS: SOLO OGGI
# ----------------------------

def parse_news_date(entry):
    published = entry.get("published", "")

    if not published:
        return None

    try:
        parsed = parsedate_to_datetime(published)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)

        parsed_italy = parsed.astimezone(ZoneInfo("Europe/Rome"))
        return parsed_italy.date()
    except Exception:
        return None


def is_news_from_today(entry):
    news_date = parse_news_date(entry)

    if news_date is None:
        return False

    return news_date >= today_italy()


def google_news_rss_url(query):
    encoded_query = requests.utils.quote(query)
    return f"https://news.google.com/rss/search?q={encoded_query}%20when:1d&hl=it&gl=IT&ceid=IT:it"


def classify_news(title, summary):
    text = f"{title} {summary}".lower()

    has_auto = contains_any(text, AUTO_WORDS)
    has_bad_topic = contains_any(text, BAD_TOPICS)
    has_important = contains_any(text, IMPORTANT_NEWS_WORDS)

    urgent_words = [
        "disponibili",
        "disponibile",
        "riapertura",
        "apertura",
        "sportello aperto",
        "sportello riaperto",
        "piattaforma aperta",
        "piattaforma attiva",
        "voucher disponibili",
        "fondi disponibili",
        "risorse disponibili",
        "click day",
        "prenotazioni aperte",
        "domande aperte",
    ]

    has_urgent = contains_any(text, urgent_words)

    if has_bad_topic and not has_auto:
        return "IGNORE", "Parla di moto/scooter/colonnine o temi non collegati alle auto elettriche."

    if has_auto and has_urgent:
        return "URGENT", "La notizia contiene parole compatibili con apertura, disponibilità fondi o voucher."

    if has_auto and has_important:
        return "IMPORTANT", "La notizia parla di bonus/incentivi auto elettriche, ma non conferma necessariamente fondi disponibili."

    if "mase" in text or "mimit" in text or "ecobonus" in text:
        return "INFO", "La notizia cita MASE/MIMIT/Ecobonus, ma non contiene segnali forti di disponibilità."

    return "IGNORE", "Notizia non abbastanza pertinente."


def cleanup_seen_news(state):
    seen_news = state.get("_seen_news", {})

    if not isinstance(seen_news, dict):
        state["_seen_news"] = {}
        return

    cutoff = now_italy() - datetime.timedelta(days=NEWS_KEEP_DAYS)

    cleaned_items = []

    for news_id, item in seen_news.items():
        saved_at = item.get("saved_at")
        parsed = parse_saved_at(saved_at)

        if parsed is None:
            continue

        if parsed >= cutoff:
            cleaned_items.append((news_id, item, parsed))

    cleaned_items.sort(key=lambda x: x[2], reverse=True)
    cleaned_items = cleaned_items[:MAX_SEEN_NEWS]

    state["_seen_news"] = {
        news_id: item for news_id, item, _ in cleaned_items
    }


def check_news(state):
    alerts = []
    seen_news = state.get("_seen_news", {})

    if not isinstance(seen_news, dict):
        seen_news = {}

    today = today_italy()

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

                if not is_news_from_today(entry):
                    continue

                news_id = hashlib.sha256(link.encode("utf-8")).hexdigest()

                if news_id in seen_news:
                    continue

                level, reason = classify_news(title, summary)

                seen_news[news_id] = {
                    "title": title,
                    "link": link,
                    "query": query,
                    "published": published,
                    "level": level,
                    "saved_at": now_string(),
                    "news_day_filter": str(today),
                }

                if level not in ["URGENT", "IMPORTANT"]:
                    continue

                emoji = "🚨" if level == "URGENT" else "⚠️"
                label = "URGENTE" if level == "URGENT" else "IMPORTANTE"

                alerts.append(
                    f"{emoji} NEWS {label} - BONUS AUTO ELETTRICHE\n\n"
                    f"Ricerca: {query}\n"
                    f"Titolo: {title}\n"
                    f"Data: {published}\n"
                    f"Link: {link}\n\n"
                    f"Valutazione:\n{reason}\n\n"
                    f"Filtro data:\n"
                    f"Il bot considera solo notizie pubblicate oggi: {today}.\n\n"
                    "Cosa fare:\n"
                    "Se parla di riapertura, fondi o voucher disponibili, controlla subito il portale MASE."
                )

        except Exception as e:
            print(f"Errore controllo news '{query}': {e}")

    state["_seen_news"] = seen_news
    return alerts


# ----------------------------
# CONTROLLO PAGINE MASE
# ----------------------------

def handle_suspicious_page(state, site, text, read_method):
    alerts = []

    suspicious, reasons = page_is_suspicious(site, text)

    key = f"_suspicious::{site['url']}"
    previous = state.get(key, {})

    count = int(previous.get("count", 0))
    last_alert = previous.get("last_alert")

    if suspicious:
        count += 1
    else:
        count = 0

    state[key] = {
        "count": count,
        "last_alert": last_alert,
        "last_checked": now_string(),
        "name": site["name"],
        "reasons": reasons,
        "read_method": read_method,
        "text_length": len(text.strip()),
    }

    should_alert = (
        suspicious
        and count >= SUSPICIOUS_PAGE_ALERT_AFTER
        and hours_since(last_alert) >= SUSPICIOUS_PAGE_ALERT_COOLDOWN_HOURS
    )

    if should_alert:
        state[key]["last_alert"] = now_string()

        alerts.append(
            "⚠️ CONTROLLO MASE ANCORA POCO AFFIDABILE\n\n"
            f"Fonte: {site['name']}\n"
            f"Link: {site['url']}\n"
            f"Controllo: {now_string()}\n"
            f"Metodo lettura: {read_method}\n\n"
            "Il bot ha provato anche con browser automatico Playwright, ma la pagina risulta ancora sospetta.\n\n"
            "Possibili motivi:\n"
            + "\n".join([f"- {r}" for r in reasons])
            + "\n\n"
            "Cosa significa:\n"
            "La pagina potrebbe richiedere login, dati caricati da API interne, o bloccare la lettura automatica.\n\n"
            "Cosa fare:\n"
            "Controlla manualmente questa pagina appena puoi, soprattutto se riguarda Plafond/Login/Beneficiario."
        )

    return alerts


def classify_mase_page(state, site, text, changed, first_run, read_method):
    alerts = []

    name = site["name"]
    url = site["url"]

    alerts.extend(handle_suspicious_page(state, site, text, read_method))

    sold_out_matches = find_matching_phrases(text, MASE_SOLD_OUT_PHRASES)
    available_matches = find_matching_phrases(text, MASE_AVAILABLE_PHRASES)
    important_matches = find_matching_phrases(text, MASE_IMPORTANT_PHRASES)

    sold_out_now = len(sold_out_matches) > 0
    available_now = len(available_matches) > 0
    important_now = len(important_matches) > 0

    status_key = f"_mase_status::{url}"
    previous = state.get(status_key, {})

    sold_out_before = previous.get("sold_out")
    available_before = previous.get("available")
    previous_hash = previous.get("hash")

    current_hash = text_hash(text)

    state[status_key] = {
        "sold_out": sold_out_now,
        "available": available_now,
        "important": important_now,
        "sold_out_matches": sold_out_matches,
        "available_matches": available_matches,
        "important_matches": important_matches,
        "hash": current_hash,
        "last_checked": now_string(),
        "name": name,
        "read_method": read_method,
        "text_length": len(text.strip()),
    }

    if first_run and not SEND_ON_FIRST_RUN:
        return alerts

    if sold_out_before is True and sold_out_now is False:
        add_alert(
            alerts,
            state,
            f"soldout_disappeared::{url}",
            0.5,
            "🚨🚨 URGENTE - POSSIBILE RIAPERTURA VOUCHER MASE 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Metodo lettura: {read_method}\n"
            f"Link: {url}\n\n"
            "Cosa è successo:\n"
            "Prima la pagina indicava che le risorse/fondi erano prenotati o esauriti.\n"
            "Adesso quel messaggio non risulta più presente.\n\n"
            "Cosa fare subito:\n"
            "Accedi al portale MASE con SPID/CIE e controlla se puoi generare il voucher.\n\n"
            "Link rapidi:\n"
            "Login: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login\n"
            "Plafond: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond"
        )

    if available_before is not True and available_now:
        snippet = make_snippet(text, available_matches)

        add_alert(
            alerts,
            state,
            f"available_phrase::{url}",
            0.5,
            "🚨🚨 URGENTE - FRASE DI DISPONIBILITÀ TROVATA 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Metodo lettura: {read_method}\n"
            f"Link: {url}\n\n"
            "Frasi trovate:\n"
            + "\n".join([f"- {p}" for p in available_matches[:10]])
            + "\n\n"
            "Cosa significa:\n"
            "La pagina contiene parole compatibili con fondi/voucher/piattaforma disponibili.\n\n"
            "Azione consigliata:\n"
            "Apri subito il portale e prova ad accedere con SPID/CIE.\n\n"
            f"Anteprima:\n{snippet[:1200]}"
        )

    if changed and previous_hash is not None and important_now:
        snippet = make_snippet(text, important_matches)

        add_alert(
            alerts,
            state,
            f"mase_page_changed::{url}",
            6,
            "⚠️ PAGINA MASE IMPORTANTE CAMBIATA\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Metodo lettura: {read_method}\n"
            f"Link: {url}\n\n"
            "La pagina è cambiata e contiene riferimenti a voucher, plafond, risorse, ISEE o beneficiario.\n"
            "Non è una conferma di fondi disponibili, ma va controllata.\n\n"
            f"Anteprima:\n{snippet[:1200]}"
        )

    return alerts


def classify_general_site(state, site, text, changed, first_run):
    alerts = []

    if first_run and not SEND_ON_FIRST_RUN:
        return alerts

    if not changed:
        return alerts

    has_auto = contains_any(text, AUTO_WORDS)
    has_bad_topic = contains_any(text, BAD_TOPICS)
    has_important = contains_any(text, IMPORTANT_NEWS_WORDS)

    if has_bad_topic and not has_auto:
        return alerts

    if has_auto and has_important:
        snippet = make_snippet(text)

        add_alert(
            alerts,
            state,
            f"general_changed::{site['url']}",
            6,
            "⚠️ POSSIBILE NOVITÀ BONUS AUTO ELETTRICHE\n\n"
            f"Fonte: {site['name']}\n"
            f"Controllo: {now_string()}\n"
            f"Link: {site['url']}\n\n"
            "La pagina è cambiata e contiene riferimenti ad auto elettriche, bonus, fondi, voucher o prenotazioni.\n\n"
            f"Anteprima:\n{snippet[:1200]}"
        )

    return alerts


def check_sites(state):
    alerts = []
    errors = []

    for site in SITES:
        name = site["name"]
        url = site["url"]

        try:
            text, read_method, api_results = get_page_text(site)
            current_hash = text_hash(text)

            old_hash = state.get(url, {}).get("hash")
            first_run = old_hash is None
            changed = old_hash != current_hash

            if is_mase_like(site):
                alerts.extend(analyze_api_results(state, site, api_results))
                alerts.extend(classify_mase_page(state, site, text, changed, first_run, read_method))
            else:
                alerts.extend(classify_general_site(state, site, text, changed, first_run))

            state[url] = {
                "hash": current_hash,
                "last_checked": now_string(),
                "name": name,
                "type": site["type"],
                "text_length": len(text.strip()),
                "read_method": read_method,
                "api_results_found": len(api_results),
            }

        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    if errors:
        print("Errori controllo siti:")
        for error in errors[:10]:
            print(error)

    state["_last_site_errors"] = errors[:10]
    return alerts


# ----------------------------
# RIEPILOGO E BOT VIVO
# ----------------------------

def should_send_summary(state):
    last_summary = state.get("_last_summary_sent")

    if not last_summary:
        return True

    return hours_since(last_summary) >= SUMMARY_EVERY_HOURS


def should_send_alive_message(state):
    today = today_string()
    last_alive_day = state.get("_last_alive_day")

    if last_alive_day == today:
        return False

    if now_italy().hour >= ALIVE_MESSAGE_HOUR:
        return True

    return False


def build_status_text(state):
    mase_statuses = []

    for key, value in state.items():
        if not key.startswith("_mase_status::"):
            continue

        name = value.get("name", "MASE")
        sold_out = value.get("sold_out")
        available = value.get("available")
        checked = value.get("last_checked", "N/D")
        read_method = value.get("read_method", "N/D")
        text_length = value.get("text_length", "N/D")

        if available:
            status = "🚨 possibile disponibilità rilevata"
        elif sold_out:
            status = "❌ risorse/fondi ancora prenotati o esauriti"
        else:
            status = "⚠️ stato non chiarissimo"

        mase_statuses.append(
            f"- {name}: {status} | metodo: {read_method} | testo: {text_length} caratteri | ultimo controllo: {checked}"
        )

    if not mase_statuses:
        return "Nessuno stato MASE salvato ancora."

    return "\n".join(mase_statuses[:10])


def build_api_status_text(state):
    inventory = state.get("_api_inventory", {})

    if not inventory:
        return "Nessun endpoint API/JSON utile scoperto finora."

    lines = []
    for _, item in list(inventory.items())[-8:]:
        url = item.get("url", "N/D")
        source = item.get("source_page", "N/D")
        available = item.get("available")
        sold_out = item.get("sold_out")
        last_seen = item.get("last_seen", "N/D")

        if available:
            status = "🚨 possibile disponibilità"
        elif sold_out:
            status = "❌ esaurito/prenotato"
        else:
            status = "ℹ️ monitorato"

        lines.append(f"- {status} | {source} | ultimo: {last_seen}\n  {url[:140]}")

    return "\n".join(lines)


def build_summary(state):
    errors = state.get("_last_site_errors", [])
    api_count = len(state.get("_api_inventory", {}))

    error_text = "0 errori recenti" if not errors else "\n".join([f"- {e}" for e in errors[:5]])

    return (
        "📊 RIEPILOGO BOT BONUS AUTO ELETTRICHE\n\n"
        f"Ora controllo: {now_string()}\n\n"
        "Stato MASE:\n"
        f"{build_status_text(state)}\n\n"
        "API Hunter:\n"
        f"Endpoint utili scoperti: {api_count}\n"
        f"{build_api_status_text(state)}\n\n"
        "Filtro news:\n"
        f"Il bot considera solo notizie pubblicate oggi: {today_italy()}.\n\n"
        "Errori recenti:\n"
        f"{error_text}\n\n"
        "Conclusione:\n"
        "Se non hai ricevuto avvisi URGENTI, al momento il bot non ha rilevato conferme forti di voucher/fondi disponibili."
    )


def build_alive_message(state):
    errors = state.get("_last_site_errors", [])
    api_count = len(state.get("_api_inventory", {}))

    return (
        "✅ BOT BONUS AUTO ATTIVO\n\n"
        f"Ultimo controllo: {now_string()}\n"
        f"News controllate: solo pubblicate oggi ({today_italy()})\n"
        f"Endpoint API/JSON utili scoperti: {api_count}\n"
        f"Errori recenti: {len(errors)}\n\n"
        "Stato rapido MASE:\n"
        f"{build_status_text(state)}\n\n"
        "Sto continuando a controllare ogni 5 minuti tramite cron-job.org + GitHub Actions."
    )


def maybe_send_summary_and_alive(state, alerts):
    if should_send_summary(state):
        alerts.append(build_summary(state))
        state["_last_summary_sent"] = now_string()

    if should_send_alive_message(state):
        alerts.append(build_alive_message(state))
        state["_last_alive_day"] = today_string()


# ----------------------------
# MAIN
# ----------------------------

def main():
    state = load_state()

    cleanup_seen_news(state)

    alerts = []

    alerts.extend(check_sites(state))
    alerts.extend(check_news(state))

    maybe_send_summary_and_alive(state, alerts)

    save_state(state)

    for alert in alerts:
        send_telegram(alert)


if __name__ == "__main__":
    main()
