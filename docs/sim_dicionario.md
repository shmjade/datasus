# Dicionário de Dados — SIM (Sistema de Informações sobre Mortalidade)

O SIM consolida **todos os óbitos** registrados no Brasil, com base na Declaração de Óbito (DO). Granularidade: **anual × UF**.

| Grupo | Nome | Conteúdo | Relacionado a DO |
|---|---|---|---|
| **DO** | Declaração de Óbito geral | **Todos os óbitos** (universo) | — |
| `DOFET` | Óbitos fetais | ≥22 sem ou ≥500g | subconjunto |
| `DOEXT` | Óbitos por causas externas | CID V-Y | subconjunto |
| `DOINF` | Óbitos infantis | < 1 ano | subconjunto |
| `DOMAT` | Óbitos maternos | causas obstétricas | subconjunto |

**Atenção:** `DO` é o grupo geral; os 4 subgrupos são **extrações temáticas** com colunas extras. **Não some** entre eles — geraria duplicata. No catálogo pysus pra RS, só o `DO` está publicado. **O dicionário abaixo cobre o `DO`.**

Convenção do nome do arquivo: `DO{UF}{YYYY}.parquet` (ex.: `DORS2024.parquet`).

---

## DO — Declaração de Óbito (87 colunas)

Cada linha = **um óbito**. ~100k/ano no RS.

### Identificação do registro

| Coluna | Descrição | Domínio |
|---|---|---|
| `CONTADOR` | Sequencial dentro do lote | inteiro |
| `NUMEROLOTE` | Número do lote de envio | string |
| `ORIGEM` | Origem do registro | `1`=Oracle (sistema novo), `2`=BD antigo |
| `TIPOBITO` | Tipo de óbito | `1`=fetal, `2`=não-fetal |
| `VERSAOSIST`, `VERSAOSCB` | Versões do sistema e classificador | string |
| `STCODIFICA` | Status de codificação | `S`/`N` |
| `CODIFICADO` | Foi codificado? | `S`/`N` |
| `ATESTANTE` | Quem atestou | `1`=médico assistente, `2`=substituto, `3`=IML, `4`=SVO |

### Datas e horários

| Coluna | Descrição | Domínio |
|---|---|---|
| `DTOBITO` | Data do óbito | `DDMMYYYY` |
| `HORAOBITO` | Hora do óbito | `HHMM` |
| `DTNASC` | Data de nascimento | `DDMMYYYY` |
| `DTATESTADO` | Data do atestado | `DDMMYYYY` |
| `DTINVESTIG` | Data da investigação (causas externas) | `DDMMYYYY` |
| `DTCADASTRO` | Cadastro no SIM | `DDMMYYYY` |
| `DTCADINV` | Cadastro da investigação | `DDMMYYYY` |
| `DTCADINF` | Cadastro de informação adicional | `DDMMYYYY` |
| `DTRECEBIM` | Recebimento na esfera estadual | `DDMMYYYY` |
| `DTRECORIGA` | Recebimento na origem (município) | `DDMMYYYY` |
| `DTCONCASO` | Conclusão do caso | `DDMMYYYY` |
| `DTCONINV` | Conclusão da investigação | `DDMMYYYY` |
| `DIFDATA` | Diferença em dias (informativo) | inteiro |
| `NUDIASOBCO` | Dias entre óbito e conclusão | |
| `NUDIASOBIN` | Dias entre óbito e investigação | |
| `NUDIASINF` | Dias até cadastro de informação | |

**Caveat de formato:** datas no SIM vêm como `DDMMYYYY` (não `YYYYMMDD` como no SIH). Cuidado no parse.

### Demografia do falecido

| Coluna | Descrição | Domínio |
|---|---|---|
| `IDADE` | **Idade codificada** | 3-4 dígitos, ver tabela abaixo |
| `SEXO` | Sexo | `1`=masc, `2`=fem, `0`=ignorado (lacuna intencional: difere de SIH onde 3=fem) |
| `RACACOR` | Raça/cor | `1`=branca, `2`=preta, `3`=amarela, `4`=parda, `5`=indígena, `9`=ignorado |
| `ESTCIV` | Estado civil | `1`=solteiro, `2`=casado, `3`=viúvo, `4`=separado, `5`=união estável, `9`=ignorado |
| `ESC` | Escolaridade (campo antigo) | `1`=nenhuma, `2`=1-3 anos, `3`=4-7 anos, `4`=8-11 anos, `5`=≥12 anos, `9`=ignorado |
| `ESC2010` | Escolaridade (Censo 2010, recomendado) | `0`-`5` + `9` |
| `ESCFALAGR1` | Escolaridade agregada | |
| `SERIESCFAL` | Série de escolaridade | |
| `OCUP` | Ocupação habitual (CBO-2002) | 6 dígitos |
| `NATURAL` | Naturalidade | código (`843`=Brasil) |
| `CODMUNNATU` | Município de naturalidade | IBGE 6 |
| `CODMUNRES` | **Município de residência** (chave de geolocalização) | IBGE 6 |

