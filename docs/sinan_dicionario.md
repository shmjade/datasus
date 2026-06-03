# Dicionário de Dados — SINAN (Sistema de Informação de Agravos de Notificação)

O SINAN consolida **notificações compulsórias** de doenças e agravos. Granularidade: **anual × Brasil** (não tem UF no nome — todos os arquivos terminam em `BR`).

Convenção de nome: `{DOENÇA}BR{YY}.parquet` (ex.: `DENGBR25.parquet` = dengue, 2025).

São **~58 doenças/agravos** diferentes, cada uma com um arquivo por ano. O esquema **muda por doença** — algumas têm 30 colunas, outras 150 — mas tem um **núcleo comum**.

---

## Estrutura desta documentação

Por causa do volume (58 doenças), vou organizar em:

1. **Núcleo comum** (~25 colunas presentes em ~todas as doenças)
2. **Grupos temáticos de doenças** com os campos específicos de cada grupo
3. **Lista completa** das 58 doenças com 1 frase + colunas-chave

---

## 1. Núcleo comum (presente em quase todas as 58)

### Identificação da notificação

| Coluna | Descrição | Domínio |
|---|---|---|
| `TP_NOT` | Tipo de notificação | `1`=negativa, `2`=individual, `3`=conglomerado, `4`=surto |
| `ID_AGRAVO` | **CID-10 do agravo** (chave do que está sendo notificado) | 4 chars (ex.: `A920`=chikungunya) |
| `DT_NOTIFIC` | Data da notificação | `YYYYMMDD` |
| `SEM_NOT` | Semana epidemiológica da notificação | `YYYYWW` (ex.: `202501`) |
| `NU_ANO` | Ano da notificação | `YYYY` |
| `SG_UF_NOT` | UF de notificação (IBGE 2) | |
| `ID_MUNICIP` | Município de notificação (IBGE 6) | |
| `ID_REGIONA` | Regional de saúde | |
| `ID_UNIDADE` | **CNES da unidade notificadora** | 7 dígitos |
| `NU_LOTE_V` | Lote de envio vertical (mun → SES) | |
| `NU_LOTE_H` | Lote de envio horizontal (SES → MS) | |
| `DT_DIGITA` | Data de digitação | `YYYYMMDD` |
| `DT_TRANSUS`, `DT_TRANSDM`, `DT_TRANSSM`, `DT_TRANSRM`, `DT_TRANSRS`, `DT_TRANSSE` | Datas de transferência entre níveis (US, DM, SM, RM, RS, SE) | `YYYYMMDD` |

### Demografia do caso

| Coluna | Descrição | Domínio |
|---|---|---|
| `ANO_NASC` | Ano de nascimento | `YYYY` |
| `NU_IDADE_N` | **Idade codificada** (igual SIM) | 4 dígitos — ver tabela abaixo |
| `CS_SEXO` | Sexo | `M`=masc, `F`=fem, `I`=ignorado |
| `CS_GESTANT` | Gestante? | `1`=1º trim, `2`=2º trim, `3`=3º trim, `4`=ignorado período, `5`=não, `6`=não se aplica, `9`=ignorado |
| `CS_RACA` | Raça/cor | `1`=branca, `2`=preta, `3`=amarela, `4`=parda, `5`=indígena, `9`=ignorado |
| `CS_ESCOL_N` | Escolaridade | `00`=analfabeto, `01-05`=fundamental incompleto/completo, etc., `10`=não se aplica |
| `SG_UF` | UF de residência | IBGE 2 |
| `ID_MN_RESI` | Município de residência | IBGE 6 |
| `ID_RG_RESI` | Regional de residência | |
| `ID_PAIS` | País de residência | `1`=Brasil |
| `ID_OCUPA_N` | Ocupação (CBO-2002) | 6 dígitos |

#### Decodificação de `NU_IDADE_N` (igual SIM/SINASC)

