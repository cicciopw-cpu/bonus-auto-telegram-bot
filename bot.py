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
BOT_VERSION = "V9"

SEND_ON_FIRST_RUN = False

SUMMARY_EVERY_HOURS = 12
ALIVE_MESSAGE_HOUR = 9

NEWS_KEEP_DAYS = 30
MAX_SEEN_NEWS = 500

DEEP_PAGE_CHECK_EVERY_HOURS = 1

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

OFFICIAL_DOCUMENTS = [
    {
        "key": "manuale_beneficiari",
        "name": "Manuale Beneficiari MASE",
        "url": f"{MASE_BENEFICIARIO_BASE}/assets/docs/Manuale_beneficiari.pdf",
    },
    {
        "key": "manuale_esercenti",
        "name": "Manuale Esercenti MASE",
        "url": f"{MASE_ESERCENTE_BASE}/assets/docs/Manuale_esercenti.pdf",
    },
    {
        "key": "faq_veicoli_elettrici",
        "name": "FAQ Bonus Veicoli Elettrici",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/assets/docs/FAQ_Veicoli_Elettrici.pdf",
    },
    {
        "key": "condizioni_beneficiari",
        "name": "Condizioni generali Beneficiari",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/assets/docs/Condizioni_generali_beneficiari.pdf",
    },
    {
        "key": "condizioni_esercenti",
        "name": "Condizioni generali Esercenti",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/assets/docs/Condizioni_generali_esercenti.pdf",
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
    "json",
    "plafond",
    "voucher",
    "beneficiario",
    "esercente",
    "disponibil",
    "fondi",
    "risorse",
    "avvisi",
    "config",
]

SITES = [
    {
        "name": "MASE - Home Bonus Veicoli Elettrici",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/index.html",
        "type": "mase_static",
    },
    {
        "name": "MASE - Investimento 4.5 PNRR",
        "url": "https://www.mase.gov.it/portale/investimento-4.5-programma-di-rinnovo-del-parco-veicoli-privati-e-commerciali-leggeri-con-veicoli-elettrici",
        "type": "mase_institutional",
    },
    {
        "name": "MASE - Bando Bonus Veicoli Elettrici",
        "url": "https://www.mase.gov.it/portale/-/bando-per-la-concessione-incentivi-a-fondo-perduto-previsti-nel-piano-nazionale-di-ripresa-e-resilienza-pnrr-missione-2-componente-2-investimento-4.5-programma-di-rinnovo-del-parco-veicoli-privati-e-commerciali-leggeri-con-veicoli-elettrici-",
        "type": "mase_institutional",
    },
    {
        "name": "MASE - Sportello Bonus Veicoli Elettrici",
        "url": "https://www.mase.gov.it/portale/-/auto-bonus-veicoli-elettrici-dal-22/10-aperto-lo-sportello-per-cittadini-e-microimprese",
        "type": "mase_institutional",
    },
    {
        "name": "MASE - PNRR",
        "url": "https://www.mase.gov.it/portale/pnrr",
        "type": "mase_institutional",
    },
    {
        "name": "MASE - Archivio News PNRR",
        "url": "https://www.mase.gov.it/portale/archivio-news-pnrr",
        "type": "mase_institutional",
    },
    {
        "name": "MASE - Login Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login",
        "type": "mase_dynamic",
    },
    {
        "name": "MASE - Home Beneficiario",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/home",
        "type": "mase_dynamic",
    },
    {
        "name": "MASE - Plafond",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond",
        "type": "mase_dynamic",
    },
    {
        "name": "MASE - Esercente / Concessionari",
        "url": "https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciEsercente/",
        "type": "mase_dynamic",
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
    "bonus veicoli elettrici MASE plafond residuo",
    "bonus veicoli elettrici MASE fondi residui",
    "bonus veicoli elettrici MASE voucher scaduti",
    "bonus veicoli elettrici MASE voucher non utilizzati",
    "MASE bonus veicoli elettrici riapertura piattaforma",
    "MASE bonus veicoli elettrici riattivazione sportello",
    "MASE voucher auto elettriche sportello aperto",
    "MASE Investimento 4.5 veicoli elettrici voucher",
    "Sogei bonus veicoli elettrici voucher",
    "ecobonus auto elettriche apertura prenotazioni",
    "incentivi auto elettriche 10000 euro MASE",
    "incentivi auto elettriche 11000 euro MASE",
]
TRUSTED_NEWS_SOURCES = [
    "ministero",
    "mase",
    "mimit",
    "gazzetta ufficiale",
    "quattroruote",
    "il sole 24 ore",
    "hdmotori",
    "insideevs",
    "vaielettrico",
    "alvolante",
    "sicuroauto",
    "ansa",
    "rai",
    "sky tg24",
    "repubblica",
    "corriere",
    "fanpage",
    "rinnovabili",
    "aci",
    "automobile club",
    "open innovation",
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
    "motociclo",
    "ciclomotori",
    "ciclomotore",
    "scooter",
    "quadricicli",
    "quadriciclo",
    "due ruote",
    "bici elettriche",
    "biciclette elettriche",
    "e-bike",
    "ebike",
    "monopattini",
    "monopattino",
    "colonnine",
    "colonnina",
    "ricarica domestica",
    "punti di ricarica",
    "punto di ricarica",
    "stazioni di ricarica",
    "infrastrutture di ricarica",
    "bonus colonnine",
    "wallbox",
    "wall box",
    "wall-box",
    "condominio",
    "condomini",
    "garage",
    "box auto",
    "installatori",
    "pompe di calore",
]

OFFICIAL_BONUS_CONTEXT_WORDS = [
    "bonus veicoli elettrici",
    "investimento 4.5",
    "m2c2",
    "pnrr m2c2",
    "mase",
    "sogei",
]

REAL_VOUCHER_SIGNAL_WORDS = [
    "voucher",
    "plafond",
    "fondi disponibili",
    "fondi residui",
    "risorse disponibili",
    "risorse residue",
    "sportello",
    "piattaforma",
    "prenotazioni",
    "domande",
    "riapertura",
    "riattivazione",
    "scaduti",
    "non utilizzati",
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


def text_hash(value):
    if isinstance(value, bytes):
        return hashlib.sha256(value).hexdigest()
    return hashlib.sha256(str(value).encode("utf-8")).hexdigest()


def contains_any(text, words):
    text_lower = str(text).lower()
    return any(word.lower() in text_lower for word in words)


def find_matching_phrases(text, phrases):
    text_lower = str(text).lower()
    return [phrase for phrase in phrases if phrase.lower() in text_lower]


def clean_text(html):
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()

    text = soup.get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text)


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


def send_telegram(message, chat_id=None):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id or CHAT_ID,
        "text": message,
        "disable_web_page_preview": False,
    }

    response = requests.post(url, json=payload, timeout=45)
    response.raise_for_status()


# ----------------------------
# DIRECT API MONITOR
# ----------------------------

def request_json(url):
    headers = {
        "User-Agent": "Mozilla/5.0 BonusAutoBot/9.0",
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
                f"Controllo: {now_string()}\n\n"
                f"Residuo precedente: {format_euro(previous_residuo)}\n"
                f"Residuo attuale: {format_euro(residuo)}\n"
                f"Aumento rilevato: +{format_euro(diff)}\n\n"
                f"Plafond totale: {format_euro(totale)}\n"
                f"Prenotato stimato: {format_euro(prenotato)} ({prenotato_percent}%)\n"
                f"Residuo: {format_euro(residuo)} ({residuo_percent}%)\n\n"
                "Cosa fare subito:\n"
                "Apri il portale MASE con SPID/CIE e controlla se il voucher è generabile.\n\n"
                "Login: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/login\n"
                "Plafond: https://www.bonusveicolielettrici.mase.gov.it/veicolielettriciBeneficiario/#/plafond"
            )

        elif diff >= PLAFOND_IMPORTANT_INCREASE_EURO:
            add_alert(
                alerts,
                state,
                "direct_api_plafond_small_increase",
                ALERT_COOLDOWN_IMPORTANT_HOURS,
                "⚠️ PLAFOND MASE AUMENTATO\n\n"
                f"Controllo: {now_string()}\n\n"
                f"Residuo precedente: {format_euro(previous_residuo)}\n"
                f"Residuo attuale: {format_euro(residuo)}\n"
                f"Aumento rilevato: +{format_euro(diff)}\n\n"
                "Non è ancora una conferma di voucher disponibili, ma è un movimento importante."
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
            "Potrebbe indicare una modifica importante delle risorse disponibili."
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
            f"Controllo: {now_string()}\n\n"
            + "\n".join([f"- {c}" for c in changes])
            + "\n\n"
            "Il conteggio ufficiale dei voucher si è mosso. Non è una conferma di fondi disponibili, ma va controllato."
        )

    return alerts


def check_avvisi_api(state, endpoint, data):
    alerts = []
    api_key = endpoint["key"]
    previous = state.get("_direct_api_state", {}).get(api_key, {})

    body_text = json.dumps(data, ensure_ascii=False, sort_keys=True)
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
                f"Controllo: {now_string()}\n\n"
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
                f"Controllo: {now_string()}\n\n"
                "Gli avvisi ufficiali sono cambiati e contengono parole importanti.\n\n"
                f"Anteprima:\n{make_snippet(body_text, important_matches)[:1200]}"
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
# DOCUMENTI UFFICIALI PDF / FAQ
# ----------------------------

def request_document(url):
    headers = {
        "User-Agent": "Mozilla/5.0 BonusAutoBot/9.0",
        "Accept": "application/pdf,application/octet-stream,*/*",
    }

    response = requests.get(url, headers=headers, timeout=60)
    response.raise_for_status()
    return response.content, response.headers.get("content-type", "")


def check_official_documents(state):
    alerts = []
    errors = []
    docs_state = state.get("_official_documents_state", {})

    if not isinstance(docs_state, dict):
        docs_state = {}

    for doc in OFFICIAL_DOCUMENTS:
        key = doc["key"]

        try:
            content, content_type = request_document(doc["url"])
            current_hash = text_hash(content)
            previous = docs_state.get(key, {})
            previous_hash = previous.get("hash")

            if previous_hash is not None and previous_hash != current_hash:
                add_alert(
                    alerts,
                    state,
                    f"official_document_changed::{key}",
                    ALERT_COOLDOWN_URGENT_HOURS,
                    "🚨 DOCUMENTO UFFICIALE MASE CAMBIATO\n\n"
                    f"Documento: {doc['name']}\n"
                    f"Controllo: {now_string()}\n"
                    f"Link: {doc['url']}\n\n"
                    "Questo può indicare nuove regole, FAQ aggiornate o modifiche operative.\n"
                    "Controllalo appena puoi."
                )

            docs_state[key] = {
                "name": doc["name"],
                "url": doc["url"],
                "hash": current_hash,
                "size_bytes": len(content),
                "content_type": content_type,
                "last_checked": now_string(),
            }

        except Exception as e:
            errors.append(f"{doc['name']}: {str(e)}")

    state["_official_documents_state"] = docs_state
    state["_official_documents_errors"] = errors[:10]
    return alerts


# ----------------------------
# PAGINE WEB: CONTROLLO LEGGERO + DEEP CHECK
# ----------------------------

def get_page_text_requests(url):
    headers = {
        "User-Agent": "Mozilla/5.0 BonusAutoBot/9.0",
    }

    response = requests.get(url, headers=headers, timeout=45)
    response.raise_for_status()
    return clean_text(response.text)


def is_mase_dynamic(site):
    return site["type"] == "mase_dynamic"


def is_mase_static(site):
    return site["type"] == "mase_static"


def page_is_suspicious(site, text):
    if not site["type"].startswith("mase"):
        return False, []

    reasons = []
    text_clean = str(text).strip()
    text_lower = text_clean.lower()

    if len(text_clean) < 350:
        reasons.append(f"testo troppo corto ({len(text_clean)} caratteri)")

    if contains_any(text_lower, JAVASCRIPT_SUSPICIOUS_WORDS):
        reasons.append("possibile pagina JavaScript/loading")

    useful_words = MASE_SOLD_OUT_PHRASES + MASE_AVAILABLE_PHRASES + MASE_IMPORTANT_PHRASES

    if not contains_any(text_lower, useful_words):
        reasons.append("mancano parole utili")

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
            args=["--no-sandbox", "--disable-dev-shm-usage"],
        )

        page = browser.new_page(
            user_agent="Mozilla/5.0 BonusAutoBot/9.0",
            viewport={"width": 1366, "height": 900},
        )

        def on_response(response):
            try:
                if not response_is_interesting(response):
                    return

                if response.status < 200 or response.status >= 400:
                    return

                body = response.text()
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
                text = clean_text(page.content())
            except Exception:
                text = ""

        browser.close()

    text = re.sub(r"\s+", " ", text).strip()

    unique = {}
    for item in api_results:
        unique[item["url"]] = item

    return text, list(unique.values())[:25]


