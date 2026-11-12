
#!/usr/bin/env python3
"""IPTV-LATINO-LEGAL: generador de listas M3U autorizadas."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "database" / "catalog.json"
OUT = ROOT / "playlists"
REPORTS = ROOT / "reports"

CATEGORIES = {"movies", "series", "anime", "cartoons"}
ALLOWED_TYPES = {"movie", "episode"}
ALLOWED_AUDIO = {"es-419"}
TIMEOUT = 15

HEADERS = {
    "User-Agent": "IPTV-LATINO-LEGAL/1.0"
}

NO_NETWORK = "--no-network" in sys.argv


def clean(value):
    """Limpiar texto para M3U."""
    return re.sub(r"[\r\n,]", " ", str(value or "")).strip()


def valid_https(value):
    """Comprobar estructura de una URL HTTPS."""
    try:
        parsed = urlparse(str(value or ""))
        return (
            parsed.scheme == "https"
            and bool(parsed.hostname)
            and not any(c.isspace() for c in str(value))
        )
    except ValueError:
        return False


def check_url(url):
    """Comprobar accesibilidad HTTP del enlace."""
    if not valid_https(url):
        return False, "Se requiere una URL HTTPS válida"

    try:
        response = requests.head(
            url,
            allow_redirects=True,
            timeout=TIMEOUT,
            headers=HEADERS
        )

        if response.status_code in (403, 405, 501):
            response.close()
            response = requests.get(
                url,
                headers={**HEADERS, "Range": "bytes=0-1023"},
                allow_redirects=True,
                stream=True,
                timeout=TIMEOUT
            )

        status = response.status_code
        response.close()

        if status in (200, 206):
            return True, "HTTP accesible"

        return False, f"HTTP {status}"

    except requests.RequestException as exc:
        return False, f"Error de conexión: {exc.__class__.__name__}"


def validate(item):
    """Validar derechos, idioma, estructura y enlace."""

    errors = []

    if not isinstance(item, dict):
        return False, ["Registro inválido"], "No comprobado"

    title = clean(item.get("title"))
    category = item.get("category")
    media_type = item.get("type")

    if not title:
        errors.append("Falta el título")

    if category not in CATEGORIES:
        errors.append("Categoría no permitida")

    if media_type not in ALLOWED_TYPES:
        errors.append("Tipo debe ser movie o episode")

    if item.get("audio_language") not in ALLOWED_AUDIO:
        errors.append("Idioma distinto de español latino (es-419)")

    if item.get("audio_verified") is not True:
        errors.append("Audio latino no verificado")

    if not clean(item.get("audio_verification_method")):
        errors.append("Falta evidencia del método de verificación de audio")

    if not clean(item.get("license")):
        errors.append("Falta información de licencia")

    if not valid_https(item.get("license_url")):
        errors.append("URL de licencia inválida")

    if item.get("rights_verified") is not True:
        errors.append("Derechos de distribución no aprobados")

    if not clean(item.get("rights_notes")):
        errors.append("Falta descripción de los derechos")

    if not valid_https(item.get("rights_evidence_url")):
        errors.append("Falta evidencia HTTPS de autorización")

    url = item.get("url", "")

    if not valid_https(url):
        errors.append("URL de reproducción HTTPS inválida")

    if media_type == "episode":
        for field in ("season", "episode"):
            value = item.get(field)
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                errors.append(f"{field}: se requiere un entero mayor que cero")

        if not clean(item.get("series_name")):
            errors.append("Falta el nombre de la serie")

    if errors:
        return False, errors, "No comprobado"

    if NO_NETWORK:
        return True, [], "No comprobado (modo sin red)"

    accessible, note = check_url(url)

    if not accessible:
        return False, [note], note

    return True, [], note


def extinf(item):
    """Construir entrada compatible con IPTV Smarters."""

    title = clean(item.get("title"))
    category = item["category"]
    poster = clean(item.get("poster"))
    group = clean(item.get("group_title")) or category.title()

    attributes = [
        f'tvg-type="{"movie" if item["type"] == "movie" else "series"}"',
        f'group-title="{group}"'
    ]

    if poster and valid_https(poster):
        attributes.append(f'tvg-logo="{poster}"')

    if item["type"] == "episode":
        series = clean(item.get("series_name")) or title
        season = item["season"]
        episode = item["episode"]

        attributes.extend([
            f'series-name="{series}"',
            f'season="{season}"',
            f'episode="{episode}"'
        ])

        display = (
            f"{series} S{season:02d}E{episode:02d} - {title}"
        )
    else:
        display = title

    return f'#EXTINF:-1 {" ".join(attributes)},{display}'


def write_playlist(path, items):
    """Crear archivo M3U."""
    lines = ["#EXTM3U"]

    for item in items:
        lines.append(extinf(item))
        lines.append(item["url"])

    path.write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8"
    )


def main():

    if not CATALOG.exists():
        raise FileNotFoundError(f"No existe: {CATALOG}")

    data = json.loads(CATALOG.read_text(encoding="utf-8"))

    if not isinstance(data, dict) or not isinstance(data.get("items"), list):
        raise ValueError("catalog.json debe contener una lista items")

    items = data["items"]

    OUT.mkdir(exist_ok=True)
    REPORTS.mkdir(exist_ok=True)

    report = {
        "checked": len(items),
        "accepted": [],
        "rejected": [],
        "network_check": not NO_NETWORK
    }

    accepted = []
    seen_ids = set()

    for item in items:

        if not isinstance(item, dict):
            report["rejected"].append({
                "id": None,
                "errors": ["Registro no válido"]
            })
            continue

        item_id = clean(item.get("id"))
        errors_extra = []

        if not item_id:
            errors_extra.append("Falta ID")

        elif item_id in seen_ids:
            errors_extra.append("ID duplicado")

        else:
            seen_ids.add(item_id)

        ok, errors, network = validate(item)
        errors.extend(errors_extra)

        record = {
            "id": item_id,
            "title": clean(item.get("title")),
            "category": item.get("category"),
            "audio": item.get("audio_language"),
            "network": network,
            "errors": errors
        }

        if ok and not errors:
            accepted.append(item)
            report["accepted"].append(record)
        else:
            report["rejected"].append(record)

    for category in sorted(CATEGORIES):

        selected = [
            item for item in accepted
            if item["category"] == category
        ]

        write_playlist(
            OUT / f"{category}.m3u",
            selected
        )

    write_playlist(OUT / "all.m3u", accepted)

    report["accepted_count"] = len(accepted)
    report["rejected_count"] = len(report["rejected"])

    (REPORTS / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print("=" * 48)
    print("       IPTV-LATINO-LEGAL")
    print("=" * 48)
    print(f"Registros revisados: {len(items)}")
    print(f"Aprobados: {len(accepted)}")
    print(f"Rechazados: {len(report['rejected'])}")
    print(f"Modo de red: {'Desactivado' if NO_NETWORK else 'Activado'}")
    print(f"Listas generadas: {OUT}")
    print(f"Informe: {REPORTS / 'validation_report.json'}")

    if report["rejected"]:
        print("\nHay registros rechazados. Revisa el informe.")


if __name__ == "__main__":
    main()