4 dígitos: primeiro = unidade, restantes = valor.
- `1XXX` = horas (`<24`)
- `2XXX` = dias (`<30`)
- `3XXX` = meses (`<12`)
- `4XXX` = anos

Exemplos: `4028`=28 anos, `3005`=5 meses, `2010`=10 dias.

### Datas do caso

| Coluna | Descrição |
|---|---|
| `DT_SIN_PRI` | Data dos primeiros sintomas (`YYYYMMDD`) |
| `SEM_PRI` | Semana epidemiológica do primeiro sintoma |
| `DT_INVEST` | Data de início da investigação |
| `DT_ENCERRA` | Data de encerramento do caso |
| `DT_OBITO` | Data do óbito (se ocorreu) |

### Desfecho

| Coluna | Descrição | Domínio |
|---|---|---|
| `CLASSI_FIN` | **Classificação final** | varia por doença — `1`=confirmado, `2`=descartado, `3`=inconclusivo, `5`=confirmado autóctone (alguns), `8`=descartado/inadequado |
| `CRITERIO` | Critério de confirmação | varia: `1`=laboratorial, `2`=clínico-epidemiológico, `3`=clínico, `4`=óbito investigado |
| `EVOLUCAO` | Desfecho do caso | `1`=cura, `2`=óbito pelo agravo, `3`=óbito outras causas, `4`=óbito em investigação, `9`=ignorado |
| `DOENCA_TRA` | Doença relacionada ao trabalho? | `1`=sim, `2`=não, `9`=ignorado |
| `TPAUTOCTO` | Caso autóctone? | `1`=sim, `2`=não importado |
| `COUFINF` | UF provável de infecção | |
| `COMUNINF` | Município provável de infecção | |
| `COPAISINF` | País provável de infecção | |
| `MIGRADO_W` | Flag interna do sistema | |
| `TP_SISTEMA` | Tipo de sistema (NetSinan / SinanWeb) | |
| `NDUPLIC_N` | Flag de duplicidade | |
| `CS_FLXRET` | Fluxo de retorno | |
| `FLXRECEBI` | Recebido pelo destino? | |

---

## 2. Grupos temáticos

### 2.1 Arboviroses — DENG, CHIK, ZIKA

Doenças virais transmitidas pelo *Aedes aegypti*. Compartilham um schema robusto com **sinais/sintomas + classificação de gravidade**.

#### Sinais e sintomas (flag `1`=sim / `2`=não / `9`=ignorado)
| Coluna | Sintoma |
|---|---|
| `FEBRE`, `MIALGIA`, `CEFALEIA`, `EXANTEMA`, `VOMITO`, `NAUSEA` | Sinais cardinais |
| `DOR_COSTAS`, `CONJUNTVIT`, `ARTRITE`, `ARTRALGIA` | Articular/musc |
| `PETEQUIA_N`, `LEUCOPENIA`, `LACO` | Sinais hemorrágicos |
| `DOR_RETRO` | Dor retro-orbitária |

#### Comorbidades
| Coluna | |
|---|---|
| `DIABETES`, `HEMATOLOG`, `HEPATOPAT`, `RENAL`, `HIPERTENSA`, `ACIDO_PEPT`, `AUTO_IMUNE` | Doenças prévias |

#### Sorologia/PCR
| Coluna | Descrição |
|---|---|
| `DT_SORO`, `RESUL_SORO` | Sorologia (IgM) |
| `DT_NS1`, `RESUL_NS1` | NS1 (antígeno, só DENG) |
| `DT_VIRAL`, `RESUL_VI_N` | Isolamento viral |
| `DT_PCR`, `RESUL_PCR_` | PCR |
| `DT_CHIK_S1`, `DT_CHIK_S2`, `DT_PRNT`, `RES_CHIKS1`, `RES_CHIKS2`, `RESUL_PRNT` | Sorologias seriadas chikungunya |
| `SOROTIPO` | Sorotipo DENV (1-4) |
| `HISTOPA_N`, `IMUNOH_N` | Histopatologia/imuno-histoquímica (pós-óbito) |

