#!/usr/bin/env python3
"""
Apple WWDC 2026 — Static site generator for wwdc2026.biolatti.it
Reads data/news.json and generates the full site:
  - index.html + en/index.html       (new structured home with featured + macro-areas + tags)
  - <slug>.html + en/<slug>.html     (one article page per news item)
  - macro-aree/<slug>.html (IT) + en/macro-areas/<slug>.html (EN)   (9 macro-area hub pages)
  - tag/<slug>.html (IT) + en/tag/<slug>.html (EN)                  (8 tag pages)
  - top-10.html + en/top-10.html     (ranking page)
  - analisi.html + en/analysis.html  (pillar SEO analysis page)
  - timeline.html + en/timeline.html (full chronological archive)
  - sitemap.xml

Build is idempotent: rebuilds cleanly from news.json + intros_data.py + analisi/01-riepilogo-tematico.md
"""

import json
import os
import re
import sys
from datetime import datetime, timezone

from intros_data import MACRO_AREA_INTROS, TAG_INTROS

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "data", "news.json")
ANALISI_MD = os.path.join(BASE_DIR, "analisi", "01-riepilogo-tematico.md")
SITE_URL = "https://wwdc2026.biolatti.it"
GA4_ID = "G-7X467EKS2K"

# Event identity (single source of truth for event-specific copy)
EVENT_NAME_IT = "Apple WWDC 2026"
EVENT_NAME_EN = "Apple WWDC 2026"
EVENT_VENDOR = "Apple"
EVENT_OFFICIAL_URL = "https://developer.apple.com/wwdc26/"


# Update reference shown in copy ("Informazioni relative al ... aggiornate al ...")
COVERAGE_END_DATE_IT = "12 giugno 2026"
COVERAGE_END_DATE_EN = "June 12, 2026"


# -----------------------------------------------------------------------------
# Macro-area hero illustrations (WebP, 1600x844, ~30-70 KB each)
# Located under assets/img/macroaree/<filename>.webp
# -----------------------------------------------------------------------------
MACROAREA_IMAGES = {
    "sistemi-operativi": "sistemi-operativi-ios-ipados-macos-wwdc-2026",
    "apple-intelligence": "apple-intelligence-siri-ai-wwdc-2026",
    "sviluppatori": "sviluppatori-xcode-swift-wwdc-2026",
    "design-interfacce": "design-interfacce-liquid-glass-wwdc-2026",
    "spatial-visionos": "spatial-visionos-wwdc-2026",
    "salute-benessere": "salute-benessere-watchos-wwdc-2026",
    "servizi-ecosistema": "servizi-ecosistema-icloud-continuity-wwdc-2026",
    "privacy-sicurezza": "privacy-sicurezza-wwdc-2026",
}

MACROAREA_ALT = {
    "sistemi-operativi": {
        "it": "Illustrazione a tratto: una figura cammina verso iPhone, iPad e Mac stilizzati collegati da un'onda sismografica, simbolo dell'aggiornamento congiunto dei sistemi operativi Apple.",
        "en": "Line illustration: a figure walks toward stylized iPhone, iPad and Mac shapes linked by a seismographic wave, symbolizing the joint update of Apple's operating systems.",
    },
    "apple-intelligence": {
        "it": "Illustrazione a tratto: un cerchio terracotta aperto attraversa una composizione di forme geometriche, a rappresentare l'intelligenza artificiale integrata in Apple Intelligence e Siri.",
        "en": "Line illustration: an open terracotta circle cuts through a composition of geometric shapes, representing the AI woven into Apple Intelligence and Siri.",
    },
    "sviluppatori": {
        "it": "Illustrazione a tratto: una figura tocca il nodo centrale di una rete di cerchi collegati da linee a molla, simbolo delle API e degli SDK per sviluppatori.",
        "en": "Line illustration: a figure touches the central node of a network of circles linked by spring-like lines, symbolizing developer APIs and SDKs.",
    },
    "design-interfacce": {
        "it": "Illustrazione a tratto: una figura osserva pannelli semitrasparenti sovrapposti attraversati da un arco terracotta, evocando gli strati del nuovo linguaggio di design Liquid Glass.",
        "en": "Line illustration: a figure looks at overlapping semi-transparent panels crossed by a terracotta arc, evoking the layers of the new Liquid Glass design language.",
    },
    "spatial-visionos": {
        "it": "Illustrazione a tratto: una figura in scala ridotta immersa in uno spazio profondo definito da linee sismografiche, a rappresentare lo spatial computing di visionOS.",
        "en": "Line illustration: a small-scale figure immersed in a deep space defined by seismographic lines, representing visionOS spatial computing.",
    },
    "salute-benessere": {
        "it": "Illustrazione a tratto: una linea pulsante come un elettrocardiogramma attraversa un orologio racchiuso da un cerchio terracotta aperto, simbolo di salute e benessere su watchOS.",
        "en": "Line illustration: a pulsing line like an electrocardiogram crosses a watch enclosed by an open terracotta circle, symbolizing health and wellbeing on watchOS.",
    },
    "servizi-ecosistema": {
        "it": "Illustrazione a tratto: forme collegate da linee oscillanti evocano la continuità tra dispositivi dell'ecosistema Apple, tra iCloud e Continuity.",
        "en": "Line illustration: shapes linked by oscillating lines evoke continuity across Apple ecosystem devices, from iCloud to Continuity.",
    },
    "privacy-sicurezza": {
        "it": "Illustrazione a tratto: un cerchio terracotta aperto protegge una forma centrale, simbolo della protezione dei dati e della sicurezza al centro del WWDC 2026.",
        "en": "Line illustration: an open terracotta circle shields a central shape, symbolizing data protection and security at the heart of WWDC 2026.",
    },
}

DEFAULT_OG_IMAGE_SLUG = "sistemi-operativi"


def macroarea_image_path(macroarea_slug, asset_pref="./"):
    """Relative URL to WebP hero for a macroarea (or None if missing)."""
    filename = MACROAREA_IMAGES.get(macroarea_slug)
    if not filename:
        return None
    return f"{asset_pref}assets/img/macroaree/{filename}.webp"


def macroarea_image_absolute(macroarea_slug):
    """Absolute URL (for og:image and schema)."""
    filename = MACROAREA_IMAGES.get(macroarea_slug)
    if not filename:
        return None
    return f"{SITE_URL}/assets/img/macroaree/{filename}.webp"


def macroarea_alt(macroarea_slug, lang):
    """Bilingual alt text for the macroarea image."""
    entry = MACROAREA_ALT.get(macroarea_slug, {})
    return entry.get(lang, "")


# -----------------------------------------------------------------------------
# Tag (argomento) hero illustrations (WebP, ~27-47 KB each)
# Located under assets/img/argomenti/<filename>.webp
# -----------------------------------------------------------------------------
TAG_IMAGES = {}

TAG_ALT = {}


def tag_image_path(tag_slug, asset_pref="./"):
    """Relative URL to WebP hero for a tag (or None if missing)."""
    filename = TAG_IMAGES.get(tag_slug)
    if not filename:
        return None
    return f"{asset_pref}assets/img/argomenti/{filename}.webp"


def tag_image_absolute(tag_slug):
    """Absolute URL (for og:image and schema)."""
    filename = TAG_IMAGES.get(tag_slug)
    if not filename:
        return None
    return f"{SITE_URL}/assets/img/argomenti/{filename}.webp"


def tag_alt(tag_slug, lang):
    """Bilingual alt text for the tag image."""
    entry = TAG_ALT.get(tag_slug, {})
    return entry.get(lang, "")


