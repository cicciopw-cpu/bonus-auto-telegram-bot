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

PLAFOND_URGENT_INCREASE_EURO = 10000
PLAFOND_IMPORTANT_INCREASE_EURO = 1000

ALERT_COOLDOWN_URGENT_HOURS = 0.25
ALERT_COOLDOWN_IMPORTANT_HOURS = 6
ALERT_COOLDOWN_INFO_HOURS = 12

MASE_BENEFICIARIO_BASE = "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario"
MASE_ESERCENTE_BASE = "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciEsercente"

DIRECT_API_ENDPOINTS = [
    {
        "key": "beneficiario_plafond",
        "name": "MASE API - Plafond Beneficiario",
        "url": f"{MASE_BENEFICIARIO_BASE}/api/unsecured/plafond",
        "kind": "plafond",
    },
    {
        "key": "beneficiario_grafico",
        "name": "MASE API - Grafico Voucher Beneficiario",
        "url": f"{MASE_BENEFICIARIO_BASE}/api/unsecured/grafico",
        "kind": "grafico",
    },
    {
        "key": "beneficiario_versione",
        "name": "MASE API - Versione Beneficiario",
        "url": f"{MASE_BENEFICIARIO_BASE}/api/unsecured/versione",
        "kind": "versione",
    },
    {
        "key": "esercente_avvisi",
        "name": "MASE API - Avvisi Esercente",
        "url": f"{MASE_ESERCENTE_BASE}/api/unsecured/avvisi",
        "kind": "avvisi",
    },
    {
        "key": "esercente_versione",
        "name": "MASE API - Versione Esercente",
        "url": f"{MASE_ESERCENTE_BASE}/api/unsecured/versione",
        "kind": "versione",
    },
]


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
    },
    {
        "name": "MASE - Login Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login",
        "type": "mase",
    },
    {
        "name": "MASE - Home Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/home",
        "type": "mase",
    },
    {
        "name": "MASE - Plafond",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond",
        "type": "mase",
    },
    {
        "name": "MASE - Esercente / Concessionari",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciEsercente/",
        "type": "mase",
    },
    {
        "name": "Ecobonus MIMIT - Cos'è",
        "url": "https://ecobonus.mimit.gov.it/cose",
        "type": "mimit",
    },
    {
        "name": "Ecobonus MIMIT - Auto",
        "url": "https://ecobonus.mimit.gov.it/auto",
        "type": "mimit",
    },
    {
        "name": "Ecobonus MIMIT - Contributi",
        "url": "https://ecobonus.mimit.gov.it/contributi",
        "type": "mimit",
    },
    {
        "name": "Ecobonus MIMIT - Risorse stanziate",
        "url": "https://ecobonus.mimit.gov.it/risorse-stanziate",
        "type": "mimit",
    },
    {
        "name": "Ecobonus MIMIT - Avvisi e notizie",
        "url": "https://ecobonus.mimit.gov.it/avvisi-notizie",
        "type": "mimit",
    },
    {
        "name": "MIMIT - Ecobonus Automotive",
        "url": "https://www.mimit.gov.it/it/incentivi/ecobonus-automotive",
        "type": "mimit",
    },
    {
        "name": "MIMIT - Incentivi Aggiornamenti",
        "url": "https://www.mimit.gov.it/it/incentivi-aggiornamenti",
        "type": "mimit",
    },
    {
        "name": "Regione Campania - Sportello Incentivi",
        "url": "https://sportelloincentivi.regione.campania.it/",
        "type": "regione",
    },
    {
        "name": "Regione Campania - News",
        "url": "https://www.regione.campania.it/regione-informa/notizie",
        "type": "regione",
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


def format_euro(value):
    try:
        return f"{int(value):,}".replace(",", ".") + " €"
    except Exception:
        return str(value)


def percent(part, total):
    try:
        if not total:
            return 0
        return round((float(part) / float(total)) * 100, 4)
    except Exception:
        return 0


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
    return hashlib.sha256(str(text).encode("utf-8")).hexdigest()


def contains_any(text, words):
    text_lower = str(text).lower()
    return any(word.lower() in text_lower for word in words)


def find_matching_phrases(text, phrases):
    text_lower = str(text).lower()
    return [phrase for phrase in phrases if phrase.lower() in text_lower]


def is_mase_like(site):
    return site["type"] == "mase"


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


def make_snippet(text, phrases=None):
    text = str(text)
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


# ----------------------------
# DIRECT API MONITOR
# ----------------------------

def request_json(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36 BonusAutoBot/7.0"
        ),
        "Accept": "application/json,text/plain,*/*",
    }

    response = requests.get(url, headers=headers, timeout=45)
    response.raise_for_status()

    return response.json()