#### Sinais de alarme (dengue grave)
| Coluna | |
|---|---|
| `ALRM_HIPOT`, `ALRM_PLAQ`, `ALRM_VOM`, `ALRM_SANG`, `ALRM_HEMAT`, `ALRM_ABDOM`, `ALRM_LETAR`, `ALRM_HEPAT`, `ALRM_LIQ` | Sinais de alarme + datas |

#### Sinais de gravidade
| Coluna | |
|---|---|
| `GRAV_PULSO`, `GRAV_CONV`, `GRAV_ENCH`, `GRAV_INSUF`, `GRAV_TAQUI`, `GRAV_EXTRE`, `GRAV_HIPOT`, `GRAV_HEMAT`, `GRAV_MELEN`, `GRAV_METRO`, `GRAV_SANG`, `GRAV_AST`, `GRAV_MIOC`, `GRAV_CONSC`, `GRAV_ORGAO` | Sinais de gravidade clínica |

#### Manifestações hemorrágicas
| `MANI_HEMOR`, `EPISTAXE`, `GENGIVO`, `METRO`, `PETEQUIAS`, `HEMATURA`, `SANGRAM`, `LACO_N`, `PLASMATICO`, `EVIDENCIA`, `PLAQ_MENOR`, `CON_FHD`, `COMPLICA` |

#### Específicas
- **DENG (`DENGBR{YY}`)**: ~122 colunas; `CLASSI_FIN` codifica `5`=clássica, `10`=com sinais de alarme, `11`=grave, `12`=descartado, `13`=chikungunya/zika
- **CHIK (`CHIKBR{YY}`)**: ~122 colunas; `CLINC_CHIK`=manifestação atípica
- **ZIKA (`ZIKABR{YY}`)**: schema mais enxuto (~94 col); foco em gestantes, microcefalia. Específica: `RES_PCR_ZI`, `CSTRA_ZIKA`

### 2.2 Doenças bacterianas — TUBE, MENI, COLE, COQU, DIFT, FTIF, LEPT, TETA, TETN, TRAC

#### TUBE (Tuberculose)
Schema rico (~85 col). Específico:
- `BACILOSC_E` — baciloscopia escarro
- `RAIOX_TORA` — Rx tórax
- `HIV` — sorologia HIV
- `HISTOPATOL` — histopatologia
- `BAAR`, `TESTE_SENS` — testes
- `TRATAMENTO` — esquema (`1`=básico, `2`=multiresistente)
- `FORMA` — forma clínica (`1`=pulmonar, `2`=extra-pulmonar)
- `EXTRAPU1_N`, `EXTRAPU2_N` — sítios extra-pulmonares
- `BENEFICIO` — recebe benefício social?
- `SITUA_9_M` — situação no 9º mês de tratamento (cura/abandono)

#### MENI (Meningite)
- `CRITERIO` codifica diagnóstico etiológico
- `SOROGRUPO` — sorogrupo meningocócica
- `CON_LCR`, `QT_PROT_LC`, `QT_GLIC_LC`, `QT_CELU_LC` — análise do líquor

#### LEPT (Leptospirose)
- `FEBRE`, `CEFALEIA`, `MIALGIA`, `PROST`, `ICTERICIA`, `ANUR_OLIG`, `CONJUNTIVAL` — sinais
- `EVOL_CASO` — desfecho

#### Outras: COLE, COQU, DIFT, FTIF, TETA, TETN, TRAC
Esquemas mais enxutos (40-70 col). Foco em sintomas + exame laboratorial + vacinação prévia.

### 2.3 Viroses — EXAN, HANT, HEPA, RAIV, ROTA, VARC

