# -*- coding: utf-8 -*-
"""
accenti.py — correzione deterministica degli accenti nei testi ITALIANI.

Usato da:
  - fix una tantum di data/news.json (campi *It);
  - update_news.py, dentro validate(), per ogni nuovo articolo generato.

Regole (solo sostituzioni sicure, a parola intera, maiuscola iniziale preservata):
  1. accento acuto finale su a/i/o/u  -> grave  (piú->più, giá->già, cosí->così)
  2. "é"/"É" isolata (verbo essere)  -> "è"/"È"; "-ché", "né", "sé" restano acute
  3. apostrofo usato come accento     -> accento (e'->è, piu'->più, sara'->sarà,
                                          novita'->novità, c'e'->c'è)
  4. parole note scritte senza accento -> accentate (piu->più, perche->perché,
                                          gia->già, puo->può, novita->novità ...)
Le parole ambigue (facilita, disabilita, unita, meta, lancio, e, se, ne, da, la)
NON vengono toccate: vanno riviste a mano.
"""
import re

# Eccezioni: parole straniere/nomi propri con accento acuto finale legittimo.
KEEP_ACUTE = {"Guaraní", "guaraní", "café", "Café", "Pokémon", "Thórsmörk"}

# Parole con -é finale da correggere in grave (oltre alla "é" isolata).
E_GRAVE = {"cioé": "cioè", "caffé": "caffè", "ahimé": "ahimè", "pié": "piè"}

# Refusi espliciti di accento interno.
EXPLICIT = {"agéntico": "agentico", "agéntica": "agentica",
            "agéntici": "agentici", "agéntiche": "agentiche"}

# Parole italiane che, scritte senza accento, sono sempre errori.
_ITA = """capacita novita possibilita qualita funzionalita modalita identita continuita
discontinuita accessibilita espressivita connettivita opacita velocita necessita
visibilita leggibilita profondita disponibilita utilita compatibilita incompatibilita
quantita interoperabilita produttivita difficolta priorita mobilita solidita attivita
responsabilita densita uniformita stabilita complessita comunita comodita affidabilita
ambiguita prossimita multimodalita flessibilita creativita autorita citta realta verita
liberta societa universita intensita scalabilita fattibilita estensibilita esclusivita
conformita integrita personalita specificita semplicita tonalita criticita sostenibilita
usabilita varieta pubblicita maturita opportunita eta granularita tracciabilita
riservatezza_placeholder""".split()
_ITA = [w for w in _ITA if not w.endswith("_placeholder")]

_FUTURI = """potra dovra avra fara verra dara andra sapra vorra ricevera trovera arrivera
consentira includera verifichera rivelera richiedera diventera continuera seguira
funzionera distinguera valutera permettera offrira supportera sostituira introdurra
dipendera sopravvivera fermera cambiera portera mostrera usera integrera aggiungera
rimarra resta_placeholder""".split()
_FUTURI = [w for w in _FUTURI if not w.endswith("_placeholder")]

UNACCENTED = {
    "piu": "più", "gia": "già", "puo": "può", "cio": "ciò", "pero": "però",
    "cosi": "così", "perche": "perché", "poiche": "poiché", "affinche": "affinché",
    "benche": "benché", "nonche": "nonché", "finche": "finché", "anziche": "anziché",
    "sicche": "sicché", "cosicche": "cosicché", "cioe": "cioè",
    "lunedi": "lunedì", "martedi": "martedì", "mercoledi": "mercoledì",
    "giovedi": "giovedì", "venerdi": "venerdì",
}
for _w in _ITA:
    UNACCENTED[_w] = _w[:-1] + "à"
for _w in _FUTURI:
    UNACCENTED[_w] = _w[:-1] + "à"
# "sara" solo minuscolo (Sara può essere un nome proprio).
UNACCENTED_LOWER_ONLY = {"sara": "sarà"}

_GRAVE = {"á": "à", "í": "ì", "ó": "ò", "ú": "ù", "Á": "À", "Í": "Ì", "Ó": "Ò", "Ú": "Ù"}

_WORD = r"[A-Za-zÀ-ÖØ-öø-ÿ]"


def _cap(src, dst):
    return dst[0].upper() + dst[1:] if src[:1].isupper() else dst


