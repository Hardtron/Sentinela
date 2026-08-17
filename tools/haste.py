#!/usr/bin/env python3
"""Sentinela — dimensionamento da haste e da ancoragem do nó de campo.

Responde três perguntas de projeto que se conflitam:

1. Que altura de antena a geometria exige, dado o vão, a vegetação e a altura
   do gateway?
2. Quanto o vento entorta a haste — e quanto disso vira falso movimento se o
   inclinômetro estiver montado nela?
3. Onde compensa investir altura: no sensor ou no gateway?

Base empírica em docs/PROPAGACAO.md; projeto da ancoragem em docs/ANCORAGEM.md.

Autoria: Luiz Matheus Marassi de Paula
"""

import argparse
import math

FREQ_MHZ = 916.8
LAMBDA_M = 299.792458 / FREQ_MHZ

RHO_AR = 1.225      # kg/m³
CD_CILINDRO = 1.2   # coeficiente de arrasto de tubo cilíndrico

# --- Vento conforme ABNT NBR 6123 -----------------------------------------
# V0 é a velocidade básica: média sobre 3 s, excedida uma vez a cada 50 anos,
# a 10 m de altura em terreno aberto e plano. O mapa de isopletas da norma dá
# de 30 a 48 m/s no território nacional.
#
# ATENÇÃO: a versão anterior desta ferramenta usava 20 m/s arbitrários, valor
# NÃO normativo e otimista. Os resultados de vento publicados antes desta
# correção subestimavam a deflexão. Ver REFERENCIAS.md, nota de revisão.
V0_PADRAO_MS = 40.0   # estimativa para o litoral de SP — [CONFIRMAR] na isopleta

# Fator S2: rugosidade do terreno e altura. S2 = b * Fr * (z/10)^p
# Categorias da NBR 6123, classe A (maior dimensão < 20 m).
CATEGORIAS_S2 = {
    "II_aberto":     dict(b=1.00, p=0.085, desc="terreno aberto, poucos obstáculos"),
    "III_obstaculos": dict(b=0.94, p=0.100, desc="terreno plano com obstáculos, casas"),
    "IV_suburbano":  dict(b=0.86, p=0.120, desc="suburbano denso"),
}

# Fator S1: topográfico. Em talude ou morro o vento acelera. A norma dá
# formulação por inclinação; 1,0 é terreno plano e valores acima de 1,1 são
# típicos de encosta. [CONFIRMAR] por eng. civil para cada sítio.
S1_PADRAO = 1.15

# Perfis comuns no comércio brasileiro. E em Pa, dimensões em m.
PERFIS = {
    "eletroduto_3/4_galv": dict(od=0.0269, par=0.00265, E=200e9, kgm=1.58, custo_m=22),
    "eletroduto_1_galv":   dict(od=0.0337, par=0.00325, E=200e9, kgm=2.44, custo_m=30),
    "tubo_1.1/2_galv":     dict(od=0.0483, par=0.00300, E=200e9, kgm=3.35, custo_m=45),
    "tubo_2_galv":         dict(od=0.0603, par=0.00350, E=200e9, kgm=4.90, custo_m=65),
    "pvc_soldavel_50mm":   dict(od=0.0500, par=0.00330, E=3.0e9,  kgm=0.75, custo_m=12),
}


def inercia(od, par):
    di = od - 2 * par
    return math.pi / 64.0 * (od**4 - di**4)


def vk_nbr6123(z, v0=V0_PADRAO_MS, categoria="III_obstaculos", s1=S1_PADRAO, s3=1.0):
    """Velocidade característica do vento na altura z, conforme NBR 6123.

    Vk = V0 * S1 * S2 * S3, com S2 = b * Fr * (z/10)^p.
    """
    c = CATEGORIAS_S2[categoria]
    s2 = c["b"] * 1.0 * (z / 10.0) ** c["p"]
    return v0 * s1 * s2 * s3


def vento_topo(L, od, E, I, v_ms):
    """Viga engastada com carga distribuída. Devolve (flecha_m, angulo_graus).

    O ângulo é o que importa: é ele que um inclinômetro montado no topo leria
    como se fosse movimento do talude.

    Simplificação: pressão dinâmica uniforme ao longo da haste, calculada na
    altura do topo. Conservador para hastes curtas. Verificação estrutural
    formal é atribuição de eng. civil — aqui serve para decidir arquitetura.
    """
    w = 0.5 * RHO_AR * v_ms**2 * CD_CILINDRO * od   # N/m
    flecha = w * L**4 / (8 * E * I)
    ang = w * L**3 / (6 * E * I)
    return flecha, math.degrees(ang)


def fresnel_r1(d_m):
    return 0.5 * math.sqrt(LAMBDA_M * d_m)


def haste_necessaria(d_m, h_gateway, h_veg, fracao=0.6):
    """Altura de antena do sensor para liberar `fracao` da 1ª zona de Fresnel.

    Em rampa uniforme, a folga no meio do vão vale (hs + hg)/2 − h_veg: o
    desnível do terreno se cancela, e o que sobra é a MÉDIA das alturas de
    antena. Daí a conclusão econômica de §3.
    """
    folga = fracao * fresnel_r1(d_m)
    return 2 * (folga + h_veg) - h_gateway


