#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_news.py — aggiornamento autonomo del sito Apple WWDC 2026.

Porta la logica del vecchio task Cowork (SKILL.md) in uno script autosufficiente
pensato per girare su GitHub Actions, senza Mac acceso. A ogni run:

  1. legge data/news.json e controlla la finestra evento (esce se WWDC e finito,
     PRIMA di verificare la chiave API: fuori finestra non serve alcun segreto);
  2. raccoglie slug e titoli gia pubblicati (nel prompt vanno solo gli ultimi 40 titoli);
  3. chiama l'API Anthropic con il tool web_search (lato server) per trovare
     SOLO annunci nuovi, scritti in italiano e inglese con i paletti editoriali
     di Biolatti;
  4. valida ogni item: schema, accenti italiani (accenti.fix_accents), dedupe per
     slug E per similarita del titolo, domini delle fonti ammessi; se manca una
     fonte ufficiale Apple l'item NON viene pubblicato ma messo in
     data/review_queue.json (escluso dal deploy) per la verifica manuale;
  5. aggiunge gli item validi in testa, aggiorna lastUpdate, rigenera con build.py.

Se la risposta del modello non si puo interpretare o e troncata
(stop_reason == "max_tokens") lo script esce con codice 1 (job rosso).

Output su stdout in forma leggibile e una riga finale machine-readable
"SUMMARY::<n>::<titoli separati da ' | '>" usata dal workflow per la notifica.

Variabili d'ambiente:
  ANTHROPIC_API_KEY  (obbligatoria)
  WWDC_MODEL         (opzionale, default claude-sonnet-4-6)
  WWDC_MAX_NEW       (opzionale, default 8 — cap di item per run)
  WWDC_MAX_SEARCHES  (opzionale, default 3 — max ricerche web per run)
  WWDC_FORCE         (opzionale, "1" per ignorare il controllo finestra)
"""

import difflib
import json
import os
import re
import subprocess
import sys
import unicodedata
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from accenti import fix_item_it_fields  # noqa: E402

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "news.json")
BUILD = os.path.join(BASE_DIR, "build.py")

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MODEL = os.environ.get("WWDC_MODEL") or "claude-sonnet-4-6"
MAX_NEW = int(os.environ.get("WWDC_MAX_NEW") or "8")
MAX_SEARCHES = int(os.environ.get("WWDC_MAX_SEARCHES") or "3")
SITE_URL = "https://wwdc2026.biolatti.it"
NOTIFY_FILE = os.path.join(BASE_DIR, "notify_items.json")
REVIEW_FILE = os.path.join(BASE_DIR, "data", "review_queue.json")
PROMPT_RECENT_TITLES = 40
TITLE_SIM_RATIO = 0.85     # difflib.SequenceMatcher sul titolo normalizzato
TITLE_SIM_JACCARD = 0.80   # Jaccard sui token significativi del titolo

# Fonti: dominio ufficiale Apple (almeno una obbligatoria per pubblicare)
OFFICIAL_DOMAINS = {"apple.com", "developer.apple.com"}
# Altre testate ammesse come fonti di supporto (sottodomini inclusi).
ALLOWED_DOMAINS = OFFICIAL_DOMAINS | {
    "macrumors.com", "9to5mac.com", "theverge.com", "engadget.com", "techradar.com",
    "appleinsider.com", "macworld.com", "techcrunch.com", "arstechnica.com",
    "wired.com", "cnet.com", "zdnet.com", "bloomberg.com", "reuters.com",
    "sixcolors.com", "daringfireball.net", "imore.com", "tomsguide.com",
    "wwdcnotes.com", "swift.org", "github.com", "ec.europa.eu", "macitynet.it",
    "hdblog.it", "ilpost.it", "wired.it", "cnbc.com", "macstories.net", "cultofmac.com",
    "macobserver.com", "thurrott.com", "gizmodo.com", "bgr.com", "techrepublic.com",
}
TZ = timezone(timedelta(hours=2))  # Europe/Rome estate (CEST)

VALID_MACRO = {
    "sistemi-operativi", "apple-intelligence", "sviluppatori", "design-interfacce",
    "spatial-visionos", "salute-benessere", "servizi-ecosistema", "privacy-sicurezza",
}
VALID_TAGS = {
    "intelligenza-artificiale", "siri", "swift-xcode", "design",
    "privacy", "salute", "continuity", "accessibilita",
}


def log(msg):
    print(msg, flush=True)


def fail(msg, code=1):
    log("ERRORE: " + msg)
    # Emit an empty summary so the workflow notification step never breaks.
    print("SUMMARY::0::" + msg, flush=True)
    sys.exit(code)


def load_data():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def within_window(data):
    if os.environ.get("WWDC_FORCE") == "1":
        return True
    end = data.get("eventEnd", "2026-06-12T23:59:00+02:00")
    try:
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        end_dt = datetime(2026, 6, 12, 23, 59, tzinfo=TZ)
    # grace di 12h per i follow-up post-evento
    return datetime.now(TZ) <= end_dt + timedelta(hours=12)


def recent_titles(data, n=PROMPT_RECENT_TITLES):
    """Ultimi n titoli IT (gli item piu recenti stanno in testa a data['items'])."""
    return [it.get("titleIt", "") for it in data.get("items", [])[:n] if it.get("titleIt")]


def build_prompt(titles):
    slugs_str = ("\n".join(f"- {t}" for t in titles)) if titles else "(nessuno: e il primo run)"
    now_str = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    return f"""Sei Kairos, l'AI di Daniele Biolatti. Stai aggiornando in autonomia il sito wwdc2026.biolatti.it, copertura italiana indipendente dell'Apple WWDC 2026 (8-12 giugno 2026).