# -----------------------------------------------------------------------------
# UI labels (content comes from news.json)
# -----------------------------------------------------------------------------
LABELS = {
    "it": {
        "lang": "it",
        "locale": "it_IT",
        "site_name": "Apple WWDC 2026",
        "site_tagline": "Copertura italiana, a cura di Daniele Biolatti",
        "nav_home": "Home",
        "nav_aree": "Aree tematiche",
        "nav_argomenti": "Argomenti",
        "nav_macroaree": "Aree tematiche",
        "nav_top10": "Top 10",
        "nav_analisi": "Analisi",
        "nav_timeline": "Archivio",
        "nav_about": "Chi cura",
        "switch_lang_label": "EN",
        "hero_eyebrow": f"Informazioni relative al WWDC 2026 aggiornate al {COVERAGE_END_DATE_IT}",
        "hero_title": "Apple WWDC 2026: <em>264 annunci</em>, in italiano, organizzati per tema.",
        "hero_subtitle": "La conferenza per sviluppatori di Apple si è svolta dall'8 al 12 giugno 2026, con il keynote di apertura la sera dell'8. Su questa pagina trovi tutti gli annunci, ricostruiti in italiano, organizzati per area, con le fonti originali a portata di click.",
        "hero_meta_dates": "8-12 giugno 2026",
        "section_featured_eyebrow": "Gli annunci che pesano di piu",
        "section_featured_title": "Da dove iniziare",
        "section_featured_subtitle": "Quelli sotto i riflettori dei media e quelli meno raccontati ma strutturalmente importanti.",
        "section_macroareas_eyebrow": "Esplora per tema",
        "section_macroareas_title": "Cosa cambia, area per area",
        "section_macroareas_subtitle": "Le macro-aree per leggere l'evento dal punto di vista di chi usera questi strumenti nei prossimi mesi.",
        "section_tags_eyebrow": "Esplora per argomento trasversale",
        "section_tags_title": "Argomenti",
        "section_tags_subtitle": "I fili tematici che attraversano piu aree contemporaneamente.",
        "section_otherpages_eyebrow": "Approfondimenti",
        "section_otherpages_title": "Le pagine pillar",
        "section_otherpages_subtitle": "Sintesi, ranking e archivio cronologico completo.",
        "page_top10_title": "Gli annunci piu importanti dell'Apple WWDC 2026",
        "page_top10_subtitle": "La classifica ragionata in base a impatto strutturale, copertura mediatica e implicazioni a medio termine.",
        "page_analisi_title": "Apple WWDC 2026 — Analisi tematica completa",
        "page_analisi_subtitle": "Cosa e stato davvero il WWDC 2026: le narrazioni dominanti, la riclassificazione, cosa e mancato.",
        "page_timeline_title": "Tutti gli annunci in ordine cronologico",
        "page_timeline_subtitle": "L'archivio completo della copertura, dal keynote di apertura ai follow-up dei giorni successivi.",
        "page_macroareas_index_title": "Le aree tematiche dell'Apple WWDC 2026",
        "page_tags_index_title": "Tutti gli argomenti",
        "tag_intro_label": "Argomento",
        "macroarea_browse_others": "Esplora le altre aree",
        "tag_browse_others": "Esplora gli altri argomenti",
        "all_topics": "Tutti gli argomenti",
        "section_announcements_eyebrow": "Annunci",
        "section_announcements_title": "In questa area",
        "section_announcements_subtitle": "",
        "read_more": "Leggi",
        "read_full": "Leggi l'approfondimento",
        "back_to_home": "\u2190 Torna alla home",
        "back_to_macroarea": "\u2190 Torna all'area",
        "sources": "Fonti",
        "published": "Pubblicato",
        "category": "Area tematica",
        "tags": "Tag",
        "about_title": "Chi cura questa pagina",
        "about_body": "Questa copertura e curata da <a href=\"https://biolatti.it\">Daniele Biolatti</a>, consulente di product management, strategia digitale e psicologia delle risorse artificiali. Le notizie sono raccolte automaticamente e riscritte in italiano con il supporto di Kairos, l'AI personale di Daniele, durante l'evento. Ogni notizia riporta le fonti originali.",
        "footer_about": "Copertura indipendente, in italiano, dell'Apple WWDC 2026. A cura di Daniele Biolatti con il supporto di Kairos.",
        "footer_links_title": "Naviga",
        "footer_resources_title": "Risorse",
        "footer_main_site": "Sito principale",
        "footer_kairos": "Cos'e Kairos",
        "footer_io_official": "Sito ufficiale Apple WWDC",
        "footer_copy": "\u00a9 2026 Daniele Biolatti. Tutte le notizie restano di proprieta delle rispettive fonti.",
        "footer_note": f"Informazioni aggiornate al {COVERAGE_END_DATE_IT}. Nessuna affiliazione con Apple. Le fonti originali sono linkate in ogni articolo.",
        "breadcrumb_home": "WWDC 2026",
        "meta_description_home": "Copertura italiana dell'Apple WWDC 2026: gli annunci Apple su iOS, macOS, Apple Intelligence, Siri e visionOS, organizzati per area, con le fonti originali a portata di click.",
        "label_articles_count": "articoli",
        "label_article_count_singular": "articolo",
        "tag_pill_label": "Argomento",
        "media_buzz_label": "I piu discussi dai media",
        "underrated_label": "I sottovalutati ma strutturali",
    },
    "en": {
        "lang": "en",
        "locale": "en_US",
        "site_name": "Apple WWDC 2026",
        "site_tagline": "Italian coverage by Daniele Biolatti",
        "nav_home": "Home",
        "nav_aree": "Areas",
        "nav_argomenti": "Topics",
        "nav_macroaree": "Areas",
        "nav_top10": "Top 10",
        "nav_analisi": "Analysis",
        "nav_timeline": "Archive",
        "nav_about": "About",
        "switch_lang_label": "IT",
        "hero_eyebrow": f"WWDC 2026 coverage, updated as of {COVERAGE_END_DATE_EN}",
        "hero_title": "Apple WWDC 2026: <em>264 announcements</em>, organized by topic.",
        "hero_subtitle": "Apple's developer conference ran from June 8 to 12, 2026, with the opening keynote on the evening of June 8. On this page you'll find every announcement, rebuilt in English, organized by area, with original sources one click away.",
        "hero_meta_dates": "June 8-12, 2026",
        "section_featured_eyebrow": "The announcements that matter most",
        "section_featured_title": "Start here",
        "section_featured_subtitle": "The ones under the media spotlight and the ones less talked about but structurally important.",
        "section_macroareas_eyebrow": "Browse by topic",
        "section_macroareas_title": "What changes, area by area",
        "section_macroareas_subtitle": "Macro-areas to read the event from the point of view of those who'll use these tools in the coming months.",
        "section_tags_eyebrow": "Browse by cross-cutting theme",
        "section_tags_title": "Tags",
        "section_tags_subtitle": "Themes that cut across multiple areas at once.",
        "section_otherpages_eyebrow": "Deep reads",
        "section_otherpages_title": "Pillar pages",
        "section_otherpages_subtitle": "Synthesis, ranking, and full chronological archive.",
        "page_top10_title": "The most important announcements of Apple WWDC 2026",
        "page_top10_subtitle": "A reasoned ranking by structural impact, media coverage, and medium-term implications.",
        "page_analisi_title": "Apple WWDC 2026 — Full thematic analysis",
        "page_analisi_subtitle": "What WWDC 2026 really was: the dominant narratives, the reclassification, what was missing.",
        "page_timeline_title": "All announcements in chronological order",
        "page_timeline_subtitle": "The complete archive of the coverage, from the opening keynote to the later follow-ups.",
        "page_macroareas_index_title": "The macro-areas of Apple WWDC 2026",
        "page_tags_index_title": "All tags",
        "tag_intro_label": "Tag",
        "macroarea_browse_others": "Browse other areas",
        "tag_browse_others": "Browse other tags",
        "all_topics": "All topics",
        "section_announcements_eyebrow": "Articles",
        "section_announcements_title": "In this area",
        "section_announcements_subtitle": "",
        "read_more": "Read",
        "read_full": "Read the full story",
        "back_to_home": "\u2190 Back to home",
        "back_to_macroarea": "\u2190 Back to area",
        "sources": "Sources",
        "published": "Published",
        "category": "Topic area",
        "tags": "Tags",
        "about_title": "About this page",
        "about_body": "This coverage is curated by <a href=\"https://biolatti.it/en\">Daniele Biolatti</a>, consultant in product management, digital strategy, and the psychology of artificial resources. News is gathered automatically and rewritten in Italian with the support of Kairos, Daniele's personal AI, throughout the event. Every story links back to its original sources.",
        "footer_about": "Independent coverage of Apple WWDC 2026, in Italian. Curated by Daniele Biolatti with the support of Kairos.",
        "footer_links_title": "Navigate",
        "footer_resources_title": "Resources",
        "footer_main_site": "Main site",
        "footer_kairos": "About Kairos",
        "footer_io_official": "Official Apple WWDC site",
        "footer_copy": "\u00a9 2026 Daniele Biolatti. All news remains the property of its respective sources.",
        "footer_note": f"Information updated as of {COVERAGE_END_DATE_EN}. No affiliation with Apple. Original sources are linked in every article.",
        "breadcrumb_home": "WWDC 2026",
        "meta_description_home": "Italian coverage of Apple WWDC 2026: Apple announcements on iOS, macOS, Apple Intelligence, Siri, and visionOS, organized by area, with original sources one click away.",
        "label_articles_count": "articles",
        "label_article_count_singular": "article",
        "tag_pill_label": "Tag",
        "media_buzz_label": "The most discussed by media",
        "underrated_label": "The underrated but structural",
    },
}



# -----------------------------------------------------------------------------
# Layout path helpers
# -----------------------------------------------------------------------------
# Page types and their on-disk locations:
#
#   type        | IT path                          | EN path
#   index       | /index.html                      | /en/index.html
#   article     | /<slug>.html                     | /en/<slug>.html
#   macroarea   | /macro-aree/<slug>.html          | /en/macro-areas/<slug>.html
#   tag         | /tag/<slug>.html                 | /en/tag/<slug>.html
#   top10       | /top-10.html                     | /en/top-10.html
#   analisi     | /analisi.html                    | /en/analysis.html
#   timeline    | /timeline.html                   | /en/timeline.html

def asset_prefix(lang, page_type):
    """Relative path from this page to /assets/"""
    if lang == "it":
        if page_type in ("macroarea", "tag"):
            return "../"
        return ""
    # en
    if page_type in ("macroarea", "tag"):
        return "../../"
    return "../"


def home_path(lang, page_type):
    """Relative URL to lang home from this page."""
    if lang == "it":
        if page_type in ("macroarea", "tag"):
            return "../"
        return "./"
    # en
    if page_type in ("macroarea", "tag"):
        return "../"
    return "./"


def root_path(lang, page_type):
    """Relative URL to site root (IT home) from this page."""
    if lang == "it":
        return home_path(lang, page_type)
    # en
    if page_type in ("macroarea", "tag"):
        return "../../"
    return "../"


def macroarea_url(lang, ma_slug_it, ma_slug_en, current_lang, current_page_type):
    """Relative URL to a macroarea page, from the current page's perspective."""
    slug = ma_slug_it if lang == "it" else ma_slug_en
    if current_lang == "it":
        if current_page_type in ("macroarea", "tag"):
            base = "../" if lang == "it" else "../en/"
            subdir = "macro-aree/" if lang == "it" else "macro-areas/"
            return f"{base}{subdir}{slug}.html"
        # IT root pages
        base = "./" if lang == "it" else "en/"
        subdir = "macro-aree/" if lang == "it" else "macro-areas/"
        return f"{base}{subdir}{slug}.html"
    # current_lang == en
    if current_page_type in ("macroarea", "tag"):
        base = "../../" if lang == "it" else "../"
        subdir = "macro-aree/" if lang == "it" else "macro-areas/"
        return f"{base}{subdir}{slug}.html"
    # EN root pages
    base = "../" if lang == "it" else "./"
    subdir = "macro-aree/" if lang == "it" else "macro-areas/"
    return f"{base}{subdir}{slug}.html"


def tag_url(lang, tag_slug_it, tag_slug_en, current_lang, current_page_type):
    """Relative URL to a tag page."""
    slug = tag_slug_it if lang == "it" else tag_slug_en
    if current_lang == "it":
        if current_page_type in ("macroarea", "tag"):
            base = "../" if lang == "it" else "../en/"
            return f"{base}tag/{slug}.html"
        base = "./" if lang == "it" else "en/"
        return f"{base}tag/{slug}.html"
    # en
    if current_page_type in ("macroarea", "tag"):
        base = "../../" if lang == "it" else "../"
        return f"{base}tag/{slug}.html"
    base = "../" if lang == "it" else "./"
    return f"{base}tag/{slug}.html"


def article_url(lang, slug, current_lang, current_page_type):
    """Relative URL to an article."""
    if current_lang == "it":
        if current_page_type in ("macroarea", "tag"):
            base = "../" if lang == "it" else "../en/"
            return f"{base}{slug}.html"
        base = "./" if lang == "it" else "en/"
        return f"{base}{slug}.html"
    # en
    if current_page_type in ("macroarea", "tag"):
        base = "../../" if lang == "it" else "../"
        return f"{base}{slug}.html"
    base = "../" if lang == "it" else "./"
    return f"{base}{slug}.html"


def simple_page_url(lang, page_type, current_lang, current_page_type):
    """Relative URL to top10/analisi/timeline pages."""
    filename = {
        "top10": "top-10.html",
        "analisi": "analisi.html" if lang == "it" else "analysis.html",
        "timeline": "timeline.html",
    }[page_type]
    if current_lang == "it":
        if current_page_type in ("macroarea", "tag"):
            base = "../" if lang == "it" else "../en/"
            return f"{base}{filename}"
        base = "./" if lang == "it" else "en/"
        return f"{base}{filename}"
    # en
    if current_page_type in ("macroarea", "tag"):
        base = "../../" if lang == "it" else "../"
        return f"{base}{filename}"
    base = "../" if lang == "it" else "./"
    return f"{base}{filename}"


def home_url(lang, current_lang, current_page_type):
    """Relative URL to the home of the given lang."""
    if current_lang == "it":
        if current_page_type in ("macroarea", "tag"):
            return "../" if lang == "it" else "../en/"
        return "./" if lang == "it" else "en/"
    # en
    if current_page_type in ("macroarea", "tag"):
        return "../../" if lang == "it" else "../"
    return "../" if lang == "it" else "./"


# Canonical URLs (absolute)
def canonical_for(lang, page_type, slug=None, slug_en=None):
    if page_type == "index":
        return f"{SITE_URL}/" if lang == "it" else f"{SITE_URL}/en/"
    if page_type == "article":
        return f"{SITE_URL}/{slug}.html" if lang == "it" else f"{SITE_URL}/en/{slug}.html"
    if page_type == "macroarea":
        if lang == "it":
            return f"{SITE_URL}/macro-aree/{slug}.html"
        return f"{SITE_URL}/en/macro-areas/{slug_en or slug}.html"
    if page_type == "tag":
        if lang == "it":
            return f"{SITE_URL}/tag/{slug}.html"
        return f"{SITE_URL}/en/tag/{slug_en or slug}.html"
    if page_type == "top10":
        return f"{SITE_URL}/top-10.html" if lang == "it" else f"{SITE_URL}/en/top-10.html"
    if page_type == "analisi":
        return f"{SITE_URL}/analisi.html" if lang == "it" else f"{SITE_URL}/en/analysis.html"
    if page_type == "timeline":
        return f"{SITE_URL}/timeline.html" if lang == "it" else f"{SITE_URL}/en/timeline.html"
    return f"{SITE_URL}/"