def check_plafond_api(state, endpoint, data):
    alerts = []
    api_key = endpoint["key"]
    previous = state.get("_direct_api_state", {}).get(api_key, {})

    residuo = int(data.get("residuoPlafond", 0) or 0)
    totale = int(data.get("totalePlafond", 0) or 0)
    prenotato = max(totale - residuo, 0)
    residuo_percent = percent(residuo, totale)
    prenotato_percent = percent(prenotato, totale)

    previous_residuo = previous.get("residuoPlafond")
    previous_totale = previous.get("totalePlafond")

    if previous_residuo is not None:
        diff = residuo - int(previous_residuo)

        if diff >= PLAFOND_URGENT_INCREASE_EURO:
            add_alert(
                alerts,
                state,
                "direct_api_plafond_big_increase",
                ALERT_COOLDOWN_URGENT_HOURS,
                "🚨🚨 URGENTE - PLAFOND MASE AUMENTATO 🚨🚨\n\n"
                f"Controllo: {now_string()}\n"
                f"API: {endpoint['url']}\n\n"
                f"Residuo precedente: {format_euro(previous_residuo)}\n"
                f"Residuo attuale: {format_euro(residuo)}\n"
                f"Aumento rilevato: +{format_euro(diff)}\n\n"
                f"Plafond totale: {format_euro(totale)}\n"
                f"Prenotato stimato: {format_euro(prenotato)} ({prenotato_percent}%)\n"
                f"Residuo: {format_euro(residuo)} ({residuo_percent}%)\n\n"
                "Cosa fare subito:\n"
                "Apri immediatamente il portale MASE con SPID/CIE e prova a verificare se il voucher è generabile.\n\n"
                "Login: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login\n"
                "Plafond: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond"
            )

        elif diff >= PLAFOND_IMPORTANT_INCREASE_EURO:
            add_alert(
                alerts,
                state,
                "direct_api_plafond_small_increase",
                ALERT_COOLDOWN_IMPORTANT_HOURS,
                "⚠️ PLAFOND MASE AUMENTATO LEGGERMENTE\n\n"
                f"Controllo: {now_string()}\n"
                f"API: {endpoint['url']}\n\n"
                f"Residuo precedente: {format_euro(previous_residuo)}\n"
                f"Residuo attuale: {format_euro(residuo)}\n"
                f"Aumento rilevato: +{format_euro(diff)}\n\n"
                "Non è ancora una conferma di voucher disponibili, ma è un movimento da controllare."
            )

        elif diff < 0:
            add_alert(
                alerts,
                state,
                "direct_api_plafond_decrease",
                ALERT_COOLDOWN_INFO_HOURS,
                "ℹ️ PLAFOND MASE DIMINUITO\n\n"
                f"Controllo: {now_string()}\n"
                f"Residuo precedente: {format_euro(previous_residuo)}\n"
                f"Residuo attuale: {format_euro(residuo)}\n"
                f"Variazione: {format_euro(diff)}\n\n"
                "Questo può indicare movimenti tecnici o utilizzo/prenotazione di fondi."
            )

    if previous_totale is not None and int(previous_totale) != totale:
        add_alert(
            alerts,
            state,
            "direct_api_total_plafond_changed",
            ALERT_COOLDOWN_URGENT_HOURS,
            "🚨 TOTALE PLAFOND MASE CAMBIATO\n\n"
            f"Controllo: {now_string()}\n"
            f"Totale precedente: {format_euro(previous_totale)}\n"
            f"Totale attuale: {format_euro(totale)}\n\n"
            "Questo può indicare una modifica importante delle risorse disponibili."
        )

    return alerts


