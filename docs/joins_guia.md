# Joins entre datasets DataSUS — guia prático

O DataSUS **não tem chave universal de pessoa.** O `CNS` (Cartão Nacional de Saúde) é o que mais se aproxima, mas vem **ofuscado nos parquets do pysus** por privacidade. Resultado: os joins se dividem em três tiers de confiabilidade muito diferentes.

| Tier | Granularidade | Chave | Confiabilidade | Caso de uso típico |
|---|---|---|---|---|
| **1. Estabelecimento** | unidade × competência | `CNES + COMPETEN` | exato (deterministic) | Enriquecer fatos com cadastro do hospital |
| **2. Geografia** | município × período | `codmun IBGE + ano/mês` | exato (em agregação) | Indicadores per capita, taxas |
| **3. Pessoa** | indivíduo | (composto: data nasc + sexo + mun + ...) | **probabilístico** | Linkage longitudinal (internação → óbito) |

Pro projeto **NF01006**, ~90% das análises só precisam dos tiers 1 e 2. Tier 3 só se for fazer rastro individual.

---

## Tier 1 — Joins via `CNES` (estabelecimento)

**A chave universal entre fatos e o cadastro.** Funciona porque toda atividade — internação, óbito, procedimento, notificação — acontece **em uma unidade de saúde**.

### Mapa de chaves

| Tabela | Coluna que aponta pra CNES.ST.CNES | Semântica |
|---|---|---|
| SIH.RD | `CNES` | hospital onde internou |
| SIH.SP | `SP_CNES` | hospital onde procedimento foi pago |
| SIH.RJ | `CNES` | hospital com AIH rejeitada |
| SIH.ER | `CNES` | hospital com erro de envio |
| SIA.PA | `PA_CODUNI` | unidade que produziu o procedimento |
| SIA.BI | `CODUNI` | idem (legacy ≤2011) |
| SIA.PS | `CNES_EXEC` | CAPS executor |
| SIA.SAD | `CNES_EXEC` | unidade de Atenção Domiciliar |
| SIM.DO | `CODESTAB` | hospital onde ocorreu o óbito (preenchido se `LOCOCOR=1`) |
| SINASC.DN | `CODESTAB` | maternidade onde nasceu |
| SINAN.* | `ID_UNIDADE` | unidade notificadora |
| CNES.LT/PF/EP/EQ/HB/SR/DC/IN/RC/GM/EE/EF | `CNES` | join entre grupos do CNES |

### Receita básica (pandas)

```python
import pandas as pd
from pathlib import Path

SAMPLES = Path("/app/data/samples")

sih_rd = pd.read_parquet(SAMPLES / "sih_rd.parquet")
cnes_st = pd.read_parquet(SAMPLES / "cnes_st.parquet")

# Join simples (ignora competência → usa último cadastro)
enriched = sih_rd.merge(
    cnes_st[["CNES", "CODUFMUN", "TP_UNID", "ESFERA_A", "NAT_JUR"]],
    on="CNES", how="left",
)
```

### Receita correta — join temporal (SCD)
**CNES é snapshot mensal.** Um hospital muda `TP_UNID`, `ESFERA_A`, leitos disponíveis ao longo do tempo. Pra análise correta, **case a competência da internação com a competência do CNES vigente**.

```python
# Competência uniforme YYYYMM (string)
sih_rd["competen"] = (
    sih_rd["ANO_CMPT"].astype(str) +
    sih_rd["MES_CMPT"].astype(str).str.zfill(2)
)
cnes_st["competen"] = cnes_st["COMPETEN"].astype(str)

enriched = sih_rd.merge(
    cnes_st[["CNES", "competen", "CODUFMUN", "TP_UNID", "ESFERA_A"]],
    on=["CNES", "competen"], how="left",
)
```

### Padrão "capacidade × ocupação" — SIH + CNES.LT

```python
cnes_lt = pd.read_parquet(SAMPLES / "cnes_lt.parquet")

# Leitos SUS por hospital × competência
leitos = (
    cnes_lt.groupby(["CNES", "COMPETEN"])
    .agg(leitos_sus=("QT_SUS", "sum"),
         leitos_total=("QT_EXIST", "sum"))
    .reset_index()
)
leitos["competen"] = leitos["COMPETEN"].astype(str)

internacoes_por_hosp = (
    sih_rd.groupby(["CNES", "competen"])
    .agg(internacoes=("N_AIH", "nunique"),
         diarias=("DIAS_PERM", "sum"))
    .reset_index()
)

ocupacao = internacoes_por_hosp.merge(leitos, on=["CNES", "competen"])
ocupacao["taxa_ocup"] = ocupacao["diarias"] / (ocupacao["leitos_sus"] * 30)
```