# -----------------------------------------------------------------------------
# Common HTML pieces
# -----------------------------------------------------------------------------

def ga_snippet():
    return f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
<script>
  window.dataLayer = window.dataLayer || [];
  function gtag(){{dataLayer.push(arguments);}}
  gtag('js', new Date());
  gtag('config', '{GA4_ID}');
</script>"""


def site_header(lang, current_page_type, other_lang_path, data):
    """Render the sticky site header with Aree + Argomenti dropdowns."""
    L = LABELS[lang]
    home_href = home_path(lang, current_page_type)
    asset_pref = asset_prefix(lang, current_page_type)
    # Switcher lingua a posizioni FISSE: IT sempre a sinistra, EN sempre a destra.
    # L'attiva e' evidenziata (class active, href #); l'altra punta all'altra lingua.
    it_is_active = (lang == "it")
    it_link = '<a href="#" class="active">IT</a>' if it_is_active else f'<a href="{other_lang_path}">IT</a>'
    en_link = f'<a href="{other_lang_path}">EN</a>' if it_is_active else '<a href="#" class="active">EN</a>'

    # Build macroarea dropdown items
    aree_items = []
    for m in data.get("macroAreas", []):
        href = macroarea_url(lang, m["slug"], m["slugEn"], lang, current_page_type)
        label = m["labelIt" if lang == "it" else "labelEn"]
        aree_items.append(f'<a href="{href}">{label}</a>')
    aree_dropdown = "\n            ".join(aree_items)

    # Build argomenti (tags) dropdown items
    arg_items = []
    for t in data.get("tagsVocabulary", []):
        href = tag_url(lang, t["slug"], t["slugEn"], lang, current_page_type)
        label = t["labelIt" if lang == "it" else "labelEn"]
        arg_items.append(f'<a href="{href}">{label}</a>')
    arg_dropdown = "\n            ".join(arg_items)

    return f"""
  <header class="site-header">
    <div class="site-header__inner">
      <a href="{home_href}" class="site-logo">
        <svg class="site-logo__mark" viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
          <rect width="64" height="64" rx="12" fill="#FFC300"/>
          <circle cx="32" cy="32" r="20" fill="none" stroke="#E96D50" stroke-width="4" stroke-linecap="round" stroke-dasharray="100 30"/>
          <path d="M 10 38 Q 18 28 26 38 T 42 38 T 56 38" fill="none" stroke="#00796B" stroke-width="3" stroke-linecap="round"/>
        </svg>
        <span class="site-logo__name">{L["site_name"]}<small>biolatti.it</small></span>
      </a>
      <nav class="site-nav">
        <a href="{home_href}" {'class="active"' if current_page_type == "index" else ""}>{L["nav_home"]}</a>
        <details class="nav-dropdown">
          <summary>{L["nav_aree"]}</summary>
          <div class="nav-dropdown__menu">
            {aree_dropdown}
          </div>
        </details>
        <details class="nav-dropdown">
          <summary>{L["nav_argomenti"]}</summary>
          <div class="nav-dropdown__menu">
            {arg_dropdown}
          </div>
        </details>
        <a href="{simple_page_url(lang, 'analisi', lang, current_page_type)}" {'class="active"' if current_page_type == "analisi" else ""}>{L["nav_analisi"]}</a>
        <a href="{simple_page_url(lang, 'top10', lang, current_page_type)}" {'class="active"' if current_page_type == "top10" else ""}>{L["nav_top10"]}</a>
        <a href="{simple_page_url(lang, 'timeline', lang, current_page_type)}" {'class="active"' if current_page_type == "timeline" else ""}>{L["nav_timeline"]}</a>
        <div class="lang-switch">
          {it_link}
          <span class="sep">/</span>
          {en_link}
        </div>
      </nav>
    </div>
  </header>
"""


def site_footer(lang, current_page_type):
    L = LABELS[lang]
    home_href = home_path(lang, current_page_type)
    main_site = "https://biolatti.it/en" if lang == "en" else "https://biolatti.it"
    return f"""
  <footer class="site-footer">
    <div class="site-footer__inner">
      <div>
        <h4>{L["site_name"]}</h4>
        <p>{L["footer_about"]}</p>
      </div>
      <div>
        <h4>{L["footer_links_title"]}</h4>
        <ul>
          <li><a href="{home_href}">{L["nav_home"]}</a></li>
          <li><a href="{simple_page_url(lang, 'analisi', lang, current_page_type)}">{L["nav_analisi"]}</a></li>
          <li><a href="{simple_page_url(lang, 'top10', lang, current_page_type)}">{L["nav_top10"]}</a></li>
          <li><a href="{simple_page_url(lang, 'timeline', lang, current_page_type)}">{L["nav_timeline"]}</a></li>
        </ul>
      </div>
      <div>
        <h4>{L["footer_resources_title"]}</h4>
        <ul>
          <li><a href="{main_site}">{L["footer_main_site"]}</a></li>
          <li><a href="{EVENT_OFFICIAL_URL}">{L["footer_io_official"]}</a></li>
        </ul>
      </div>
    </div>
    <div class="site-footer__bottom">
      <span>{L["footer_copy"]}</span>
      <span>{L["footer_note"]}</span>
    </div>
  </footer>
"""


def render_head(lang, current_page_type, title, description, canonical, hreflang_pair, og_image=None):
    """
    hreflang_pair: dict {'it': absolute_url_it, 'en': absolute_url_en}
    """
    L = LABELS[lang]
    og_image_html = ""
    if og_image:
        og_image_html = f'  <meta property="og:image" content="{og_image}">\n'
    asset_pref = asset_prefix(lang, current_page_type)
    return f"""<!doctype html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <meta name="description" content="{description}">
  <meta name="author" content="Daniele Biolatti">
  <link rel="canonical" href="{canonical}">
  <link rel="alternate" hreflang="it" href="{hreflang_pair['it']}">
  <link rel="alternate" hreflang="en" href="{hreflang_pair['en']}">
  <link rel="alternate" hreflang="x-default" href="{hreflang_pair['it']}">
  <meta property="og:title" content="{title}">
  <meta property="og:description" content="{description}">
  <meta property="og:url" content="{canonical}">
  <meta property="og:type" content="article">
  <meta property="og:locale" content="{L['locale']}">
{og_image_html}  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{title}">
  <meta name="twitter:description" content="{description}">
  <link rel="icon" type="image/svg+xml" href="{asset_pref}assets/img/favicon.svg">
  <link rel="stylesheet" href="{asset_pref}assets/css/style.css?v=20260522b">
  {ga_snippet()}
</head>
<body>
"""


def safe_description(text, max_len=160):
    """Smart truncation for meta description."""
    if len(text) <= max_len:
        return text.replace('"', '&quot;')
    cut = text[:max_len - 2].rsplit(" ", 1)[0]
    return (cut + "…").replace('"', '&quot;')


def get_macroarea(data, slug):
    """Lookup macroArea config by IT slug."""
    for m in data.get("macroAreas", []):
        if m["slug"] == slug:
            return m
    return None


def get_tag(data, slug):
    """Lookup tag config by IT slug."""
    for t in data.get("tagsVocabulary", []):
        if t["slug"] == slug:
            return t
    return None


def find_article(data, slug):
    for item in data["items"]:
        if item["slug"] == slug:
            return item
    return None


def render_article_card(lang, news_item, current_lang, current_page_type, data):
    """Render a card for the news grid."""
    L = LABELS[lang]
    slug = news_item["slug"]
    title_key = "titleIt" if lang == "it" else "titleEn"
    excerpt_key = "excerptIt" if lang == "it" else "excerptEn"
    href = article_url(lang, slug, current_lang, current_page_type)
    ma_slug = news_item.get("macroArea", "")
    ma = get_macroarea(data, ma_slug)
    ma_label = ma["labelIt" if lang == "it" else "labelEn"] if ma else news_item.get("category", "")
    tags_attr = ",".join(news_item.get("tags", []))
    return f"""
        <a href="{href}" class="news-card" data-tag="{tags_attr}">
          <div class="news-card__tag">{ma_label}</div>
          <h3 class="news-card__title">{news_item[title_key]}</h3>
          <p class="news-card__excerpt">{news_item[excerpt_key]}</p>
          <div class="news-card__meta">
            <span data-ts="{news_item["publishedAt"]}">{news_item["publishedAt"]}</span>
            <span class="news-card__arrow">{L["read_more"]} →</span>
          </div>
        </a>"""


# -----------------------------------------------------------------------------
# Page: HOME (new structured)
# -----------------------------------------------------------------------------

def render_home(lang, data):
    L = LABELS[lang]
    page_type = "index"
    news = data["items"]

    canonical = canonical_for(lang, page_type)
    hreflang_pair = {"it": f"{SITE_URL}/", "en": f"{SITE_URL}/en/"}
    title = "Apple WWDC 2026 — copertura italiana | biolatti.it" if lang == "it" else "Apple WWDC 2026 — Italian coverage | biolatti.it"

    other_lang_link = home_url("en" if lang == "it" else "it", lang, page_type)
    head = render_head(
        lang, page_type, title, L["meta_description_home"], canonical, hreflang_pair,
        og_image=macroarea_image_absolute(DEFAULT_OG_IMAGE_SLUG),
    )
    header = site_header(lang, page_type, other_lang_link, data)

    # Hero
    hero = f"""
  <section class="hero">
    <div class="container hero__inner">
      <span class="hero__eyebrow">{L["hero_eyebrow"]}</span>
      <h1 class="hero__title">{L["hero_title"]}</h1>
      <p class="hero__subtitle">{L["hero_subtitle"]}</p>
      <div class="hero__meta">
        <span><strong>{len(news)}</strong> {L["label_articles_count"]}</span>
        <span class="dot">·</span>
        <span>{L["hero_meta_dates"]}</span>
        <span class="dot">·</span>
        <span><a href="{simple_page_url(lang, 'analisi', lang, page_type)}">{L['nav_analisi']}</a></span>
      </div>
    </div>
  </section>
"""

    # Featured: 6 stories in 2 groups
    featured = data.get("featuredStories", {})

    def render_featured_group(group_key, group_label):
        group = featured.get(group_key, {})
        slugs = group.get("items", [])
        cards = []
        for s in slugs:
            item = find_article(data, s)
            if not item:
                continue
            cards.append(render_article_card(lang, item, lang, page_type, data))
        return (
            f'<div class="featured-group">'
            f'<h3 class="featured-group__label">{group_label}</h3>'
            f'<div class="news-grid news-grid--3">{"".join(cards)}</div>'
            f'</div>'
        )

    media_group = render_featured_group("mediaBuzz", L["media_buzz_label"])
    underrated_group = render_featured_group("underratedStructural", L["underrated_label"])
    # Durante la live i due gruppi sono vuoti (curati a mano in fase 2): in quel
    # caso la sezione viene omessa del tutto, per non mostrare blocchi vuoti.
    has_featured = bool((featured.get("mediaBuzz") or {}).get("items")) or \
                   bool((featured.get("underratedStructural") or {}).get("items"))
    featured_section = f"""
  <section class="section--featured">
    <div class="container">
      <div class="section-header">
        <span class="section-header__eyebrow">{L["section_featured_eyebrow"]}</span>
        <h2 class="section-header__title">{L["section_featured_title"]}</h2>
        <p class="section-header__subtitle">{L["section_featured_subtitle"]}</p>
      </div>
      {media_group}
      {underrated_group}
    </div>
  </section>
