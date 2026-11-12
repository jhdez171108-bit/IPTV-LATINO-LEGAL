#!/usr/bin/env python3
"""Build authorized M3U playlists from database/catalog.json."""
from __future__ import annotations
import json, re, sys
from pathlib import Path
from urllib.parse import urlparse
import requests

ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "database" / "catalog.json"
OUT = ROOT / "playlists"
REPORTS = ROOT / "reports"
ALLOWED_TYPES = {"movie", "episode"}
CATEGORIES = {"movies", "series", "anime", "cartoons"}
ALLOWED_AUDIO = {"es-419"}
TIMEOUT = 15
HEADERS = {"User-Agent": "IPTV-LATINO-LEGAL/0.1 (+authorized-media-catalog)"}

def safe_text(value: str) -> str:
    return re.sub(r"[\r\n,]", " ", str(value or "")).strip()

def check_url(url: str) -> tuple[bool, str]:
    try:
        p = urlparse(url)
        if p.scheme not in ("https", "http") or not p.netloc:
            return False, "URL inválida: se requiere HTTP(S)"
        # HEAD first; some media hosts reject HEAD, so retry a small ranged GET.
        r = requests.head(url, allow_redirects=True, timeout=TIMEOUT, headers=HEADERS)
        if r.status_code in (405, 403, 501):
            r = requests.get(url, allow_redirects=True, stream=True, timeout=TIMEOUT,
                             headers={**HEADERS, "Range": "bytes=0-0"})
        if r.status_code >= 400:
            return False, f"HTTP {r.status_code}"
        ctype = r.headers.get("Content-Type", "").lower()
        if any(x in ctype for x in ("text/html", "application/json")):
            return False, f"El servidor devolvió {ctype}, no un medio directo"
        return True, f"HTTP {r.status_code}; {ctype or 'tipo no declarado'}"
    except requests.RequestException as e:
        return False, f"Error de conexión: {e.__class__.__name__}"

def validate(item: dict, check_network: bool) -> tuple[bool, list[str], str]:
    errors = []
    if not safe_text(item.get("id")): errors.append("Falta id")
    if not safe_text(item.get("title")): errors.append("Falta título")
    typ = item.get("type")
    cat = item.get("category")
    if typ not in ALLOWED_TYPES: errors.append("type debe ser movie o episode")
    if cat not in CATEGORIES: errors.append("Categoría no válida")
    if item.get("audio_language") not in ALLOWED_AUDIO:
        errors.append("Audio no identificado como español latino (es-419)")
    if item.get("audio_verified") is not True:
        errors.append("Audio latino no verificado")
    if not safe_text(item.get("audio_verification_method")):
        errors.append("Indica método/evidencia de verificación de audio")
    if not safe_text(item.get("license")) or not safe_text(item.get("license_url")):
        errors.append("Falta licencia o URL de licencia")
    if item.get("rights_verified") is not True:
        errors.append("Derechos de redistribución no aprobados")
    if not safe_text(item.get("rights_notes")):
        errors.append("Falta evidencia/notas de derechos")
    url = item.get("url", "")
    if not url: errors.append("Falta URL de reproducción")
    if typ == "episode":
        if not isinstance(item.get("season"), int) or item["season"] < 1:
            errors.append("Episodio: temporada debe ser entero >= 1")
        if not isinstance(item.get("episode"), int) or item["episode"] < 1:
            errors.append("Episodio: número debe ser entero >= 1")
    network_note = "No comprobado (modo sin red)"
    if check_network and url:
        ok, network_note = check_url(url)
        if not ok: errors.append(network_note)
    return not errors, errors, network_note

def extinf(item: dict) -> str:
    title = safe_text(item.get("title"))
    group = safe_text(item.get("group_title") or item["category"].title())
    poster = safe_text(item.get("poster"))
    attrs = [f'tvg-type="{"movie" if item["type"] == "movie" else "series"}"',
             f'group-title="{group}"']
    if poster: attrs.append(f'tvg-logo="{poster}"')
    if item["type"] == "episode":
        attrs += [f'series-name="{safe_text(item.get("series_name") or title)}"',
                  f'season="{item["season"]}"', f'episode="{item["episode"]}"']
        label = f'{safe_text(item.get("series_name") or title)} S{item["season"]:02d}E{item["episode"]:02d} - {title}'
    else:
        label = title
    return f'#EXTINF:-1 {" ".join(attrs)},{label}'

def main():
    check_network = "--no-network" not in sys.argv
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    items = data.get("items", [])
    OUT.mkdir(exist_ok=True); REPORTS.mkdir(exist_ok=True)
    report = {"checked": len(items), "accepted": [], "rejected": []}
    accepted = []
    for item in items:
        ok, errors, net = validate(item, check_network)
        record = {"id": item.get("id"), "title": item.get("title"),
                  "network": net, "errors": errors}
        if ok:
            accepted.append(item); report["accepted"].append(record)
        else:
            report["rejected"].append(record)
    for category in sorted(CATEGORIES):
        selected = [x for x in accepted if x["category"] == category]
        lines = ["#EXTM3U"]
        for item in selected:
            lines += [extinf(item), item["url"]]
        (OUT / f"{category}.m3u").write_text("\n".join(lines) + "\n", encoding="utf-8")
    (OUT / "all.m3u").write_text(
        "\n".join(["#EXTM3U"] + [line for x in accepted for line in (extinf(x), x["url"])]) + "\n",
        encoding="utf-8")
    report["accepted_count"] = len(accepted)
    report["rejected_count"] = len(report["rejected"])
    (REPORTS / "validation_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Catálogo: {len(items)} | Aprobados: {len(accepted)} | Rechazados: {len(report['rejected'])}")
    print(f"Listas generadas en: {OUT}")
    if report["rejected"]:
        print("Revisa reports/validation_report.json. Los elementos rechazados no se publican.")

if __name__ == "__main__":
    main()
