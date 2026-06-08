#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
update_news.py — aggiornamento autonomo del sito Apple WWDC 2026.

Porta la logica del vecchio task Cowork (SKILL.md) in uno script autosufficiente
pensato per girare su GitHub Actions, senza Mac acceso. A ogni run:

  1. legge data/news.json e raccoglie gli slug gia pubblicati;
  2. controlla la finestra evento (esce se WWDC e finito);
  3. chiama l'API Anthropic con il tool web_search (lato server) per trovare
     SOLO annunci nuovi, scritti in italiano e inglese con i paletti editoriali
     di Biolatti;
  4. deduplica per slug, aggiunge gli item in testa, aggiorna lastUpdate;
  5. rigenera il sito statico con build.py.

Output su stdout in forma leggibile e una riga finale machine-readable
"SUMMARY::<n>::<titoli separati da ' | '>" usata dal workflow per la notifica.

Variabili d'ambiente:
  ANTHROPIC_API_KEY  (obbligatoria)
  WWDC_MODEL         (opzionale, default claude-sonnet-4-6)
  WWDC_MAX_NEW       (opzionale, default 8 — cap di item per run)
  WWDC_FORCE         (opzionale, "1" per ignorare il controllo finestra)
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "news.json")
BUILD = os.path.join(BASE_DIR, "build.py")

API_URL = "https://api.anthropic.com/v1/messages"
API_VERSION = "2023-06-01"
MODEL = os.environ.get("WWDC_MODEL") or "claude-sonnet-4-6"
MAX_NEW = int(os.environ.get("WWDC_MAX_NEW") or "8")
SITE_URL = "https://wwdc2026.biolatti.it"
NOTIFY_FILE = os.path.join(BASE_DIR, "notify_items.json")
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


def build_prompt(existing_slugs):
    slugs_str = ", ".join(sorted(existing_slugs)) if existing_slugs else "(nessuno: e il primo run)"
    now_str = datetime.now(TZ).strftime("%d/%m/%Y %H:%M")
    return f"""Sei Kairos, l'AI di Daniele Biolatti. Stai aggiornando in autonomia il sito wwdc2026.biolatti.it, copertura italiana indipendente dell'Apple WWDC 2026 (8-12 giugno 2026).

CONTESTO TEMPORALE — LEGGI CON ATTENZIONE
Adesso sono le {now_str} (ora italiana). L'Apple WWDC 2026 E' IN CORSO PROPRIO IN QUESTO MOMENTO: il keynote di apertura e' iniziato l'8 giugno alle 19:00 ora italiana. Apple sta gia annunciando dal vivo iOS 27, iPadOS 27, macOS 27, watchOS 27, tvOS 27, visionOS 27, il nuovo Siri, le funzioni di Apple Intelligence e molto altro. NON e' un evento futuro o ipotetico: sta succedendo ORA e ci sono gia decine di annunci concreti gia fatti.

COMPITO
Usa la ricerca web (live blog e articoli di MacRumors, 9to5Mac, The Verge, Engadget, TechRadar, AppleInsider, Macworld, Apple Newsroom) per raccogliere gli annunci CONCRETI gia fatti da Apple durante il keynote e le sessioni in corso. Ogni singola novita annunciata (una funzione o un prodotto) diventa un articolo. Restituisci SOLO annunci NUOVI non gia coperti.

GIA COPERTI (non ripetere, ne come slug ne come contenuto):
{slugs_str}

REGOLE — IMPORTANTE
- Un annuncio FATTO da Apple sul palco e riportato dalla copertura live E' un fatto confermato, NON un rumor. I "rumor" sono solo le ipotesi PRIMA dell'evento; ora l'evento e' iniziato, quindi raccogli cio che Apple ha effettivamente mostrato e annunciato, cosi come riportato dalle fonti. Non auto-censurarti: se le fonti live lo riportano, e' materiale valido.
- Evita solo le pure speculazioni su cosa potrebbe arrivare in futuro: attieniti a cio che e' GIA stato annunciato durante l'evento.
- Cita 2-3 fonti con URL diretti reali presi dalla ricerca.
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
        "max_tokens": 8000,
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 6}],
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


def parse_new_items(text):
    # Prendi l'ultimo blocco ```json ... ``` o, in mancanza, l'ultimo oggetto {...}.
    blocks = re.findall(r"```json\s*(.*?)\s*```", text, re.DOTALL)
    candidate = blocks[-1] if blocks else None
    if candidate is None:
        m = re.search(r'\{[^{}]*"newItems"[\s\S]*\}\s*$', text)
        candidate = m.group(0) if m else None
    if candidate is None:
        return []
    try:
        obj = json.loads(candidate)
    except json.JSONDecodeError:
        return []
    items = obj.get("newItems", [])
    return items if isinstance(items, list) else []


REQUIRED = {"slug", "macroArea", "tags", "titleIt", "titleEn",
            "excerptIt", "excerptEn", "bodyIt", "bodyEn", "sources"}


def validate(item, existing_slugs):
    if not REQUIRED.issubset(item):
        return None
    if item["slug"] in existing_slugs:
        return None
    if item["macroArea"] not in VALID_MACRO:
        return None
    tags = [t for t in item.get("tags", []) if t in VALID_TAGS][:3]
    if not tags:
        tags = ["intelligenza-artificiale"]
    item["tags"] = tags
    src = [s for s in item.get("sources", []) if s.get("url", "").startswith("http")]
    if not src:
        return None
    item["sources"] = src[:3]
    item.setdefault("category", item["macroArea"])
    item["publishedAt"] = datetime.now(TZ).isoformat()
    return item


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        fail("ANTHROPIC_API_KEY mancante", code=1)

    data = load_data()
    if not within_window(data):
        log("Finestra WWDC 2026 chiusa: nessun aggiornamento.")
        print("SUMMARY::0::finestra chiusa", flush=True)
        return

    existing = {it["slug"] for it in data.get("items", [])}
    log(f"Slug gia presenti: {len(existing)}")

    resp = call_anthropic(build_prompt(existing), api_key)
    text = extract_text(resp)
    raw_items = parse_new_items(text)
    log(f"Item proposti dal modello: {len(raw_items)}")

    added = []
    for it in raw_items[:MAX_NEW]:
        v = validate(it, existing)
        if v:
            added.append(v)
            existing.add(v["slug"])

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