""" if has_featured else ""

    # Macro-areas grid (with narrative subtitle + hero thumbnail)
    ma_cards = []
    from collections import Counter
    ma_counts = Counter(n.get("macroArea", "") for n in news)
    asset_pref_home = asset_prefix(lang, page_type)
    for i, ma in enumerate(data["macroAreas"], 1):
        slug_it = ma["slug"]
        slug_en = ma["slugEn"]
        href = macroarea_url(lang, slug_it, slug_en, lang, page_type)
        label = ma["labelIt" if lang == "it" else "labelEn"]
        count = ma_counts.get(slug_it, 0)
        label_count = L["label_articles_count"] if count != 1 else L["label_article_count_singular"]
        # Narrative subtitle from intros
        intro = MACRO_AREA_INTROS.get(slug_it, {})
        subtitle = intro.get("h2It" if lang == "it" else "h2En", "")
        # Thumbnail (lazy, below the fold)
        img_path = macroarea_image_path(slug_it, asset_pref_home)
        img_alt = macroarea_alt(slug_it, lang)
        img_html = ""
        if img_path:
            img_html = (
                f'<div class="macroarea-card__image">'
                f'<img src="{img_path}" alt="{img_alt}" '
                f'width="1600" height="844" loading="lazy" decoding="async">'
                f'</div>'
            )
        ma_cards.append(f"""
        <a href="{href}" class="macroarea-card macroarea-card--with-image">
          {img_html}
          <div class="macroarea-card__body">
            <span class="macroarea-card__index">{i:02d}</span>
            <h3 class="macroarea-card__title">{label}</h3>
            <p class="macroarea-card__subtitle">{subtitle}</p>
            <div class="macroarea-card__count">{count} {label_count}</div>
          </div>
        </a>""")

    macroareas_section = f"""
  <section class="section--macroareas">
    <div class="container">
      <div class="section-header">
        <span class="section-header__eyebrow">{L["section_macroareas_eyebrow"]}</span>
        <h2 class="section-header__title">{L["section_macroareas_title"]}</h2>
        <p class="section-header__subtitle">{L["section_macroareas_subtitle"]}</p>
      </div>
      <div class="macroareas-grid">{"".join(ma_cards)}</div>
    </div>
  </section>
"""

    # Tags pills
    tag_counts = Counter(t for n in news for t in n.get("tags", []))
    tag_pills = []
    for t in data["tagsVocabulary"]:
        slug_it = t["slug"]
        slug_en = t["slugEn"]
        href = tag_url(lang, slug_it, slug_en, lang, page_type)
        label = t["labelIt" if lang == "it" else "labelEn"]
        count = tag_counts.get(slug_it, 0)
        tag_pills.append(f'<a href="{href}" class="tag-pill">{label} <span class="tag-pill__count">{count}</span></a>')

    tags_section = f"""
  <section class="section--tags">
    <div class="container">
      <div class="section-header">
        <span class="section-header__eyebrow">{L["section_tags_eyebrow"]}</span>
        <h2 class="section-header__title">{L["section_tags_title"]}</h2>
        <p class="section-header__subtitle">{L["section_tags_subtitle"]}</p>
      </div>
      <div class="tag-pills">{"".join(tag_pills)}</div>
    </div>
  </section>
"""

    # Other pages section
    other_cards = []
    other_cards.append(f"""
        <a href="{simple_page_url(lang, 'analisi', lang, page_type)}" class="otherpage-card">
          <h3>{L["page_analisi_title"]}</h3>
          <p>{L["page_analisi_subtitle"]}</p>
        </a>""")
    other_cards.append(f"""
        <a href="{simple_page_url(lang, 'top10', lang, page_type)}" class="otherpage-card">
          <h3>{L["page_top10_title"]}</h3>
          <p>{L["page_top10_subtitle"]}</p>
        </a>""")
    other_cards.append(f"""
        <a href="{simple_page_url(lang, 'timeline', lang, page_type)}" class="otherpage-card">
          <h3>{L["page_timeline_title"]}</h3>
          <p>{L["page_timeline_subtitle"]}</p>
        </a>""")
    otherpages_section = f"""
  <section class="section--otherpages">
    <div class="container">
      <div class="section-header">
        <span class="section-header__eyebrow">{L["section_otherpages_eyebrow"]}</span>
        <h2 class="section-header__title">{L["section_otherpages_title"]}</h2>
        <p class="section-header__subtitle">{L["section_otherpages_subtitle"]}</p>
      </div>
      <div class="otherpages-grid">{"".join(other_cards)}</div>
    </div>
  </section>
"""

    # About
    about = f"""
  <section id="about" class="section--about">
    <div class="container--narrow">
      <div class="section-header">
        <span class="section-header__eyebrow">{"Chi" if lang == "it" else "Who"}</span>
        <h2 class="section-header__title">{L["about_title"]}</h2>
      </div>
      <p style="font-size: 1.05rem; line-height: 1.75; text-align: center;">{L["about_body"]}</p>
    </div>
  </section>
"""

    footer = site_footer(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    # Schema.org WebSite + ItemList of top 10
    item_list = []
    for i, slug in enumerate(data.get("topStories", []), 1):
        item = find_article(data, slug)
        if not item:
            continue
        item_list.append({
            "@type": "ListItem",
            "position": i,
            "url": f"{canonical}{slug}.html",
            "name": item["titleIt" if lang == "it" else "titleEn"],
        })
    schema = {
        "@context": "https://schema.org",
        "@graph": [
            {
                "@type": "WebSite",
                "name": L["site_name"],
                "url": canonical,
                "inLanguage": lang,
                "publisher": {"@type": "Person", "name": "Daniele Biolatti", "url": "https://biolatti.it"},
            },
            {
                "@type": "ItemList",
                "name": L["page_top10_title"],
                "itemListElement": item_list,
            },
        ],
    }
    schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return head + header + hero + featured_section + macroareas_section + tags_section + otherpages_section + about + footer + schema_block + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Page: MACRO-AREA
# -----------------------------------------------------------------------------

def render_macroarea_page(lang, macroarea, data):
    L = LABELS[lang]
    page_type = "macroarea"
    news = [n for n in data["items"] if n.get("macroArea") == macroarea["slug"]]
    news = sorted(news, key=lambda n: n["publishedAt"], reverse=True)

    intro = MACRO_AREA_INTROS.get(macroarea["slug"], {})

    title = f'{macroarea["seoTitleIt" if lang == "it" else "seoTitleEn"]} | biolatti.it'
    body_intro = intro.get("bodyIt" if lang == "it" else "bodyEn", "")
    description = safe_description(body_intro, 160)

    canonical = canonical_for(lang, page_type, macroarea["slug"], macroarea["slugEn"])
    hreflang_pair = {
        "it": f"{SITE_URL}/macro-aree/{macroarea['slug']}.html",
        "en": f"{SITE_URL}/en/macro-areas/{macroarea['slugEn']}.html",
    }

    other_lang_link = macroarea_url("en" if lang == "it" else "it", macroarea["slug"], macroarea["slugEn"], lang, page_type)
    og_image_abs = macroarea_image_absolute(macroarea["slug"])
    head = render_head(lang, page_type, title, description, canonical, hreflang_pair, og_image=og_image_abs)
    header = site_header(lang, page_type, other_lang_link, data)

    label = macroarea["labelIt" if lang == "it" else "labelEn"]
    h2 = intro.get("h2It" if lang == "it" else "h2En", "")

    # Hero with side illustration (2-col layout on desktop, stacked on mobile)
    home_href = home_path(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    img_path = macroarea_image_path(macroarea["slug"], asset_pref)
    img_alt = macroarea_alt(macroarea["slug"], lang)
    hero_img_html = ""
    if img_path:
        hero_img_html = (
            f'<div class="hero__visual">'
            f'<img src="{img_path}" alt="{img_alt}" '
            f'width="1600" height="844" loading="eager" decoding="async">'
            f'</div>'
        )
    hero = f"""
  <section class="hero hero--macroarea">
    <div class="container hero__inner hero__inner--with-visual">
      <div class="hero__text">
        <nav class="article__breadcrumb"><a href="{home_href}">{L["breadcrumb_home"]}</a> / <span>{L["nav_macroaree"]}</span></nav>
        <span class="hero__eyebrow">{L["section_macroareas_eyebrow"]}</span>
        <h1 class="hero__title">{label}</h1>
        <p class="hero__subtitle">{h2}</p>
      </div>
      {hero_img_html}
    </div>
  </section>
"""

    # Intro block — improved typography with decorative open-circle mark and lead paragraph
    intro_block = f"""
  <section class="section--intro">
    <div class="container--narrow">
      <div class="macroarea-intro">
        <span class="macroarea-intro__mark" aria-hidden="true"></span>
        <p class="macroarea-intro__lead">{body_intro}</p>
      </div>
    </div>
  </section>
"""

    # Article grid
    cards = [render_article_card(lang, n, lang, page_type, data) for n in news]
    articles_block = f"""
  <section class="section--tight">
    <div class="container">
      <div class="section-header">
        <span class="section-header__eyebrow">{L["section_announcements_eyebrow"]}</span>
        <h2 class="section-header__title">{L["section_announcements_title"]} <span class="count">({len(news)})</span></h2>
      </div>
      <div class="news-grid">{"".join(cards)}</div>
    </div>
  </section>
"""

    # Browse other macro-areas — card grid (was tag-pills, ridisegnato per leggibilità UX/UI)
    other_cards = []
    for m in data["macroAreas"]:
        if m["slug"] == macroarea["slug"]:
            continue
        href = macroarea_url(lang, m["slug"], m["slugEn"], lang, page_type)
        m_label = m["labelIt" if lang == "it" else "labelEn"]
        m_intro = MACRO_AREA_INTROS.get(m["slug"], {})
        m_subtitle = m_intro.get("h2It" if lang == "it" else "h2En", "")
        other_cards.append(
            f'<a href="{href}" class="macroarea-other-card">'
            f'<h3>{m_label}</h3>'
            f'<p>{m_subtitle}</p>'
            f'<span class="macroarea-other-card__arrow" aria-hidden="true">→</span>'
            f'</a>'
        )
    other_block = f"""
  <section class="section--browse-others">
    <div class="container">
      <div class="section-header">
        <h2 class="section-header__title">{L["macroarea_browse_others"]}</h2>
      </div>
      <div class="macroarea-other-grid">{"".join(other_cards)}</div>
    </div>
  </section>
