# Dicionário de Dados — SIA (Sistema de Informações Ambulatoriais)

O SIA registra **atendimentos sem internação** pagos pelo SUS: consultas, exames, procedimentos terapêuticos. É o complemento ambulatorial do SIH.

Granularidade: **mensal × UF**. Volume gigantesco — `PA` chega a 4-5 milhões de linhas/mês no RS.

| Grupo | Nome | Linhas/mês (RS) | Conteúdo central |
|---|---|---|---|
| **PA** | Produção Ambulatorial | ~4M | Procedimentos individualizados (uma linha por procedimento) |
| **BI** | BPA Individualizado | ~350k | Boletim de Produção Ambulatorial com paciente identificado (descontinuado em 2011) |
| **PS** | RAAS Psicossocial | ~55k | Atendimentos em CAPS (saúde mental) |
| **SAD** | RAAS Atenção Domiciliar | ~300 | Atendimento domiciliar (SAD/Melhor em Casa) |

**Caveat de escopo:** PA e BI são procedimentos faturados. PS e SAD são RAAS (Registro de Ações Ambulatoriais de Saúde) — formato mais novo, com mais contexto clínico.

---

## PA — Produção Ambulatorial (61 colunas)

A tabela **maior e mais usada** do SIA. Cada linha = um procedimento executado.

Convenção: **a maioria das colunas começa com `PA_`**. Algumas raras não (legacy).

### Identificação do estabelecimento

| Coluna | Descrição |
|---|---|
| `PA_CODUNI` | **CNES do estabelecimento** (chave pra CNES.ST) |
| `PA_GESTAO` | Município de gestão |
| `PA_CONDIC` | Condição da gestão | `EP`=plena, `EM`=municipal |
| `PA_UFMUN` | Município IBGE da unidade |
| `PA_TPUPS` | Tipo de unidade (idêntico a CNES.TP_UNID) |
| `PA_TIPPRE` | Tipo de prestador |
| `PA_MN_IND` | Município/individual | `M`=municipal, `I`=indiv |
| `PA_CNPJCPF` | CNPJ/CPF do estabelecimento |
| `PA_CNPJMNT` | CNPJ da mantenedora |
| `PA_CNPJ_CC` | CNPJ do convênio/contrato |
| `PA_NAT_JUR` | Natureza jurídica |

### Competência e processamento

| Coluna | Descrição |
|---|---|
| `PA_MVM` | Movimento (mês/ano de execução) — `YYYYMM` |
| `PA_CMP` | Competência (mês/ano faturamento) — `YYYYMM` |

### Procedimento

| Coluna | Descrição | Domínio |
|---|---|---|
| `PA_PROC_ID` | **Procedimento SIGTAP (10 dígitos)** | tabela DataSUS |
| `PA_TPFIN` | Tipo de financiamento | `06`=MAC ambulatorial, `04`=PAB, etc. |
| `PA_SUBFIN` | Subfinanciamento | |
| `PA_NIVCPL` | Nível de complexidade | `1`=básica, `2`=média, `3`=alta |
| `PA_DOCORIG` | Documento de origem | `B`=BPA, `I`=BPA-I, `P`=APAC |
| `PA_AUTORIZ` | Número APAC (se aplicável) | |
| `PA_REGCT` | Regra contratual | |
| `PA_INCOUT`, `PA_INCURG` | Incentivos outros / urgência | |
| `PA_SRV_C` | Classificação de serviço/CNES.SR | |
| `PA_INE` | Identificador da equipe (CNES.EP) | 18 dígitos |
| `PA_FNTORC` | Fonte orçamentária | |

### Profissional executor

| Coluna | Descrição |
|---|---|
| `PA_CNSMED` | CNS do profissional executor (15 dígitos) |
| `PA_CBOCOD` | CBO do profissional |

### Paciente

| Coluna | Descrição | Domínio |
|---|---|---|
| `PA_IDADE` | Idade do paciente | string 3 dígitos |
| `PA_FLIDADE` | Flag idade válida | |
| `IDADEMIN`, `IDADEMAX` | Faixa etária esperada pro procedimento | inteiros |
| `PA_SEXO` | Sexo | `M`/`F` |
| `PA_RACACOR` | Raça/cor | mesmo padrão do SIH (`01`=branca etc.) |
| `PA_MUNPCN` | Município de residência do paciente | IBGE 6 |
| `PA_ETNIA` | Etnia indígena | |

### Quantidades e valores (R$)

| Coluna | Descrição |
|---|---|
| `PA_QTDPRO` | Quantidade produzida |
| `PA_QTDAPR` | Quantidade aprovada |
| `PA_VALPRO` | Valor produzido (R$) |
| `PA_VALAPR` | Valor aprovado (R$) — **o que vale pra análise financeira** |
| `PA_DIF_VAL` | Diferença (produzido - aprovado) |
| `NU_VPA_TOT` | Valor total VPA |
| `NU_PA_TOT` | Valor total PA |
| `PA_VL_CF` | Valor componente federal |
| `PA_VL_CL` | Valor componente local |
| `PA_VL_INC` | Valor incentivo |

