"""
news_crawler.py — Crawler de links de noticias por sección
Uso:
    python news_crawler.py
    o importar extract_news_links() en tu propio código
"""

import re
import requests
from datetime import date, datetime
from scrapy.http import TextResponse
from urllib.parse import urlparse

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/120.0.0.0 Safari/537.36'
    ),
}

# ─────────────────────────────────────────────
# SELECTORES GENÉRICOS DE LINKS
# ─────────────────────────────────────────────
GENERIC_SELECTORS = [
    "h1 a", "h2 a", "h3 a", "h4 a",
    ".entry-title a", ".post-title a", ".article-title a",
    ".news-title a", ".headline a", ".story-title a", ".titulo a",
    "article a[href]",
    ".card-title a", ".teaser-title a", ".item-title a",
    "[data-testid*='headline'] a", "[data-testid*='title'] a",
    "[class*='headline'] a", "[class*='article-link']", "[class*='story-link']",
]

# Selectores genéricos de fecha
GENERIC_DATE_SELECTORS = [
    "time::attr(datetime)",
    "time::text",
    "[itemprop='datePublished']::attr(content)",
    "[itemprop='datePublished']::text",
    ".date::text",
    ".fecha::text",
    ".published::text",
    ".post-date::text",
    ".entry-date::text",
    ".article-date::text",
    "[class*='date']::text",
    "[class*='fecha']::text",
]

# ─────────────────────────────────────────────
# CONFIGURACIÓN DE FUENTES
# Agrega aquí cualquier fuente nueva.
# "selectors"      → vacío = usa GENERIC_SELECTORS
# "date_selectors" → vacío = usa GENERIC_DATE_SELECTORS
# ─────────────────────────────────────────────
SOURCES = {
    "semana": {
        "selectors": ["a.pcbg-bgoverlay", ".entry-title a"],
        "exclude_patterns": ["/category/", "/tag/", "/author/"],
        "date_selectors": ["time::attr(datetime)", ".fecha::text", ".date::text"],
    },
    "eltiempo": {
        "selectors": [],
        "exclude_patterns": ["/section/", "/tema/"],
        "date_selectors": ["time::attr(datetime)", ".publish-date::text"],
    },
    "elespectador": {
        "selectors": [],
        "exclude_patterns": ["/temas/", "/etiquetas/"],
        "date_selectors": ["time::attr(datetime)", ".article-date::text"],
    },
    "larepublica": {
        "selectors": ["h2.title a", "h3.title a"],
        "exclude_patterns": ["/categoria/"],
        "date_selectors": ["time::attr(datetime)", ".date::text"],
    },
    # ── Agrega más fuentes así: ──────────────────
    # "nuevafuente": {
    #     "selectors": [],
    #     "exclude_patterns": ["/tag/"],
    #     "date_selectors": [],    # vacío = usa genéricos
    # },
}

# Formatos de fecha que intentamos parsear
DATE_FORMATS = [
    "%Y-%m-%dT%H:%M:%S%z",
    "%Y-%m-%dT%H:%M:%S",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y %H:%M",
    "%d/%m/%Y",
    "%d de %B de %Y",
    "%B %d, %Y",
]

MONTHS_ES = {
    "enero": "January", "febrero": "February", "marzo": "March",
    "abril": "April", "mayo": "May", "junio": "June",
    "julio": "July", "agosto": "August", "septiembre": "September",
    "octubre": "October", "noviembre": "November", "diciembre": "December",
}


# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def _parse_date(raw: str) -> date | None:
    """Intenta convertir un string de fecha en objeto date."""
    raw = raw.strip()
    for es, en in MONTHS_ES.items():
        raw = raw.lower().replace(es, en)
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    match = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y-%m-%d").date()
        except ValueError:
            pass
    return None


def _extract_date_from_url(url: str) -> date | None:
    """Extrae fecha desde el path si tiene formato /YYYY/MM/DD/."""
    match = re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass
    return None


def _detect_source_key(url: str) -> str | None:
    domain = urlparse(url).netloc.lower().replace("www.", "")
    for key in SOURCES:
        if key in domain:
            return key
    return None


def _build_selectors(source_key: str | None) -> list[str]:
    if source_key and SOURCES[source_key].get("selectors"):
        return SOURCES[source_key]["selectors"]
    return GENERIC_SELECTORS