"""

    footer = site_footer(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    # Schema.org CollectionPage + ItemList
    item_list = []
    for i, n in enumerate(news, 1):
        item_list.append({
            "@type": "ListItem",
            "position": i,
            "url": f"{SITE_URL}/{n['slug']}.html" if lang == "it" else f"{SITE_URL}/en/{n['slug']}.html",
            "name": n["titleIt" if lang == "it" else "titleEn"],
        })
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": label,
        "description": body_intro,
        "url": canonical,
        "inLanguage": lang,
        "mainEntity": {"@type": "ItemList", "itemListElement": item_list},
    }
    if og_image_abs:
        schema["image"] = og_image_abs
    schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return head + header + hero + intro_block + articles_block + other_block + footer + schema_block + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Page: TAG
# -----------------------------------------------------------------------------

def render_tag_page(lang, tag, data):
    L = LABELS[lang]
    page_type = "tag"
    news = [n for n in data["items"] if tag["slug"] in n.get("tags", [])]
    news = sorted(news, key=lambda n: n["publishedAt"], reverse=True)

    intro = TAG_INTROS.get(tag["slug"], {})

    label = tag["labelIt" if lang == "it" else "labelEn"]
    title = f'{label} — {"articoli Apple WWDC 2026" if lang == "it" else "Apple WWDC 2026 articles"} | biolatti.it'
    body_intro = intro.get("bodyIt" if lang == "it" else "bodyEn", "")
    description = safe_description(body_intro, 160)

    canonical = canonical_for(lang, page_type, tag["slug"], tag["slugEn"])
    hreflang_pair = {
        "it": f"{SITE_URL}/tag/{tag['slug']}.html",
        "en": f"{SITE_URL}/en/tag/{tag['slugEn']}.html",
    }

    other_lang_link = tag_url("en" if lang == "it" else "it", tag["slug"], tag["slugEn"], lang, page_type)
    tag_og_image = tag_image_absolute(tag["slug"]) or macroarea_image_absolute(DEFAULT_OG_IMAGE_SLUG)
    head = render_head(lang, page_type, title, description, canonical, hreflang_pair,
                       og_image=tag_og_image)
    header = site_header(lang, page_type, other_lang_link, data)

    h2 = intro.get("h2It" if lang == "it" else "h2En", "")

    home_href = home_path(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    tag_img_path = tag_image_path(tag["slug"], asset_pref)
    tag_img_alt = tag_alt(tag["slug"], lang)
    tag_img_html = ""
    if tag_img_path:
        tag_img_html = (
            f'<div class="hero__visual">'
            f'<img src="{tag_img_path}" alt="{tag_img_alt}" '
            f'width="1600" height="844" loading="eager" decoding="async">'
            f'</div>'
        )
    hero = f"""
  <section class="hero hero--tag">
    <div class="container hero__inner hero__inner--with-visual">
      <div class="hero__text">
        <nav class="article__breadcrumb"><a href="{home_href}">{L["breadcrumb_home"]}</a> / <span>{L["tag_intro_label"]}</span></nav>
        <span class="hero__eyebrow">{L["tag_intro_label"]}</span>
        <h1 class="hero__title">{label}</h1>
        <p class="hero__subtitle">{h2}</p>
      </div>
      {tag_img_html}
    </div>
  </section>
"""

    intro_block = f"""
  <section class="section--intro">
    <div class="container--narrow">
      <div class="macroarea-intro">
        <span class="macroarea-intro__mark" aria-hidden="true"></span>
        <p class="macroarea-intro__lead">{body_intro}</p>
      </div>
    </div>
  </section>
"""

    cards = [render_article_card(lang, n, lang, page_type, data) for n in news]
    articles_block = f"""
  <section class="section--tight">
    <div class="container">
      <div class="section-header">
        <h2 class="section-header__title">{L["section_announcements_title"]} <span class="count">({len(news)})</span></h2>
      </div>
      <div class="news-grid">{"".join(cards)}</div>
    </div>
  </section>
"""

    # Browse other tags
    other_links = []
    for t in data["tagsVocabulary"]:
        if t["slug"] == tag["slug"]:
            continue
        href = tag_url(lang, t["slug"], t["slugEn"], lang, page_type)
        other_links.append(f'<a href="{href}" class="tag-pill">{t["labelIt" if lang == "it" else "labelEn"]}</a>')
    other_block = f"""
  <section class="section--tags">
    <div class="container">
      <div class="section-header">
        <h2 class="section-header__title">{L["tag_browse_others"]}</h2>
      </div>
      <div class="tag-pills">{"".join(other_links)}</div>
    </div>
  </section>
"""

    footer = site_footer(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": label,
        "description": body_intro,
        "url": canonical,
        "inLanguage": lang,
    }
    if tag_og_image:
        schema["image"] = tag_og_image
    schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return head + header + hero + intro_block + articles_block + other_block + footer + schema_block + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Page: TOP 10
# -----------------------------------------------------------------------------

# Rationale text shown next to each top-10 entry — kept brief, one paragraph.
TOP10_RATIONALE_IT = {
    "siri-27-chatbot-gemini-app-dedicata": "Il pivot più atteso degli ultimi anni: Siri lascia il formato assistente per diventare un'app chatbot a sé stante, alimentata da modelli co-sviluppati con Google. Cambia il prodotto, cambia la promessa.",
    "siri-ai-beta-separata-non-inclusa-ios27-lancio-autunno": "La riserva più importante sull'annuncio più importante: Siri AI non sarà nel lancio autunnale di iOS 27. Una beta separata arriva più avanti, senza una data precisa.",
    "liquid-glass-rifondazione-tecnica-diffusione-bordo-scuro-highlights-speculari": "Non un ritocco estetico ma una revisione tecnica delle fondamenta: bordi scuri, riflessi speculari e una diffusione ripensata rispondono punto per punto alle critiche di leggibilità di iOS 26.",
    "xcode-27-coding-assistant-simula-intere-app": "L'assistente di Xcode 27 non suggerisce più solo righe di codice: genera, costruisce e simula un'intera app in autonomia, mentre Core AI sostituisce Core ML come framework di sistema.",
    "foundation-models-languagemodel-protocol-gemini-claude-swift": "Con un'unica interfaccia Swift, Gemini, Claude e i modelli on-device diventano intercambiabili aggiornando una dipendenza. Apple smette di insistere di avere sempre il modello migliore.",
    "macos-golden-gate-fine-era-intel-impatto-concreto-utenti": "Nessun Mac Intel riceverà più aggiornamenti di sistema, e Rosetta 2 viene dismesso. La fine ufficiale, dopo sei anni di transizione, di un intero capitolo hardware Apple.",
    "wwdc-2026-tre-aree-focus-platform-trust-intelligence-struttura-keynote": "Federighi abbandona il tradizionale giro piattaforma per piattaforma e organizza il keynote attorno a tre assi — piattaforma, fiducia, intelligenza — con oltre dieci minuti dedicati al child safety.",
    "wwdc-2026-tim-cook-discorso-finale-keynote-the-best-is-still-ahead": "'Il meglio deve ancora venire': Tim Cook chiude il suo ultimo keynote da CEO con un messaggio personale. Il successore Ternus, visto alla cena della vigilia, non è apparso sul palco.",
    "siri-ai-iphone-17-pro-air-modello-on-device-piu-potente-esclusivo": "Voci espressive e dettatura potenziata restano esclusive di iPhone 17 Pro e iPhone Air. Apple traccia una linea netta dentro la propria gamma, non solo tra chi ha Apple Intelligence e chi no.",
    "foundation-models-open-source-estate-2026-apple-annuncio": "Il core del framework Foundation Models sarà open source entro l'estate, prima ancora del lancio pubblico di iOS 27. Una scommessa sulla fiducia degli sviluppatori più che sul prodotto finito.",
}

TOP10_RATIONALE_EN = {
    "siri-27-chatbot-gemini-app-dedicata": "The most anticipated pivot in years: Siri leaves the assistant format behind to become a standalone chatbot app, powered by models co-developed with Google. The product changes, and so does the promise.",
    "siri-ai-beta-separata-non-inclusa-ios27-lancio-autunno": "The biggest caveat on the biggest announcement: Siri AI won't ship with iOS 27 this autumn. A separate beta arrives later, with no firm date.",
    "liquid-glass-rifondazione-tecnica-diffusione-bordo-scuro-highlights-speculari": "Not a cosmetic tweak but a technical rebuild of the foundations: dark edges, specular highlights and reworked diffusion answer iOS 26's legibility complaints point by point.",
    "xcode-27-coding-assistant-simula-intere-app": "Xcode 27's assistant no longer just suggests lines of code: it generates, builds and simulates an entire app on its own, while Core AI replaces Core ML as the system framework.",
    "foundation-models-languagemodel-protocol-gemini-claude-swift": "With a single Swift interface, Gemini, Claude and on-device models become interchangeable by updating one dependency. Apple stops insisting it always has the best model.",
    "macos-golden-gate-fine-era-intel-impatto-concreto-utenti": "No Intel Mac will receive further system updates, and Rosetta 2 is retired. The official close, after six years of transition, of an entire Apple hardware chapter.",
    "wwdc-2026-tre-aree-focus-platform-trust-intelligence-struttura-keynote": "Federighi drops the traditional platform-by-platform tour and organizes the keynote around three axes — platform, trust, intelligence — with over ten minutes devoted to child safety.",
    "wwdc-2026-tim-cook-discorso-finale-keynote-the-best-is-still-ahead": "'The best is still ahead': Tim Cook closes his final keynote as CEO with a personal message. Successor Ternus, seen at the eve dinner, never appeared on stage.",
    "siri-ai-iphone-17-pro-air-modello-on-device-piu-potente-esclusivo": "Expressive voices and upgraded dictation stay exclusive to iPhone 17 Pro and iPhone Air. Apple draws a sharp line inside its own lineup, not just between who has Apple Intelligence and who doesn't.",
    "foundation-models-open-source-estate-2026-apple-annuncio": "The core of the Foundation Models framework will go open source by summer, ahead of iOS 27's public launch. A bet on developer trust more than on the finished product.",
}

def render_top10_page(lang, data):
    L = LABELS[lang]
    page_type = "top10"

    title = f'{L["page_top10_title"]} | biolatti.it'
    description = safe_description(L["page_top10_subtitle"], 160)

    canonical = canonical_for(lang, page_type)
    hreflang_pair = {
        "it": f"{SITE_URL}/top-10.html",
        "en": f"{SITE_URL}/en/top-10.html",
    }

    other_lang_link = simple_page_url("en" if lang == "it" else "it", "top10", lang, page_type)
    head = render_head(lang, page_type, title, description, canonical, hreflang_pair,
                       og_image=macroarea_image_absolute(DEFAULT_OG_IMAGE_SLUG))
    header = site_header(lang, page_type, other_lang_link, data)

    home_href = home_path(lang, page_type)
    hero = f"""
  <section class="hero hero--top10">
    <div class="container hero__inner">
      <nav class="article__breadcrumb"><a href="{home_href}">{L["breadcrumb_home"]}</a> / <span>{L["nav_top10"]}</span></nav>
      <span class="hero__eyebrow">Top 10</span>
      <h1 class="hero__title">{L["page_top10_title"]}</h1>
      <p class="hero__subtitle">{L["page_top10_subtitle"]}</p>
    </div>
  </section>
"""

    rationale = TOP10_RATIONALE_IT if lang == "it" else TOP10_RATIONALE_EN
    rows = []
    for i, slug in enumerate(data.get("topStories", []), 1):
        item = find_article(data, slug)
        if not item:
            continue
        title_key = "titleIt" if lang == "it" else "titleEn"
        ma_slug = item.get("macroArea", "")
        ma = get_macroarea(data, ma_slug)
        ma_label = ma["labelIt" if lang == "it" else "labelEn"] if ma else ""
        ma_href = macroarea_url(lang, ma["slug"], ma["slugEn"], lang, page_type) if ma else "#"
        href = article_url(lang, slug, lang, page_type)
        rationale_text = rationale.get(slug, "")
        rows.append(f"""
        <article class="top10-row">
          <div class="top10-row__rank">{i:02d}</div>
          <div class="top10-row__body">
            <a href="{ma_href}" class="top10-row__tag">{ma_label}</a>
            <h2 class="top10-row__title"><a href="{href}">{item[title_key]}</a></h2>
            <p class="top10-row__rationale">{rationale_text}</p>
            <a href="{href}" class="top10-row__cta">{L["read_full"]} →</a>
          </div>
        </article>""")

    list_block = f"""
  <section class="section--top10">
    <div class="container--narrow">{"".join(rows)}</div>
  </section>