def should_run_deep_page_check(state):
    last = state.get("_last_deep_page_check")

    if not last:
        return True

    return hours_since(last) >= DEEP_PAGE_CHECK_EVERY_HOURS


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
        inventory = dict(list(inventory.items())[-80:])

    state["_api_inventory"] = inventory


def classify_mase_text(state, site, text, read_method, first_run):
    alerts = []
    url = site["url"]
    name = site["name"]

    sold_out_matches = find_matching_phrases(text, MASE_SOLD_OUT_PHRASES)
    available_matches = find_matching_phrases(text, MASE_AVAILABLE_PHRASES)
    important_matches = find_matching_phrases(text, MASE_IMPORTANT_PHRASES)

    sold_out_now = len(sold_out_matches) > 0
    available_now = len(available_matches) > 0

    previous = state.get(f"_mase_status::{url}", {})

    sold_out_before = previous.get("sold_out")
    available_before = previous.get("available")

    state[f"_mase_status::{url}"] = {
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
            f"Metodo: {read_method}\n"
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
            f"Metodo: {read_method}\n"
            f"Link: {url}\n\n"
            "Frasi trovate:\n"
            + "\n".join([f"- {p}" for p in available_matches[:10]])
            + "\n\n"
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
    has_important = contains_any(text, IMPORTANT_NEWS_WORDS)

    if has_disqualifying_topic(text):
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
            f"Anteprima:\n{make_snippet(text)[:1200]}"
        )

    return alerts