### Caveat — CNES.PF tem multiplicidade

Cada profissional pode aparecer N vezes em PF (um por vínculo). Pra "número de médicos do hospital", dedupe primeiro:

```python
medicos_por_hosp = (
    cnes_pf[cnes_pf["CBO"].str.startswith("22")]   # 22xxxx = médicos
    .drop_duplicates(["CNES", "COMPETEN", "CPFUNICO"])
    .groupby(["CNES", "COMPETEN"]).size()
    .rename("n_medicos").reset_index()
)
```

---

## Tier 2 — Joins via `município IBGE` (geografia)

**O caminho ideal pra agregações.** Cada dataset tem coluna(s) de município (de residência e/ou de ocorrência) — códigos IBGE 6 dígitos compatíveis com a tabela do IBGE.

### Mapa de colunas

| Dataset | Residência (paciente) | Ocorrência (onde foi feito) |
|---|---|---|
| SIH.RD | `MUNIC_RES` | `MUNIC_MOV` |
| SIH.SP | `SP_M_PAC` | `SP_M_HOSP` |
| SIA.PA | `PA_MUNPCN` | `PA_UFMUN` |
| SIA.BI / PS / SAD | `MUNPAC` | `UFMUN` |
| SIM.DO | `CODMUNRES` | `CODMUNOCOR` |
| SINASC.DN | `CODMUNRES` | `CODMUNNASC` |
| SINAN.* | `ID_MN_RESI` | `ID_MUNICIP` |
| CNES.ST (e outros) | — | `CODUFMUN` (é a entidade) |

**Regra prática:** pra **taxa de incidência** (por habitante), use a coluna de **residência**. Pra **utilização de serviço**, use a de **ocorrência**.

### Receita — taxa de mortalidade por município/ano

```python
sim_do = pd.read_parquet(SAMPLES / "sim_do.parquet")
sim_do["ano"] = sim_do["DTOBITO"].str[-4:].astype(int)

obitos = (
    sim_do.groupby(["CODMUNRES", "ano"]).size()
    .rename("obitos").reset_index()
)

# Carrega IBGE (você precisa baixar separadamente — não está no pysus)
populacao = pd.read_csv("data/ibge/populacao_rs.csv")
# Colunas esperadas: codmun, ano, populacao

taxa = (
    obitos.merge(
        populacao,
        left_on=["CODMUNRES", "ano"],
        right_on=["codmun", "ano"],
        how="left",
    )
    .assign(taxa_mort_1000=lambda d: d["obitos"] / d["populacao"] * 1000)
)
```

### Receita — indicador composto SIH × CNES × SIM × IBGE (pro NF01006)

Esse é o **padrão da sua tese**: leitos per capita × taxa de internação × mortalidade.

```python
# 1. Capacidade (CNES.ST + LT) por município/competência
cap = (
    cnes_lt
    .merge(cnes_st[["CNES", "CODUFMUN", "COMPETEN"]], on=["CNES", "COMPETEN"])
    .groupby(["CODUFMUN", "COMPETEN"])
    .agg(leitos_sus=("QT_SUS", "sum"),
         leitos_total=("QT_EXIST", "sum"))
    .reset_index()
)
cap["ano"] = cap["COMPETEN"].astype(str).str[:4].astype(int)
cap_anual = cap.groupby(["CODUFMUN", "ano"]).agg(
    leitos_sus_medio=("leitos_sus", "mean"),
).reset_index()

# 2. Internações SIH por município de residência/ano
sih_rd["ano"] = sih_rd["ANO_CMPT"].astype(int)
internacoes = (
    sih_rd.groupby(["MUNIC_RES", "ano"])
    .agg(internacoes=("N_AIH", "nunique"),
         obitos_hosp=("MORTE", "sum"))
    .reset_index()
)

# 3. Óbitos totais SIM por município de residência/ano
sim_do["ano"] = sim_do["DTOBITO"].str[-4:].astype(int)
obitos = sim_do.groupby(["CODMUNRES", "ano"]).size().rename("obitos_total").reset_index()

# 4. População IBGE
pop = pd.read_csv("data/ibge/populacao_rs.csv")  # codmun, ano, populacao

# 5. Join encadeado
indicadores = (
    pop.merge(cap_anual, left_on=["codmun", "ano"], right_on=["CODUFMUN", "ano"], how="left")
       .merge(internacoes, left_on=["codmun", "ano"], right_on=["MUNIC_RES", "ano"], how="left")
       .merge(obitos, left_on=["codmun", "ano"], right_on=["CODMUNRES", "ano"], how="left")
       .assign(
           leitos_per_1000=lambda d: d["leitos_sus_medio"] / d["populacao"] * 1000,
           taxa_internacao=lambda d: d["internacoes"] / d["populacao"] * 1000,
           taxa_mortalidade=lambda d: d["obitos_total"] / d["populacao"] * 1000,
           letalidade_hosp=lambda d: d["obitos_hosp"] / d["internacoes"],
       )
)
```

