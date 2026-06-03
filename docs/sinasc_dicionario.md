# Dicionário de Dados — SINASC (Sistema de Informações sobre Nascidos Vivos)

O SINASC registra **todos os nascidos vivos** no Brasil via Declaração de Nascido Vivo (DN). Granularidade: **anual × UF**.

| Grupo | Conteúdo |
|---|---|
| **DN** | Declaração de Nascido Vivo padrão |
| `DNEX` | Externo — registros tardios / fora da UF de residência |

Convenção de nome: `DN{UF}{YYYY}.parquet` (ex.: `DNRS2024.parquet`).

No catálogo pysus pra RS só `DN` está disponível. **O dicionário abaixo cobre o DN.**

---

## DN — Declaração de Nascido Vivo

Cada linha = **um nascimento vivo**. Cerca de **120-140k/ano no RS**.

Esquema com ~80-90 colunas dependendo da versão do sistema (mudou em ~2010 com `_2010` suffixes). Abaixo cobertura das principais.

### Identificação do registro

| Coluna | Descrição | Domínio |
|---|---|---|
| `NUMERODN` | Número da DN (chave) | string |
| `ORIGEM` | Origem do registro | `1`=Oracle, `2`=BD antigo |
| `NUMEROLOTE` | Número do lote | string |
| `VERSAOSIST` | Versão do sistema | string |
| `DTCADASTRO` | Data de cadastro | `DDMMYYYY` |
| `DTRECEBIM` | Recebimento na esfera estadual | `DDMMYYYY` |
| `DTRECORIGA` | Recebimento na origem | `DDMMYYYY` |

### Mãe

| Coluna | Descrição | Domínio |
|---|---|---|
| `IDADEMAE` | Idade da mãe | inteiro |
| `ESTCIVMAE` | Estado civil | `1`=solteira, `2`=casada, `3`=viúva, `4`=separada, `5`=união estável, `9`=ignorado |
| `ESCMAE` | Escolaridade (antigo) | `1`=nenhuma, `2`=1-3 anos, `3`=4-7 anos, `4`=8-11 anos, `5`=≥12 anos, `9`=ignorado |
| `ESCMAE2010` | Escolaridade (Censo 2010) | `0`=sem instrução, `1`=fundamental I, `2`=fundamental II, `3`=médio, `4`=superior incompleto, `5`=superior completo, `9`=ignorado |
| `ESCMAEAGR1` | Escolaridade agregada | |
| `SERIESCMAE` | Série escolar | |
| `OCUPMAE` | Ocupação (CBO-2002) | 6 dígitos |
| `RACACORMAE` | Raça/cor da mãe | `1`=branca, `2`=preta, `3`=amarela, `4`=parda, `5`=indígena, `9`=ignorado |
| `NATURALMAE` | Naturalidade | código |
| `CODMUNNATU` | Município de naturalidade da mãe (IBGE 6) | |
| `CODMUNRES` | **Município de residência** (IBGE 6) — chave de geolocalização | |
| `CODPAISRES` | País de residência | `1`=Brasil |
| `CODUFNATU` | UF de naturalidade da mãe | 2 dígitos |
| `QTDFILVIVO` | Filhos vivos anteriores | inteiro |
| `QTDFILMORT` | Filhos mortos anteriores | inteiro |
| `QTDGESTANT` | Gestações anteriores | inteiro |
| `QTDPARTNOR` | Partos vaginais anteriores | inteiro |
| `QTDPARTCES` | Partos cesáreos anteriores | inteiro |

### Gestação

| Coluna | Descrição | Domínio |
|---|---|---|
| `GESTACAO` | Faixa gestacional | `1`=<22 sem, `2`=22-27, `3`=28-31, `4`=32-36, `5`=37-41, `6`=≥42, `9`=ignorado |
| `SEMAGESTAC` | Semanas de gestação | inteiro |
| `TPMETESTIM` | Método de estimativa da idade gestacional | `1`=DUM, `2`=USG, `3`=ex físico/outro |
| `GRAVIDEZ` | Tipo de gravidez | `1`=única, `2`=dupla, `3`=tripla ou mais, `9`=ignorado |
| `CONSULTAS` | Faixa de consultas pré-natal | `1`=nenhuma, `2`=1-3, `3`=4-6, `4`=≥7, `9`=ignorado |
| `CONSPRENAT` | Número exato de consultas pré-natal | inteiro |
| `MESPRENAT` | Mês de início do pré-natal | inteiro |
| `PARTO` | Tipo de parto | `1`=vaginal, `2`=cesário, `9`=ignorado |
| `STTRABPART` | Trabalho de parto induzido? | `1`=sim, `2`=não, `9`=ignorado |
| `STCESPARTO` | Cesárea ocorreu antes do trabalho de parto? | `1`=sim, `2`=não, `3`=não aplica |
| `TPAPRESENT` | Tipo de apresentação | `1`=cefálica, `2`=pélvica, `3`=transversa, `9`=ignorado |

### Nascido vivo