def check_sites(state):
    alerts = []
    errors = []
    deep_due = should_run_deep_page_check(state)

    for site in SITES:
        try:
            if is_mase_dynamic(site) and not deep_due:
                old = state.get(site["url"], {})
                old["last_skipped_deep_check"] = now_string()
                old["skipped_reason"] = "deep check non dovuto, API dirette già controllate"
                state[site["url"]] = old
                continue

            read_method = "requests"
            api_results = []

            if is_mase_dynamic(site):
                text, api_results = get_page_text_playwright(site)
                read_method = "playwright"
                update_api_inventory(state, api_results)
            else:
                text = get_page_text_requests(site["url"])

            current_hash = text_hash(text)
            old_hash = state.get(site["url"], {}).get("hash")
            first_run = old_hash is None
            changed = old_hash != current_hash

            if site["type"].startswith("mase"):
                alerts.extend(classify_mase_text(state, site, text, read_method, first_run))
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

    if deep_due:
        state["_last_deep_page_check"] = now_string()

    state["_last_site_errors"] = errors[:10]
    return alerts


# ----------------------------
# NEWS
# ----------------------------

def parse_news_date(entry):
    published = entry.get("published", "")

    if not published:
        return None

    try:
        parsed = parsedate_to_datetime(published)

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)

        return parsed.astimezone(ZoneInfo("Europe/Rome")).date()
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


