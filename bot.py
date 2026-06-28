import os
import re
import json
import hashlib
import datetime
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

STATE_FILE = "state.json"

SEND_ON_FIRST_RUN = False

SITES = [
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
        "name": "Bonus Veicoli Elettrici MASE",
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

KEYWORDS = [
    "auto elettrica",
    "auto elettriche",
    "veicoli elettrici",
    "elettriche",
    "bev",
    "plug-in",
    "plug in",
    "phev",
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
    "m1",
    "leapmotor",
    "t03",
    "beneficiario",
    "accedi",
    "login",
    "richiedi voucher",
    "richiedi il voucher",
    "voucher disponibile",
    "voucher disponibili",
    "piattaforma attiva",
    "sportello aperto",
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
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


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
        "User-Agent": "Mozilla/5.0 BonusAutoTelegramBot/1.0"
    }
    response = requests.get(url, headers=headers, timeout=25)
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
        value = int(amount.replace(".", ""))
        if value >= 10000:
            return True

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
    response = requests.post(url, json=payload, timeout=25)
    response.raise_for_status()


def should_alert(text, changed, first_run, site_important):
    has_bonus_words = contains_any(text, KEYWORDS)
    has_availability = contains_any(text, AVAILABILITY_WORDS)
    has_big_amount = contains_amount_10000_or_more(text)

    if first_run and not SEND_ON_FIRST_RUN:
        return False

    if not changed:
        return False

    if site_important and has_bonus_words:
        return True

    if has_bonus_words and has_availability:
        return True

    if has_big_amount and has_bonus_words:
        return True

    return False


def main():
    state = load_state()
    now = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

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

            if should_alert(text, changed, first_run, site.get("important", False)):
                snippet = make_snippet(text)

                message = (
                    "🚗 POSSIBILE BONUS AUTO ELETTRICHE DISPONIBILE / AGGIORNATO\n\n"
                    f"Fonte: {name}\n"
                    f"Controllo: {now}\n"
                    f"Link: {url}\n\n"
                    "Motivo: la pagina è cambiata e contiene parole collegate a bonus, incentivi, fondi, voucher o auto elettriche.\n\n"
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

    save_state(state)

    for alert in alerts:
        send_telegram(alert)

    if errors:
        error_message = (
            "⚠️ Errore nel controllo bonus auto\n\n"
            + "\n".join(errors[:5])
        )
        send_telegram(error_message)


if __name__ == "__main__":
    main()