def check_grafico_api(state, endpoint, data):
    alerts = []
    api_key = endpoint["key"]
    previous = state.get("_direct_api_state", {}).get(api_key, {})

    totale_voucher = int(data.get("totaleVoucher", 0) or 0)
    validati = int(data.get("totaleVoucherValidati", 0) or 0)
    non_validati = int(data.get("totaleVoucherNonValidati", 0) or 0)

    prev_totale = previous.get("totaleVoucher")
    prev_validati = previous.get("totaleVoucherValidati")
    prev_non_validati = previous.get("totaleVoucherNonValidati")

    changes = []

    if prev_totale is not None and int(prev_totale) != totale_voucher:
        changes.append(f"Voucher totali: {prev_totale} → {totale_voucher}")

    if prev_validati is not None and int(prev_validati) != validati:
        changes.append(f"Voucher validati: {prev_validati} → {validati}")

    if prev_non_validati is not None and int(prev_non_validati) != non_validati:
        changes.append(f"Voucher non validati: {prev_non_validati} → {non_validati}")

    if changes:
        add_alert(
            alerts,
            state,
            "direct_api_voucher_numbers_changed",
            ALERT_COOLDOWN_IMPORTANT_HOURS,
            "⚠️ NUMERI VOUCHER MASE CAMBIATI\n\n"
            f"Controllo: {now_string()}\n"
            f"API: {endpoint['url']}\n\n"
            + "\n".join([f"- {c}" for c in changes])
            + "\n\n"
            "Cosa significa:\n"
            "Si è mosso il conteggio ufficiale dei voucher. Non è una conferma di fondi disponibili, ma può anticipare variazioni sul plafond.\n\n"
            "Controlla il portale MASE se il movimento è importante."
        )

    return alerts


def check_avvisi_api(state, endpoint, data):
    alerts = []
    api_key = endpoint["key"]
    previous = state.get("_direct_api_state", {}).get(api_key, {})

    body_text = json.dumps(data, ensure_ascii=False)
    current_hash = text_hash(body_text)
    previous_hash = previous.get("hash")

    if previous_hash is not None and previous_hash != current_hash:
        available_matches = find_matching_phrases(body_text, MASE_AVAILABLE_PHRASES)
        important_matches = find_matching_phrases(body_text, MASE_IMPORTANT_PHRASES)

        if available_matches:
            add_alert(
                alerts,
                state,
                "direct_api_avvisi_available",
                ALERT_COOLDOWN_URGENT_HOURS,
                "🚨 AVVISO MASE CON POSSIBILE DISPONIBILITÀ\n\n"
                f"Controllo: {now_string()}\n"
                f"API: {endpoint['url']}\n\n"
                "Frasi trovate:\n"
                + "\n".join([f"- {p}" for p in available_matches[:10]])
                + "\n\n"
                f"Anteprima:\n{make_snippet(body_text, available_matches)[:1200]}"
            )

        elif important_matches:
            add_alert(
                alerts,
                state,
                "direct_api_avvisi_changed",
                ALERT_COOLDOWN_IMPORTANT_HOURS,
                "⚠️ AVVISI MASE CAMBIATI\n\n"
                f"Controllo: {now_string()}\n"
                f"API: {endpoint['url']}\n\n"
                "Gli avvisi ufficiali sono cambiati e contengono parole importanti come voucher, plafond, rottamazione o PNRR.\n\n"
                f"Anteprima:\n{make_snippet(body_text, important_matches)[:1200]}"
            )

    return alerts


def check_versione_api(state, endpoint, data):
    alerts = []
    api_key = endpoint["key"]
    previous = state.get("_direct_api_state", {}).get(api_key, {})

    versione = data.get("versione")
    previous_versione = previous.get("versione")

    if previous_versione is not None and versione and previous_versione != versione:
        add_alert(
            alerts,
            state,
            f"direct_api_version_changed::{api_key}",
            ALERT_COOLDOWN_INFO_HOURS,
            "ℹ️ VERSIONE PORTALE MASE CAMBIATA\n\n"
            f"Controllo: {now_string()}\n"
            f"Portale: {endpoint['name']}\n"
            f"Versione precedente: {previous_versione}\n"
            f"Versione attuale: {versione}\n\n"
            "Non è una conferma di fondi disponibili, ma indica un aggiornamento tecnico del portale."
        )

    return alerts


