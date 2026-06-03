# Dicionário de Dados — SIH (Sistema de Informações Hospitalares)

O SIH registra internações pagas pelo SUS via **AIH (Autorização de Internação Hospitalar)**. Cada competência (mês × UF) é publicada em quatro arquivos:

| Grupo | Conteúdo | Granularidade |
|---|---|---|
| **RD** | AIH Reduzida — registro principal da internação | 1 linha / AIH |
| **SP** | Serviços Profissionais — procedimentos executados dentro da AIH | N linhas / AIH (≈10× RD) |
| **RJ** | AIHs Rejeitadas pelo gestor | 1 linha / AIH rejeitada |
| **ER** | Estabelecimentos Rejeitados / erros de envio | 1 linha / erro |

Convenções gerais:
- **Datas**: `YYYYMMDD` como **string** (preserva zeros à esquerda).
- **Valores monetários**: R$ com 2 decimais.
- **Município**: código IBGE de 6 dígitos (UF + 4).
- **UF**: 2 dígitos IBGE — RS=43, SC=42, PR=41.

---

## RD — AIH Reduzida (113 colunas)

A tabela mais rica. **Use ela como ponto de partida pra qualquer análise de internação.**

### Identificação

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `N_AIH` | Número da AIH (chave de fato) | 13 dígitos: UF(2)+ano(2)+sequencial(9) |
| `CNES` | Estabelecimento (FK p/ CNES.ST) | 7 dígitos |
| `CGC_HOSP` | CNPJ do hospital | 14 dígitos |
| `CNPJ_MANT` | CNPJ da mantenedora (se diferente) | 14 dígitos |
| `IDENT` | Tipo de AIH | `1`=principal, `5`=longa permanência |
| `SEQ_AIH5` | Sequencial da AIH-5 | `000` se não aplica |

### Competência

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `ANO_CMPT` | Ano de competência (cobrança) | `2024` |
| `MES_CMPT` | Mês de competência | `01`..`12` |

### Paciente

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `NASC` | Data de nascimento | `YYYYMMDD` |
| `IDADE` | Idade na unidade de `COD_IDADE` | inteiro |
| `COD_IDADE` | Unidade da idade | `2`=dias, `3`=meses, `4`=anos, `5`=anos≥100 |
| `SEXO` | Sexo | `1`=masc, `3`=fem (lacuna intencional no `2`) |
| `RACA_COR` | Raça/cor autodeclarada | `01`=branca, `02`=preta, `03`=parda, `04`=amarela, `05`=indígena, `99`=sem inf |
| `ETNIA` | Etnia indígena | só preenchido se `RACA_COR=05` |
| `NACIONAL` | Nacionalidade | `010`=Brasil, demais = códigos DataSUS |
| `CEP` | CEP da residência | 8 dígitos |
| `MUNIC_RES` | Município de residência | IBGE 6 dígitos |
| `INSTRU` | Escolaridade | `1`=analfabeto … `5`=superior |
| `HOMONIMO` | Flag de homônimo | `0/1` |
| `CBOR` | CBO da ocupação do paciente | 6 dígitos |
| `CNAER` | CNAE da atividade econômica | |
| `VINCPREV` | Vínculo previdenciário | |

### Internação

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `DT_INTER` | Data de entrada | `YYYYMMDD` |
| `DT_SAIDA` | Data de saída | `YYYYMMDD` |
| `DIAS_PERM` | Dias de permanência | inteiro |
| `ESPEC` | Especialidade do leito | `01`=clínica, `02`=cirurgia, `03`=obstetrícia, `04`=pediatria, `05`=outras, `06`=hospital-dia, `07`=psiquiatria, `08`=hansen, `09`=psiq dia, `10`=reabilitação |
| `CAR_INT` | Caráter da internação | `01`=eletiva, `02`=urgência, `03`=acidente trânsito, `04`=acidente trabalho, `05`=acidente outros, `06`=causas externas |
| `MUNIC_MOV` | Município do hospital | IBGE 6 dígitos |
| `UF_ZI` | UF do hospital (zona de internação) | `430000` = RS |