def _build_date_selectors(source_key: str | None) -> list[str]:
    if source_key and SOURCES[source_key].get("date_selectors"):
        return SOURCES[source_key]["date_selectors"]
    return GENERIC_DATE_SELECTORS


def _build_exclude(source_key: str | None) -> list[str]:
    defaults = ["/category/", "/tag/", "/author/", "/page/", "#", "javascript:"]
    if source_key:
        return defaults + SOURCES[source_key].get("exclude_patterns", [])
    return defaults


def _is_likely_article(url: str, base_domain: str, exclude: list[str]) -> bool:
    if any(p in url for p in exclude):
        return False
    if base_domain not in urlparse(url).netloc:
        return False
    path = urlparse(url).path
    if len(path.strip("/").split("/")) < 2:
        return False
    return True



def enrich_dates(items: list[dict]) -> list[dict]:
    """
    Intenta recuperar la fecha de artículos con fecha null
    revisando únicamente el URL — sin hacer ninguna llamada HTTP.

    Uso:
        results = extract_news_links(url, limit=10)
        results = enrich_dates(results)
    """
    nulls = [i for i in items if not i.get("fecha")]
    for item in nulls:
        fecha = _extract_date_from_url(item["link"])
        item["fecha"] = fecha.isoformat() if fecha else None
    encontradas = sum(1 for i in nulls if i.get("fecha"))
    print(f"🔎 enrich_dates: {encontradas}/{len(nulls)} fechas recuperadas desde URL")
    return items


# ─────────────────────────────────────────────
# FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────

def extract_news_links(
    url_section: str,
    limit: int = 10,
    fecha_corte: date | None = None,
    fuente_nombre: str | None = None,
) -> list[dict]:
    """
    Extrae links de noticias desde una URL de sección.

    Parámetros
    ----------
    url_section   : str          URL de la sección
    limit         : int          Máximo de artículos (default 10)
    fecha_corte   : date | None  Excluye artículos anteriores a esta fecha
    fuente_nombre : str | None   Nombre custom para el campo "fuente".
                                 Si no se provee, se usa el dominio.

    Retorna
    -------
    list[dict]  con keys: fuente, link, fecha ("YYYY-MM-DD" o null)
    """
    print(f"\n🔍 Analizando: {url_section}")
    if fecha_corte:
        print(f"  📅 Fecha de corte: {fecha_corte}")

    try:
        res = requests.get(url_section, headers=HEADERS, timeout=15)
        res.raise_for_status()
    except Exception as e:
        print(f"  ✗ Error de conexión: {e}")
        return []

    response = TextResponse(url=url_section, body=res.text, encoding='utf-8')
    base_domain = urlparse(url_section).netloc
    source_key = _detect_source_key(url_section)
    fuente = fuente_nombre or source_key or urlparse(url_section).netloc.replace("www.", "")

    print(f"  ✓ Fuente: {fuente}" if source_key else f"  ℹ Fuente desconocida ({fuente}) — selectores genéricos")

    selectors      = _build_selectors(source_key)
    date_selectors = _build_date_selectors(source_key)
    exclude        = _build_exclude(source_key)

    # Extraer links
    raw_links = []
    for sel in selectors:
        raw_links.extend(response.css(f"{sel}::attr(href)").getall())

    # Extraer fechas del HTML de la sección (cuando están disponibles)
    raw_dates    = [d for sel in date_selectors for d in response.css(sel).getall() if d.strip()]
    parsed_dates = [_parse_date(d) for d in raw_dates]

    seen       = set()
    results    = []
    date_index = 0

    for link in raw_links:
        full_url = response.urljoin(link)
        if full_url in seen:
            continue
        seen.add(full_url)

        if not _is_likely_article(full_url, base_domain, exclude):
            continue

        # Fecha: primero del HTML, luego del URL
        fecha = None
        if date_index < len(parsed_dates):
            fecha = parsed_dates[date_index]
            date_index += 1
        if fecha is None:
            fecha = _extract_date_from_url(full_url)

        # Filtro de fecha de corte (si no se conoce la fecha, se incluye)
        if fecha_corte and fecha and fecha < fecha_corte:
            continue

        results.append({
            "fuente": fuente,
            "link":   full_url,
            "fecha":  fecha.isoformat() if fecha else None,
        })

        if len(results) >= limit:
            break

    print(f"  → {len(results)} artículos")
    return results