# Segmenti da NON toccare: URL, destinazioni dei link Markdown, `codice`,
# slug (parole minuscole unite da almeno due trattini) e tag HTML.
_PROTECT = re.compile(
    r"https?://[^\s)\]\"'<>]+"
    r"|\]\([^)]*\)"
    r"|`[^`]*`"
    r"|<[^>]+>"
    r"|\b[a-z0-9]+(?:-[a-z0-9]+){2,}\b"
)


def fix_accents(text, counter=None):
    """Restituisce il testo corretto. Se counter (dict) è passato, conta le regole.
    URL, codice inline, destinazioni dei link, tag HTML e slug restano invariati."""
    if not text or not isinstance(text, str):
        return text
    out, pos = [], 0
    for m in _PROTECT.finditer(text):
        out.append(_fix_plain(text[pos:m.start()], counter))
        out.append(m.group(0))
        pos = m.end()
    out.append(_fix_plain(text[pos:], counter))
    return "".join(out)


def _fix_plain(text, counter=None):
    if not text:
        return text

    def bump(key):
        if counter is not None:
            counter[key] = counter.get(key, 0) + 1

    # 3a. c'e' / c'e  -> c'è
    def _ce(m):
        bump("c'e -> c'è")
        return m.group(1) + "'è"
    text = re.sub(r"(?<!" + _WORD + r")([cC])'e'?(?!" + _WORD + r"|')", _ce, text)

    # 3b. e' / E' isolate -> è / È
    def _e_apo(m):
        bump("e' -> è")
        return "È" if m.group(1) == "E" else "è"
    text = re.sub(r"(?<![\w'])([eE])'(?!" + _WORD + r")", _e_apo, text)

    # 3c. parola' con apostrofo-accento
    def _word_apo(m):
        prev, w = m.group(1), m.group(2)
        low = w.lower()
        if low in UNACCENTED or (w in UNACCENTED_LOWER_ONLY):
            dst = UNACCENTED.get(low) or UNACCENTED_LOWER_ONLY[w]
        elif prev != "'" and re.search(r"(ita|[aei]ra)$", low) and len(low) > 4:
            # generico (-ità, futuri in -rà) solo se la parola non è tra apici
            dst = low[:-1] + "à"
        else:
            return m.group(0)
        bump(f"{low}' -> {dst}")
        return prev + _cap(w, dst)
    text = re.sub(r"(^|[^A-Za-zÀ-ÖØ-öø-ÿ])(" + _WORD + r"+)'(?!" + _WORD + r")", _word_apo, text)

    # 1-2. accenti acuti/errati sulle parole
    def _word(m):
        w = m.group(0)
        if w in KEEP_ACUTE:
            return w
        if w in EXPLICIT:
            bump(f"{w} -> {EXPLICIT[w]}")
            return EXPLICIT[w]
        if w in ("é", "É"):
            dst = "è" if w == "é" else "È"
            bump("é -> è")
            return dst
        low = w.lower()
        if low in E_GRAVE:
            bump(f"{low} -> {E_GRAVE[low]}")
            return _cap(w, E_GRAVE[low])
        if w[-1] in _GRAVE:
            dst = w[:-1] + _GRAVE[w[-1]]
            bump(f"{low} -> {dst.lower()}")
            return dst
        # 4. parole note senza accento (solo minuscolo o Iniziale maiuscola, mai TUTTO MAIUSCOLO)
        if w == low or (w[0].isupper() and w[1:] == w[1:].lower()):
            if low in UNACCENTED:
                bump(f"{low} -> {UNACCENTED[low]}")
                return _cap(w, UNACCENTED[low])
            if w in UNACCENTED_LOWER_ONLY:
                bump(f"{w} -> {UNACCENTED_LOWER_ONLY[w]}")
                return UNACCENTED_LOWER_ONLY[w]
        return w
    text = re.sub(_WORD + r"+", _word, text)
    return text


def has_accent_errors(text):
    """True se fix_accents cambierebbe il testo."""
    return isinstance(text, str) and fix_accents(text) != text


def fix_item_it_fields(item, counter=None):
    """Corregge in place i campi italiani di un articolo (chiavi che finiscono in 'It' + category)."""
    changed = 0
    for k in list(item.keys()):
        if (k.endswith("It") or k == "category") and isinstance(item[k], str):
            new = fix_accents(item[k], counter)
            if new != item[k]:
                item[k] = new
                changed += 1
    return changed
