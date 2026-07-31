#!/usr/bin/env python3
"""Sentinela — importa um ensaio registrado apenas por fotos.

Quando o ensaio corre sem o log automático (tools/coleta.py), o que sobra são as
fotos da tela. Elas bastam: a leitura vem da transcrição do display e a
coordenada vem do EXIF da própria foto.

Entrada:
  - CSV de transcrição, uma linha por ponto, com a coluna `foto` apontando o
    arquivo correspondente
  - pasta com as fotos originais do celular

Saída: GeoJSON, KML e CSV com RSSI, margem, perda e veredito como atributos,
mais uma análise de perda de percurso se a posição do gateway for informada.

Uso:
    python3 importar_fotos.py --transcricao dados/ensaio02-transcricao.csv \\
                              --fotos ~/Downloads --ensaio 02

Em macOS o GPS é lido via `mdls`, que entende HEIC nativamente. Em outros
sistemas, cai para exifread (JPEG/TIFF).

Autoria: Matheus Marassi
"""

import argparse
import csv
import json
import math
import platform
import subprocess
import sys
from pathlib import Path

SENSIBILIDADE = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0, 11: -134.5, 12: -137.0}

CORES_KML = {
    "APROVADO": "ff00ff00",
    "LIMITE": "ff00ffff",
    "REPROVADO": "ff0000ff",
    "COLETANDO": "ff888888",
}


def gps_mdls(caminho):
    """Lê coordenada via Spotlight — funciona com HEIC, que exifread não abre."""
    campos = ["kMDItemLatitude", "kMDItemLongitude", "kMDItemAltitude",
              "kMDItemContentCreationDate"]
    cmd = ["mdls"] + [a for c in campos for a in ("-name", c)] + [str(caminho)]
    try:
        saida = subprocess.run(cmd, capture_output=True, text=True, timeout=20).stdout
    except Exception:
        return None

    val = {}
    for linha in saida.splitlines():
        if "=" not in linha:
            continue
        chave, bruto = linha.split("=", 1)
        val[chave.strip()] = bruto.strip()

    try:
        lat = float(val.get("kMDItemLatitude", ""))
        lon = float(val.get("kMDItemLongitude", ""))
    except ValueError:
        return None

    alt = None
    try:
        alt = round(float(val.get("kMDItemAltitude", "")), 1)
    except ValueError:
        pass

    return {"lat": lat, "lon": lon, "alt": alt,
            "quando": val.get("kMDItemContentCreationDate", "").strip('"')}


def gps_exifread(caminho):
    try:
        import exifread
    except ImportError:
        return None

    def grau(valores, ref):
        g, m, s = [float(v.num) / float(v.den) for v in valores]
        d = g + m / 60.0 + s / 3600.0
        return -d if ref in ("S", "W") else d

    with open(caminho, "rb") as f:
        tags = exifread.process_file(f, details=False)
    lat, lat_r = tags.get("GPS GPSLatitude"), tags.get("GPS GPSLatitudeRef")
    lon, lon_r = tags.get("GPS GPSLongitude"), tags.get("GPS GPSLongitudeRef")
    if not (lat and lon and lat_r and lon_r):
        return None
    alt = None
    if "GPS GPSAltitude" in tags:
        v = tags["GPS GPSAltitude"].values[0]
        alt = round(float(v.num) / float(v.den), 1)
    quando = tags.get("EXIF DateTimeOriginal")
    return {"lat": grau(lat.values, str(lat_r)), "lon": grau(lon.values, str(lon_r)),
            "alt": alt, "quando": str(quando) if quando else ""}


def le_gps(caminho):
    if platform.system() == "Darwin":
        r = gps_mdls(caminho)
        if r:
            return r
    return gps_exifread(caminho)


def distancia_m(lat1, lon1, lat2, lon2):
    """Haversine. Precisão de sobra para as centenas de metros deste ensaio."""
    R = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def fspl_db(d_m, freq_mhz):
    """Perda de percurso em espaço livre. Referência do que seria o melhor caso."""
    if d_m <= 0:
        return 0.0
    return 20 * math.log10(d_m / 1000.0) + 20 * math.log10(freq_mhz) + 32.44