- **EXAN (exantemáticas)**: dengue/sarampo/rubéola/etc. Sinais: `FEBRE`, `EXANTEMA`, `CONJUNTVIT`, `TOSSE`, `CORIZA`. Sorologias: `SOROIGM_S`, `SOROIGG_S`
- **HEPA (hepatites virais)**: tipo viral em `CLASSI_FIN` (`1`=A, `2`=B, `3`=C, `4`=D, `5`=E). Marcadores: `HBSAG`, `ANTIHBS`, `ANTIHBC`, `HBEAG`, `ANTIHBE`, `ANTI_HAV`, `ANTI_HCV`, `ANTI_HEV`, `HCVRNA`
- **RAIV (raiva humana)**: sintomas neurológicos + histórico de exposição (`ANIMAL`, `EXPO_RAIV`)
- **HANT (hantavirose)**: pulmonar/renal; foco no contato (`CONTATO`, `LIMPESA_R`, `RATOEXP`)
- **ROTA (rotavírus)**: gastroenterite. Específico: vacinação (`VAC_ROTA`)
- **VARC (varicela)**: vacinação (`VAC_PRECED`), gravidade (`ENCEFALIT`, `PNEUMONIA`)

### 2.4 Parasitoses — CHAG, ESQU, LEIV, LTAN, MALA, TOXG, TOXC

- **MALA (malária)**: `EXAME` (laboratorial), `RESULT_EX` (espécie: P. falciparum, vivax, malariae, etc.)
- **CHAG (Chagas aguda)**: forma de transmissão (`ORAL`, `MAECHAGA`), parasitológico
- **ESQU (esquistossomose)**: contato com água, ovos no exame
- **LEIV/LTAN (leishmaniose visceral/tegumentar)**: hemograma, sorologia, espécie
- **TOXG (toxoplasmose gestante)**: sorologia IgM/IgG, idade gestacional
- **TOXC (toxoplasmose congênita)**: investigação no RN

### 2.5 HIV/AIDS — AIDA, AIDC, HIVA, HIVC, HIVE, HIVG

Esses 6 grupos têm schemas grandes (60-110 col).

- **AIDA (AIDS adulto)**: 77 col. Marcadores clínicos (`ANT_TUBERC`, `ANT_HERPES`, `ANT_CAQUEX`, `ANT_DIARRE`, etc.). Exames (`LAB_TRIAGE`, `LAB_CONFIR`, `TPRAPIDO1/2/3`, `DT_RAPIDO`)
- **AIDC (AIDS criança)**: 104 col. Investigação perinatal (`ANT_PERINA`, `ANT_T_HEMO`)
- **HIVA (HIV gestante/parturiente)**: 60+ col. Foco em transmissão vertical
- **HIVC (HIV criança exposta)**: 60 col
- **HIVE (HIV exposição ocupacional)**: 60 col
- **HIVG (HIV gestante)**: 60+ col

### 2.6 Sífilis — SIFA, SIFC, SIFG

- **SIFA (sífilis adquirida adulto)**: ~45 col. `VDRL`, `TPESQ_VDRL`, `TPTRATA`, `CLINICA` (primária, secundária, latente, terciária)
- **SIFC (sífilis congênita)**: ~70 col. Foco no RN: `LIQUOR_VDRL`, `LIQUOR_RX`, `RADIOLOGIA`, `EVO_BEBE`
- **SIFG (sífilis gestante)**: ~45 col. `IDADE_GEST`, `TIPO_TESTE`, `TRATAGEST`

### 2.7 Saúde do Trabalhador — ACBI, ACGR, CANC, DERM, LER, LERD, PAIR, PNEU, MENT, NTRA