CONTESTO TEMPORALE — LEGGI CON ATTENZIONE
Adesso sono le {now_str} (ora italiana). L'Apple WWDC 2026 si svolge dall'8 al 12 giugno 2026 ed E' attualmente in corso. Il keynote di apertura si e' tenuto la sera dell'8 giugno (dalle 19:00 ora italiana) e ha presentato iOS 27, iPadOS 27, macOS 27, watchOS 27, tvOS 27, visionOS 27, il nuovo Siri, le funzioni di Apple Intelligence e molto altro. Nei giorni successivi il keynote e' concluso, ma l'evento prosegue con sessioni tecniche, lab e approfondimenti: continuano a emergere annunci di dettaglio, novita delle singole sessioni e follow-up dalla copertura. NON e' un evento futuro o ipotetico: il keynote e' GIA avvenuto e ci sono decine di annunci concreti gia fatti. Regolati sull'orario indicato sopra: se ti trovi la sera dell'8 il keynote e' dal vivo; nei giorni seguenti raccogli cio che e' emerso e viene approfondito fino a {now_str}.

COMPITO
Usa la ricerca web (live blog e articoli di MacRumors, 9to5Mac, The Verge, Engadget, TechRadar, AppleInsider, Macworld, Apple Newsroom) per raccogliere gli annunci CONCRETI gia fatti da Apple durante il keynote e le sessioni in corso. Ogni singola novita annunciata (una funzione o un prodotto) diventa un articolo. Restituisci SOLO annunci NUOVI non gia coperti.

GIA COPERTI — ultimi {PROMPT_RECENT_TITLES} titoli pubblicati (non ripetere questi annunci ne altri gia coperti; lo script scarta comunque i duplicati):
{slugs_str}