| Coluna | Descrição | Domínio |
|---|---|---|
| `DTNASC` | Data de nascimento | `DDMMYYYY` |
| `HORANASC` | Hora de nascimento | `HHMM` |
| `SEXO` | Sexo | `1`=masc, `2`=fem, `0`=ignorado (igual SIM, diferente SIH) |
| `RACACOR` | Raça/cor do RN | `1`=branca, `2`=preta, `3`=amarela, `4`=parda, `5`=indígena, `9`=ignorado |
| `RACACOR_RN` | Raça/cor (campo redundante em versões mais novas) | |
| `PESO` | Peso ao nascer (gramas) | inteiro |
| `APGAR1` | Apgar no 1º minuto | `0`-`10` |
| `APGAR5` | **Apgar no 5º minuto** (indicador de saúde neonatal) | `0`-`10` |
| `IDANOMAL` | Tem anomalia congênita? | `1`=sim, `2`=não, `9`=ignorado |
| `CODANOMAL` | Código CID-10 da anomalia | 4 chars |

### Parto

| Coluna | Descrição | Domínio |
|---|---|---|
| `LOCNASC` | Local de nascimento | `1`=hospital, `2`=outro estab. saúde, `3`=domicílio, `4`=outros |
| `CODESTAB` | **CNES do estabelecimento** | 7 dígitos |
| `CODMUNNASC` | Município de nascimento (IBGE 6) | |
| `TPFUNCRESP` | Tipo de profissional responsável | `1`=médico, `2`=enfermeiro/obstetriz, `3`=parteira, `4`=outros, `9`=ignorado |
| `TPNASCASSI` | Nascimento assistido por: | `1`=médico, `2`=enfermagem, `3`=parteira, `4`=outros |
| `TPDOCRESP` | Tipo de documento do responsável | `1`=CNES, `2`=CRM, etc. |
| `DTDECLARAC` | Data da declaração | `DDMMYYYY` |
| `KOTELCHUCK` | Índice Kotelchuck (adequação pré-natal) | `1`-`4` |

### Pai

| Coluna | Descrição |
|---|---|
| `IDADEPAI` | Idade do pai |

### Auditoria/investigação (raro)

| Coluna | Descrição |
|---|---|
| `STDNEPIDEM` | DN investigada por epidemio? | `0/1` |
| `STDNNOVA` | Substitui DN anterior? | `0/1` |
| `DIFDATA` | Diferença em dias (informativo) | inteiro |
| `NATURALIDADE` | Estado de naturalidade | |
| `CODMUNCART` | Município do cartório de registro | |
| `NUMREGCART` | Número de registro civil | |
| `DTREGCART` | Data do registro civil | |
| `PARIDADE` | Paridade calculada | |
| `TPROBSON` | Classificação de Robson (cesárea) | `1`-`10` |

---

## Glossário

| Sigla | Significado |
|---|---|
| **DN** | Declaração de Nascido Vivo |
| **SINASC** | Sistema de Informações sobre Nascidos Vivos |
| **DUM** | Data da Última Menstruação |
| **USG** | Ultrassonografia |
| **Apgar** | Avaliação de vitalidade do RN (Activity, Pulse, Grimace, Appearance, Respiration) |
| **CID-10** | Classificação Internacional de Doenças |
| **CBO-2002** | Classificação Brasileira de Ocupações |
| **Robson** | Classificação de Robson de cesáreas (10 grupos) |
| **Kotelchuck** | Índice de adequação do pré-natal |

---

## Joins típicos

```
SINASC.DN ─┬─ CODESTAB ─── CNES (CNES.ST)    → hospital onde nasceu
           ├─ CODMUNRES ── codmun (IBGE)     → município de residência da mãe
           ├─ CODMUNNASC ── codmun (IBGE)    → município onde nasceu
           └─ (mãe)    ─── (SIM.DOMAT)       → ❌ sem chave direta; linkage probabilístico (data, município, idade)
```

## Caveats que economizam tempo

1. **Datas em `DDMMYYYY`** — igual SIM, diferente do SIH. Parse com `pd.to_datetime(s, format="%d%m%Y")`.
2. **`SEXO=2 é feminino`** (padrão SIM/SINASC, diferente de SIH onde `3=fem`).
3. **Lag típico: ~1 ano.** Catálogo pysus tem `DNRS2022.parquet` como mais recente em jun/2026 — ainda atrasado.
4. **`PESO`** crítico pra análise: baixo peso ao nascer = `<2500g`. Filtrar `PESO < 500` ou `PESO > 6000` (provavelmente erros).
5. **`APGAR5 < 7` é o ponto de corte clássico** para asfixia neonatal. `APGAR5` é melhor preditor de desfecho que `APGAR1`.
6. **`KOTELCHUCK`** consolida `CONSPRENAT`+`MESPRENAT` num índice de adequação. Já vem calculado, não precisa derivar.
7. **`TPROBSON`** vem pré-calculado nas versões >= 2018. Cesárea geral é a soma dos grupos 1-10; grupos 1-4 são pop de baixo risco (taxa esperada de cesárea baixa).
8. **`CODANOMAL`** quase sempre vazio (~98% dos nascimentos) — só preenchido se `IDANOMAL=1`. Use com cuidado pra prevalência (subnotificação).
9. **`CONSULTAS=4` (≥7 consultas)** é o indicador clássico de pré-natal adequado por contagem (mas Kotelchuck é mais correto).
10. **Para cruzar com SIH** (parto → AIH 4101*, 4102*): não há chave direta entre DN e N_AIH. Use linkage probabilístico por `CODESTAB + DTNASC + IDADEMAE + CODMUNRES`.
11. **Para cruzar com SIM** pra mortalidade infantil/perinatal: idem, sem chave direta. **`CODESTAB + DTNASC ± dias`** + `IDADE` da DO codificada como dias.
12. **Dado de cor da pele do RN** é frequentemente preenchido como "branca" por padrão (qualidade ruim em algumas regiões).