- **ACBI (Acidente Biológico)**: 68 col. Exposição: `PERCUTANEA`, `PELE_INTEG`, `MAT_ORG`, `TIPO_ACID`, `AGENTE`. EPI: `LUVA`, `AVENTAL`, `OCULOS`, `MASCARA`. Vacinas: `VACINA`, `ANTI_HIV`, `HBSAG`, `ANTI_HBS`, `ANTI_HCV`. Profilaxia: `SEM_QUIMIO`, `AZT3TC`, `IMU_HEP_B`
- **ACGR (Acidente de Trabalho Grave)**: 54 col. `LOCAL_ACID`, `HORA_ACID`, `TIPO_ACID`, `CID_ACID`, `CID_LESAO`, `PART_CORP1/2/3` (partes do corpo afetadas), `REGIME` (formal/informal)
- **CANC (Câncer relacionado ao trabalho)**: ~66 col. Exposições ocupacionais: `ASBESTO`, `SILICA`, `AMINA`, `BENZENO`, `ALCATRAO`, `HIDROCARBO`, `OLEOS`, `BERILIO`, `CADMIO`, `CROMO`, `NIQUEL`, `IONIZANTES`, `NAO_IONIZA`, `HORMONIO`, `NEOPLASICO`. Hábitos: `FUMA`, `TEMPO_FUMA`
- **DERM (Dermatoses ocupacionais)**, **LER/LERD (LER/DORT)**, **PAIR (Perda auditiva)**, **PNEU (Pneumoconioses)**: schemas similares, com exposições específicas (poeira, ruído, produtos químicos)
- **MENT (Transtornos mentais relacionados ao trabalho)**: jornada, agente estressor
- **NTRA (Notificação de surto ocupacional)**: surto coletivo

### 2.8 Acidentes com animais peçonhentos e zoonoses — ANIM, ANTR

- **ANIM (Acidente com Animal Peçonhento)**: 75 col. Tipo: `TP_ACIDENT` (1=cobra, 2=aranha, 3=escorpião, etc.). Animais: `ANI_SERPEN`, `ANI_ARANHA`, `ANI_LAGART`. Soroterapia: `CON_SOROTE`, `NU_AMPOLAS` (e variantes `NU_AMPOL_1` a `_9` por tipo). Sintomas locais/sistêmicos
- **ANTR (Atendimento Antirrábico)**: 78 col. Tipo de exposição: `ANT_CONTAT`, `ANT_ARRANH`, `ANT_LAMBED`, `ANT_MORDED`. Local: `ANT_CABECA`, `ANT_MAOS`, etc. Vacina/soro: `DOSES`, `LAB_VACINA`, `TIP_SORO`

### 2.9 Outras notificações — IEXO, BOTU, ESPO, FMAC, HANS, PEST, PFAN, SRC, DCRJ, SDTA, VIOL

- **IEXO (Intoxicação exógena)**: agente tóxico, via, circunstância
- **BOTU (Botulismo)**: 149 col. Sintomas neurológicos detalhados (`STDIPLOPIA`, `STDISFONIA`, `STPTOSE`, `STMIDRIASE`, etc.), alimento suspeito (`STCASEIRA`, `STCOMERCIO`, `STDOMICILI`)
- **HANS (Hanseníase)**: classificação operacional (PB/MB), número de lesões, baciloscopia, esquema PQT
- **PFAN (Paralisia Flácida Aguda)**: investigação de pólio
- **SRC (Síndrome Respiratória Aguda)**: predecessora de SRAG/COVID
- **VIOL (Violência Interpessoal/Autoprovocada)**: tipos de violência (física, sexual, psicológica, financeira, negligência), agressor, local
- **DCRJ (Creutzfeldt-Jakob)**: neurológica rara
- **SDTA (Doenças Transmitidas por Alimentos)**: surto, alimento, agente
- **FMAC (Febre Maculosa)**: vetor (carrapato), exposição
- **ESPO (Esporotricose)**: contato com gato, lesão cutânea
- **PEST (Peste)**: zoonose rara

---

## 3. Lista completa dos 58 grupos