def get_news_source(entry):
    source = entry.get("source", {})
    if hasattr(source, "get"):
        return source.get("title", "")
    return ""


def source_is_trusted(source, title):
    text = f"{source} {title}".lower()
    return any(src in text for src in TRUSTED_NEWS_SOURCES)


def is_official_bonus_context(text):
    text = str(text).lower()
    return contains_any(text, OFFICIAL_BONUS_CONTEXT_WORDS) and contains_any(text, REAL_VOUCHER_SIGNAL_WORDS)


def has_disqualifying_topic(text):
    text = str(text).lower()

    if not contains_any(text, BAD_TOPICS):
        return False

    # Se parla di wallbox/colonnine/moto/scooter va scartata, tranne quando il testo
    # è chiaramente dentro il programma ufficiale MASE Bonus Veicoli Elettrici.
    return not is_official_bonus_context(text)


def classify_news(title, summary, source):
    text = f"{title} {summary} {source}".lower()

    has_auto = contains_any(text, AUTO_WORDS)
    has_important = contains_any(text, IMPORTANT_NEWS_WORDS)
    official_bonus_context = is_official_bonus_context(text)

    urgent_words = [
        "disponibili",
        "disponibile",
        "riapertura",
        "apertura",
        "sportello aperto",
        "sportello riaperto",
        "piattaforma aperta",
        "piattaforma attiva",
        "piattaforma riaperta",
        "piattaforma riattivata",
        "voucher disponibili",
        "fondi disponibili",
        "fondi residui",
        "risorse disponibili",
        "risorse residue",
        "click day",
        "prenotazioni aperte",
        "domande aperte",
        "voucher scaduti",
        "voucher non utilizzati",
        "tornano disponibili",
        "torna disponibile",
    ]

    has_urgent = contains_any(text, urgent_words)

    if has_disqualifying_topic(text):
        return "IGNORE", "Scartata: parla di wallbox/colonnine/moto/scooter/ricarica o temi fuori dal voucher auto MASE."

    if official_bonus_context and has_urgent:
        return "URGENT", "Contesto ufficiale MASE/Bonus Veicoli Elettrici con segnali di voucher, plafond, fondi o riapertura."

    if has_auto and has_urgent and contains_any(text, ["voucher", "plafond", "fondi", "risorse", "sportello", "piattaforma"]):
        return "URGENT", "Contiene parole compatibili con apertura, disponibilità fondi, plafond o voucher auto."

    if official_bonus_context or (has_auto and has_important and contains_any(text, ["mase", "mimit", "ministero", "sogei", "ecobonus"])):
        return "IMPORTANT", "Parla del bonus/incentivo auto elettriche con segnali collegati a MASE/MIMIT/Sogei."

    if "mase" in text or "mimit" in text or "ecobonus" in text:
        return "INFO", "Cita MASE/MIMIT/Ecobonus, ma non contiene segnali forti sul voucher auto."

    return "IGNORE", "Notizia non abbastanza pertinente."