def main():
    ap = argparse.ArgumentParser(description="Dimensionamento de haste e ancoragem")
    ap.add_argument("--v0", type=float, default=V0_PADRAO_MS,
                    help="velocidade basica do vento V0 em m/s (NBR 6123)")
    ap.add_argument("--categoria", default="III_obstaculos",
                    choices=list(CATEGORIAS_S2), help="rugosidade do terreno")
    ap.add_argument("--s1", type=float, default=S1_PADRAO,
                    help="fator topografico (1,0 plano; >1,1 encosta)")
    ap.add_argument("--vao", type=float, default=500.0, help="vao do enlace em m")
    ap.add_argument("--vegetacao", type=float, default=3.0,
                    help="altura da vegetacao no meio do vao, em m")
    args = ap.parse_args()

    print("=" * 74)
    print("1. VENTO — quanto a haste entorta, e o que isso vira em falso movimento")
    print("=" * 74)
    cat = CATEGORIAS_S2[args.categoria]
    print(f"NBR 6123: V0 = {args.v0:.0f} m/s, categoria {args.categoria}")
    print(f"          ({cat['desc']}), S1 = {args.s1:.2f}")
    print(f"velocidade caracteristica por altura:")
    for z in (1.5, 3.0, 4.0):
        vk = vk_nbr6123(z, args.v0, args.categoria, args.s1)
        print(f"          z = {z:.1f} m -> Vk = {vk:.1f} m/s ({vk*3.6:.0f} km/h)")
    print()
    print(f"{'perfil':<22}{'L':>5}{'Vk':>8}{'flecha':>9}{'angulo':>9}{'custo':>8}")
    print("-" * 74)
    for nome, p in PERFIS.items():
        I = inercia(p["od"], p["par"])
        for L in (1.5, 3.0, 4.0):
            vk = vk_nbr6123(L, args.v0, args.categoria, args.s1)
            f, a = vento_topo(L, p["od"], p["E"], I, vk)
            print(f"{nome:<22}{L:>4.1f}m{vk:>7.1f}{f*100:>8.1f}cm{a:>8.2f}°"
                  f"{p['custo_m']*L:>7.0f}R$")
        print()

    print("A resolucao tipica de um inclinometro MEMS de instrumentacao e de")
    print("0,0025° (Sisgeo/ESS). O limiar de alerta NAO e universal: e definido")
    print("por sitio, por eng. geotecnico. O que o projeto precisa garantir e que")
    print("o RUIDO ESTRUTURAL fique muito abaixo do limiar que vier a ser adotado.")
    print("Angulo de vento da ordem de decimos de grau ja compromete essa margem.\n")

    print("=" * 74)
    print("2. GEOMETRIA — que altura de antena o enlace exige")
    print("=" * 74)
    print(f"vegetacao no meio do vao: {args.vegetacao:.1f} m")
    print("altura de antena do SENSOR necessaria, por altura do GATEWAY:\n")
    gws = [3, 6, 10, 15, 20, 30]
    print(f"{'vao':>7}{'F1':>7}{'60%F1':>7}   " +
          "".join(f"{'gw '+str(g)+'m':>9}" for g in gws))
    print("-" * 74)
    for d in (200, 500, 1000, 2000):
        r = fresnel_r1(d)
        linha = f"{d:>6}m{r:>6.1f}m{0.6*r:>6.1f}m   "
        for g in gws:
            h = haste_necessaria(d, g, args.vegetacao)
            linha += f"{max(h,0):>8.1f}m" if h > 0 else f"{'-':>9}"
        print(linha)
    print("\n'-' significa que a altura do gateway ja resolve: o sensor pode ficar")
    print("no solo, sem haste.\n")

    print("=" * 74)
    print("3. ONDE INVESTIR ALTURA — sensor ou gateway")
    print("=" * 74)
    print("A folga no meio do vao vale (h_sensor + h_gateway)/2 menos a vegetacao.")
    print("Os dois entram com MESMO peso. Mas o gateway e um para muitos nos:\n")
    for n in (5, 10, 20, 50):
        print(f"  rede com {n:>2} nos: 1 m no gateway equivale a 1 m em cada um dos")
        print(f"                  {n} sensores -> {n}x mais barato subir o gateway")
    print("\nRegra: elevar o gateway primeiro, ate o limite estrutural. So depois")
    print("      considerar haste no sensor.\n")

    print("=" * 74)
    print("4. ALTERNATIVA SEM HASTE — antena direcional no gateway")
    print("=" * 74)
    print("Yagi de 9 dBi no gateway rende ~9 dB, o mesmo que uma haste de 4 m no")
    print("sensor — sem estrutura, sem vento, sem risco de raio no no de campo.")
    print("Custa direcionalidade: serve quando os nos estao num setor definido,")
    print("que e o caso de uma encosta monitorada. Usado no SitkaNet.")


if __name__ == "__main__":
    main()