def check_direct_mase_apis(state):
    alerts = []
    errors = []

    direct_state = state.get("_direct_api_state", {})

    if not isinstance(direct_state, dict):
        direct_state = {}

    for endpoint in DIRECT_API_ENDPOINTS:
        key = endpoint["key"]

        try:
            data = request_json(endpoint["url"])
            data_hash = text_hash(json.dumps(data, ensure_ascii=False, sort_keys=True))

            if endpoint["kind"] == "plafond":
                alerts.extend(check_plafond_api(state, endpoint, data))

            elif endpoint["kind"] == "grafico":
                alerts.extend(check_grafico_api(state, endpoint, data))

            elif endpoint["kind"] == "avvisi":
                alerts.extend(check_avvisi_api(state, endpoint, data))

            elif endpoint["kind"] == "versione":
                alerts.extend(check_versione_api(state, endpoint, data))

            record = {
                "name": endpoint["name"],
                "url": endpoint["url"],
                "kind": endpoint["kind"],
                "last_checked": now_string(),
                "hash": data_hash,
                "raw": data,
            }

            if endpoint["kind"] == "plafond":
                residuo = int(data.get("residuoPlafond", 0) or 0)
                totale = int(data.get("totalePlafond", 0) or 0)

                record["residuoPlafond"] = residuo
                record["totalePlafond"] = totale
                record["prenotatoStimato"] = max(totale - residuo, 0)
                record["residuoPercent"] = percent(residuo, totale)

            if endpoint["kind"] == "grafico":
                record["totaleVoucher"] = int(data.get("totaleVoucher", 0) or 0)
                record["totaleVoucherValidati"] = int(data.get("totaleVoucherValidati", 0) or 0)
                record["totaleVoucherNonValidati"] = int(data.get("totaleVoucherNonValidati", 0) or 0)

            if endpoint["kind"] == "versione":
                record["versione"] = data.get("versione")

            direct_state[key] = record

        except Exception as e:
            errors.append(f"{endpoint['name']}: {str(e)}")

    state["_direct_api_state"] = direct_state
    state["_direct_api_errors"] = errors[:10]

    return alerts


# ----------------------------
# LETTURA PAGINE: REQUESTS + PLAYWRIGHT
# ----------------------------

def get_page_text_requests(url):
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0 Safari/537.36 BonusAutoBot/7.0"
        )
    }

    response = requests.get(url, headers=headers, timeout=45)
    response.raise_for_status()

    return clean_text(response.text)


