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

# False = non manda avvisi inutili al primo giro.
SEND_ON_FIRST_RUN = False

# Riepilogo automatico ogni 12 ore.
SUMMARY_EVERY_HOURS = 12


# Frase critica attuale vista sul portale MASE.
MASE_SOLD_OUT_PHRASES = [
    "tutte le risorse risultano al momento prenotate",
    "risorse risultano al momento prenotate",
    "risorse al momento prenotate",
    "risorse prenotate",
    "fondi prenotati",
    "plafond esaurito",
    "fondi esauriti",
    "risorse esaurite",
]


# Frasi che indicano possibile disponibilità fondi/voucher.
MASE_AVAILABLE_PHRASES = [
    "voucher disponibili",
    "voucher disponibile",
    "fondi disponibili",
    "fondo disponibile",
    "risorse disponibili",
    "risorsa disponibile",
    "plafond disponibile",
    "disponibilità plafond",
    "sportello aperto",
    "piattaforma aperta",
    "piattaforma attiva",
    "piattaforma riattivata",
    "prenotazioni aperte",
    "domande aperte",
    "presenta domanda",
    "presentare domanda",
    "richiedi il voucher",
    "richiedere il voucher",
    "richiesta voucher",
    "genera voucher",
    "generare voucher",
    "accedi per richiedere",
    "è possibile richiedere",
    "sono disponibili risorse",
    "sono disponibili fondi",
    "riapertura dello sportello",
    "riapertura piattaforma",
    "riaperti i termini",
]


# Frasi che non indicano ancora disponibilità, ma sono importanti.
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
    "10.000",
    "10000",
    "11.000",
    "11000",
]


def now_string():
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


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
            "Chrome/120.0 Safari/537.36 BonusAutoBot/2.0"
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


def classify_mase_page(state, site, text, changed, first_run):
    alerts = []

    name = site["name"]
    url = site["url"]

    text_lower = text.lower()

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

    # CASO PIÙ IMPORTANTE:
    # prima c'era il messaggio fondi prenotati/esauriti, ora non c'è più.
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
            "Accedi al portale MASE con SPID/CIE e controlla se puoi generare il voucher."
        )

    # Compare una frase di disponibilità.
    if available_before is not True and available_now:
        snippet = make_snippet(text, available_matches)

        alerts.append(
            "🚨🚨 URGENTE - FRASE DI DISPONIBILITÀ TROVATA 🚨🚨\n\n"
            f"Fonte: {name}\n"
            f"Controllo: {now_string()}\n"
            f"Link: {url}\n\n"
            "Frasi trovate:\n"
            + "\n".join([f"- {p}" for p in available_matches[:8]])
            + "\n\n"
            "Cosa significa:\n"
            "La pagina contiene parole compatibili con fondi/voucher/piattaforma disponibili.\n\n"
            "Azione consigliata:\n"
            "Apri subito il portale e prova ad accedere con SPID/CIE.\n\n"
            f"Anteprima:\n{snippet[:1200]}"
        )

    # Cambia una pagina MASE importante contenente plafond/avvisi/risorse.
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

    text_lower = text.lower()

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

            if site["type"] == "mase":
                alerts.extend(classify_mase_page(state, site, text, changed, first_run))
            else:
                alerts.extend(classify_general_site(state, site, text, changed, first_run))

            state[url] = {
                "hash": current_hash,
                "last_checked": now_string(),
                "name": name,
                "type": site["type"],
            }

        except Exception as e:
            errors.append(f"{name}: {str(e)}")

    if errors:
        print("Errori controllo siti:")
        for error in errors[:10]:
            print(error)

    return alerts


def google_news_rss_url(query):
    encoded_query = requests.utils.quote(query)
    return f"https://news.google.com/rss/search?q={encoded_query}&hl=it&gl=IT&ceid=IT:it"


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
        "piattaforma aperta",
        "voucher disponibili",
        "fondi disponibili",
        "risorse disponibili",
        "click day",
        "prenotazioni aperte",
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

                level, reason = classify_news(title, summary)

                seen_news[news_id] = {
                    "title": title,
                    "link": link,
                    "query": query,
                    "published": published,
                    "level": level,
                    "saved_at": now_string(),
                }

                if level == "IGNORE":
                    continue

                if level == "URGENT":
                    emoji = "🚨"
                    label = "URGENTE"
                elif level == "IMPORTANT":
                    emoji = "⚠️"
                    label = "IMPORTANTE"
                else:
                    emoji = "ℹ️"
                    label = "INFORMATIVA"

                # Mandiamo Telegram solo per urgente/importante.
                # Le informative vengono salvate ma non spammate.
                if level not in ["URGENT", "IMPORTANT"]:
                    continue

                alerts.append(
                    f"{emoji} NEWS {label} - BONUS AUTO ELETTRICHE\n\n"
                    f"Ricerca: {query}\n"
                    f"Titolo: {title}\n"
                    f"Data: {published}\n"
                    f"Link: {link}\n\n"
                    f"Valutazione:\n{reason}\n\n"
                    "Cosa fare:\n"
                    "Se parla di riapertura, fondi o voucher disponibili, controlla subito il portale MASE."
                )

        except Exception as e:
            print(f"Errore controllo news '{query}': {e}")

    state["_seen_news"] = seen_news

    return alerts


def should_send_summary(state):
    last_summary = state.get("_last_summary_sent")

    if not last_summary:
        return True

    try:
        last = datetime.datetime.strptime(last_summary, "%d/%m/%Y %H:%M")
        diff = datetime.datetime.now() - last
        return diff.total_seconds() >= SUMMARY_EVERY_HOURS * 3600
    except Exception:
        return True


def build_summary(state):
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
        mase_text = "Nessuno stato MASE salvato ancora."
    else:
        mase_text = "\n".join(mase_statuses[:8])

    return (
        "📊 RIEPILOGO BOT BONUS AUTO ELETTRICHE\n\n"
        f"Ora controllo: {now_string()}\n\n"
        "Stato MASE:\n"
        f"{mase_text}\n\n"
        "Conclusione:\n"
        "Se non hai ricevuto avvisi URGENTI, al momento il bot non ha rilevato conferme forti di voucher/fondi disponibili.\n\n"
        "Nota:\n"
        "Il bot resta attivo e controlla automaticamente siti ufficiali e news."
    )


def maybe_send_summary(state, alerts):
    if should_send_summary(state):
        alerts.append(build_summary(state))
        state["_last_summary_sent"] = now_string()


def main():
    state = load_state()

    alerts = []

    alerts.extend(check_sites(state))
    alerts.extend(check_news(state))

    maybe_send_summary(state, alerts)

    save_state(state)

    for alert in alerts:
        send_telegram(alert)


if __name__ == "__main__":
    main()