Esse DataFrame final é o que vira **a sua análise**.

---

## Tier 3 — Joins por pessoa (probabilístico)

**Use só se precisar rastreio individual.** Pra agregações geográficas/temporais, pule este tier.

### Por que não existe join exato

| Coluna candidata | Disponível? |
|---|---|
| `CPF` do paciente | ❌ nunca em microdados |
| `CNS` (Cartão SUS) | ⚠️ presente, mas **ofuscado** nos parquets pysus (caracteres altos da tabela ASCII) |
| Nome completo | ❌ nunca |
| Documento qualquer | ❌ |

### Receita determinística simples (alta precisão, baixa cobertura)

Pra responder "essa AIH terminou em óbito?":

```python
# 1. AIHs onde paciente morreu no hospital
sih_obitos = sih_rd[sih_rd["MORTE"] == 1].copy()

# 2. Óbitos hospitalares no SIM
sim_hosp = sim_do[sim_do["LOCOCOR"] == "1"].copy()

# 3. Normalizar formato de datas (SIH: YYYYMMDD, SIM: DDMMYYYY)
sim_hosp["dt_obito_iso"] = (
    sim_hosp["DTOBITO"].str[4:] +
    sim_hosp["DTOBITO"].str[2:4] +
    sim_hosp["DTOBITO"].str[:2]
)

# 4. Normalizar SEXO (SIH 1/3 vs SIM 1/2)
sim_hosp["sexo_norm"] = sim_hosp["SEXO"].map({"1": "1", "2": "3"})

# 5. Chave composta — CNES + data + sexo + idade
def idade_sim_para_anos(s):
    """Decodifica IDADE do SIM (4 dígitos: 1º dígito = unidade) pra anos."""
    s = str(s).zfill(4)
    unidade, valor = int(s[0]), int(s[1:])
    return valor if unidade in (4, 5) else 0   # tudo <1 ano → 0

sih_obitos["match"] = (
    sih_obitos["CNES"].astype(str) + "_" +
    sih_obitos["DT_SAIDA"] + "_" +
    sih_obitos["SEXO"].astype(str) + "_" +
    sih_obitos["IDADE"].astype(str)
)
sim_hosp["match"] = (
    sim_hosp["CODESTAB"].astype(str) + "_" +
    sim_hosp["dt_obito_iso"] + "_" +
    sim_hosp["sexo_norm"] + "_" +
    sim_hosp["IDADE"].apply(idade_sim_para_anos).astype(str)
)

linkados = sih_obitos.merge(sim_hosp, on="match", how="inner", suffixes=("_sih", "_sim"))
```

Captura ~60-80% dos pares verdadeiros (perde por divergência de sexo/idade entre fontes).

### Receita probabilística (recall maior)

Pra recall acima de 90%, use **Fellegi-Sunter** com pesos por concordância:

