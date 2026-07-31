#!/usr/bin/env python3
"""Sentinela — georreferencia os pontos do ensaio usando as fotos do celular.

A placa não tem GPS. O celular tem — e toda foto tirada por ele carrega a
coordenada no EXIF. Este script casa as duas coisas pelo relógio: para cada
ponto medido, procura as fotos tiradas durante aquele intervalo e usa a
coordenada delas.

Resultado: GeoJSON, KML e CSV prontos para carregar no QGIS ou no Google Earth,
com RSSI, margem, perda e veredito como atributos.

Uso:
    python3 georreferenciar.py --pontos dados/ensaio02-...-pontos.csv \\
                               --fotos ~/Desktop/fotos-ensaio

Requisito: relógios do computador e do celular sincronizados. Ambos usam NTP por
padrão, então na prática já estão — mas se houver desvio, use --offset.

Autoria: Matheus Marassi
"""

import argparse
import csv
import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

try:
    import exifread
except ImportError:
    sys.exit("exifread nao encontrado. Instale com: pip install exifread")

EXTENSOES = {".jpg", ".jpeg", ".heic", ".png", ".tif", ".tiff"}

CORES_KML = {
    "APROVADO": "ff00ff00",
    "LIMITE": "ff00ffff",
    "REPROVADO": "ff0000ff",
    "COLETANDO": "ff888888",
}


def _grau(valores, ref):
    """Converte a tripla EXIF (grau, minuto, segundo) em grau decimal."""
    g, m, s = [float(v.num) / float(v.den) for v in valores]
    dec = g + m / 60.0 + s / 3600.0
    if ref in ("S", "W"):
        dec = -dec
    return dec


def le_foto(caminho):
    with open(caminho, "rb") as f:
        tags = exifread.process_file(f, details=False)

    quando = tags.get("EXIF DateTimeOriginal") or tags.get("Image DateTime")
    lat = tags.get("GPS GPSLatitude")
    lat_ref = tags.get("GPS GPSLatitudeRef")
    lon = tags.get("GPS GPSLongitude")
    lon_ref = tags.get("GPS GPSLongitudeRef")
    if not (quando and lat and lon and lat_ref and lon_ref):
        return None

    try:
        t = datetime.strptime(str(quando), "%Y:%m:%d %H:%M:%S")
    except ValueError:
        return None

    alt = None
    if "GPS GPSAltitude" in tags:
        v = tags["GPS GPSAltitude"].values[0]
        alt = round(float(v.num) / float(v.den), 1)

    return {
        "arquivo": Path(caminho).name,
        "quando": t,
        "lat": round(_grau(lat.values, str(lat_ref)), 7),
        "lon": round(_grau(lon.values, str(lon_ref)), 7),
        "alt": alt,
    }


def carrega_pontos(caminho):
    with open(caminho, encoding="utf-8") as f:
        pontos = [l for l in csv.DictReader(f) if l["enviados"] != "0"]
    if not pontos:
        sys.exit("nenhum ponto com amostras no arquivo informado")
    return pontos


def carrega_fotos(pasta_str, offset_s):
    pasta = Path(pasta_str).expanduser()
    if not pasta.is_dir():
        sys.exit(f"pasta nao encontrada: {pasta}")
    fotos = []
    for arq in sorted(pasta.iterdir()):
        if arq.suffix.lower() not in EXTENSOES:
            continue
        info = le_foto(arq)
        if not info:
            print(f"  (sem GPS ou sem data) {arq.name}")
            continue
        info["quando"] += timedelta(seconds=offset_s)
        fotos.append(info)
    return fotos


def monta_feicao(p, candidatas):
    lat = sum(f["lat"] for f in candidatas) / len(candidatas)
    lon = sum(f["lon"] for f in candidatas) / len(candidatas)
    alts = [f["alt"] for f in candidatas if f["alt"] is not None]
    props = {
        "ponto": int(p["ponto"]), "veredito": p["veredito"], "motivo": p["motivo"],
        "rssi_med": p["rssi_med"], "rssi_min": p["rssi_min"],
        "rssi_max": p["rssi_max"], "snr_med": p["snr_med"],
        "margem_db": p["margem_db"], "assimetria_db": p["assimetria_db"],
        "perda_pct": p["perda_pct"],
        "pacotes": f"{p['recebidos']}/{p['enviados']}", "inicio": p["inicio"],
        "altitude_m": round(sum(alts) / len(alts), 1) if alts else None,
        "fotos": ", ".join(f["arquivo"] for f in candidatas),
    }
    return {
        "type": "Feature",
        "geometry": {"type": "Point",
                     "coordinates": [round(lon, 7), round(lat, 7)]},
        "properties": props,
    }, lat, lon