def should_notify_news(level, source, title):
    text = f"{source} {title}".lower()
    trusted = source_is_trusted(source, title)
    official_hint = contains_any(text, ["mase", "mimit", "ministero", "sogei", "bonus veicoli elettrici"])

    if has_disqualifying_topic(text):
        return False

    if level == "URGENT":
        return trusted or official_hint

    if level == "IMPORTANT":
        return trusted and official_hint

    return False


def cleanup_seen_news(state):
    seen_news = state.get("_seen_news", {})

    if not isinstance(seen_news, dict):
        state["_seen_news"] = {}
        return

    cutoff = now_italy() - datetime.timedelta(days=NEWS_KEEP_DAYS)
    cleaned_items = []

    for news_id, item in seen_news.items():
        parsed = parse_saved_at(item.get("saved_at"))

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
            feed = feedparser.parse(google_news_rss_url(query))

            for entry in feed.entries[:8]:
                title = entry.get("title", "").strip()
                link = entry.get("link", "").strip()
                summary = entry.get("summary", "").strip()
                published = entry.get("published", "Data non disponibile")
                source = get_news_source(entry)

                if not title or not link:
                    continue

                if not is_news_from_today(entry):
                    continue

                news_id = hashlib.sha256(link.encode("utf-8")).hexdigest()

                if news_id in seen_news:
                    continue

                level, reason = classify_news(title, summary, source)

                seen_news[news_id] = {
                    "title": title,
                    "source": source,
                    "link": link,
                    "query": query,
                    "published": published,
                    "level": level,
                    "saved_at": now_string(),
                    "news_day_filter": str(today),
                }

                if not should_notify_news(level, source, title):
                    continue

                emoji = "🚨" if level == "URGENT" else "⚠️"
                label = "URGENTE" if level == "URGENT" else "IMPORTANTE"

                alerts.append(
                    f"{emoji} NEWS {label} - BONUS AUTO ELETTRICHE\n\n"
                    f"Fonte: {source or 'N/D'}\n"
                    f"Titolo: {title}\n"
                    f"Data: {published}\n"
                    f"Link: {link}\n\n"
                    f"Valutazione:\n{reason}\n\n"
                    "Il bot filtra solo notizie pubblicate oggi e da fonti più affidabili."
                )

        except Exception as e:
            print(f"Errore controllo news '{query}': {e}")

    state["_seen_news"] = seen_news
    return alerts