### Diagnóstico (CID-10)

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `DIAG_PRINC` | CID principal | 4 chars (`O021`) |
| `DIAG_SECUN` | CID secundário (principal) | 4 chars |
| `DIAGSEC1`..`DIAGSEC9` | CIDs secundários adicionais | 4 chars cada |
| `TPDISEC1`..`TPDISEC9` | Tipo do CID secundário | código |
| `CID_NOTIF` | CID de notificação compulsória | preenchido só se aplicável |
| `CID_ASSO` | CID associado (causa subjacente em óbito) | |
| `CID_MORTE` | CID da morte | só se `MORTE=1` |

### Procedimento

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `PROC_SOLIC` | Procedimento solicitado | SIGTAP 10 dígitos |
| `PROC_REA` | Procedimento realizado (chave operacional) | SIGTAP 10 dígitos |
| `TOT_PT_SP` | Pontos totais dos serviços profissionais | inteiro |

### UTI / UCI

| Coluna | Descrição |
|---|---|
| `UTI_MES_IN` | Diárias UTI no início do mês |
| `UTI_MES_AN` | Diárias UTI no mês anterior |
| `UTI_MES_AL` | Diárias UTI na alta |
| `UTI_MES_TO` | Total de diárias UTI |
| `MARCA_UTI` | Tipo de UTI: `00`=sem, `51`/`52`/`53`=adulto I/II/III, `61`/`62`/`63`=pediátrica, `71`/`72`/`73`=neonatal, `74`=queimados, `75`=coronariana |
| `UTI_INT_IN/AN/AL/TO` | Diárias UTI intermediária (em desuso) |
| `VAL_UCI` | Valor da Unidade de Cuidados Intermediários |
| `MARCA_UCI` | Tipo da UCI |
| `DIAR_ACOM` | Diárias do acompanhante |
| `QT_DIARIAS` | Total geral de diárias |

### Valores (R$)

| Coluna | Descrição |
|---|---|
| `VAL_SH` | Serviços Hospitalares |
| `VAL_SP` | Serviços Profissionais |
| `VAL_SADT` | SADT (Diagnose/Terapia) com remoção |
| `VAL_SADTSR` | SADT sem remoção |
| `VAL_RN` | Recém-nascido |
| `VAL_ACOMP` | Acompanhante |
| `VAL_ORTP` | Órteses/próteses |
| `VAL_SANGUE` | Sangue/hemoderivados |
| `VAL_OBSANG` | Observação de sangue (em desuso) |
| `VAL_TRANSP` | Transplante |
| `VAL_PED1AC` | Pediatria 1º acompanhante |
| `VAL_UTI` | UTI |
| `VAL_TOT` | **Total da AIH** (soma dos componentes) |
| `US_TOT` | Total em USD (cotação BC do fechamento) |
| `VAL_SH_FED` | Parcela federal de `VAL_SH` |
| `VAL_SP_FED` | Parcela federal de `VAL_SP` |
| `VAL_SH_GES` | Parcela do gestor (estadual/municipal) de `VAL_SH` |
| `VAL_SP_GES` | Parcela do gestor de `VAL_SP` |

### Desfecho

| Coluna | Descrição | Domínio |
|---|---|---|
| `MORTE` | Flag óbito durante internação | `0/1` |
| `COBRANCA` | Motivo da saída/cobrança | `11`=alta curado, `12`=alta melhorado, `14`=transferência, `21`=permanência, `28`=alta a pedido, `41`=óbito sem causa externa, `42`=óbito por causa externa, `51`=permanência cirurgia |
| `INFEHOSP` | Indicador de infecção hospitalar | flag |

### Gestão / Financiamento

| Coluna | Descrição | Domínio |
|---|---|---|
| `GESTAO` | Esfera de gestão da unidade | `M`=municipal, `E`=estadual, `D`=dupla |
| `NATUREZA` | Natureza da unidade (campo antigo, descontinuado) | |
| `NAT_JUR` | Natureza jurídica (Cadastro Sec. Receita) | 4 dígitos |
| `COMPLEX` | Complexidade | `01`=básica, `02`=média, `03`=alta |
| `FINANC` | Tipo de financiamento (subteto) | |
| `FAEC_TP` | Tipo FAEC (Fundo de Ações Estratégicas) | |
| `REGCT` | Regra contratual | |
| `RUBRICA` | Rubrica orçamentária | |
| `GESTOR_COD` | Código do gestor que autorizou | |
| `GESTOR_TP` | Tipo do gestor | `1`=municipal, `2`=estadual, `3`=federal |
| `GESTOR_CPF` | CPF do autorizador | |
| `GESTOR_DT` | Data da autorização | `YYYYMMDD` |
| `IND_VDRL` | Indicação de VDRL (sífilis gestante) | `0/1` |

