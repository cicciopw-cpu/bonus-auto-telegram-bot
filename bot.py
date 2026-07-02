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


def get_page_text(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36 BonusAutoBot/3.0"
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


def find_matching_phrases(text, phrases):
    text_lower = text.lower()
    return [phrase for phrase in phrases if phrase.lower() in text_lower]


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

def page_is_suspicious(site, text):
    if site["type"] not in ["mase", "mase_news"]:
        return False, []

    reasons = []
    text_lower = text.lower()

    if len(text.strip()) < MIN_MASE_TEXT_LENGTH:
        reasons.append(f"testo troppo corto ({len(text.strip())} caratteri)")

    if contains_any(text, JAVASCRIPT_SUSPICIOUS_WORDS):
        reasons.append("possibile pagina JavaScript/loading")

    useful_words = MASE_SOLD_OUT_PHRASES + MASE_AVAILABLE_PHRASES + MASE_IMPORTANT_PHRASES

    if not contains_any(text, useful_words):
        reasons.append("mancano parole utili come voucher/plafond/risorse/beneficiario")

    return len(reasons) > 0, reasons


def handle_suspicious_page(state, site, text):
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
    }

    should_alert = (
        suspicious
        and count >= SUSPICIOUS_PAGE_ALERT_AFTER
        and hours_since(last_alert) >= SUSPICIOUS_PAGE_ALERT_COOLDOWN_HOURS
    )

    if should_alert:
        state[key]["last_alert"] = now_string()

        alerts.append(
            "⚠️ CONTROLLO MASE POCO AFFIDABILE\n\n"
            f"Fonte: {site['name']}\n"
            f"Link: {site['url']}\n"
            f"Controllo: {now_string()}\n\n"
            "Il bot ha rilevato più controlli sospetti consecutivi.\n\n"
            "Possibili motivi:\n"
            + "\n".join([f"- {r}" for r in reasons])
            + "\n\n"
            "Cosa significa:\n"
            "La pagina potrebbe essere caricata tramite JavaScript e il bot semplice potrebbe non leggere tutto.\n\n"
            "Cosa fare:\n"
            "Controlla manualmente questa pagina appena puoi, soprattutto se riguarda Plafond/Login/Beneficiario."
        )

    return alerts


def classify_mase_page(state, site, text, changed, first_run):
    alerts = []

    name = site["name"]
    url = site["url"]

    alerts.extend(handle_suspicious_page(state, site, text))

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
    }

    if first_run and not SEND_ON_FIRST_RUN:
        return alerts

    if sold_out_before is True and sold_out_now is False:
        alerts.append(
            "🚨🚨 URGENTE - POSSIBILE RIAPERTURA VOUCHER MASE 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Link: {url}\n\n"
            "Cosa è successo:\n"
            "Prima la pagina indicava che le risorse/fondi erano prenotati o esauriti.\n"
            "Adesso quel messaggio non risulta più presente.\n\n"
            "Cosa può significare:\n"
            "Potrebbero aver aggiornato il portale, riaperto fondi o modificato lo stato del plafond.\n\n"
            "Cosa fare subito:\n"
            "Accedi al portale MASE con SPID/CIE e controlla se puoi generare il voucher.\n\n"
            "Link rapidi:\n"
            "Login Beneficiario: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login\n"
            "Plafond: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond"
        )

    if available_before is not True and available_now:
        snippet = make_snippet(text, available_matches)

        alerts.append(
            "🚨🚨 URGENTE - FRASE DI DISPONIBILITÀ TROVATA 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Link: {url}\n\n"
            "Frasi trovate:\n"
            + "\n".join([f"- {p}" for p in available_matches[:10]])
            + "\n\n"
            "Cosa significa:\n"
            "La pagina contiene parole compatibili con fondi/voucher/piattaforma disponibili.\n\n"
            "Azione consigliata:\n"
            "Apri subito il portale e prova ad accedere con SPID/CIE.\n\n"
            "Link rapidi:\n"
            "Login Beneficiario: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login\n"
            "Plafond: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond\n\n"
            f"Anteprima:\n{snippet[:1200]}"
        )

    if changed and previous_hash is not None and important_now:
        snippet = make_snippet(text, important_matches)

        alerts.append(
            "⚠️ PAGINA MASE IMPORTANTE CAMBIATA\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
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

        alerts.append(
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
            text = get_page_text(url)
            current_hash = text_hash(text)

            old_hash = state.get(url, {}).get("hash")
            first_run = old_hash is None
            changed = old_hash != current_hash

            if site["type"] in ["mase", "mase_news"]:
                alerts.extend(classify_mase_page(state, site, text, changed, first_run))
            else:
                alerts.extend(classify_general_site(state, site, text, changed, first_run))

            state[url] = {
                "hash": current_hash,
                "last_checked": now_string(),
                "name": name,
                "type": site["type"],
                "text_length": len(text),
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

        if available:
            status = "🚨 possibile disponibilità rilevata"
        elif sold_out:
            status = "❌ risorse/fondi ancora prenotati o esauriti"
        else:
            status = "⚠️ messaggio fondi prenotati non rilevato"

        mase_statuses.append(f"- {name}: {status} | ultimo controllo: {checked}")

    if not mase_statuses:
        return "Nessuno stato MASE salvato ancora."

    return "\n".join(mase_statuses[:10])


def build_summary(state):
    errors = state.get("_last_site_errors", [])

    error_text = "0 errori recenti" if not errors else "\n".join([f"- {e}" for e in errors[:5]])

    return (
        "📊 RIEPILOGO BOT BONUS AUTO ELETTRICHE\n\n"
        f"Ora controllo: {now_string()}\n\n"
        "Stato MASE:\n"
        f"{build_status_text(state)}\n\n"
        "Filtro news:\n"
        f"Il bot considera solo notizie pubblicate oggi: {today_italy()}.\n\n"
        "Errori recenti:\n"
        f"{error_text}\n\n"
        "Conclusione:\n"
        "Se non hai ricevuto avvisi URGENTI, al momento il bot non ha rilevato conferme forti di voucher/fondi disponibili."
    )


def build_alive_message(state):
    errors = state.get("_last_site_errors", [])

    return (
        "✅ BOT BONUS AUTO ATTIVO\n\n"
        f"Ultimo controllo: {now_string()}\n"
        f"News controllate: solo pubblicate oggi ({today_italy()})\n"
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