# ----------------------------
# MESSAGGI STATUS
# ----------------------------

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
            "🎯 Stato principale:\n"
            "Nessuna riapertura utile rilevata, salvo avviso urgente separato.\n\n"
            "📌 Plafond beneficiario:\n"
            f"- Totale: {format_euro(totale)}\n"
            f"- Prenotato stimato: {format_euro(prenotato)}\n"
            f"- Residuo: {format_euro(residuo)} ({residuo_percent}%)\n"
            f"- Ultimo controllo API: {plafond.get('last_checked', 'N/D')}"
        )
    else:
        lines.append("🎯 Plafond beneficiario: non letto.")

    if grafico:
        lines.append(
            "🎟️ Voucher:\n"
            f"- Totali: {grafico.get('totaleVoucher', 'N/D')}\n"
            f"- Validati: {grafico.get('totaleVoucherValidati', 'N/D')}\n"
            f"- Non validati: {grafico.get('totaleVoucherNonValidati', 'N/D')}"
        )

    if versione_ben or versione_es:
        lines.append(
            "🛠️ Versioni portale:\n"
            f"- Beneficiario: {versione_ben.get('versione', 'N/D')}\n"
            f"- Esercente: {versione_es.get('versione', 'N/D')}"
        )

    return "\n\n".join(lines)


def build_docs_status_text(state):
    docs = state.get("_official_documents_state", {})

    if not docs:
        return "Documenti ufficiali: baseline non ancora creata."

    lines = []

    for _, item in docs.items():
        lines.append(
            f"- {item.get('name', 'Documento')}: OK | ultimo controllo {item.get('last_checked', 'N/D')}"
        )

    return "\n".join(lines[:8])


def build_recent_news_text(state):
    seen = state.get("_seen_news", {})

    if not seen:
        return "Nessuna news salvata."

    items = list(seen.values())
    today = str(today_italy())
    today_items = [x for x in items if x.get("news_day_filter") == today]

    interesting = [
        x for x in today_items
        if x.get("level") in ["URGENT", "IMPORTANT"]
    ]

    if not interesting:
        return "Nessuna news urgente/importante di oggi."

    lines = []

    for item in interesting[-5:]:
        lines.append(
            f"- [{item.get('level')}] {item.get('title')}\n  Fonte: {item.get('source', 'N/D')}"
        )

    return "\n".join(lines)