| Código | Nome | Tema | # col aprox |
|---|---|---|---|
| `ACBI` | Acidente material biológico | Trabalhador | 68 |
| `ACGR` | Acidente de trabalho grave | Trabalhador | 54 |
| `AIDA` | AIDS adulto | HIV/AIDS | 77 |
| `AIDC` | AIDS criança | HIV/AIDS | 104 |
| `ANIM` | Animais peçonhentos | Zoonose | 75 |
| `ANTR` | Atendimento antirrábico | Zoonose | 78 |
| `BOTU` | Botulismo | Bacteriana | 149 |
| `CANC` | Câncer ocupacional | Trabalhador | 66 |
| `CHAG` | Chagas aguda | Parasitose | 108 |
| `CHIK` | Chikungunya | Arbovirose | 122 |
| `COLE` | Cólera | Bacteriana | ~40 |
| `COQU` | Coqueluche | Bacteriana | ~50 |
| `DCRJ` | Creutzfeldt-Jakob | Neurológica | ~40 |
| `DENG` | Dengue | Arbovirose | ~122 |
| `DERM` | Dermatoses ocupacionais | Trabalhador | ~60 |
| `DIFT` | Difteria | Bacteriana | ~50 |
| `ESPO` | Esporotricose | Fúngica/zoonose | ~50 |
| `ESQU` | Esquistossomose | Parasitose | ~50 |
| `EXAN` | Doenças exantemáticas | Viroses | ~70 |
| `FMAC` | Febre maculosa | Bacteriana/zoonose | ~60 |
| `FTIF` | Febre tifoide | Bacteriana | ~50 |
| `HANS` | Hanseníase | Bacteriana | ~50 |
| `HANT` | Hantavirose | Virose/zoonose | ~80 |
| `HEPA` | Hepatites virais | Virose | ~100 |
| `HIVA` | HIV adulto | HIV/AIDS | ~60 |
| `HIVC` | HIV criança exposta | HIV/AIDS | ~60 |
| `HIVE` | HIV exposição ocupacional | HIV/AIDS | ~60 |
| `HIVG` | HIV gestante | HIV/AIDS | ~60 |
| `IEXO` | Intoxicação exógena | Outros | ~120 |
| `LEIV` | Leishmaniose visceral | Parasitose | ~70 |
| `LEPT` | Leptospirose | Bacteriana/zoonose | ~80 |
| `LER` | LER/DORT (legacy) | Trabalhador | ~50 |
| `LERD` | LER/DORT | Trabalhador | ~60 |
| `LTAN` | Leishmaniose tegumentar | Parasitose | ~70 |
| `MALA` | Malária | Parasitose | ~80 |
| `MENI` | Meningite | Bacteriana/viral | ~80 |
| `MENT` | Transtornos mentais ocupacionais | Trabalhador | ~50 |
| `NTRA` | Notificação de surto trabalhador | Trabalhador | ~30 |
| `PAIR` | Perda auditiva ocupacional | Trabalhador | ~50 |
| `PEST` | Peste | Bacteriana/zoonose | ~50 |
| `PFAN` | Paralisia flácida aguda | Viral (pólio) | ~60 |
| `PNEU` | Pneumoconioses | Trabalhador | ~60 |
| `RAIV` | Raiva humana | Virose/zoonose | ~70 |
| `ROTA` | Rotavírus | Virose | ~50 |
| `SDTA` | DTA (Doenças Transmitidas por Alimentos) | Surto | ~50 |
| `SIFA` | Sífilis adquirida | Bacteriana | ~45 |
| `SIFC` | Sífilis congênita | Bacteriana | ~70 |
| `SIFG` | Sífilis gestante | Bacteriana | ~45 |
| `SRC` | Síndrome Resp. Aguda | Viral | ~60 |
| `TETA` | Tétano acidental | Bacteriana | ~50 |
| `TETN` | Tétano neonatal | Bacteriana | ~50 |
| `TOXC` | Toxoplasmose congênita | Parasitose | ~70 |
| `TOXG` | Toxoplasmose gestante | Parasitose | ~70 |
| `TRAC` | Tracoma | Bacteriana | ~40 |
| `TUBE` | Tuberculose | Bacteriana | ~85 |
| `VARC` | Varicela | Virose | ~50 |
| `VIOL` | Violência interpessoal/autoprovocada | Social | ~120 |
| `ZIKA` | Zika | Arbovirose | ~94 |