- Python: [`splink`](https://github.com/moj-analytical-services/splink) (estado da arte)
- Python: `recordlinkage`
- Brasil: `RecLink` (em Pascal, mas tem wrappers)

Receita conceitual:
1. Blocking por `CODESTAB + ano_obito` (reduz pares candidatos)
2. Comparadores por `(sexo, idade ± 1, dia ± 1)` com pesos
3. Threshold de score pra decidir match

### Quando vale o esforço?
- ✅ Mortalidade pós-alta (paciente teve alta SIH, morreu em casa depois → aparece no SIM, não no SIH)
- ✅ Re-internações (mesma pessoa, múltiplas AIHs)
- ✅ Coorte longitudinal: nasceu (SINASC) → adoeceu (SINAN) → internou (SIH) → morreu (SIM)
- ❌ Pro NF01006, **não vale** — análise é populacional (município/período)

---

## Joins dentro de cada dataset

### SIH (4 grupos)
```python
# RD ↔ SP: 1:N pela AIH
sih_full = sih_rd.merge(
    sih_sp.groupby("SP_NAIH").agg(
        n_procedimentos=("SP_ATOPROF", "count"),
        valor_sp=("SP_VALATO", "sum"),
    ).reset_index(),
    left_on="N_AIH", right_on="SP_NAIH", how="left",
)

# RD vs RJ: união, não join (RJ é o que foi rejeitado — não há overlap)
```

### CNES (13 grupos)
Sempre join por `(CNES, COMPETEN)`:
```python
hosp_completo = (
    cnes_st
    .merge(cnes_lt.groupby(["CNES","COMPETEN"]).agg(leitos=("QT_SUS","sum")).reset_index(),
           on=["CNES","COMPETEN"], how="left")
    .merge(cnes_eq.groupby(["CNES","COMPETEN"]).agg(equips=("QT_USO","sum")).reset_index(),
           on=["CNES","COMPETEN"], how="left")
    .merge(cnes_hb[cnes_hb["CMPT_FIM"]==999999].groupby(["CNES","COMPETEN"]).agg(habs=("SGRUPHAB","count")).reset_index(),
           on=["CNES","COMPETEN"], how="left")
)
```

### SINAN (58 doenças)
Para análise multi-doença, **UNION** (concat) em vez de join. As 58 compartilham núcleo comum.

```python
import pyarrow.dataset as ds

# Só as colunas comuns
COMUNS = ["TP_NOT", "ID_AGRAVO", "DT_NOTIFIC", "NU_ANO", "SG_UF_NOT",
          "ID_MUNICIP", "ID_UNIDADE", "ANO_NASC", "NU_IDADE_N", "CS_SEXO",
          "CS_RACA", "ID_MN_RESI", "CLASSI_FIN", "CRITERIO", "EVOLUCAO"]

frames = []
for f in Path("data/samples").glob("sinan_*.parquet"):
    df = pd.read_parquet(f, columns=COMUNS)
    df["doenca"] = f.stem.replace("sinan_", "").upper()
    frames.append(df)

sinan_unificado = pd.concat(frames, ignore_index=True)
```

---

## Cheatsheet — pegadinhas que custam horas

| # | Problema | Solução |
|---|---|---|
| 1 | `SEXO=2` (fem) no SIM/SINASC/SINAN vs `SEXO=3` (fem) no SIH | Map: `{"1":"1","2":"3"}` (SIM→SIH) |
| 2 | Datas `DDMMYYYY` (SIM, SINASC) vs `YYYYMMDD` (SIH, SINAN) | Normalize antes de comparar |
| 3 | `CNES` muda características ao longo do tempo | Join por `(CNES, COMPETEN)`, não só `CNES` |
| 4 | `CNES.PF` tem N linhas por profissional (1 por vínculo) | Dedupe por `(CNES, CPFUNICO)` antes de contar |
| 5 | `MUNIC_*` é 6 dígitos IBGE; alguns CSVs externos usam 7 (com DV) | `codmun_7 = codmun_6 * 10 + dv`. Ou trunque pra 6 |
| 6 | `IDADE` codificada no SIM/SINAN (4 dígitos, 1º = unidade) | Decode antes de comparar com `IDADE` em anos do SIH |
| 7 | `SIA.PA` é gigante (~4M linhas/mês) | Agregue antes do join. Use duckdb se precisar bater linha-a-linha |
| 8 | `SINAN` é Brasil-wide | Filtre por `SG_UF_NOT == 43` (RS) antes de tudo |
| 9 | `CNES.LT` representa cada tipo de leito separado | Agregue `QT_SUS` por `CNES` antes do join |
| 10 | `SIM.LOCOCOR` pode ser vazio em causas externas (via pública) | `LOCOCOR=1 AND CODESTAB IS NOT NULL` pra hospital |

---

## Joins relevantes pro NF01006 — priorizados

Dado o escopo (**distribuição de estabelecimentos de saúde × mortalidade no RS**), os joins na sua ordem provável de uso:

| Prioridade | Join | Granularidade | Pra responder |
|---|---|---|---|
| 1 | CNES.ST + CNES.LT | hospital × competência | Capacidade total de leitos por município |
| 2 | SIH.RD + IBGE | município × ano | Taxa de internação por habitante |
| 3 | SIM.DO + IBGE | município × ano | Taxa de mortalidade por habitante |
| 4 | CNES.ST + SIH.RD + IBGE | município × ano | Indicador composto: oferta × demanda × resultado |
| 5 | CNES.HB filtrada | hospital | Quem tem alta complexidade (UNACON, UTI tipo II) |
| 6 | SIH.RD + CNES.ST | AIH × hospital cadastro | Internação em hospital de qual tipo / esfera |
| 7 | SIM.DO + CNES.ST | óbito × hospital | Óbitos por hospital (concentração de morbi-mortalidade) |

Os Tier-3 (linkage SIH↔SIM) só se for fazer recorte de **letalidade pós-alta** — fora do escopo declarado.