"""

    footer = site_footer(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    # Schema.org ItemList
    item_list = []
    for i, slug in enumerate(data.get("topStories", []), 1):
        item = find_article(data, slug)
        if not item:
            continue
        url = f"{SITE_URL}/{slug}.html" if lang == "it" else f"{SITE_URL}/en/{slug}.html"
        item_list.append({
            "@type": "ListItem",
            "position": i,
            "url": url,
            "name": item["titleIt" if lang == "it" else "titleEn"],
        })
    schema = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": L["page_top10_title"],
        "description": L["page_top10_subtitle"],
        "url": canonical,
        "inLanguage": lang,
        "mainEntity": {"@type": "ItemList", "itemListElement": item_list},
    }
    schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return head + header + hero + list_block + footer + schema_block + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Page: ANALISI
# -----------------------------------------------------------------------------

def markdown_to_html(md_text, slug_url_resolver=None):
    """
    Minimal markdown -> HTML converter for the analysis page.
    Handles: # H1, ## H2, ### H3, paragraphs, bold **x**, em *x*,
    links [text](url), inline code `x`, ordered/unordered lists.
    The slug_url_resolver is a callable (slug -> href) used to rewrite
    relative article links like (/foo.html) into the right relative URL
    from the analisi page.
    """
    lines = md_text.split("\n")
    out = []
    in_list = None  # 'ul' or 'ol'

    def close_list():
        nonlocal in_list
        if in_list:
            out.append(f"</{in_list}>")
            in_list = None

    def inline(text):
        # Resolve internal article links: (/<slug>.html)
        if slug_url_resolver:
            def link_resolver(m):
                inner = m.group(2)
                if inner.startswith("/") and inner.endswith(".html"):
                    slug = inner[1:-5]  # strip leading / and trailing .html
                    resolved = slug_url_resolver(slug)
                    return f'<a href="{resolved}">{m.group(1)}</a>'
                return f'<a href="{inner}">{m.group(1)}</a>'
            text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", link_resolver, text)
        else:
            text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)", r'<a href="\2">\1</a>', text)
        # Bold
        text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
        # Em
        text = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", text)
        # Inline code
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        return text

    for raw in lines:
        line = raw.rstrip()

        if not line.strip():
            close_list()
            continue
        if line.startswith("### "):
            close_list()
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.startswith("## "):
            close_list()
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("# "):
            close_list()
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif re.match(r"^\d+\.\s", line):
            if in_list != "ol":
                close_list()
                out.append("<ol>")
                in_list = "ol"
            content = re.sub(r"^\d+\.\s", "", line)
            out.append(f"<li>{inline(content)}</li>")
        elif line.startswith("- "):
            if in_list != "ul":
                close_list()
                out.append("<ul>")
                in_list = "ul"
            out.append(f"<li>{inline(line[2:])}</li>")
        else:
            close_list()
            out.append(f"<p>{inline(line)}</p>")

    close_list()
    return "\n".join(out)


# Hand-translated EN version of the analisi content (kept inline to avoid an extra MD file)
ANALISI_BODY_EN = """# Apple WWDC 2026 — Thematic analysis and takeaways

## What WWDC 2026 really was

WWDC 2026 was the WWDC where Apple stopped talking about Siri as a promise and started treating it as something it had to explain. Three dominant narratives hold together the 264 articles published on this site: **the Siri AI pivot, arriving late on itself**, **Liquid Glass walking back a year of criticism**, and **a bet on model-agnostic AI infrastructure**, most visible in how Apple opened Xcode and Foundation Models to Gemini, Claude, and third-party models.

### Narrative 1 — Siri AI: the pivot that arrives late on itself