def build_sources_text(state):
    lines = [
        f"🔎 FONTI MONITORATE - {BOT_VERSION}",
        "",
        f"API MASE dirette: {len(DIRECT_API_ENDPOINTS)}",
        f"Documenti ufficiali: {len(OFFICIAL_DOCUMENTS)}",
        f"Pagine/siti controllati: {len(SITES)}",
        f"Query Google News: {len(NEWS_QUERIES)}",
        "",
        "Fonti principali:",
        "- Portale Bonus Veicoli Elettrici MASE",
        "- API plafond/grafico/versione/avvisi MASE",
        "- Manuali, FAQ e condizioni ufficiali MASE",
        "- Pagine MASE Investimento 4.5 / PNRR / Archivio News PNRR",
        "- Ecobonus MIMIT e aggiornamenti MIMIT, con filtro stretto",
        "- Google News, solo oggi e filtrate anti-falsi positivi",
    ]

    return "\n".join(lines)


def build_debug_text(state):
    site_errors = state.get("_last_site_errors", [])
    api_errors = state.get("_direct_api_errors", [])
    doc_errors = state.get("_official_documents_errors", [])
    seen_news = state.get("_seen_news", {})
    api_inventory = state.get("_api_inventory", {})
    telegram_error = state.get("_telegram_command_error")

    lines = [
        f"🧪 DEBUG BOT BONUS AUTO - {BOT_VERSION}",
        "",
        f"Ora: {now_string()}",
        f"Ultimo deep check pagine: {state.get('_last_deep_page_check', 'N/D')}",
        f"News salvate: {len(seen_news) if isinstance(seen_news, dict) else 0}",
        f"Endpoint scoperti via Playwright: {len(api_inventory) if isinstance(api_inventory, dict) else 0}",
        "",
        "Errori:",
        f"- Siti: {len(site_errors)}",
        f"- API: {len(api_errors)}",
        f"- Documenti: {len(doc_errors)}",
        f"- Telegram comandi: {telegram_error or 'OK'}",
    ]

    if site_errors:
        lines.append("\nUltimi errori siti:")
        lines.extend([f"- {err}" for err in site_errors[:5]])

    if api_errors:
        lines.append("\nUltimi errori API:")
        lines.extend([f"- {err}" for err in api_errors[:5]])

    if doc_errors:
        lines.append("\nUltimi errori documenti:")
        lines.extend([f"- {err}" for err in doc_errors[:5]])

    return "\n".join(lines)


def build_status_text(state):
    site_errors = state.get("_last_site_errors", [])
    api_errors = state.get("_direct_api_errors", [])
    doc_errors = state.get("_official_documents_errors", [])

    return (
        "📊 STATUS BOT BONUS AUTO - V9\n\n"
        f"Ora: {now_string()}\n\n"
        f"{build_direct_api_status_text(state)}\n\n"
        "📄 Documenti ufficiali:\n"
        f"{build_docs_status_text(state)}\n\n"
        "📰 News:\n"
        f"{build_recent_news_text(state)}\n\n"
        "⚠️ Errori:\n"
        f"- Siti: {len(site_errors)}\n"
        f"- API: {len(api_errors)}\n"
        f"- Documenti: {len(doc_errors)}"
    )


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


def build_summary(state):
    return (
        "📊 RIEPILOGO BOT BONUS AUTO - V9\n\n"
        f"{build_direct_api_status_text(state)}\n\n"
        "📄 Documenti:\n"
        f"{build_docs_status_text(state)}\n\n"
        "📰 News:\n"
        f"{build_recent_news_text(state)}\n\n"
        "Conclusione:\n"
        "Se non hai ricevuto avvisi URGENTI separati, il bot non ha rilevato una riapertura utile del plafond."
    )


def build_alive_message(state):
    return (
        "✅ BOT BONUS AUTO ATTIVO - V9\n\n"
        f"Ultimo controllo: {now_string()}\n"
        "Controllo principale: API MASE dirette ogni 5 minuti.\n"
        "Deep check pagine: circa ogni 1 ora.\n"
        "Documenti ufficiali: monitorati.\n"
        "News: solo di oggi e filtrate meglio.\n\n"
        f"{build_direct_api_status_text(state)}"
    )