REGOLE — IMPORTANTE
- Un annuncio FATTO da Apple sul palco e riportato dalla copertura live E' un fatto confermato, NON un rumor. I "rumor" sono solo le ipotesi PRIMA dell'evento; ora l'evento e' iniziato, quindi raccogli cio che Apple ha effettivamente mostrato e annunciato, cosi come riportato dalle fonti. Non auto-censurarti: se le fonti live lo riportano, e' materiale valido.
- Evita solo le pure speculazioni su cosa potrebbe arrivare in futuro: attieniti a cio che e' GIA stato annunciato durante l'evento.
- Cita 2-3 fonti con URL diretti reali presi dalla ricerca. Almeno UNA fonte deve essere ufficiale Apple (apple.com/newsroom o developer.apple.com): senza fonte ufficiale l'articolo non viene pubblicato ma messo in revisione manuale.
- Massimo {MAX_NEW} item per run, dando priorita agli annunci piu importanti. Se davvero non trovi nulla di nuovo oltre ai gia coperti, restituisci lista vuota.
- Tono Biolatti: prosa lucida, leggermente critica, niente sicofantia, niente "rivoluzionario/game-changer". Spiega COSA cambia e PERCHE conta.
- Niente emoji nel contenuto.
- TIPOGRAFIA ITALIANA con accenti UTF-8 corretti (e/E con accento grave o acuto, piu, perche, poiche, gia, sara, citta, qualita, ecc.) e apostrofo solo per elisioni (l'app, dell'utente, c'e).

SCHEMA DI OGNI ITEM
- slug: kebab-case univoco e descrittivo (es. "ios-27-nuova-schermata-blocco")
- macroArea: ESATTAMENTE uno tra: {", ".join(sorted(VALID_MACRO))}
- tags: 1-3 valori SOLO tra: {", ".join(sorted(VALID_TAGS))}
- category: nome leggibile italiano dell'area
- titleIt / titleEn: titolo (max ~80 caratteri)
- excerptIt / excerptEn: 1-2 frasi di sintesi
- bodyIt / bodyEn: Markdown semplice (## per sottotitoli, paragrafi separati da doppia newline). 2-4 paragrafi. Fonti citate per nome nel testo.
- sources: lista di {{"title": "Nome fonte", "url": "URL diretto reale"}} (2-3 elementi)

OUTPUT
Dopo aver cercato, termina la risposta con UN SOLO blocco di codice json contenente esattamente:
```json
{{"newItems": [ ... ]}}
```
Nessun altro testo dopo il blocco. Se non ci sono novita: {{"newItems": []}}."""


def call_anthropic(prompt, api_key):
    payload = {
        "model": MODEL,
        "max_tokens": 16000,
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": MAX_SEARCHES}],
        "messages": [{"role": "user", "content": prompt}],
    }
    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "x-api-key": api_key,
            "anthropic-version": API_VERSION,
            "content-type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        fail(f"HTTP {e.code} dall'API Anthropic: {detail}")
    except Exception as e:  # noqa
        fail(f"Chiamata API fallita: {e}")


def extract_text(resp):
    parts = []
    for block in resp.get("content", []):
        if block.get("type") == "text":
            parts.append(block.get("text", ""))
    return "\n".join(parts)


class ParseError(ValueError):
    """La risposta del modello non contiene un JSON {"newItems": [...]} valido."""


def parse_new_items(text):
    """Estrae la lista newItems. Solleva ParseError se la risposta non si interpreta
    (nessun blocco JSON, JSON malformato, newItems assente o non lista).
    Una lista vuota e un risultato VALIDO (nessuna novita)."""
    # Prendi l'ultimo blocco ```json ... ``` o, in mancanza, l'ultimo oggetto {...}.
    blocks = re.findall(r"```json\s*(.*?)\s*```", text or "", re.DOTALL)
    candidate = blocks[-1] if blocks else None
    if candidate is None:
        m = re.search(r'\{[^{}]*"newItems"[\s\S]*\}\s*$', text or "")
        candidate = m.group(0) if m else None
    if candidate is None:
        raise ParseError("nessun blocco JSON con newItems nella risposta")
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError as e:
        raise ParseError(f"JSON malformato: {e}")
    items = obj.get("newItems") if isinstance(obj, dict) else None
    if not isinstance(items, list):
        raise ParseError("campo newItems assente o non e una lista")
    return items


REQUIRED = {"slug", "macroArea", "tags", "titleIt", "titleEn",
            "excerptIt", "excerptEn", "bodyIt", "bodyEn", "sources"}


_STOP = {"il", "lo", "la", "i", "gli", "le", "un", "una", "uno", "di", "del", "della",
         "dei", "delle", "e", "è", "a", "al", "alla", "in", "nel", "nella", "per", "con",
         "su", "da", "che", "non", "the", "of", "and", "to", "for", "on", "with", "wwdc",
         "2026", "apple"}


def normalize_title(title):
    t = unicodedata.normalize("NFD", (title or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return " ".join(t.split())


def _tokens(norm):
    return {w for w in norm.split() if w not in _STOP and len(w) > 1}


def title_similarity(a, b):
    """(ratio difflib, jaccard token) tra due titoli normalizzati."""
    na, nb = normalize_title(a), normalize_title(b)
    if not na or not nb:
        return 0.0, 0.0
    ratio = difflib.SequenceMatcher(None, na, nb).ratio()
    ta, tb = _tokens(na), _tokens(nb)
    jac = len(ta & tb) / len(ta | tb) if (ta | tb) else 0.0
    return ratio, jac


def is_duplicate_title(title, existing_titles):
    for t in existing_titles:
        ratio, jac = title_similarity(title, t)
        if ratio > TITLE_SIM_RATIO or jac >= TITLE_SIM_JACCARD:
            return t
    return None


def _domain(url):
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _domain_in(host, domains):
    return any(host == d or host.endswith("." + d) for d in domains)


def is_official(url):
    host = _domain(url)
    return _domain_in(host, OFFICIAL_DOMAINS)


def validate(item, existing_slugs, existing_titles=()):
    """Restituisce (item, stato, motivo) con stato in:
       'ok'      -> pubblicabile
       'review'  -> valido ma senza fonte ufficiale Apple: va in coda di revisione
       'reject'  -> scartato (schema, duplicato, fonti non ammesse)"""
    if not isinstance(item, dict) or not REQUIRED.issubset(item):
        return None, "reject", "campi obbligatori mancanti"
    if item["slug"] in existing_slugs:
        return None, "reject", f"slug duplicato: {item['slug']}"
    if item["macroArea"] not in VALID_MACRO:
        return None, "reject", f"macroArea non valida: {item['macroArea']}"
    # Accenti italiani: correzione deterministica dei campi *It (mai slug/URL/campi En).
    acc = {}
    fix_item_it_fields(item, acc)
    if acc:
        log(f"  [accenti] {item['slug']}: {sum(acc.values())} correzioni")
    dup = (is_duplicate_title(item["titleIt"], existing_titles)
           or is_duplicate_title(item["titleEn"], existing_titles))
    if dup:
        return None, "reject", f"titolo troppo simile a: {dup}"
    tags = [t for t in item.get("tags", []) if t in VALID_TAGS][:3]
    if not tags:
        tags = ["intelligenza-artificiale"]
    item["tags"] = tags
    src = [s for s in item.get("sources", [])
           if isinstance(s, dict) and str(s.get("url", "")).startswith("http")
           and _domain_in(_domain(s["url"]), ALLOWED_DOMAINS)]
    if not src:
        return None, "reject", "nessuna fonte da un dominio ammesso"
    # porta in testa la fonte ufficiale, poi tronca a 3
    src.sort(key=lambda s: 0 if is_official(s["url"]) else 1)
    item["sources"] = src[:3]
    item.setdefault("category", item["macroArea"])
    item["publishedAt"] = datetime.now(TZ).isoformat()
    if not any(is_official(s["url"]) for s in item["sources"]):
        item["status"] = "da verificare"
        return item, "review", "nessuna fonte ufficiale Apple"
    return item, "ok", ""


def queue_for_review(items, path=None):
    """Accoda in data/review_queue.json (file escluso dal deploy Vercel)."""
    path = path or REVIEW_FILE
    try:
        with open(path, encoding="utf-8") as f:
            queue = json.load(f)
        if not isinstance(queue, list):
            queue = []
    except (FileNotFoundError, json.JSONDecodeError):
        queue = []
    queue.extend(items)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(queue, f, ensure_ascii=False, indent=2)


def main():
    # 1. Finestra evento PRIMA della chiave API: fuori finestra si esce puliti.
    data = load_data()
    if not within_window(data):
        log("Finestra WWDC 2026 chiusa: nessun aggiornamento.")
        print("SUMMARY::0::finestra chiusa", flush=True)
        return

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        fail("ANTHROPIC_API_KEY mancante", code=1)

    existing = {it["slug"] for it in data.get("items", [])}
    existing_titles = []
    for it in data.get("items", []):
        existing_titles += [it.get("titleIt", ""), it.get("titleEn", "")]
    log(f"Slug gia presenti: {len(existing)}")

    resp = call_anthropic(build_prompt(recent_titles(data)), api_key)
    if not isinstance(resp, dict):
        fail("risposta API vuota o non valida")
    text = extract_text(resp)
    # --- DIAGNOSTICA: capire COSA produce il modello (stop_reason, lunghezza, coda) ---
    usage = resp.get("usage", {})
    log(f"[debug] stop_reason={resp.get('stop_reason')} | text_len={len(text)} | "
        f"json_blocks={text.count('```json')} | out_tokens={usage.get('output_tokens')} | "
        f"search_uses={(usage.get('server_tool_use') or {}).get('web_search_requests')}")
    log("[debug] CODA risposta (ultimi 600 char):\n" + (text[-600:] if text else "(testo vuoto)"))
    if resp.get("stop_reason") == "max_tokens":
        fail("risposta del modello troncata (stop_reason=max_tokens)")
    try:
        raw_items = parse_new_items(text)
    except ParseError as e:
        fail(f"risposta del modello non interpretabile: {e}")
    log(f"Item proposti dal modello: {len(raw_items)}")

    added, review = [], []
    for it in raw_items[:MAX_NEW]:
        v, status, why = validate(it, existing, existing_titles)
        if status == "reject":
            log(f"  - scartato: {why}")
            continue
        existing.add(v["slug"])
        existing_titles += [v["titleIt"], v["titleEn"]]
        if status == "review":
            log(f"  ? in revisione ({why}): {v['titleIt']}")
            review.append(v)
        else:
            added.append(v)

    if review:
        queue_for_review(review)
        log(f"{len(review)} item messi in data/review_queue.json (non pubblicati).")

    if not added:
        log("Nessuna notizia nuova valida. Nessun rebuild.")
        print("SUMMARY::0::nessuna novita", flush=True)
        return

    data["items"] = added + data.get("items", [])
    data["lastUpdate"] = datetime.now(TZ).isoformat()
    save_data(data)
    log(f"Aggiunti {len(added)} item. Rigenero il sito...")

    r = subprocess.run([sys.executable, BUILD], cwd=BASE_DIR,
                       capture_output=True, text=True)
    if r.returncode != 0:
        fail(f"build.py fallito: {r.stderr[-500:]}")
    log(r.stdout.strip().splitlines()[-1] if r.stdout.strip() else "build ok")

    # Dati per il canale Telegram: un oggetto per articolo (titolo, estratto, link pubblico).
    notify = [
        {"title": it["titleIt"], "excerpt": it.get("excerptIt", ""),
         "url": f"{SITE_URL}/{it['slug']}.html"}
        for it in added
    ]
    with open(NOTIFY_FILE, "w", encoding="utf-8") as f:
        json.dump(notify, f, ensure_ascii=False)

    titles = " | ".join(it["titleIt"] for it in added)
    for it in added:
        log(f"  + {it['titleIt']}  [{it['macroArea']}]")
    print(f"SUMMARY::{len(added)}::{titles}", flush=True)


if __name__ == "__main__":
    main()