def main():
    ap = argparse.ArgumentParser(description="Importa ensaio registrado por fotos")
    ap.add_argument("--transcricao", required=True)
    ap.add_argument("--fotos", required=True)
    ap.add_argument("--ensaio", default="00")
    ap.add_argument("--gateway", default=None,
                    help='posicao do no fixo, "lat,lon" — habilita analise de distancia')
    ap.add_argument("--sf", type=int, default=9)
    ap.add_argument("--freq", type=float, default=916.8)
    ap.add_argument("--tx-dbm", type=float, default=17.0)
    ap.add_argument("--saida", default=None)
    args = ap.parse_args()

    pasta = Path(args.fotos).expanduser()
    with open(args.transcricao, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    if not linhas:
        sys.exit("transcricao vazia")

    gw = None
    if args.gateway:
        try:
            a, b = args.gateway.split(",")
            gw = (float(a), float(b))
        except ValueError:
            sys.exit('--gateway deve ser "lat,lon"')

    feicoes = []
    print(f"{'pt':>3} {'lat':>12} {'lon':>12} {'alt':>6} {'rssi':>6} "
          f"{'marg':>5} {'perda':>6}  veredito")
    print("-" * 78)

    for lin in linhas:
        arq = pasta / lin["foto"]
        if not arq.exists():
            print(f"  aviso: foto nao encontrada: {arq.name}")
            continue
        g = le_gps(arq)
        if not g:
            print(f"  aviso: sem GPS: {arq.name}")
            continue

        env = int(lin["enviados"])
        rec = int(lin["recebidos"])
        perda = 100.0 * (env - rec) / env if env else 0.0

        props = {
            "ponto": int(lin["ponto"]),
            "veredito": lin["veredito"],
            "motivo": lin["motivo"],
            "rssi_med": float(lin["rssi_med"]),
            "rssi_min": float(lin["rssi_min"]),
            "rssi_max": float(lin["rssi_max"]),
            "margem_db": float(lin["margem_db"]),
            "assimetria_db": float(lin["assimetria_db"]),
            "perda_pct": round(perda, 1),
            "pacotes": f"{rec}/{env}",
            "altitude_m": g["alt"],
            "ambiente": lin.get("ambiente", ""),
            "foto": lin["foto"],
            "quando": g["quando"],
        }

        if gw:
            d = distancia_m(gw[0], gw[1], g["lat"], g["lon"])
            perda_medida = args.tx_dbm - float(lin["rssi_med"])
            props["distancia_m"] = round(d, 1)
            props["perda_percurso_db"] = round(perda_medida, 1)
            props["fspl_db"] = round(fspl_db(d, args.freq), 1)
            props["excesso_db"] = round(perda_medida - fspl_db(d, args.freq), 1)

        feicoes.append({
            "type": "Feature",
            "geometry": {"type": "Point",
                         "coordinates": [round(g["lon"], 7), round(g["lat"], 7)]},
            "properties": props,
        })

        print(f"{props['ponto']:>3} {g['lat']:>12.6f} {g['lon']:>12.6f} "
              f"{str(g['alt']):>6} {props['rssi_med']:>6.0f} "
              f"{props['margem_db']:>5.0f} {props['perda_pct']:>5.1f}%  "
              f"{props['veredito']}")

    if not feicoes:
        sys.exit("nenhum ponto georreferenciado")

    base = Path(args.saida) if args.saida else \
        Path(args.transcricao).parent / f"ensaio{args.ensaio}"
    f_geo = base.with_name(base.name + ".geojson")
    f_kml = base.with_name(base.name + ".kml")
    f_csv = base.with_name(base.name + "-geo.csv")

    with open(f_geo, "w", encoding="utf-8") as f:
        json.dump({"type": "FeatureCollection", "features": feicoes}, f,
                  ensure_ascii=False, indent=2)

    campos = list(feicoes[0]["properties"].keys())
    with open(f_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["lat", "lon"] + campos)
        for ft in feicoes:
            lon, lat = ft["geometry"]["coordinates"]
            w.writerow([lat, lon] + [ft["properties"].get(c, "") for c in campos])

    with open(f_kml, "w", encoding="utf-8") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        f.write('<kml xmlns="http://www.opengis.net/kml/2.2"><Document>\n')
        f.write(f"<name>Sentinela - ensaio {args.ensaio}</name>\n")
        for v, cor in CORES_KML.items():
            f.write(f'<Style id="{v}"><IconStyle><color>{cor}</color>'
                    f"<scale>1.1</scale></IconStyle></Style>\n")
        for ft in feicoes:
            p = ft["properties"]
            lon, lat = ft["geometry"]["coordinates"]
            desc = (f"rssi {p['rssi_med']:.0f} dBm | margem {p['margem_db']:.0f} dB | "
                    f"perda {p['perda_pct']}% | {p['ambiente']}")
            if "distancia_m" in p:
                desc += f" | {p['distancia_m']:.0f} m"
            f.write(f"<Placemark><name>P{p['ponto']} {p['veredito']}</name>"
                    f"<description>{desc}</description>"
                    f"<styleUrl>#{p['veredito']}</styleUrl>"
                    f"<Point><coordinates>{lon},{lat}</coordinates></Point>"
                    f"</Placemark>\n")
        f.write("</Document></kml>\n")

    print(f"\ngerado:\n  {f_geo}\n  {f_kml}\n  {f_csv}")

    # --- geometria do percurso -------------------------------------------
    print("\n=== distancias entre pontos consecutivos ===")
    for i in range(1, len(feicoes)):
        a = feicoes[i - 1]["geometry"]["coordinates"]
        b = feicoes[i]["geometry"]["coordinates"]
        d = distancia_m(a[1], a[0], b[1], b[0])
        pa = feicoes[i - 1]["properties"]["ponto"]
        pb = feicoes[i]["properties"]["ponto"]
        print(f"  P{pa} -> P{pb}: {d:6.0f} m")

    p0 = feicoes[0]["geometry"]["coordinates"]
    print("\n=== distancia ao ponto de partida (P0) ===")
    for ft in feicoes:
        c = ft["geometry"]["coordinates"]
        d = distancia_m(p0[1], p0[0], c[1], c[0])
        p = ft["properties"]
        print(f"  P{p['ponto']}: {d:6.0f} m   rssi {p['rssi_med']:>6.0f} dBm   "
              f"margem {p['margem_db']:>3.0f} dB   {p['veredito']}")


if __name__ == "__main__":
    main()