def maybe_send_summary_and_alive(state, alerts):
    if should_send_summary(state):
        alerts.append(build_summary(state))
        state["_last_summary_sent"] = now_string()

    if should_send_alive_message(state):
        alerts.append(build_alive_message(state))
        state["_last_alive_day"] = today_string()


# ----------------------------
# COMANDI TELEGRAM
# ----------------------------

def get_telegram_updates(state):
    offset = state.get("_telegram_update_offset")
    params = {"timeout": 0}

    if offset is not None:
        params["offset"] = offset

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    response = requests.get(url, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    return data.get("result", [])


def command_name(text):
    first = text.strip().split()[0].lower()
    return first.split("@")[0]


def handle_telegram_commands(state):
    try:
        updates = get_telegram_updates(state)
    except Exception as e:
        state["_telegram_command_error"] = str(e)
        return

    if not updates:
        return

    max_update_id = state.get("_telegram_update_offset", 0) - 1
    now_ts = int(datetime.datetime.now(datetime.timezone.utc).timestamp())

    for update in updates:
        update_id = update.get("update_id")

        if update_id is not None:
            max_update_id = max(max_update_id, update_id)

        message = update.get("message") or update.get("edited_message") or {}
        text = message.get("text", "")
        chat = message.get("chat", {})
        chat_id = chat.get("id")
        msg_date = message.get("date", 0)

        if not text.startswith("/"):
            continue

        if str(chat_id) != str(CHAT_ID):
            continue

        if msg_date and now_ts - int(msg_date) > 3600:
            continue

        cmd = command_name(text)

        if cmd in ["/start", "/help"]:
            send_telegram(
                "🤖 Comandi disponibili:\n\n"
                "/status - stato completo del bot\n"
                "/plafond - stato plafond e voucher\n"
                "/news - ultime news importanti di oggi\n"
                "/docs - stato documenti ufficiali\n"
                "/fonti - elenco fonti monitorate\n"
                "/debug - diagnostica tecnica rapida\n"
                "/check - mostra l’ultimo controllo disponibile\n\n"
                "Il bot controlla automaticamente ogni 5 minuti.",
                chat_id=chat_id,
            )

        elif cmd in ["/status", "/check"]:
            send_telegram(build_status_text(state), chat_id=chat_id)

        elif cmd == "/plafond":
            send_telegram(
                "🎯 STATO PLAFOND / VOUCHER\n\n"
                f"{build_direct_api_status_text(state)}",
                chat_id=chat_id,
            )

        elif cmd == "/news":
            send_telegram(
                "📰 NEWS IMPORTANTI DI OGGI\n\n"
                f"{build_recent_news_text(state)}",
                chat_id=chat_id,
            )

        elif cmd == "/docs":
            send_telegram(
                "📄 DOCUMENTI UFFICIALI MONITORATI\n\n"
                f"{build_docs_status_text(state)}",
                chat_id=chat_id,
            )

        elif cmd == "/fonti":
            send_telegram(build_sources_text(state), chat_id=chat_id)

        elif cmd == "/debug":
            send_telegram(build_debug_text(state), chat_id=chat_id)

        else:
            send_telegram(
                "Comando non riconosciuto. Scrivi /help.",
                chat_id=chat_id,
            )

    state["_telegram_update_offset"] = max_update_id + 1


# ----------------------------
# MAIN
# ----------------------------

def main():
    state = load_state()

    cleanup_seen_news(state)

    alerts = []

    alerts.extend(check_direct_mase_apis(state))
    alerts.extend(check_official_documents(state))
    alerts.extend(check_sites(state))
    alerts.extend(check_news(state))

    maybe_send_summary_and_alive(state, alerts)

    save_state(state)

    for alert in alerts:
        send_telegram(alert)

    handle_telegram_commands(state)

    save_state(state)


if __name__ == "__main__":
    main()