### Materno-infantil

| Coluna | Descrição |
|---|---|
| `NUM_FILHOS` | Filhos vivos |
| `GESTRISCO` | Gestação de risco (`0/1`) |
| `INSC_PN` | Inscrição SISPRENATAL |
| `CONTRACEP1` | Contraceptivo 1 (código) |
| `CONTRACEP2` | Contraceptivo 2 (código) |

### Auditoria

| Coluna | Descrição |
|---|---|
| `AUD_JUST` | Justificativa textual da auditoria |
| `SIS_JUST` | Sistema de auditoria |
| `NUM_PROC` | Número de processo judicial associado |
| `CPF_AUT` | CPF do autorizador |

### Metadata do registro

| Coluna | Descrição |
|---|---|
| `SEQUENCIA` | Sequência da linha no arquivo enviado |
| `REMESSA` | Identificador da remessa (ex.: `HE43000001N202406.DTS` — tipo + UF + sequencial + AAAA + MM) |

---

## SP — Serviços Profissionais (37 colunas)

**Uma linha por procedimento/profissional executado em cada AIH.** ~10× o volume da RD. Use pra análise de custo detalhado, quem executou, e quais procedimentos compõem cada internação.

Convenção: colunas prefixadas com `SP_`.

### Chaves para juntar com RD

| Coluna | Descrição |
|---|---|
| `SP_NAIH` | Número AIH (junta com `RD.N_AIH`) |
| `SP_CNES` | Estabelecimento |
| `SP_UF` | UF (`43`) |
| `SP_AA` | Ano |
| `SP_MM` | Mês |

### Datas e localização

| Coluna | Descrição |
|---|---|
| `SP_DTINTER` | Data internação |
| `SP_DTSAIDA` | Data saída |
| `SP_M_HOSP` | Município hospital (IBGE 6) |
| `SP_M_PAC` | Município paciente (IBGE 6) |
| `SP_DES_HOS` | Desempenho hospital (flag) |
| `SP_DES_PAC` | Desempenho paciente (flag) |
| `SP_GESTOR` | Código do gestor |

### Ato profissional (o coração de SP)

| Coluna | Descrição |
|---|---|
| `SP_PROCREA` | Procedimento realizado (SIGTAP) |
| `SP_ATOPROF` | Código do ato profissional dentro do procedimento |
| `SP_TP_ATO` | Tipo do ato |
| `SP_QTD_ATO` | Quantidade |
| `SP_PTSP` | Pontuação SP |
| `SP_VALATO` | Valor unitário do ato (R$) |
| `SP_PF_CBO` | CBO do profissional executor |
| `SP_PF_DOC` | CNS do profissional (15 dígitos) |
| `SP_PJ_DOC` | CNPJ pessoa jurídica |
| `SP_CPFCGC` | CPF/CNPJ do estabelecimento |

### Classificação e outras

| Coluna | Descrição |
|---|---|
| `IN_TP_VAL` | Tipo de valor (federal/gestor) |
| `SERV_CLA` | Classificação do serviço |
| `SP_CIDPRI` | CID principal |
| `SP_CIDSEC` | CID secundário |
| `SP_QT_PROC` | Quantidade de procedimentos |
| `SP_U_AIH` | Flag uso de AIH |
| `SP_COMPLEX` | Complexidade |
| `SP_FINANC` | Financiamento |
| `SP_CO_FAEC` | Código FAEC |
| `SP_NUM_PR` | Número do processo |
| `SP_TIPO` | Tipo de registro |
| `SP_NF` | Nota fiscal |
| `FONTE_ORC` | Fonte orçamentária |
| `SEQUENCIA`, `REMESSA` | Metadata do envio (igual a RD) |

---

## RJ — AIHs Rejeitadas (90 colunas)

**Subconjunto de RD + 3 colunas de status.** Mesma chave (`N_AIH`), mas a internação não foi autorizada pelo gestor.

### Colunas exclusivas de RJ