#### Tabela de decodificação de `IDADE`

| 1º dígito | Unidade | Demais dígitos |
|---|---|---|
| `0` | Anos (especial) | reservado |
| `1` | Minutos | `<60` |
| `2` | Horas | `<24` |
| `3` | Dias | `<30` |
| `4` | Meses | `<12` |
| `4` | **Anos** | `40` a `99` (idade direta) |
| `5` | Anos | `0` a `19` (centenários: 100-119 anos) |

Exemplo: `IDADE=470` significa 70 anos. `IDADE=4070` também (70 anos). Para `<1 ano`: `IDADE=305` = 5 dias, `IDADE=402` = 2 meses.

### Local do óbito

| Coluna | Descrição | Domínio |
|---|---|---|
| `LOCOCOR` | Local de ocorrência | `1`=hospital, `2`=outro estab. saúde, `3`=domicílio, `4`=via pública, `5`=outros, `9`=ignorado |
| `CODESTAB` | **CNES do estabelecimento** (se hospital) | 7 dígitos |
| `ESTABDESCR` | Descrição do estabelecimento | string |
| `CODMUNOCOR` | Município de ocorrência (IBGE 6) | |

### Materno-fetal (se aplicável)

| Coluna | Descrição |
|---|---|
| `IDADEMAE` | Idade da mãe |
| `ESCMAE`, `ESCMAE2010`, `SERIESCMAE`, `ESCMAEAGR1` | Escolaridade da mãe |
| `OCUPMAE` | Ocupação da mãe (CBO) |
| `QTDFILVIVO` | Filhos vivos |
| `QTDFILMORT` | Filhos mortos anteriores |
| `GRAVIDEZ` | Tipo de gravidez | `1`=única, `2`=dupla, `3`=tripla ou mais, `9`=ignorada |
| `SEMAGESTAC` | Semanas de gestação |
| `GESTACAO` | Faixa gestacional | `1`=<22 sem, `2`=22-27 sem, `3`=28-31 sem, `4`=32-36 sem, `5`=37-41 sem, `6`=≥42 sem |
| `PARTO` | Tipo de parto | `1`=vaginal, `2`=cesário, `9`=ignorado |
| `OBITOPARTO` | Óbito em relação ao parto | `1`=antes, `2`=durante, `3`=depois |
| `PESO` | Peso ao nascer (g) | inteiro |
| `TPMORTEOCO` | Momento óbito materno | `1`=durante gestação, `2`=durante parto, `3`=puerpério |
| `OBITOGRAV` | Óbito durante gravidez? | `1/2` |
| `OBITOPUERP` | Óbito no puerpério? | `1`=até 42 dias, `2`=43 dias-1 ano |
| `MORTEPARTO` | Morte em relação ao parto |
| `CAUSAMAT` | Causa materna |

### Atendimento médico

| Coluna | Descrição | Domínio |
|---|---|---|
| `ASSISTMED` | Recebeu assistência médica? | `1`=sim, `2`=não, `9`=ignorado |
| `EXAME` | Exames complementares? | `1/2` |
| `CIRURGIA` | Cirurgia? | `1/2` |
| `NECROPSIA` | Necropsia? | `1`=sim, `2`=não, `9`=ignorado |

### Causa do óbito (CID-10) — **o coração do SIM**

| Coluna | Descrição |
|---|---|
| `LINHAA` | Causa terminal (1ª linha do atestado) — ex.: `*J960` (insuf respiratória aguda) |
| `LINHAB` | Causa antecedente intermediária |
| `LINHAC` | Causa antecedente |
| `LINHAD` | Causa básica original do atestante |
| `LINHAII` | Outras causas contribuintes (Parte II do atestado) |
| `ATESTADO` | Texto literal das causas (concatenação das linhas) |
| **`CAUSABAS`** | **Causa básica codificada** (após SCB) — **chave da maioria das análises** |
| `CAUSABAS_O` | Causa básica original (sem ajustes do SCB) |
| `CB_PRE` | Causa básica pré-codificada |