### Desfecho (preenchido pra APAC)

| Coluna | Descrição |
|---|---|
| `PA_MOTSAI` | Motivo de saída | `00`=continuidade, `11`=alta cura, `14`=transferência, `41`=óbito |
| `PA_OBITO`, `PA_ENCERR`, `PA_PERMAN`, `PA_ALTA`, `PA_TRANSF` | Flags de desfecho (mutuamente exclusivos) |

### CID (preenchido só em APAC e alguns procedimentos)

| Coluna | Descrição |
|---|---|
| `PA_CIDPRI` | CID-10 principal |
| `PA_CIDSEC` | CID-10 secundário |
| `PA_CIDCAS` | CID-10 caso (causa) |
| `PA_CATEND` | Caráter de atendimento | `01`=eletivo, `02`=urgência |

### Outros

| Coluna | Descrição |
|---|---|
| `PA_UFDIF`, `PA_MNDIF` | Flag procedimento em UF/município diferente da residência |
| `PA_INDICA` | Indicação (código DataSUS) |
| `PA_CODOCO` | Código de ocorrência |
| `PA_FLQT` | Flag de quantidade | `R`=registrado |
| `PA_FLER` | Flag de erro |

---

## BI — BPA Individualizado (35 colunas)

**Procedimentos com paciente identificado.** Subconjunto do PA com CNS, data de nascimento, etc. **Descontinuado em 2011** — substituído pelo PA-I em 2012 (que vive dentro do PA com `PA_DOCORIG='I'`).

### Colunas específicas (sem prefixo)

| Coluna | Descrição | Domínio |
|---|---|---|
| `CODUNI` | CNES da unidade |
| `GESTAO` | Município de gestão |
| `CONDIC` | Condição da gestão |
| `UFMUN` | Município IBGE |
| `TPUPS`, `TIPPRE`, `MN_IND` | Tipo unidade, prestador, indicador |
| `CNPJCPF`, `CNPJMNT`, `CNPJ_CC` | Documentos |
| `DT_PROCESS` | Data de processamento | `YYYYMM` |
| `DT_ATEND` | Data do atendimento | `YYYYMM` |
| `PROC_ID` | Procedimento SIGTAP |
| `TPFIN`, `SUBFIN`, `COMPLEX` | Financiamento e complexidade |
| `AUTORIZ` | Autorização |
| `CNSPROF` | CNS do profissional |
| `CBOPROF` | CBO do profissional |
| `CIDPRI` | CID principal |
| `CATEND` | Caráter de atendimento |
| `CNS_PAC` | **CNS do paciente** (ofuscado no parquet do pysus) |
| `DTNASC` | Data de nascimento | `YYYYMMDD` |
| `TPIDADEPAC` | Tipo da idade | `4`=anos |
| `IDADEPAC` | Idade | inteiro |
| `SEXOPAC` | Sexo |
| `RACACOR`, `ETNIA` | Raça/cor e etnia |
| `MUNPAC` | Município residência |
| `QT_APRES`, `QT_APROV` | Quantidades apresentada/aprovada |
| `VL_APRES`, `VL_APROV` | Valores apresentado/aprovado |
| `UFDIF`, `MNDIF` | Flags UF/município diferente |

**Caveat:** desde 2012 esses dados estão dentro do PA com `PA_DOCORIG='I'`. **Use BI só pra análise histórica pré-2012.**

---

## PS — RAAS Psicossocial (45 colunas)

**Atendimentos em CAPS** (Centros de Atenção Psicossocial). Estrutura RAAS = registro detalhado de longa duração (não 1 procedimento/linha, mas 1 plano de cuidado/linha).

### Identificação

| Coluna | Descrição |
|---|---|
| `CNES_EXEC` | CNES do CAPS (chave) |
| `GESTAO`, `CONDIC`, `UFMUN`, `TPUPS`, `TIPPRE`, `MN_IND` | Padrão SIA |
| `CNPJCPF`, `CNPJMNT` | Documentos |
| `NAT_JUR` | Natureza jurídica |

### Competência

| Coluna | Descrição |
|---|---|
| `DT_PROCESS` | Mês de processamento (`YYYYMM`) |
| `DT_ATEND` | Mês do atendimento (`YYYYMM`) |
| `INICIO`, `FIM` | Datas de início/fim do período RAAS (`YYYYMMDD`) |
| `PERMANEN` | Permanência em dias |

### Paciente

| Coluna | Descrição |
|---|---|
| `CNS_PAC` | CNS do paciente (ofuscado) |
| `DTNASC` | Nascimento |
| `TPIDADEPAC`, `IDADEPAC`, `SEXOPAC`, `RACACOR`, `ETNIA`, `NACION_PAC`, `MUNPAC` | Demografia padrão |
| `SIT_RUA` | Situação de rua? | `S`/`N` |
| `TP_DROGA` | Tipo de droga | `CO`=cocaína, `AL`=álcool, `MA`=maconha, `CR`=crack, etc. |
| `LOC_REALIZ` | Local | `C`=CAPS, `D`=domicílio, etc. |