| Coluna | Descrição |
|---|---|
| `ST_SITUAC` | Situação da AIH |
| `ST_BLOQ` | Status de bloqueio |
| `ST_MOT_BLO` | **Motivo do bloqueio** (chave da análise — código DataSUS) |

### Colunas presentes em RD mas **ausentes** em RJ

- `DIAGSEC1`..`9` e `TPDISEC1`..`9` (CIDs secundários extras)
- `VAL_SH_FED`, `VAL_SP_FED`, `VAL_SH_GES`, `VAL_SP_GES` (parcelas)
- `VAL_UCI`, `MARCA_UCI`
- `AUD_JUST`, `SIS_JUST`

Útil pra entender **padrões de glosa** — quais hospitais/procedimentos/CIDs são rejeitados com mais frequência.

---

## ER — Estabelecimentos Rejeitados (13 colunas)

Arquivo bem enxuto. **Uma linha por AIH com erro de envio.** Não é a internação rejeitada (isso é RJ) — é o estabelecimento que mandou dado inconsistente.

| Coluna | Descrição |
|---|---|
| `SEQUENCIA` | Linha do envio |
| `REMESSA` | Identificador da remessa |
| `CNES` | Estabelecimento |
| `AIH` | Número da AIH (sem prefixo `N_`) |
| `ANO` | Ano da competência |
| `MES` | Mês da competência |
| `DT_INTER` | Data internação |
| `DT_SAIDA` | Data saída |
| `MUN_MOV` | Município do hospital |
| `UF_ZI` | UF do hospital |
| `MUN_RES` | Município do paciente |
| `UF_RES` | UF do paciente (`43`) |
| `CO_ERRO` | **Código do erro** — DataSUS publica lista oficial |

Volume típico no RS: poucas dezenas a poucos milhares por mês. Útil pra QA de envio, não pra epidemiologia.

---

## Glossário

| Sigla | Significado |
|---|---|
| **AIH** | Autorização de Internação Hospitalar |
| **CID-10** | Classificação Internacional de Doenças, 10ª revisão |
| **CNES** | Cadastro Nacional de Estabelecimentos de Saúde |
| **SIGTAP** | Sistema de Gerenciamento da Tabela de Procedimentos |
| **CBO** | Classificação Brasileira de Ocupações |
| **CNS** | Cartão Nacional de Saúde |
| **FAEC** | Fundo de Ações Estratégicas e Compensação |
| **SADT** | Serviços Auxiliares de Diagnóstico e Terapia |
| **UTI** | Unidade de Terapia Intensiva |
| **UCI** | Unidade de Cuidados Intermediários |
| **VDRL** | Veneral Disease Research Laboratory (rastreio sífilis) |
| **DTS** | Sufixo de arquivo de envio do SIH |

---

## Joins típicos

```
RD ─┬─ N_AIH ───── SP_NAIH ─ SP
    ├─ N_AIH ───── N_AIH ─── RJ
    ├─ CNES   ──── CNES ──── CNES.ST  (estabelecimento)
    ├─ CNES   ──── CNES ──── CNES.LT  (leitos)
    └─ MUNIC_RES ─ codmunbr ─ IBGE     (denominador populacional)
```

## Caveats que economizam tempo

1. **`SEXO=3` significa feminino**, não 2. O valor `2` não é usado.
2. **`COD_IDADE` é obrigatório pra interpretar `IDADE`** — uma criança de 6 meses tem `IDADE=6, COD_IDADE=3`. Não some idade sem normalizar.
3. **`VAL_TOT` ≠ Σ componentes** em ~1-2% dos casos (arredondamento e ajustes). Use `VAL_TOT` como verdade e investigue divergências.
4. **`DT_INTER > DT_SAIDA`** acontece (erros de digitação). Filtrar antes de calcular permanência.
5. **`DIAG_PRINC = '0000'`** ou `NULL` é cabível — internação cadastrada antes do diagnóstico.
6. **`MORTE` cobre só óbito durante a internação**. Pra mortalidade pós-alta, cruzar com SIM/DO.
7. **`PROC_REA` ≠ `PROC_SOLIC`** quando o procedimento muda no curso da internação. `PROC_REA` é o que foi pago.
8. **RJ e ER só passam a ser publicados a partir de 2008**. Datasets anteriores não existem.
