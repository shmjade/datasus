# Dicionário de Dados

Referência dos campos mais relevantes de cada fonte utilizada no projeto.
Campos marcados com ⚠️ requerem tratamento especial (nulos frequentes, codificações inconsistentes, etc.).

---

## 1. SIH/DataSUS — Registros de Internação (Tabela RD)

**Arquivo:** `RDUF_AAAAMM.dbc` (ex: `RDRS2401.dbc` = Rio Grande do Sul, Janeiro/2024)
**Acesso:** [DATASUS — Transferência de Arquivos](https://datasus.saude.gov.br/transferencia-de-arquivos/)
**Ferramenta de leitura:** `pysus` ou `read.dbc` (R) → conversão para `.parquet`

| Campo | Tipo | Descrição | Valores / Domínio | Notas |
|---|---|---|---|---|
| `UF_ZI` | CHAR(2) | UF de internação | Sigla (RS, SC, PR...) | |
| `ANO_CMPT` | INT | Ano de competência | AAAA | |
| `MES_CMPT` | INT | Mês de competência | 1–12 | |
| `ESPEC` | CHAR(2) | Especialidade do leito | Tabela SIGTAP | |
| `CGC_HOSP` | VARCHAR(14) | CNPJ do hospital | Sem formatação | Requer zero-padding à esquerda |
| `N_AIH` | VARCHAR(13) | Número da AIH | — | **Dado sensível** — armazenar apenas o hash |
| `IDENT` | CHAR(1) | Tipo de AIH | 1=normal, 5=longa permanência | |
| `CEP` | VARCHAR(8) | CEP do paciente | Sem hífen | ⚠️ ~15% nulos ou inválidos |
| `MUNIC_RES` | CHAR(6) | Município de residência | Código IBGE 6 dígitos | |
| `MUNIC_MOV` | CHAR(6) | Município de atendimento | Código IBGE 6 dígitos | Diferente de MUNIC_RES = transferência |
| `NASC` | DATE | Data de nascimento | YYYYMMDD no arquivo | ⚠️ Datas inválidas (00/00/0000) frequentes |
| `SEXO` | CHAR(1) | Sexo | 1=masc, 3=fem | ⚠️ Valores 0 e 9 = ignorado |
| `DT_INTER` | DATE | Data de internação | YYYYMMDD | |
| `DT_SAIDA` | DATE | Data de saída | YYYYMMDD | ⚠️ Anterior a DT_INTER em ~0.1% dos registros |
| `DIAG_PRINC` | VARCHAR(4) | CID-10 diagnóstico principal | Ex: J18 (pneumonia) | |
| `DIAG_SECUN` | VARCHAR(4) | CID-10 diagnóstico secundário | — | ⚠️ Frequentemente em branco |
| `COBRANCA` | INT | Código de cobrança | Tabela SIGTAP | |
| `NATUREZA` | CHAR(2) | Natureza jurídica | 01=pública, 02=privada... | |
| `GESTAO` | CHAR(1) | Tipo de gestão | M=municipal, E=estadual | |
| `MORTE` | INT | Indicador de óbito | **0=não, 1=sim** | Campo central da análise |
| `VAL_TOT` | DECIMAL | Valor total da AIH (R$) | — | |

### Regras de Qualidade (SIH)

- Filtrar registros com `DT_SAIDA < DT_INTER` (inconsistência).
- Registros com `SEXO IN (0, 9)` → tratar como nulo.
- `NASC` com `'00000000'` ou datas futuras → nulo.
- `MORTE = 1` E `DT_SAIDA IS NULL` → registros a descartar.

---

## 2. CNES/DataSUS — Estabelecimentos de Saúde

**Arquivos principais:**
- `STUF_AAAAMM.dbc` — dados gerais do estabelecimento
- `LTUF_AAAAMM.dbc` — leitos
- `EQUF_AAAAMM.dbc` — equipamentos

**Acesso:** [DATASUS — CNES](https://datasus.saude.gov.br/cadastro-de-estabelecimentos-de-saude-cnes/)

### Tabela: Estabelecimentos (ST)

| Campo | Tipo | Descrição | Valores / Domínio | Notas |
|---|---|---|---|---|
| `CNES` | VARCHAR(7) | Código CNES | 7 dígitos | Chave primária do estabelecimento |
| `CODUFMUN` | CHAR(6) | Código IBGE do município | 6 dígitos | |
| `REGSAUDE` | CHAR(4) | Região de saúde | — | |
| `MICRREG` | CHAR(5) | Microrregião IBGE | — | |
| `DISTRSAN` | VARCHAR(4) | Distrito sanitário | — | ⚠️ Preenchimento irregular |
| `TPGESTAO` | CHAR(1) | Tipo de gestão | M=municipal, E=estadual, D=dupla | |
| `PF_PJ` | CHAR(1) | Pessoa Física/Jurídica | 1=PF, 3=PJ | |
| `CPF_CNPJ` | VARCHAR(14) | CPF ou CNPJ | — | |
| `NIV_DEP` | CHAR(1) | Nível de dependência | — | |
| `CODFAETON` | CHAR(7) | Código da entidade mantenedora | — | |
| `COD_IR` | CHAR(5) | Código no CNES da entidade | — | |
| `CNES_VINC` | VARCHAR(7) | CNES vinculado | — | |
| `TP_UNID` | CHAR(2) | Tipo de unidade | 01=UBS, 04=Hosp geral, 05=Hosp esp... | Campo crítico para filtros |
| `TURNO_ATD` | CHAR(2) | Turno de atendimento | — | |
| `NIV_HIER` | CHAR(2) | Nível hierárquico | — | |
| `TP_ATEND` | CHAR(2) | Tipo de atendimento | — | |
| `VINC_SUS` | CHAR(1) | Vínculo com SUS | S=sim, N=não | Campo para filtro de leitos SUS |
| `CNPJ_MAN` | VARCHAR(14) | CNPJ da mantenedora | — | |
| `LAT` | DECIMAL | Latitude | — | ⚠️ ~30% nulo ou (0,0) |
| `LON` | DECIMAL | Longitude | — | ⚠️ ~30% nulo ou (0,0) |

### Tabela: Leitos (LT)

| Campo | Tipo | Descrição | Notas |
|---|---|---|---|
| `CNES` | VARCHAR(7) | Código CNES | FK para estabelecimento |
| `TP_LEITO` | CHAR(2) | Tipo de leito | 01=cirúrgico, 02=obstétrico, 03=clínico... |
| `CODLEITO` | CHAR(2) | Código do leito | |
| `QT_EXIST` | INT | Quantidade existente | |
| `QT_CONTR` | INT | Quantidade contratada | |
| `QT_SUS` | INT | Quantidade disponível ao SUS | Campo mais relevante para análise |
| `QT_NSUS` | INT | Quantidade não-SUS | |
| `IND_LEITO` | CHAR(1) | Indicador | |
| `COMPETEN` | CHAR(6) | Competência | AAAAMM |

### Tipos de Unidade Relevantes (TP_UNID)

| Código | Descrição |
|---|---|
| 01 | Posto de Saúde |
| 02 | Centro de Saúde / UBS |
| 04 | Hospital Geral |
| 05 | Hospital Especializado |
| 07 | UPA — Unidade de Pronto Atendimento |
| 15 | Unidade Mista |
| 36 | Clínica/Centro de Especialidade |

---

## 3. IBGE — Indicadores Socioeconômicos (POA / Censo)

**Fontes:**
- Censo Demográfico 2022 — por setor censitário
- POF (Pesquisa de Orçamentos Familiares)
- FEE/SEPLAG-RS — Indicadores por bairro (Porto Alegre)

| Campo | Tipo | Descrição | Notas |
|---|---|---|---|
| `CD_SETOR` | VARCHAR(15) | Código do setor censitário | 15 dígitos: UF(2) + mun(5) + distrito(2) + subdistrito(2) + setor(4) |
| `CD_GEOCODM` | CHAR(7) | Código IBGE do município (7 dígitos) | ⚠️ IBGE usa 7 dígitos; SIH/CNES usam 6 — remover último dígito |
| `NM_BAIRRO` | VARCHAR(100) | Nome do bairro | ⚠️ Nomenclatura não padronizada entre anos |
| `V001` | INT | Total de domicílios | Variável do Censo — nomenclatura muda por edição |
| `V002` | INT | Domicílios particulares permanentes | |
| `Renda_media` | DECIMAL | Renda média mensal do responsável | POF — estimativa por setor |
| `IDHM` | DECIMAL | IDH Municipal | Escala 0–1 |
| `Pop_total` | INT | População total do setor | |
| `Pop_vulneravel` | INT | Pop. em vulnerabilidade social | Definição: renda < 1/2 salário mínimo per capita |

### Atenção: Divergência de Código IBGE

O campo `MUNIC_MOV` do SIH e `CODUFMUN` do CNES usam **6 dígitos** (sem o dígito verificador).
O IBGE publica códigos de **7 dígitos** nos Censos. Para joins:

```sql
-- Truncar para 6 dígitos (remover dígito verificador)
SUBSTRING(ibge.CD_GEOCODM, 1, 6) = sih.MUNIC_MOV
```

---

## 4. Tabelas de Domínio (Auxiliares)

### CID-10 (grupos relevantes para análise)

| Capítulo | Faixa CID | Descrição |
|---|---|---|
| I | A00–B99 | Doenças infecciosas e parasitárias |
| II | C00–D48 | Neoplasias |
| IX | I00–I99 | Doenças do aparelho circulatório |
| X | J00–J99 | Doenças do aparelho respiratório |
| XIX | S00–T98 | Lesões, envenenamentos (causas externas) |

### Tipos de Leito SUS (TP_LEITO)

| Código | Descrição |
|---|---|
| 01 | Cirúrgico |
| 02 | Obstétrico |
| 03 | Clínico |
| 04 | Complementar (UTI) |
| 05 | Pediátrico |
| 70–79 | Hospital Dia |