def page_is_suspicious(site, text):
    if not is_mase_like(site):
        return False, []

    reasons = []
    text_clean = str(text).strip()
    text_lower = text_clean.lower()

    if len(text_clean) < MIN_MASE_TEXT_LENGTH:
        reasons.append(f"testo troppo corto ({len(text_clean)} caratteri)")

    if contains_any(text_lower, JAVASCRIPT_SUSPICIOUS_WORDS):
        reasons.append("possibile pagina JavaScript/loading")

    useful_words = MASE_SOLD_OUT_PHRASES + MASE_AVAILABLE_PHRASES + MASE_IMPORTANT_PHRASES

    if not contains_any(text_lower, useful_words):
        reasons.append("mancano parole utili come voucher/plafond/risorse/beneficiario")

    return len(reasons) > 0, reasons


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
                "Chrome/120.0 Safari/537.36 BonusAutoBot/7.0"
            ),
            viewport={"width": 1366, "height": 900},
        )

        def on_response(response):
            try:
                if not response_is_interesting(response):
                    return

                if response.status < 200 or response.status >= 400:
                    return

                body = response.text()

                if not body:
                    return

                body_short = re.sub(r"\s+", " ", body).strip()[:25000]

                if not contains_any(
                    body_short,
                    MASE_IMPORTANT_PHRASES + MASE_AVAILABLE_PHRASES + ["api", "plafond", "voucher"],
                ):
                    return

                api_results.append({
                    "url": response.url,
                    "status": response.status,
                    "content_type": response.headers.get("content-type", ""),
                    "hash": text_hash(body_short),
                    "body_preview": body_short[:800],
                    "last_seen": now_string(),
                    "source_page": site["name"],
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

    return text, list(unique.values())[:25]


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


def update_api_inventory(state, api_results):
    if not api_results:
        return

    inventory = state.get("_api_inventory", {})

    if not isinstance(inventory, dict):
        inventory = {}

    for api in api_results:
        url = api.get("url", "")

        if not url:
            continue

        endpoint_id = text_hash(url)

        old = inventory.get(endpoint_id, {})
        new_record = dict(old)
        new_record.update(api)
        new_record["last_seen"] = now_string()

        inventory[endpoint_id] = new_record

    if len(inventory) > 80:
        items = list(inventory.items())[-80:]
        inventory = dict(items)

    state["_api_inventory"] = inventory


def classify_mase_page(state, site, text, changed, first_run, read_method):
    alerts = []

    url = site["url"]
    name = site["name"]

    sold_out_matches = find_matching_phrases(text, MASE_SOLD_OUT_PHRASES)
    available_matches = find_matching_phrases(text, MASE_AVAILABLE_PHRASES)
    important_matches = find_matching_phrases(text, MASE_IMPORTANT_PHRASES)

    sold_out_now = len(sold_out_matches) > 0
    available_now = len(available_matches) > 0

    status_key = f"_mase_status::{url}"
    previous = state.get(status_key, {})

    sold_out_before = previous.get("sold_out")
    available_before = previous.get("available")

    state[status_key] = {
        "sold_out": sold_out_now,
        "available": available_now,
        "important": bool(important_matches),
        "sold_out_matches": sold_out_matches,
        "available_matches": available_matches,
        "important_matches": important_matches,
        "hash": text_hash(text),
        "last_checked": now_string(),
        "name": name,
        "read_method": read_method,
        "text_length": len(str(text).strip()),
    }

    suspicious, reasons = page_is_suspicious(site, text)

    state[f"_suspicious::{url}"] = {
        "count": 1 if suspicious else 0,
        "last_checked": now_string(),
        "name": name,
        "reasons": reasons,
        "read_method": read_method,
        "text_length": len(str(text).strip()),
    }

    if first_run and not SEND_ON_FIRST_RUN:
        return alerts

    if sold_out_before is True and sold_out_now is False:
        add_alert(
            alerts,
            state,
            f"mase_soldout_disappeared::{url}",
            ALERT_COOLDOWN_URGENT_HOURS,
            "🚨🚨 URGENTE - MESSAGGIO ESAURITO/PRENOTATO SPARITO 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Metodo lettura: {read_method}\n"
            f"Link: {url}\n\n"
            "Prima la pagina indicava risorse/fondi prenotati o esauriti. Ora quel messaggio non risulta più presente.\n\n"
            "Controlla subito il portale MASE con SPID/CIE."
        )

    if available_before is not True and available_now:
        add_alert(
            alerts,
            state,
            f"mase_available_phrase::{url}",
            ALERT_COOLDOWN_URGENT_HOURS,
            "🚨🚨 URGENTE - FRASE DI DISPONIBILITÀ TROVATA 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Metodo lettura: {read_method}\n"
            f"Link: {url}\n\n"
            "Frasi trovate:\n"
            + "\n".join([f"- {p}" for p in available_matches[:10]])
            + "\n\n"
            "Apri subito il portale e prova ad accedere con SPID/CIE.\n\n"
            f"Anteprima:\n{make_snippet(text, available_matches)[:1200]}"
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
        add_alert(
            alerts,
            state,
            f"general_site_changed::{site['url']}",
            ALERT_COOLDOWN_IMPORTANT_HOURS,
            "⚠️ POSSIBILE NOVITÀ BONUS AUTO ELETTRICHE\n\n"
            f"Fonte: {site['name']}\n"
            f"Controllo: {now_string()}\n"
            f"Link: {site['url']}\n\n"
            "La pagina è cambiata e contiene riferimenti ad auto elettriche, bonus, fondi, voucher o prenotazioni.\n\n"
            f"Anteprima:\n{make_snippet(text)[:1200]}"
        )

    return alerts


def check_sites(state):
    alerts = []
    errors = []

    for site in SITES:
        try:
            text, read_method, api_results = get_page_text(site)
            update_api_inventory(state, api_results)

            current_hash = text_hash(text)
            old_hash = state.get(site["url"], {}).get("hash")
            first_run = old_hash is None
            changed = old_hash != current_hash

            if is_mase_like(site):
                alerts.extend(classify_mase_page(state, site, text, changed, first_run, read_method))
            else:
                alerts.extend(classify_general_site(state, site, text, changed, first_run))

            state[site["url"]] = {
                "hash": current_hash,
                "last_checked": now_string(),
                "name": site["name"],
                "type": site["type"],
                "text_length": len(str(text).strip()),
                "read_method": read_method,
                "api_results_found": len(api_results),
            }

        except Exception as e:
            errors.append(f"{site['name']}: {str(e)}")

    state["_last_site_errors"] = errors[:10]

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
                    "Se parla di riapertura, fondi o voucher disponibili, controlla subito il portale MASE."
                )

        except Exception as e:
            print(f"Errore controllo news '{query}': {e}")

    state["_seen_news"] = seen_news

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

    return now_italy().hour >= ALIVE_MESSAGE_HOUR


def build_direct_api_status_text(state):
    direct = state.get("_direct_api_state", {})

    plafond = direct.get("beneficiario_plafond", {})
    grafico = direct.get("beneficiario_grafico", {})
    versione_ben = direct.get("beneficiario_versione", {})
    versione_es = direct.get("esercente_versione", {})

    lines = []

    if plafond:
        residuo = plafond.get("residuoPlafond", 0)
        totale = plafond.get("totalePlafond", 0)
        prenotato = plafond.get("prenotatoStimato", 0)
        residuo_percent = plafond.get("residuoPercent", 0)

        lines.append(
            "Plafond beneficiario:\n"
            f"- Totale: {format_euro(totale)}\n"
            f"- Prenotato stimato: {format_euro(prenotato)}\n"
            f"- Residuo: {format_euro(residuo)} ({residuo_percent}%)\n"
            f"- Ultimo controllo: {plafond.get('last_checked', 'N/D')}"
        )
    else:
        lines.append("Plafond beneficiario: non letto.")

    if grafico:
        lines.append(
            "Voucher:\n"
            f"- Totali: {grafico.get('totaleVoucher', 'N/D')}\n"
            f"- Validati: {grafico.get('totaleVoucherValidati', 'N/D')}\n"
            f"- Non validati: {grafico.get('totaleVoucherNonValidati', 'N/D')}"
        )

    if versione_ben or versione_es:
        lines.append(
            "Versioni portale:\n"
            f"- Beneficiario: {versione_ben.get('versione', 'N/D')}\n"
            f"- Esercente: {versione_es.get('versione', 'N/D')}"
        )

    return "\n\n".join(lines)


def build_status_text(state):
    statuses = []

    for key, value in state.items():
        if not key.startswith("_mase_status::"):
            continue

        name = value.get("name", "MASE")
        available = value.get("available")
        sold_out = value.get("sold_out")
        read_method = value.get("read_method", "N/D")
        text_length = value.get("text_length", "N/D")
        checked = value.get("last_checked", "N/D")

        if available:
            status = "🚨 possibile disponibilità nel testo"
        elif sold_out:
            status = "❌ testo indica esaurito/prenotato"
        else:
            status = "ℹ️ nessuna frase forte"

        statuses.append(
            f"- {name}: {status} | metodo: {read_method} | testo: {text_length} caratteri | ultimo: {checked}"
        )

    if not statuses:
        return "Nessuno stato MASE salvato ancora."

    return "\n".join(statuses[:8])


def build_summary(state):
    site_errors = state.get("_last_site_errors", [])
    direct_errors = state.get("_direct_api_errors", [])

    error_lines = []

    if site_errors:
        error_lines.extend([f"- Sito: {e}" for e in site_errors[:5]])

    if direct_errors:
        error_lines.extend([f"- API: {e}" for e in direct_errors[:5]])

    error_text = "0 errori recenti" if not error_lines else "\n".join(error_lines)

    return (
        "📊 RIEPILOGO BOT BONUS AUTO ELETTRICHE - V7\n\n"
        f"Ora controllo: {now_string()}\n\n"
        "API MASE dirette:\n"
        f"{build_direct_api_status_text(state)}\n\n"
        "Stato pagine MASE:\n"
        f"{build_status_text(state)}\n\n"
        "Filtro news:\n"
        f"Il bot considera solo notizie pubblicate oggi: {today_italy()}.\n\n"
        "Errori recenti:\n"
        f"{error_text}\n\n"
        "Conclusione:\n"
        "Ora la priorità è il controllo diretto delle API MASE. Se il residuo plafond aumenta in modo utile, ti avviso subito."
    )


def build_alive_message(state):
    site_errors = state.get("_last_site_errors", [])
    direct_errors = state.get("_direct_api_errors", [])

    return (
        "✅ BOT BONUS AUTO ATTIVO - V7\n\n"
        f"Ultimo controllo: {now_string()}\n"
        f"News controllate: solo pubblicate oggi ({today_italy()})\n"
        f"Errori siti: {len(site_errors)}\n"
        f"Errori API dirette: {len(direct_errors)}\n\n"
        "API MASE dirette:\n"
        f"{build_direct_api_status_text(state)}\n\n"
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

    alerts.extend(check_direct_mase_apis(state))
    alerts.extend(check_sites(state))
    alerts.extend(check_news(state))

    maybe_send_summary_and_alive(state, alerts)

    save_state(state)

    for alert in alerts:
        send_telegram(alert)


if __name__ == "__main__":
    main()