This is the story that dominated coverage, with 62 articles in the Apple Intelligence and Siri area alone. Apple unveils [Siri AI as a standalone, chatbot-style app](/siri-27-chatbot-gemini-app-dedicata.html), a format it had excluded from its vision of the assistant for years. Under the hood, cloud processing runs on [Foundation Models co-developed with Google, on Nvidia GPUs inside Google's cloud infrastructure](/afm-cloud-pro-foundation-models-nvidia-google.html) — an architectural detail that says more than any slide on stage.

Then the caveats arrive, one after another. Siri AI [isn't included in the iOS 27 autumn launch](/siri-ai-beta-separata-non-inclusa-ios27-lancio-autunno.html): a separate beta slips to later in the year. The best features — expressive voices, upgraded dictation — [remain exclusive to iPhone 17 Pro and iPhone Air](/siri-ai-iphone-17-pro-air-modello-on-device-piu-potente-esclusivo.html). At launch it [speaks only English](/siri-ai-solo-inglese-lancio-lingue-future.html). It's [blocked on iOS and iPadOS in the European Union under the Digital Markets Act, and excluded from China too](/siri-ai-china-blocco-eu-ios-ipad-disponibile-macos-watchos-visionos.html) — with Brussels [publicly correcting Apple's own account](/commissione-europea-risposta-blocco-siri-ai-ue.html), noting the company had sought an exemption rather than build a compliant solution.

The sharpest comment comes from outside Apple: analyst Ming-Chi Kuo, [after the keynote, observes that Apple's real test isn't announcing Siri AI but proving it can use Google's own models better than Google itself](/wwdc-2026-kuo-analisi-post-keynote-gemini-siri-test-reale.html). WWDC 2026 delivered the promise. The real test is still ahead.

### Narrative 2 — Liquid Glass, the redesign that listens (a year late)

Apple didn't stop at an opacity slider: it [reworked the technical foundations of how Liquid Glass diffuses content behind it](/liquid-glass-rifondazione-tecnica-diffusione-bordo-scuro-highlights-speculari.html), adding dark edges and specular highlights for genuinely better legibility. The [new intensity slider on iOS 27 is a direct response to accessibility failures documented by the Nielsen Norman Group](/ios-27-liquid-glass-intensity-slider-accessibilita-risposta.html) after iOS 26 shipped — the source of the problem, cited explicitly.

The rest of the revision is systematic: [sidebars that extend to the window edge, icons that keep their own color instead of turning translucent, cross-platform color consistency](/liquid-glass-revisione-sidebar-bordo-icone-colore-uniformita.html), [a unified toolbar on macOS Golden Gate](/macos-golden-gate-toolbar-uniforme-design-aggiornamento.html), and [HDR support extended to the entire system interface](/macos-golden-gate-hdr-system-ui-interfaccia-display.html). This isn't a new design language. It's the old one, corrected by someone who read every complaint.

### Narrative 3 — Apple bets on model-agnostic AI infrastructure

The least-hyped story on stage, and the most interesting one for anyone watching Apple as a developer platform. The [LanguageModel protocol makes Gemini, Claude, and on-device models interchangeable](/foundation-models-languagemodel-protocol-gemini-claude-swift.html): swap one Swift Package Manager dependency, no application code touched. It's an implicit admission that Apple no longer insists it has the best model for every task.

In the same vein, [Core AI replaces Core ML](/apple-core-ai-framework-sostituisce-core-ml-wwdc-2026.html) as the system framework built for large language and multimodal models, [Foundation Models will go open source by summer](/foundation-models-open-source-estate-2026-apple-annuncio.html), and Private Cloud Compute access [becomes free for developers under two million downloads](/foundation-models-free-tier-sviluppatori-piccoli-private-cloud-compute.html), lowering the economic barrier to entry. Xcode 27 opens to a [third-party plugin ecosystem — Figma, GitHub, and soon Anthropic, OpenAI and Google — through an agent-client protocol](/xcode-27-plugin-ecosystem-figma-github-mcp-agent-client.html), and its coding assistant [can now simulate an entire app before it's even built](/xcode-27-coding-assistant-simula-intere-app.html). Apple is building the infrastructure for a world where the model behind its own apps might not be its own.

## The 10 most important announcements

1. **Siri becomes Siri AI** — A standalone, chatbot-style app powered by Foundation Models co-developed with Google. The most anticipated pivot in years, with every caveat that comes with its launch. ([/siri-27-chatbot-gemini-app-dedicata.html](https://wwdc2026.biolatti.it/en/siri-27-chatbot-gemini-app-dedicata.html))

2. **Siri AI doesn't ship with iOS 27 this autumn** — A separate beta slips to late 2026, decoupling the new interface from the system release. The single most important caveat on the event's most-hyped product. ([/siri-ai-beta-separata-non-inclusa-ios27-lancio-autunno.html](https://wwdc2026.biolatti.it/en/siri-ai-beta-separata-non-inclusa-ios27-lancio-autunno.html))

3. **Liquid Glass technically rebuilt** — Dark edges, specular highlights, and diffusion reworked from the ground up: the concrete answer to iOS 26's legibility complaints. ([/liquid-glass-rifondazione-tecnica-diffusione-bordo-scuro-highlights-speculari.html](https://wwdc2026.biolatti.it/en/liquid-glass-rifondazione-tecnica-diffusione-bordo-scuro-highlights-speculari.html))

4. **Xcode goes agentic** — The coding assistant can generate, build and simulate an entire app on its own, while Core AI replaces Core ML as the system framework for large models. ([/xcode-27-coding-assistant-simula-intere-app.html](https://wwdc2026.biolatti.it/en/xcode-27-coding-assistant-simula-intere-app.html))

5. **The LanguageModel protocol** — Gemini, Claude and on-device models become interchangeable by updating a single Swift dependency. Apple stops insisting it always has the best model. ([/foundation-models-languagemodel-protocol-gemini-claude-swift.html](https://wwdc2026.biolatti.it/en/foundation-models-languagemodel-protocol-gemini-claude-swift.html))

6. **macOS Golden Gate closes the book on Intel** — No Intel Mac will receive further updates, and Rosetta 2 is retired. The official end of a six-year era. ([/macos-golden-gate-fine-era-intel-impatto-concreto-utenti.html](https://wwdc2026.biolatti.it/en/macos-golden-gate-fine-era-intel-impatto-concreto-utenti.html))

7. **The keynote restructures around three axes** — Platform, trust, intelligence: Federighi drops the traditional platform-by-platform tour to organize the event by theme, with over ten minutes devoted to child safety. ([/wwdc-2026-tre-aree-focus-platform-trust-intelligence-struttura-keynote.html](https://wwdc2026.biolatti.it/en/wwdc-2026-tre-aree-focus-platform-trust-intelligence-struttura-keynote.html))

8. **Tim Cook's last keynote** — "The best is still ahead": Cook closes his final WWDC as CEO with a personal message. Ternus, his successor, had been seen at the pre-event dinner but never appeared on stage. ([/wwdc-2026-tim-cook-discorso-finale-keynote-the-best-is-still-ahead.html](https://wwdc2026.biolatti.it/en/wwdc-2026-tim-cook-discorso-finale-keynote-the-best-is-still-ahead.html))

9. **Siri AI at two speeds** — The most advanced features — expressive voices, higher-quality dictation — require iPhone 17 Pro or iPhone Air. Apple draws a sharp line inside its own lineup. ([/siri-ai-iphone-17-pro-air-modello-on-device-piu-potente-esclusivo.html](https://wwdc2026.biolatti.it/en/siri-ai-iphone-17-pro-air-modello-on-device-piu-potente-esclusivo.html))

10. **Foundation Models goes open source** — The framework's core will be released by summer 2026, ahead of iOS 27's public launch. A bet on developer trust more than on the finished product. ([/foundation-models-open-source-estate-2026-apple-annuncio.html](https://wwdc2026.biolatti.it/en/foundation-models-open-source-estate-2026-apple-annuncio.html))

## Reclassification into 8 thematic areas

The site organizes coverage into eight areas, framed from the point of view of the people who'll use these systems in the coming months, not from the stage demo. Below, one by one, with links to the most representative articles.

### 1. Apple Intelligence and Siri — 62 articles

The most populated area, and it's the story told above: from [Siri AI's debut as a chatbot](/siri-27-chatbot-gemini-app-dedicata.html) to [geographic restrictions](/siri-ai-china-blocco-eu-ios-ipad-disponibile-macos-watchos-visionos.html), from [hardware stratification](/siri-ai-iphone-17-pro-air-modello-on-device-piu-potente-esclusivo.html) to Apple Intelligence features [turning proactive](/apple-intelligence-proattivita-cross-app-messaggi-foto-calendario-suggerimenti.html) across messages, email and photos without being asked.

### 2. Operating systems — 61 articles

Platform news read from the point of view of daily use: from [the end of Intel support on macOS Golden Gate](/macos-golden-gate-fine-era-intel-impatto-concreto-utenti.html) to [watchOS 27 compatibility cuts, discovered by users rather than announced on stage](/watchos-27-sei-apple-watch-tagliati-ultra1-series9-compatibilita-silenziosa.html), down to [foldable iPhone references found in the beta's code](/ios-27-foldable-iphone-riferimenti-beta-foldstate-angledegrees.html) with no official confirmation whatsoever.

### 3. Services and ecosystem — 48 articles

The glue between Apple's devices, but also where the company's leadership transition played out: [Tim Cook's last keynote](/wwdc-2026-tim-cook-discorso-finale-keynote-the-best-is-still-ahead.html), [Ternus seen at the eve dinner but absent from the stage](/john-ternus-cena-pre-wwdc-assente-keynote-debutto-pubblico.html), and a [shorter, restructured keynote than usual](/wwdc-2026-keynote-formato-insolito-76-minuti-senza-piattaforme.html). On the product side, from [Tesla finally supporting CarPlay](/tesla-apple-carplay-supporto-finalmente.html) to Wallet [splitting the bill from a photographed receipt](/apple-cash-bill-splitting-scontrino-foto-wallet-messages.html).

### 4. Developers — 34 articles

WWDC's technical soul: the [LanguageModel protocol](/foundation-models-languagemodel-protocol-gemini-claude-swift.html), [open-source Foundation Models](/foundation-models-open-source-estate-2026-apple-annuncio.html), [Xcode going agentic](/xcode-27-coding-assistant-simula-intere-app.html), the [plugin ecosystem with Figma and GitHub](/xcode-27-plugin-ecosystem-figma-github-mcp-agent-client.html). Not every developer was happy: part of the community [praised the tools but panned the keynote format](/wwdc-2026-react-community-keynote-critiche-sviluppatori.html), calling it among the worst in years.

### 5. Design and interfaces — 22 articles

The systematic Liquid Glass revision told above: from the [technical rebuild of diffusion](/liquid-glass-rifondazione-tecnica-diffusione-bordo-scuro-highlights-speculari.html) to the [intensity slider built to answer documented accessibility complaints](/ios-27-liquid-glass-intensity-slider-accessibilita-risposta.html), down to [HDR support extended across the entire macOS system interface](/macos-golden-gate-hdr-system-ui-interfaccia-display.html).

### 6. Privacy and security — 18 articles

Where Apple's promises meet regulatory reality: [the European Commission publicly correcting Apple's account of the Siri AI block](/commissione-europea-risposta-blocco-siri-ai-ue.html), a keynote that [devoted over ten minutes to child safety](/wwdc-2026-keynote-struttura-nuova-child-safety-10-minuti-parental-controls.html) with [mandatory child accounts under thirteen](/ios-27-child-accounts-obbligatori-under-13-sistema-eta.html), and a [protest against non-consensual deepfakes outside Apple Park](/protesta-deepfake-wwdc-2026-apple-park-ingresso.html) that shadowed the event from the outside.

### 7. Spatial computing and visionOS — 13 articles

The most experimental area, and this year the most explicitly enterprise-facing: [Kia using Vision Pro with VRED to validate car design](/visionos-27-foveated-streaming-kia-autodesk-enterprise.html), a new [Spatial Preview framework bringing Cinema 4D and SketchUp models to real scale](/visionos-27-spatial-preview-framework-cinema4d-sketchup-design-review.html), a hardware baseline raised to [Vision Pro with the M5 chip](/visionos-27-m5-apple-vision-pro-specifiche-foveated-streaming-pc.html). One bright spot on accessibility: [Wheelchair Control uses eye tracking to drive a motorized wheelchair](/visionos-27-wheelchair-control-eye-tracking-sedia-a-rotelle.html).

### 8. Health and wellbeing — 6 articles

The smallest area of the event, and almost entirely incremental: [Fitness+ adds perimenopause and menopause workouts](/fitness-plus-workout-perimenopause-menopausa-wwdc-2026.html), [GymKit arrives on iPhone and AirPods Pro 3, breaking a seven-year Apple Watch exclusive](/gymkit-iphone-airpods-pro-3-ios-27.html), [indoor run and walk tracking gets more precise](/watchos-27-indoor-run-walk-tracking-precisione-migliorata.html). No structural news on sensors or diagnostics.

## What was missing (or barely covered)

A few absences and a few threads covered too thinly, noted for honesty's sake — they're part of the picture as much as the strong announcements.

**No consumer hook for spatial computing.** Every meaningful visionOS announcement targets enterprise and developers — Kia, Autodesk, Cinema 4D, SketchUp. Zero new hardware at a more accessible price, zero new reason for a consumer to consider Vision Pro.

**Health nearly stood still.** With just 6 pieces of news and no new sensor or diagnostic capability, the area where Apple has historically built its strongest advantage was the least eventful of the whole conference.

**Siri AI's real test is still ahead.** As Ming-Chi Kuo notes, the on-stage demo — directions pulled from an Instagram post — is isolated and curated. No independent benchmarks, no extended real-world use beyond the keynote.

**Official communication less precise than usual.** Apple had to correct itself at least three times after the keynote: Siri AI's EU availability (two successive corrections on which platforms are excluded), and Apple Watch Series 9's compatibility with watchOS 27, mistakenly omitted from the official page and then restored. For a company that treats precision as an identity trait, that's not a small detail.

**The foldable iPhone remains an official non-statement.** The references in the beta code — foldState, angleDegrees, a third indicator counting displays, new layout APIs — are numerous and consistent. On stage, total silence.

## Temporal pattern: when the announcements that matter actually broke

Coverage followed three distinct waves, reconstructed from articles' publication timestamps.

**Wave 1 — Keynote and opening night** (June 8, 15:29–23:33). The opening announcements and the big consumer headlines: the Golden Gate name, Siri AI's debut with the EU block already stated, the Liquid Glass redesign with its opacity slider, Image Playground 2, mandatory child accounts, Tim Cook's closing remarks. The densest stretch of "on-stage" news.

**Wave 2 — Overnight and the Platforms State of the Union** (June 9, 00:03–23:19). The most technical and densest block: open-source Foundation Models, the LanguageModel protocol, agentic Xcode, most of the Apple Intelligence integrations across system apps, the first round of regulatory corrections on Siri AI in Europe, Group Labs selling out within minutes for Foundation Models and App Intents. The single busiest day for article volume.

**Wave 3 — Follow-ups and analysis** (June 10-11). Hands-on videos from the beta, technical deep dives on RealityKit and visionOS, Ming-Chi Kuo's post-keynote analysis, the discovery of the slide listing over 250 (later 263) minor changes flashed briefly during the keynote, the Apple Design Awards and Swift Student Challenge winners. This is where the details the keynote had no time for surface — and it's no accident that the foldable references and the compatibility corrections show up precisely in this window.

The rule that emerges: **the announcements with the most structural weight — the LanguageModel protocol, open-source Foundation Models, the end of Intel support — landed in the second, technical wave, not in the opening keynote.** The keynote sells Siri AI. The content that actually changes how you build on Apple is elsewhere.
"""


def render_analisi_page(lang, data):
    L = LABELS[lang]
    page_type = "analisi"

    title = f'{L["page_analisi_title"]} | biolatti.it'
    description = safe_description(L["page_analisi_subtitle"], 160)

    canonical = canonical_for(lang, page_type)
    hreflang_pair = {
        "it": f"{SITE_URL}/analisi.html",
        "en": f"{SITE_URL}/en/analysis.html",
    }

    other_lang_link = simple_page_url("en" if lang == "it" else "it", "analisi", lang, page_type)
    head = render_head(lang, page_type, title, description, canonical, hreflang_pair,
                       og_image=macroarea_image_absolute(DEFAULT_OG_IMAGE_SLUG))
    header = site_header(lang, page_type, other_lang_link, data)

    home_href = home_path(lang, page_type)

    # Load source markdown
    if lang == "it":
        try:
            with open(ANALISI_MD, "r", encoding="utf-8") as f:
                md_text = f.read()
        except FileNotFoundError:
            md_text = "# Analisi non disponibile\n\nFile sorgente mancante."
    else:
        md_text = ANALISI_BODY_EN

    # Resolver: rewrite /foo.html relative article links into proper relative URLs from analisi page
    def resolver(slug):
        return article_url(lang, slug, lang, page_type)

    body_html = markdown_to_html(md_text, slug_url_resolver=resolver)

    hero = f"""
  <section class="hero hero--analisi">
    <div class="container hero__inner">
      <nav class="article__breadcrumb"><a href="{home_href}">{L["breadcrumb_home"]}</a> / <span>{L["nav_analisi"]}</span></nav>
      <span class="hero__eyebrow">{L["nav_analisi"]}</span>
      <h1 class="hero__title">{L["page_analisi_title"]}</h1>
      <p class="hero__subtitle">{L["page_analisi_subtitle"]}</p>
    </div>
  </section>
"""

    article_block = f"""
  <main class="article">
    <div class="article__inner">
      <div class="article__body analisi-body">
        {body_html}
        <p style="margin-top: 2.5rem;"><a href="{home_href}">{L["back_to_home"]}</a></p>
      </div>
    </div>
  </main>
"""

    footer = site_footer(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    schema = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": L["page_analisi_title"],
        "description": L["page_analisi_subtitle"],
        "author": {"@type": "Person", "name": "Daniele Biolatti", "url": "https://biolatti.it"},
        "publisher": {"@type": "Person", "name": "Daniele Biolatti", "url": "https://biolatti.it"},
        "datePublished": "2026-05-21",
        "dateModified": "2026-05-21",
        "inLanguage": lang,
        "url": canonical,
        "mainEntityOfPage": canonical,
    }
    schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return head + header + hero + article_block + footer + schema_block + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Page: TIMELINE
# -----------------------------------------------------------------------------

def render_timeline_page(lang, data):
    L = LABELS[lang]
    page_type = "timeline"

    title = f'{L["page_timeline_title"]} | biolatti.it'
    description = safe_description(L["page_timeline_subtitle"], 160)

    canonical = canonical_for(lang, page_type)
    hreflang_pair = {
        "it": f"{SITE_URL}/timeline.html",
        "en": f"{SITE_URL}/en/timeline.html",
    }

    other_lang_link = simple_page_url("en" if lang == "it" else "it", "timeline", lang, page_type)
    head = render_head(lang, page_type, title, description, canonical, hreflang_pair,
                       og_image=macroarea_image_absolute(DEFAULT_OG_IMAGE_SLUG))
    header = site_header(lang, page_type, other_lang_link, data)

    home_href = home_path(lang, page_type)

    hero = f"""
  <section class="hero hero--timeline">
    <div class="container hero__inner">
      <nav class="article__breadcrumb"><a href="{home_href}">{L["breadcrumb_home"]}</a> / <span>{L["nav_timeline"]}</span></nav>
      <span class="hero__eyebrow">{L["nav_timeline"]}</span>
      <h1 class="hero__title">{L["page_timeline_title"]}</h1>
      <p class="hero__subtitle">{L["page_timeline_subtitle"]}</p>
    </div>
  </section>
"""

    news = sorted(data["items"], key=lambda n: n["publishedAt"], reverse=True)
    cards = [render_article_card(lang, n, lang, page_type, data) for n in news]
    articles_block = f"""
  <section class="section--tight">
    <div class="container">
      <div class="news-grid">{"".join(cards)}</div>
    </div>
  </section>
"""

    footer = site_footer(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    return head + header + hero + articles_block + footer + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Page: ARTICLE
# -----------------------------------------------------------------------------

def render_article(lang, news_item, data):
    L = LABELS[lang]
    page_type = "article"
    slug = news_item["slug"]
    title_key = "titleIt" if lang == "it" else "titleEn"
    excerpt_key = "excerptIt" if lang == "it" else "excerptEn"
    body_key = "bodyIt" if lang == "it" else "bodyEn"

    canonical = canonical_for(lang, page_type, slug)
    hreflang_pair = {
        "it": f"{SITE_URL}/{slug}.html",
        "en": f"{SITE_URL}/en/{slug}.html",
    }
    title = f"{news_item[title_key]} | Apple WWDC 2026"
    description = safe_description(news_item[excerpt_key])

    other_lang_link = article_url("en" if lang == "it" else "it", slug, lang, page_type)
    ma_slug_for_og = news_item.get("macroArea", "")
    og_image_abs = macroarea_image_absolute(ma_slug_for_og) or macroarea_image_absolute(DEFAULT_OG_IMAGE_SLUG)
    head = render_head(lang, page_type, title, description, canonical, hreflang_pair, og_image=og_image_abs)
    header = site_header(lang, page_type, other_lang_link, data)

    # Body
    paragraphs_html = []
    for block in news_item[body_key].split("\n\n"):
        block = block.strip()
        if not block:
            continue
        if block.startswith("### "):
            paragraphs_html.append(f"<h3>{block[4:]}</h3>")
        elif block.startswith("## "):
            paragraphs_html.append(f"<h2>{block[3:]}</h2>")
        else:
            paragraphs_html.append(f"<p>{block}</p>")
    body_html = "\n".join(paragraphs_html)

    # Sources
    sources_html = ""
    if news_item.get("sources"):
        items = "".join(
            f'<li><a href="{s["url"]}" target="_blank" rel="noopener">{s["title"]}</a></li>'
            for s in news_item["sources"]
        )
        sources_html = f"""
        <div class="sources">
          <h3>{L["sources"]}</h3>
          <ul>{items}</ul>
        </div>
"""

    # Breadcrumb with macroArea link
    home_href = home_path(lang, page_type)
    ma = get_macroarea(data, news_item.get("macroArea", ""))
    if ma:
        ma_href = macroarea_url(lang, ma["slug"], ma["slugEn"], lang, page_type)
        ma_label = ma["labelIt" if lang == "it" else "labelEn"]
        breadcrumb = f'<a href="{home_href}">{L["breadcrumb_home"]}</a> / <a href="{ma_href}">{ma_label}</a>'
    else:
        breadcrumb = f'<a href="{home_href}">{L["breadcrumb_home"]}</a>'

    # Tags pill block (uses tag pages)
    tag_links = []
    for tag_slug in news_item.get("tags", []):
        t = get_tag(data, tag_slug)
        if t:
            href = tag_url(lang, t["slug"], t["slugEn"], lang, page_type)
            label = t["labelIt" if lang == "it" else "labelEn"]
            tag_links.append(f'<a href="{href}" class="tag-pill">{label}</a>')
    tags_block = ""
    if tag_links:
        tags_block = f"""
        <div class="article-tags">
          <h4 style="margin-bottom: 0.5rem; font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.06em;">{L["tags"]}</h4>
          <div class="tag-pills">{"".join(tag_links)}</div>
        </div>
"""

    # Article meta: published + macroArea (legacy "category" removed from visible meta)
    ma_meta = ma["labelIt" if lang == "it" else "labelEn"] if ma else news_item.get("category", "")

    article_html = f"""
  <main class="article">
    <div class="article__inner">
      <nav class="article__breadcrumb">{breadcrumb}</nav>
      <header class="article__header">
        <h1 class="article__title">{news_item[title_key]}</h1>
        <p class="article__lede">{news_item[excerpt_key]}</p>
        <div class="article__meta">
          <span>{L["published"]}: <span data-ts="{news_item["publishedAt"]}">{news_item["publishedAt"]}</span></span>
          <span>{L["category"]}: {ma_meta}</span>
        </div>
      </header>
      <div class="article__body">
        {body_html}
        {sources_html}
        {tags_block}
        <p style="margin-top: 2.5rem;"><a href="{home_href}">{L["back_to_home"]}</a></p>
      </div>
    </div>
  </main>
"""

    footer = site_footer(lang, page_type)
    asset_pref = asset_prefix(lang, page_type)
    scripts = f'<script src="{asset_pref}assets/js/main.js"></script>'

    schema = {
        "@context": "https://schema.org",
        "@type": "NewsArticle",
        "headline": news_item[title_key],
        "description": news_item[excerpt_key],
        "datePublished": news_item["publishedAt"],
        "dateModified": news_item["publishedAt"],
        "author": {"@type": "Person", "name": "Daniele Biolatti", "url": "https://biolatti.it"},
        "publisher": {"@type": "Person", "name": "Daniele Biolatti", "url": "https://biolatti.it"},
        "inLanguage": lang,
        "mainEntityOfPage": canonical,
        "url": canonical,
        "articleSection": ma_meta,
        "keywords": ", ".join(news_item.get("tags", [])),
    }
    schema_block = f'<script type="application/ld+json">{json.dumps(schema, ensure_ascii=False)}</script>'

    return head + header + article_html + footer + schema_block + scripts + "\n</body>\n</html>"


# -----------------------------------------------------------------------------
# Sitemap
# -----------------------------------------------------------------------------

def render_sitemap(data):
    last_update = data.get("lastUpdate") or datetime.now(timezone.utc).isoformat()
    urls = []

    def add(loc_it, loc_en, lastmod=None):
        lm = lastmod or last_update
        urls.append({
            "loc": loc_it, "lastmod": lm,
            "hreflang": [("it", loc_it), ("en", loc_en)],
        })
        urls.append({
            "loc": loc_en, "lastmod": lm,
            "hreflang": [("it", loc_it), ("en", loc_en)],
        })

    # Home
    add(f"{SITE_URL}/", f"{SITE_URL}/en/")

    # Pillar pages
    add(f"{SITE_URL}/analisi.html", f"{SITE_URL}/en/analysis.html")
    add(f"{SITE_URL}/top-10.html", f"{SITE_URL}/en/top-10.html")
    add(f"{SITE_URL}/timeline.html", f"{SITE_URL}/en/timeline.html")

    # Macro-areas
    for m in data.get("macroAreas", []):
        add(f"{SITE_URL}/macro-aree/{m['slug']}.html",
            f"{SITE_URL}/en/macro-areas/{m['slugEn']}.html")

    # Tags
    for t in data.get("tagsVocabulary", []):
        add(f"{SITE_URL}/tag/{t['slug']}.html",
            f"{SITE_URL}/en/tag/{t['slugEn']}.html")

    # Articles
    for n in data["items"]:
        slug = n["slug"]
        add(f"{SITE_URL}/{slug}.html", f"{SITE_URL}/en/{slug}.html", lastmod=n["publishedAt"])

    parts = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">']
    for u in urls:
        hreflang_tags = "".join(
            f'<xhtml:link rel="alternate" hreflang="{lng}" href="{href}"/>' for lng, href in u["hreflang"]
        )
        parts.append(f'<url><loc>{u["loc"]}</loc><lastmod>{u["lastmod"]}</lastmod>{hreflang_tags}</url>')
    parts.append('</urlset>')
    return "\n".join(parts)


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def main():
    if not os.path.exists(DATA_FILE):
        print(f"ERROR: data file not found: {DATA_FILE}", file=sys.stderr)
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    news = data["items"]

    # Directories
    en_dir = os.path.join(BASE_DIR, "en")
    macroaree_dir = os.path.join(BASE_DIR, "macro-aree")
    en_macroaree_dir = os.path.join(en_dir, "macro-areas")
    tag_dir = os.path.join(BASE_DIR, "tag")
    en_tag_dir = os.path.join(en_dir, "tag")
    for d in [en_dir, macroaree_dir, en_macroaree_dir, tag_dir, en_tag_dir]:
        os.makedirs(d, exist_ok=True)

    # Home
    write_file(os.path.join(BASE_DIR, "index.html"), render_home("it", data))
    write_file(os.path.join(en_dir, "index.html"), render_home("en", data))

    # Article pages
    for n in news:
        write_file(os.path.join(BASE_DIR, f"{n['slug']}.html"), render_article("it", n, data))
        write_file(os.path.join(en_dir, f"{n['slug']}.html"), render_article("en", n, data))

    # Macro-area pages
    for m in data.get("macroAreas", []):
        write_file(os.path.join(macroaree_dir, f"{m['slug']}.html"), render_macroarea_page("it", m, data))
        write_file(os.path.join(en_macroaree_dir, f"{m['slugEn']}.html"), render_macroarea_page("en", m, data))

    # Tag pages
    for t in data.get("tagsVocabulary", []):
        write_file(os.path.join(tag_dir, f"{t['slug']}.html"), render_tag_page("it", t, data))
        write_file(os.path.join(en_tag_dir, f"{t['slugEn']}.html"), render_tag_page("en", t, data))

    # Top 10
    write_file(os.path.join(BASE_DIR, "top-10.html"), render_top10_page("it", data))
    write_file(os.path.join(en_dir, "top-10.html"), render_top10_page("en", data))

    # Analisi
    write_file(os.path.join(BASE_DIR, "analisi.html"), render_analisi_page("it", data))
    write_file(os.path.join(en_dir, "analysis.html"), render_analisi_page("en", data))

    # Timeline
    write_file(os.path.join(BASE_DIR, "timeline.html"), render_timeline_page("it", data))
    write_file(os.path.join(en_dir, "timeline.html"), render_timeline_page("en", data))

    # Sitemap
    write_file(os.path.join(BASE_DIR, "sitemap.xml"), render_sitemap(data))

    print(f"OK: built")
    print(f"  - {len(news)} articles x 2 langs")
    print(f"  - 2 home pages")
    print(f"  - {len(data.get('macroAreas',[]))} macro-area pages x 2 langs")
    print(f"  - {len(data.get('tagsVocabulary',[]))} tag pages x 2 langs")
    print(f"  - 3 pillar pages (top-10, analisi, timeline) x 2 langs")
    print(f"  - 1 sitemap.xml")
    print(f"Last update: {data.get('lastUpdate')}")


if __name__ == "__main__":
    main()