### Atendimento

| Coluna | Descrição |
|---|---|
| `CATEND` | Caráter de atendimento |
| `CIDPRI` | CID principal (geralmente F00-F99, transtornos mentais) |
| `CIDASSOC` | CID associado |
| `ORIGEM_PAC` | Origem do paciente |
| `MOT_COB`, `DT_MOTCOB` | Motivo da cobrança e data |
| `DESTINOPAC` | Destino final |
| `COB_ESF` | Cobertura ESF (paciente)? |
| `CNES_ESF` | CNES da equipe ESF |

### Procedimento

| Coluna | Descrição |
|---|---|
| `PA_PROC_ID` | Procedimento SIGTAP |
| `PA_QTDPRO`, `PA_QTDAPR` | Quantidades |
| `PA_SRV` | Serviço (CNES.SR) |
| `PA_CLASS_S` | Classificação do serviço |
| `QTDATE`, `QTDPCN` | Quantidade atendimentos / pacientes |

---

## SAD — RAAS Atenção Domiciliar (44 colunas)

**Atendimento domiciliar** (Serviço de Atenção Domiciliar / Melhor em Casa). Estrutura quase idêntica à do PS.

### Diferenças vs. PS

| Coluna | Descrição |
|---|---|
| `PA_EQUIPE` | Identificador da equipe SAD |
| `PA_TP_EQP` | Tipo de equipe | `01`=EMAD, `02`=EMAP |
| `PA_CID` | CID do procedimento |
| `CO_INE` | Identificador INE da equipe (CNES.EP) | 10 dígitos |

**Sem:** `SIT_RUA`, `TP_DROGA`, `LOC_REALIZ`, `CIDASSOC`, `ORIGEM_PAC`, `COB_ESF` (não fazem sentido pro contexto domiciliar).

---

## Glossário

| Sigla | Significado |
|---|---|
| **SIGTAP** | Sistema de Gerenciamento da Tabela de Procedimentos |
| **BPA** | Boletim de Produção Ambulatorial |
| **BPA-I** | BPA Individualizado |
| **APAC** | Autorização de Procedimentos Ambulatoriais (alta complexidade) |
| **RAAS** | Registro de Ações Ambulatoriais de Saúde |
| **PS** | RAAS Psicossocial |
| **SAD** | RAAS Serviço de Atenção Domiciliar |
| **CAPS** | Centro de Atenção Psicossocial |
| **MAC** | Média e Alta Complexidade (subteto financeiro) |
| **PAB** | Piso de Atenção Básica |
| **CNS** | Cartão Nacional de Saúde |
| **INE** | Identificador Nacional de Equipes |

---

## Joins típicos

```
SIA.PA ─┬─ PA_CODUNI ─── CNES (CNES.ST)         → estabelecimento
        ├─ PA_PROC_ID ── proc       (SIGTAP)    → custo unitário oficial
        ├─ PA_INE    ─── IDEQUIPE (CNES.EP)     → equipe da AB executora
        ├─ PA_CNSMED ─── CNS_PROF (CNES.PF)     → profissional executor (vínculos)
        └─ PA_MUNPCN ─── codmun    (IBGE)        → residência do paciente

SIA.PS / SAD ─── CNS_PAC ─── (SIH.RD)  → não existe link direto; PA-I é a única ligação por paciente
```

## Caveats que economizam tempo

1. **Volume:** PA é descomunal (~4M linhas/mês no RS, ~70 MB parquet). Pra agregar, prefira pyspark/duckdb ao pandas. Pro range de 10 anos × 12 meses, são ~500M linhas — não cabe em pandas.
2. **`PA_VALAPR` ≠ `PA_VALPRO` em ~5% dos casos** — glosas. Use `PA_VALAPR` pra orçamento real, `PA_VALPRO` pra "intenção".
3. **`PA_DOCORIG='I'` é BI moderno**, integrado ao PA desde 2012. Use isso pra reconstituir a série histórica de BPA-I sem precisar de BI legado.
4. **`PA_CIDPRI` é vazio (`0000`) na maioria dos procedimentos** — só preenchido em APAC e alguns BPA-I específicos (ex.: oncologia, psicossocial).
5. **`PA_NIVCPL` pode estar errado** em comparação ao SIGTAP — alguns procedimentos básicos aparecem como média complexidade por engano cadastral. Sempre cruze com a tabela SIGTAP oficial.
6. **PS e SAD são RAAS** — não é "1 linha = 1 procedimento", é "1 linha = 1 período de cuidado". `PERMANEN` é em dias.
7. **`MUNPAC` (BI/PS/SAD) vs `PA_MUNPCN` (PA)** — mesma semântica, nomes diferentes. Pegadinha em joins multi-grupo.
8. **BI parou de ser publicado em 2011.** No catálogo pysus aparece como `BIRS1106.parquet` (junho/2011) como último. Pra dados modernos, use PA com filtro `PA_DOCORIG='I'`.
