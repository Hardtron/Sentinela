#!/usr/bin/env python3
"""Sentinela — dimensionamento de alcance por cenário, spreading factor e altura.

Calcula alcance previsto a partir do modelo log-distância calibrado no ensaio 02
e de expoentes publicados para os cenários que interessam ao projeto — encosta
com mata, que é onde os sensores vão ficar.

Também dimensiona a haste do sensor: mostra quanto de alcance se ganha elevando
a antena e qual altura a primeira zona de Fresnel exige em cada distância.

Uso:
    python3 alcance.py                      # tabela completa
    python3 alcance.py --haste 4 --sf 12    # cenário específico

Base empírica e referências em docs/PROPAGACAO.md.

Autoria: Matheus Marassi
"""

import argparse
import math

FREQ_MHZ = 916.8
LAMBDA_M = 299.792458 / FREQ_MHZ

SENSIBILIDADE = {7: -123.0, 8: -126.0, 9: -129.0, 10: -132.0,
                 11: -134.5, 12: -137.0}

TEMPO_NO_AR_MS = {7: 41, 8: 72, 9: 169, 10: 289, 11: 660, 12: 1155}

# Expoente de perda por cenário. O "suburbano" é medido por nós; os demais vêm
# da literatura (docs/PROPAGACAO.md §3).
CENARIOS = {
    "los": ("visada limpa", 2.31),
    "suburbano": ("alvenaria esparsa (nosso ensaio 02)", 3.28),
    "mata": ("floresta tropical", 3.22),
    "mata_densa": ("vegetacao densa / dossel alto", 4.00),
}

# Altura de referência da antena no ensaio: placa na mão.
H_REF_M = 1.4

# Perda fixa medida no ensaio 02, além do FSPL e do expoente. Reflete o
# ambiente imediato do nó fixo — quintal murado, antena baixa. Um gateway bem
# instalado elimina boa parte disto.
PERDA_FIXA_ENSAIO_DB = 33.4


def fspl_db(d_m):
    if d_m <= 0:
        return 0.0
    return 20 * math.log10(d_m / 1000.0) + 20 * math.log10(FREQ_MHZ) + 32.44


def rssi_previsto(d_m, n, tx_dbm, perda_fixa_db, ganho_altura_db):
    """Log-distância ancorado no FSPL a 1 m."""
    pl = fspl_db(1.0) + 10 * n * math.log10(d_m) + perda_fixa_db
    return tx_dbm - pl + ganho_altura_db


def alcance_m(n, sf, margem_db, tx_dbm, perda_fixa_db, ganho_altura_db):
    alvo = SENSIBILIDADE[sf] + margem_db
    # inverte: alvo = tx - fspl(1) - 10n log10(d) - fixa + ganho
    log_d = (tx_dbm - fspl_db(1.0) - perda_fixa_db + ganho_altura_db - alvo) / (10 * n)
    return 10 ** log_d


def ganho_dois_raios(h_m, h_ref=H_REF_M):
    """Elevar a antena de h_ref para h_m. No regime de dois raios, dobrar a
    altura de uma das antenas vale +6 dB."""
    return 20 * math.log10(h_m / h_ref)


def fresnel_r1(d_m):
    """Raio da primeira zona de Fresnel no meio do vão."""
    return 0.5 * math.sqrt(LAMBDA_M * d_m)


def main():
    ap = argparse.ArgumentParser(description="Dimensionamento de alcance LoRa")
    ap.add_argument("--sf", type=int, default=None, choices=list(SENSIBILIDADE))
    ap.add_argument("--margem", type=float, default=20.0)
    ap.add_argument("--haste", type=float, default=None,
                    help="altura da antena do sensor, em metros")
    ap.add_argument("--tx-dbm", type=float, default=17.0)
    ap.add_argument("--perda-fixa", type=float, default=PERDA_FIXA_ENSAIO_DB,
                    help="perda fixa do ambiente do no fixo (0 = gateway limpo)")
    args = ap.parse_args()

    hastes = [args.haste] if args.haste else [1.4, 3.0, 4.0, 6.0]
    sfs = [args.sf] if args.sf else [7, 9, 12]

    print(f"Sentinela — alcance previsto   (margem alvo {args.margem:.0f} dB, "
          f"TX {args.tx_dbm:.0f} dBm)")
    print(f"perda fixa do ambiente do no fixo: {args.perda_fixa:.1f} dB")
    print(f"altura de referencia: {H_REF_M} m (placa na mao)\n")

    for chave, (rotulo, n) in CENARIOS.items():
        print(f"--- {rotulo}  (n = {n}) ---")
        cab = f"{'haste':>7} " + "".join(f"{'SF'+str(s):>10}" for s in sfs) + \
              f"{'ganho':>8}"
        print(cab)
        for h in hastes:
            g = ganho_dois_raios(h)
            linha = f"{h:>6.1f}m "
            for sf in sfs:
                d = alcance_m(n, sf, args.margem, args.tx_dbm, args.perda_fixa, g)
                linha += f"{d:>9.0f}m"
            linha += f"{g:>+7.1f}dB"
            print(linha)
        print()

    print("=== tempo no ar por spreading factor (quadro de 11 bytes) ===")
    for sf in sorted(TEMPO_NO_AR_MS):
        rel = TEMPO_NO_AR_MS[sf] / TEMPO_NO_AR_MS[7]
        print(f"  SF{sf:<3} sensib {SENSIBILIDADE[sf]:>7.1f} dBm   "
              f"ToA {TEMPO_NO_AR_MS[sf]:>5} ms   ({rel:>4.1f}x sobre SF7)")

    print("\n=== primeira zona de Fresnel — folga necessaria no meio do vao ===")
    print(f"{'distancia':>10} {'raio F1':>9} {'60% F1':>9}  <- obstaculo abaixo disto atenua")
    for d in (100, 200, 500, 1000, 2000):
        r = fresnel_r1(d)
        print(f"{d:>8} m {r:>8.1f} m {0.6*r:>8.1f} m")

    print("\nnota: a haste do sensor precisa levantar a antena acima da vegetacao")
    print("      rasteira E dar folga de Fresnel. Em encosta, o desnivel do")
    print("      terreno costuma resolver metade do problema — ver PROPAGACAO.md.")


if __name__ == "__main__":
    main()