---

## Glossário

| Sigla | Significado |
|---|---|
| **SINAN** | Sistema de Informação de Agravos de Notificação |
| **CID-10** | Classificação Internacional de Doenças |
| **EPI** | Equipamento de Proteção Individual |
| **PQT** | Poliquimioterapia (hanseníase) |
| **VDRL** | Veneral Disease Research Laboratory (sorologia sífilis) |
| **NS1** | Antígeno NS1 (dengue) |
| **PCR** | Reação em Cadeia da Polimerase |
| **DUM** | Data da Última Menstruação |
| **DTA** | Doença Transmitida por Alimento |
| **LER/DORT** | Lesão por Esforço Repetitivo / Distúrbio Osteomuscular Relacionado ao Trabalho |
| **CAPS** | Centro de Atenção Psicossocial |
| **PRNT** | Teste de Neutralização por Redução de Placas (sorologia arboviroses) |

---

## Joins típicos

```
SINAN.* ─┬─ ID_UNIDADE ──── CNES (CNES.ST)          → unidade notificadora
         ├─ ID_MN_RESI ──── codmun (IBGE)           → município de residência
         ├─ ID_MUNICIP ──── codmun (IBGE)           → município de notificação
         └─ DT_NOTIFIC ──── (SIM.DO via CAUSABAS)   → linkage probabilístico em casos de óbito
```

## Caveats que economizam tempo

1. **Datas em `YYYYMMDD`** (string) — diferente do SIM/SINASC. Cuidado se for cruzar.
2. **`SEM_NOT` / `SEM_PRI`** são semanas epidemiológicas (`YYYYWW`), não ISO 8601. Tem reset no início de cada ano.
3. **`NU_IDADE_N` é codificada** (mesmo padrão do SIM/SINASC) — `4028` = 28 anos.
4. **`CLASSI_FIN` varia por doença**. Sempre confira o dicionário oficial daquela doença antes de filtrar. Em geral, `CLASSI_FIN ∈ {1,5}` significa "confirmado".
5. **Subnotificação MASSIVA** em quase tudo. Notificação compulsória ≠ ocorrência real. Subnotificação típica: hanseníase ~30%, hepatite ~80%, dengue varia muito.
6. **Datas de transferência (`DT_TRANS*`)** são úteis pra entender latência de notificação. Subtraindo de `DT_NOTIFIC`, dá medida da agilidade do sistema.
7. **SINAN é Brasil-wide** — pra filtrar pro seu estado de interesse, use `SG_UF_NOT == 43` (RS) **e** `SG_UF == 43` (residência). UFs são números aqui, não siglas.
8. **`ID_AGRAVO`** dentro de um mesmo arquivo de doença pode variar (ex.: HEPA tem HEPA A, B, C, D, E todos no mesmo arquivo, codificados por CID no `ID_AGRAVO`).
9. **VIOL** tem 5 "tipos" empilhados na mesma linha (cada coluna `LES_*` é uma forma): física, psicológica, sexual, tortura, tráfico, financeira, negligência. Útil mas complexo.
10. **Pra pegar evolução completa de um caso (notificação → encerramento)**, precisa de `DT_NOTIFIC` + `DT_ENCERRA`. Casos abertos ao fim do ano ficam com `DT_ENCERRA` vazio até virem encerrados no ano seguinte (mas continuam no arquivo do ano original).