def associa(pontos, fotos, folga):
    feicoes, semcoord = [], []
    for p in pontos:
        inicio = datetime.fromisoformat(p["inicio"]) - folga
        fim = datetime.fromisoformat(p["fim"]) + folga
        candidatas = [f for f in fotos if inicio <= f["quando"] <= fim]
        if not candidatas:
            semcoord.append(p["ponto"])
            print(f"P{p['ponto']:<3} sem foto no intervalo — coordenada faltando")
            continue
        feicao, lat, lon = monta_feicao(p, candidatas)
        feicoes.append(feicao)
        print(f"P{p['ponto']:<3} {lat:.6f}, {lon:.6f}  "
              f"margem {p['margem_db']:>5}  {p['veredito']}  "
              f"({len(candidatas)} foto(s))")
    return feicoes, semcoord


def escreve_geojson(caminho, feicoes):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feicoes}, f,
                  ensure_ascii=False, indent=2)


def escreve_csv(caminho, feicoes):
    campos = list(feicoes[0]["properties"].keys())
    with open(caminho, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lat", "lon"] + campos)
        for ft in feicoes:
            lon, lat = ft["geometry"]["coordinates"]
            w.writerow([lat, lon] + [ft["properties"][c] for c in campos])


def escreve_kml(caminho, feicoes):
    with open(caminho, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n')
        f.write("<name>Sentinela - cobertura</name>\n")
        for v, cor in CORES_KML.items():
            f.write(f'<Style id="{v}"><IconStyle><color>{cor}</color>'
                    f"<scale>1.1</scale></IconStyle></Style>\n")
        for ft in feicoes:
            p = ft["properties"]
            lon, lat = ft["geometry"]["coordinates"]
            desc = (f"margem {p['margem_db']} dB | rssi {p['rssi_med']} dBm | "
                    f"perda {p['perda_pct']}% | {p['motivo']}")
            f.write(f"<Placemark><name>P{p['ponto']} {p['veredito']}</name>"
                    f"<description>{desc}</description>"
                    f"<styleUrl>#{p['veredito']}</styleUrl>"
                    f"<Point><coordinates>{lon},{lat}</coordinates></Point>"
                    f"</Placemark>\n")
        f.write("</Document></kml>\n")


def main():
    ap = argparse.ArgumentParser(description="Georreferencia pontos do ensaio")
    ap.add_argument("--pontos", required=True, help="CSV de resumo gerado por coleta.py")
    ap.add_argument("--fotos", required=True, help="pasta com as fotos do celular")
    ap.add_argument("--offset", type=int, default=0,
                    help="segundos a somar na hora das fotos, se os relogios divergirem")
    ap.add_argument("--tolerancia", type=int, default=120,
                    help="segundos de folga fora do intervalo do ponto (padrao 120)")
    ap.add_argument("--saida", default=None, help="prefixo dos arquivos de saida")
    args = ap.parse_args()

    pontos = carrega_pontos(args.pontos)
    fotos = carrega_fotos(args.fotos, args.offset)
    print(f"{len(pontos)} pontos, {len(fotos)} fotos com coordenada\n")

    feicoes, semcoord = associa(pontos, fotos,
                                timedelta(seconds=args.tolerancia))
    if not feicoes:
        sys.exit("\nnenhum ponto pode ser georreferenciado — confira os relogios "
                 "e o --offset")

    base = Path(args.saida) if args.saida else Path(args.pontos).with_suffix("")
    f_geo = base.with_name(base.name + ".geojson")
    f_kml = base.with_name(base.name + ".kml")
    f_csv = base.with_name(base.name + "-geo.csv")

    escreve_geojson(f_geo, feicoes)
    escreve_csv(f_csv, feicoes)
    escreve_kml(f_kml, feicoes)

    print(f"\ngerado:\n  {f_geo}\n  {f_kml}\n  {f_csv}")
    if semcoord:
        print(f"\npontos sem coordenada: {', '.join(semcoord)}")
        print("tire ao menos uma foto durante a medicao de cada ponto.")


if __name__ == "__main__":
    main()