**Como o SCB (Seletor de Causa Básica) decide CAUSABAS:** algoritmo do MS aplica regras da CID-10 sobre as 5 linhas pra escolher qual evento patológico **iniciou a cadeia** que levou à morte. Quase sempre é uma das linhas C/D, raramente A.

### Causas externas (preenchido só se CAUSABAS começa com V-Y)

| Coluna | Descrição | Domínio |
|---|---|---|
| `CIRCOBITO` | Circunstância | `1`=acidente, `2`=suicídio, `3`=homicídio, `4`=outros, `9`=ignorado |
| `ACIDTRAB` | Acidente de trabalho? | `1/2/9` |
| `FONTE` | Fonte da informação | código |

### Investigação adicional (mortalidade materna/infantil)

| Coluna | Descrição |
|---|---|
| `STDOEPIDEM` | DO foi investigada por vigilância epidemiológica? | `0/1` |
| `STDONOVA` | DO substitui outra (correção)? | `0/1` |
| `TPPOS` | Tipo de pós-investigação |
| `FONTEINV` | Fonte da investigação |
| `TPNIVELINV` | Nível de investigação |
| `TPRESGINFO` | Tipo de resgate de informação |
| `TPOBITOCOR` | Tipo de óbito corrigido |
| `FONTES`, `FONTESINF` | Fontes de informação |
| `ALTCAUSA` | Alteração de causa após investigação? | `0/1` |
| `COMUNSVOIM` | Comunicação à vigilância de óbito infantil/materno |

---

## Glossário

| Sigla | Significado |
|---|---|
| **DO** | Declaração de Óbito |
| **SIM** | Sistema de Informações sobre Mortalidade |
| **CID-10** | Classificação Internacional de Doenças, 10ª revisão |
| **SCB** | Seletor de Causa Básica (algoritmo MS) |
| **SVO** | Serviço de Verificação de Óbito |
| **IML** | Instituto Médico Legal |
| **CBO-2002** | Classificação Brasileira de Ocupações |

---

## Joins típicos

```
SIM.DO ─┬─ CODESTAB ─── CNES (CNES.ST)    → estabelecimento onde ocorreu o óbito
        ├─ CODMUNRES ── codmun (IBGE)     → município de residência
        ├─ CODMUNOCOR ── codmun (IBGE)    → município de ocorrência
        └─ N_AIH    ─── (SIH.RD)          → ❌ não existe — usar (CODESTAB + CODMUNRES + DTOBITO ± idade) pra "linkage probabilístico"

CAUSABAS ─── CID-10 (referência externa)  → tabela oficial WHO/MS
```

## Caveats que economizam tempo

1. **Datas em `DDMMYYYY`** — não `YYYYMMDD`. Pegadinha clássica. Parse com `pd.to_datetime(s, format="%d%m%Y")`.
2. **`SEXO=2 é feminino no SIM, diferente do SIH (SEXO=3).** Inconsistência famosa entre sistemas DataSUS.
3. **`IDADE` é codificada** (primeiro dígito = unidade). Não interprete como inteiro direto.
4. **`CAUSABAS` é o que você quer pra maioria das análises** — é a causa "que iniciou a cadeia", já aplicado o algoritmo SCB. Não use `LINHAA` (causa imediata).
5. **`CAUSABAS_O` pode diferir de `CAUSABAS`** em ~10% dos óbitos (correções pelo SCB ou investigação).
6. **Óbitos por causas externas (`V*`-`Y*` em `CAUSABAS`) frequentemente têm CODESTAB vazio** — morrem na via pública ou em casa.
7. **Subnotificação:** mortalidade infantil e materna têm subnotificação histórica de ~10-15% no Brasil; melhor no Sul. Pra análise rigorosa, usar fatores de correção (PRO-SUS / IHME).
8. **Defasagem:** o SIM tem **lag de ~1 ano** — dados de 2024 só ficam completos em 2025. O catálogo pysus tem `DORS2024.parquet` como mais recente em jun/2026.
9. **`LOCOCOR=1` (hospital) + `CODESTAB`** = chave pra cruzar com SIH e ver se houve internação prévia (mas não há join direto — precisa ser linkage probabilístico).
10. **Para cruzar "óbitos hospitalares" com "internações que terminaram em óbito" (SIH.MORTE=1):** os universos não batem exatamente — SIH cobre só óbitos que ocorreram durante AIHs SUS; SIM cobre TODOS os óbitos hospitalares. Diferença típica: ~20-30%.
