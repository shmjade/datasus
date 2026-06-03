# Dicionário de Dados — CNES (Cadastro Nacional de Estabelecimentos de Saúde)

O CNES é o **"registro civil" dos estabelecimentos de saúde** no Brasil. Cada unidade (hospital, UBS, clínica, laboratório, consultório) tem um código `CNES` de 7 dígitos que é a chave usada em todos os outros sistemas DataSUS (SIH, SIA, etc).

Granularidade: **mensal × UF**. Cada competência publica 13 arquivos, um por aspecto cadastrado (estabelecimento, leitos, profissionais, equipes, equipamentos, habilitações, serviços...).

Convenção de nomes: `{TIPO}{UF}{YY}{MM}.parquet` (ex.: `STRS2602.parquet` = Estabelecimentos do RS de fevereiro/2026).

---

## Visão geral dos 13 grupos

| Grupo | Nome | Linhas/competência típicas (RS) | Pro projeto NF01006 |
|---|---|---|---|
| **ST** | Estabelecimentos | ~40k | ⭐ **central** — geolocalização e tipologia |
| **LT** | Leitos | ~3k | ⭐ **central** — capacidade hospitalar |
| **PF** | Profissionais (vínculos) | ~400k | profissionais por estabelecimento |
| **EP** | Equipes (atenção básica) | ~6k | cobertura ESF/NASF |
| **EQ** | Equipamentos | ~56k | capacidade diagnóstica |
| **HB** | Habilitações | ~2.5k | credenciamentos de alta complexidade |
| **SR** | Serviços especializados | ~59k | oncologia, transplante, hemodiálise |
| **EF** | Estabelecimentos Filantrópicos | ~70 | flag de natureza |
| **DC** | Dados Complementares (hemoterapia/diálise/oncologia) | ~220 | unidades de serviços críticos |
| **IN** | Incentivos financeiros | ~975 | repasses específicos |
| **RC** | Regras Contratuais | ~700 | contratos por unidade |
| **GM** | Gestão e Metas | ~28 | metas pactuadas |
| **EE** | Estabelecimentos de Ensino | ~20 | hospitais universitários |

---

## Colunas comuns a quase todos os 13 grupos

Aparecem em ST, LT, PF, EP, EQ, HB, SR, IN, RC, GM, EE (com mesmo significado e tipo):

### Identificação

| Coluna | Descrição | Domínio / Exemplo |
|---|---|---|
| `CNES` | **Código do estabelecimento (chave primária)** | 7 dígitos: `2261235` |
| `CODUFMUN` | Município IBGE (UF + 4) | `430003` = Aceguá/RS |
| `CPF_CNPJ` | CPF ou CNPJ do estabelecimento | 14 dígitos (zero-padded p/ CPF) |
| `CNPJ_MAN` | CNPJ da mantenedora | `00000000000000` se mesmo do estabelecimento |
| `PF_PJ` | Pessoa física ou jurídica | `1`=PF, `3`=PJ |
| `NIV_DEP` | Nível de dependência | `1`=individual, `3`=mantida |
| `COD_CEP` | CEP da unidade (em alguns grupos) | 8 dígitos |
| `COMPETEN` | Competência (ano + mês) | `202602` |
| `NAT_JUR` | Natureza jurídica (Receita Federal) | 4 dígitos (`1244`=município, `3999`=privado, `2062`=SS) |

### Classificação administrativa

| Coluna | Descrição | Domínio |
|---|---|---|
| `TPGESTAO` | Tipo de gestão | `M`=municipal, `E`=estadual, `D`=dupla |
| `ESFERA_A` | Esfera administrativa | `M`=municipal, `E`=estadual, `F`=federal |
| `REGSAUDE` | Região de saúde | código interno SUS |
| `MICR_REG` | Microrregião IBGE | |
| `DISTRSAN` | Distrito sanitário | |
| `DISTRADM` | Distrito administrativo | |
| `ATIVIDAD` | Atividade principal | `04`=assistência, `05`=ensino, `06`=pesquisa |
| `NATUREZA` | Natureza (antigo, descontinuado) | |
| `CLIENTEL` | Tipo de clientela | `01`=SUS, `03`=duplo, `04`=privado |
| `TP_UNID` | Tipo de unidade | ver tabela abaixo |
| `TURNO_AT` | Turno de atendimento | `01`=manhã, `02`=tarde, `03`=2 turnos, `06`=24h |
| `NIV_HIER` | Nível hierárquico (atenção) | `1`-`8` |
| `TERCEIRO` | Indicador terceirizado | flag |
| `RETENCAO` | Retenção de impostos | |

### SUS

| Coluna | Descrição | Domínio |
|---|---|---|
| `VINC_SUS` | Vinculado ao SUS? | `0/1` |
| `TP_PREST` | Tipo de prestador | `99`=próprio, `20`=conveniado, etc. |

### Códigos de `TP_UNID` mais comuns

| Código | Tipo |
|---|---|
| `01` | Posto de Saúde |
| `02` | Centro de Saúde / UBS |
| `04` | Policlínica |
| `05` | Hospital Geral |
| `07` | Hospital Especializado |
| `15` | Unidade Mista |
| `20` | Pronto Socorro Geral |
| `21` | Pronto Socorro Especializado |
| `22` | Consultório |
| `36` | Clínica/Centro Especializado |
| `39` | Unidade de Apoio Diagnose/Terapia (SADT) |
| `40` | Unidade Móvel |
| `42` | Unidade Móvel Pré-hospitalar (SAMU) |
| `43` | Farmácia |
| `50` | Unidade de Vigilância |
| `61` | Centro Parto Normal |
| `62` | Hospital/Dia |
| `64` | Central de Regulação |
| `70` | Centro de Atenção Psicossocial (CAPS) |
| `71` | Centro de Apoio à Saúde da Família |
| `72` | Unidade Acadêmica |
| `73` | Pronto Atendimento (UPA) |

---

## ST — Estabelecimentos (208 colunas)

**A "raiz" do CNES.** Uma linha por estabelecimento × competência. Cabeçalho cadastral + ~150 flags de capacidade instalada.

### Colunas adicionais (além das comuns)

#### Cadastro bancário/jurídico
| Coluna | Descrição |
|---|---|
| `CO_BANCO`, `CO_AGENC`, `C_CORREN` | Dados bancários da unidade |
| `CONTRATM`, `DT_PUBLM` | Contrato municipal e data |
| `CONTRATE`, `DT_PUBLE` | Contrato estadual e data |
| `ALVARA`, `DT_EXPED`, `ORGEXPED` | Alvará sanitário |
| `AV_ACRED`, `CLASAVAL`, `DT_ACRED` | Acreditação hospitalar |
| `AV_PNASS`, `DT_PNASS` | PNASS (Programa Nacional de Avaliação de Serviços) |
| `COD_IR` | Código de incentivo regional |

#### Capacidade instalada — Programas (1 linha = unidade tem o programa)
| Coluna | Descrição |
|---|---|
| `GESPRG{1-6}E` / `GESPRG{1-6}M` | Gestão de programas estaduais/municipais (1=saúde mulher, 2=criança, 3=adolescente, 4=idoso, 5=outros) |
| `NIVATE_A` | Nível atenção ambulatorial |
| `NIVATE_H` | Nível atenção hospitalar |

#### Leitos resumo (detalhe completo está no LT)
| Coluna | Descrição |
|---|---|
| `QTLEITP1`, `QTLEITP2`, `QTLEITP3` | Leitos por porte (P1-P3) |
| `LEITHOSP` | Total de leitos hospitalares |
| `QTLEIT{05-40}` | Quantidade de leitos por especialidade (códigos detalhados no LT) |

#### Instalações físicas (`QTINST01`-`QTINST37`)
Quantidade de cada tipo de instalação:
- `QTINST01`-`QTINST14`: Consultórios médicos especializados
- `QTINST15`: **Consultório indiferenciado** (típico de UBS)
- `QTINST16`-`QTINST21`: Salas de atendimento
- `QTINST22`-`QTINST29`: Salas de procedimento (curativos, vacina, nebulização, etc.)
- `QTINST30`-`QTINST37`: Cirurgia, parto, terapia

| Coluna | Descrição |
|---|---|
| `URGEMERG` | Tem urgência/emergência? |
| `ATENDAMB` | Atende ambulatorial? |
| `CENTRCIR` | Tem centro cirúrgico? |
| `CENTROBS` | Centro obstétrico? |
| `CENTRNEO` | Centro de neonatologia? |
| `ATENDHOS` | Atende internação? |

#### Serviços de apoio (`SERAP01P/T`-`SERAP11T`)
Por tipo de serviço: P=Próprio, T=Terceirizado. Tipos:
- 01=Lavanderia, 02=SADT, 03=Nutrição, 04=Manutenção, 05=Esterilização, 06=Necrotério, 07=Patologia clínica, 08=Radiologia, 09=Hemoterapia, 10=Anatomia patológica, 11=Resíduos

| `SERAPOIO` | Tem serviços de apoio? | flag |
| `RES_BIOL`, `RES_QUIM`, `RES_RADI`, `RES_COMU` | Tipos de resíduo gerado |
| `COLETRES` | Coleta de resíduos |

#### Comissões hospitalares (`COMISS01`-`COMISS12`)
01=Óbito, 02=Ética médica, 03=Documentação médica, 04=Farmácia/Terapêutica, 05=Controle de infecção, 06=Ética de enfermagem, 07=Avaliação prontuários, 08=Padronização medicamentos, 09=Biossegurança, 10=CIPA, 11=Apropriação de custos, 12=Ouvidoria

| `COMISSAO` | Tem alguma comissão? | flag |

#### Atendimento prestado por convênio (`AP01CV01`-`AP07CV07`)
Matriz 7×7 (tipo de atendimento × tipo de convênio). Tipos de atendimento:
1. Internação
2. Ambulatorial
3. SADT
4. Urgência/Emergência
5. APAC
6. Plano gestor
7. Ações coletivas

Convênios: 01=SUS, 02=Particular, 03=Plano de saúde privado, 04=Plano de saúde público, 05=Outros

| `ATEND_PR` | Atendimento prestado? | flag |

#### Outros
| `DT_ATUAL` | Data da última atualização cadastral | `YYYYMM` |

---

## LT — Leitos (28 colunas)

**Uma linha por (estabelecimento × tipo de leito × competência).** Use pra calcular oferta hospitalar.

### Colunas específicas

| Coluna | Descrição | Domínio |
|---|---|---|
| `TP_LEITO` | Tipo geral | `1`=cirúrgico, `2`=clínico, `3`=complementar, `4`=obstétrico, `5`=pediátrico, `6`=outras especialidades, `7`=hospital-dia |
| `CODLEITO` | **Código detalhado do leito** | tabela DataSUS (45=clínica geral, 51=UTI adulto I, etc.) |
| `QT_EXIST` | Leitos existentes | inteiro |
| `QT_CONTR` | Leitos contratados (SUS via contrato) | |
| `QT_SUS` | **Leitos disponíveis ao SUS** | inteiro |
| `QT_NSUS` | Leitos NÃO disponíveis ao SUS | inteiro |

### Códigos `CODLEITO` mais comuns

| Código | Especialidade |
|---|---|
| `01-13` | Cirúrgicos (geral, cardio, gastro, oftalmo, ortopedia, etc.) |
| `14-32` | Clínicos (geral, cardio, pediatria, geriatria, etc.) |
| `33-40` | Complementares (UTI/UI) |
| `41-44` | Obstétricos (normal, patológica, cirúrgica) |
| `45-49` | Pediátricos |
| `51` | UTI adulto tipo I |
| `52` | UTI adulto tipo II |
| `53` | UTI adulto tipo III |
| `61-63` | UTI pediátrica I/II/III |
| `74-76` | UTI neonatal I/II/III |
| `77-78` | UTI queimados |

**Cálculo padrão de leitos SUS:** `SUM(QT_SUS) GROUP BY CNES`.

---

## PF — Profissionais (40 colunas)

**Vínculos profissionais.** Uma linha por (profissional × estabelecimento × ocupação × competência). Não é "uma linha por profissional" — um mesmo médico pode aparecer 3x se tem 3 vínculos.

### Colunas específicas

| Coluna | Descrição | Domínio |
|---|---|---|
| `CPF_PROF` | CPF do profissional (criptografado/ofuscado nos parquets do pysus) | string |
| `CPFUNICO` | CPF padronizado para deduplicação | |
| `CBO` | Classificação Brasileira de Ocupações | 6 dígitos (ex.: `225235`=cirurgião geral) |
| `CBOUNICO` | CBO canônico | |
| `NOMEPROF` | Nome do profissional | string |
| `CNS_PROF` | Cartão Nacional de Saúde do profissional | 15 dígitos |
| `CONSELHO` | Conselho de classe | `06`=CREMERS (RS), `08`=COREN, etc. |
| `REGISTRO` | Número do registro no conselho | |
| `VINCULAC` | Tipo de vínculo (código DataSUS) | `010301`=estatutário, etc. |
| `VINCUL_C` | Vínculo contratual (flag) | |
| `VINCUL_A` | Vínculo autônomo (flag) | |
| `VINCUL_N` | Sem vínculo formal (flag) | |
| `PROF_SUS` | Atende SUS? | `0/1` |
| `PROFNSUS` | Atende não-SUS? | `0/1` |
| `HORAOUTR` | Horas outras atividades | inteiro |
| `HORAHOSP` | Horas hospitalares/semana | inteiro |
| `HORA_AMB` | Horas ambulatoriais/semana | inteiro |
| `UFMUNRES` | Município de residência do profissional | IBGE 6 |

**Caveat — confidencialidade:** o `CPF_PROF` no parquet aparece ofuscado (caracteres altos da tabela ASCII). Use `CPFUNICO` ou `CNS_PROF` se precisar identificar/deduplicar.

---

## EP — Equipes (108 colunas)

**Equipes da Atenção Básica** (Saúde da Família, NASF, Consultório na Rua, etc.).

### Colunas específicas

| Coluna | Descrição | Domínio |
|---|---|---|
| `IDEQUIPE` | ID único da equipe | 18 dígitos |
| `TIPO_EQP` | Tipo de equipe | `01`=eSF, `03`=eABP, `54`=eSB, `71`=eSF Saúde Bucal, `34`=eAP, `35`=NASF, etc. |
| `NOME_EQP` | Nome da equipe | string |
| `ID_AREA`, `NOMEAREA` | Área de atuação | |
| `ID_SEGM`, `DESCSEGM`, `TIPOSEGM` | Segmento populacional | |
| `DT_ATIVA` | Data de ativação | `YYYYMM` |
| `DT_DESAT` | Data de desativação | `900001` = ativa |
| `QUILOMBO`, `ASSENTAD`, `INDIGENA` | Populações cobertas (flags) | `0/1` |
| `POPGERAL`, `ESCOLA`, `PRONASCI` | Outras populações cobertas | `0/1` |
| `MOTDESAT`, `TP_DESAT` | Motivo da desativação | código |

Resto das colunas: campos administrativos compartilhados com ST/EQ (GESPRG, AP*CV*, etc.).

---

## EQ — Equipamentos (28 colunas)

**Inventário de equipamentos.** Uma linha por (estabelecimento × tipo equipamento × competência).

### Colunas específicas

| Coluna | Descrição | Domínio |
|---|---|---|
| `TIPEQUIP` | Categoria do equipamento | `01`=Diagnose por imagem, `02`=Infraestrutura, `03`=Métodos diagnósticos, `04`=Métodos terapêuticos, `05`=Odontológicos, `06`=Outros |
| `CODEQUIP` | Código específico | tabela DataSUS — `41`=raio-X, `42`=mamógrafo, `43`=tomógrafo, `44`=RM, `45`=ultrassom |
| `QT_EXIST` | Quantidade total | inteiro |
| `QT_USO` | Quantidade em uso | inteiro |
| `IND_SUS` | Disponível ao SUS? | `0/1` |
| `IND_NSUS` | Disponível não-SUS? | `0/1` |

**Cálculo padrão:** `SUM(QT_USO) WHERE CODEQUIP=44 AND IND_SUS=1 GROUP BY CODUFMUN` → ressonâncias SUS por município.

---

## HB — Habilitações (32 colunas)

**Credenciamentos formais** (UNACON, CACON, UTI tipo II, gestação alto risco, etc).

### Colunas específicas

| Coluna | Descrição |
|---|---|
| `SGRUPHAB` | Código da habilitação (tabela SUS) — ex.: `1901`=UNACON, `5001`=Hosp. Ensino, `7008`=UTI adulto II |
| `CMPT_INI` | Competência inicial (`YYYYMM`) |
| `CMPT_FIM` | Competência final — `999999` = ativa |
| `DTPORTAR` | Data da portaria | `DD/MM/YYYY` |
| `PORTARIA` | Identificação da portaria | string |
| `MAPORTAR` | Mês/ano da portaria | `YYYYMM` |
| `NULEITOS` | Número de leitos da habilitação (quando aplicável) | |

---

## SR — Serviços Especializados (32 colunas)

**Serviços ofertados pela unidade** (oncologia, transplante, hemodiálise, atenção domiciliar...).

### Colunas específicas

| Coluna | Descrição | Domínio |
|---|---|---|
| `SERV_ESP` | Código do serviço (tabela SUS) | `112`=Atenção em saúde mental, `121`=Atenção oncológica, etc. |
| `CLASS_SR` | Classificação dentro do serviço | |
| `SRVUNICO` | Identificador canônico | |
| `CARACTER` | Caráter | `1`=ambulatorial, `2`=hospitalar, `3`=ambos |
| `AMB_NSUS`, `AMB_SUS` | Atende ambulatorial? | flags |
| `HOSP_NSUS`, `HOSP_SUS` | Atende hospitalar? | flags |
| `CONTSRVU` | Contagem? (controle interno) | |
| `CNESTERC` | CNES da unidade terceirizada (se houver) | |

---

## EF — Estabelecimentos Filantrópicos (31 colunas)

Marca os estabelecimentos com **certificação filantrópica** (CEBAS). Estrutura idêntica a HB — usa os mesmos campos `SGRUPHAB`, `CMPT_INI`, `CMPT_FIM`, `DTPORTAR`, `PORTARIA`, `MAPORTAR`.

`SGRUPHAB=6001` indica certificação filantrópica padrão.

---

## DC — Dados Complementares (171 colunas)

**Detalhes operacionais de unidades de Diálise, Quimio/Radio e Hemoterapia.** Subconjunto restrito de unidades (~220 no RS).

### Blocos temáticos

| Prefixo | Tema |
|---|---|
| `S_HBSAGP`, `S_HBSAGN`, `S_DPI`, `S_DPAC`, `S_REAGP`, `S_REAGN`, `S_REHCV` | Capacidade de diálise (sorologias dos pacientes, máquinas) |
| `MAQ_PROP`, `MAQ_OUTR` | Quantidade de máquinas próprias / terceiras |
| `F_AREIA`, `F_CARVAO`, `ABRANDAD`, `DEIONIZA`, `OSMOSE_R`, `OUT_TRAT` | Tratamento de água (diálise) |
| `CNS_NEFR`, `DIALISE` | Responsável técnico nefrologista |
| `SIMUL_RD`, `PLANJ_RD`, `ARMAZ_FT`, `CONF_MAS`, `SALA_MOL`, `BLOCOPER` | Áreas físicas de radioterapia/oncologia |
| `S_ARMAZE`, `S_PREPAR`, `S_QCDURA`, `S_QLDURA`, `S_CPFLUX`, `S_SIMULA`, `S_ACELL6`, `S_ALSEME`, `S_ALCOME` | Salas/equipamentos de radioterapia |
| `ORTV1050`, `ORV50150`, `OV150500`, `UN_COBAL` | Equipamentos de ortovoltagem / bomba de cobalto |
| `EQBRBAIX`, `EQBRMEDI`, `EQBRALTA`, `EQ_MAREA`, `EQ_MINDI`, `EQSISPLN`, `EQDOSCLI`, `EQFONSEL` | Braquiterapia (alta/média/baixa taxa) |
| `CNS_ADM`, `CNS_OPED`, `CNS_CONC`, `CNS_OCLIN`, `CNS_MRAD`, `CNS_FNUC` | Profissionais responsáveis técnicos |
| `QUIMRADI` | Tem quimioterapia + radioterapia? |
| `S_RECEPC`, `S_TRIHMT`, `S_TRICLI`, `S_COLETA`, `S_AFERES`, `S_PREEST`, `S_PROCES`, `S_ESTOQU`, `S_DISTRI`, `S_SOROLO`, `S_IMUNOH`, `S_PRETRA`, `S_HEMOST`, `S_CONTRQ`, `S_BIOMOL`, `S_IMUNFE`, `S_TRANSF`, `S_SGDOAD` | Setores de hemoterapia |
| `QT_CADRE`, `QT_CENRE`, `QT_REFSA`, `QT_CONRA`, `QT_EXTPL`, `QT_FRE18`, `QT_FRE30`, `QT_AGIPL`, `QT_SELAD`, `QT_IRRHE`, `QT_AGLTN`, `QT_MAQAF`, `QT_REFRE`, `QT_REFAS`, `QT_CAPFL` | Equipamentos de hemoterapia (refrigeradores, freezers, centrífugas, etc.) |
| `CNS_HMTR`, `CNS_HMTL`, `CNS_CRES`, `CNS_RTEC` | Hematologistas / responsáveis técnicos |
| `HEMOTERA` | Tem hemoterapia? | flag |

Restante: campos comuns (GESPRG, AP*CV*, ATEND_PR).

---

## IN — Incentivos Financeiros (31 colunas)

Estrutura **idêntica a HB**: marca quais incentivos federais a unidade recebe. Use `SGRUPHAB` pra ver o tipo de incentivo (programa Saúde da Família, IAPI, etc.).

`SGRUPHAB=8107` é exemplo de PAB — Piso de Atenção Básica.

---

## RC — Regras Contratuais (31 colunas)

Idem HB/IN — `SGRUPHAB` identifica a regra (`7111` = contratualização hospitalar).

---

## GM — Gestão e Metas (31 colunas)

Idem HB — `SGRUPHAB` identifica a meta pactuada (`7008` = contratualização rede materno-infantil, etc.).

---

## EE — Estabelecimentos de Ensino (31 colunas)

Idem HB — certificação de hospital de ensino. `SGRUPHAB=5001` é a certificação padrão.

**Note:** EE tem poucas linhas (~20 no RS) porque só hospitais universitários/de ensino têm essa certificação.

---

## Joins típicos com outros DataSUS

```
CNES.ST ─┬─ CNES ─── CNES (SIH.RD)         → hospital onde a internação aconteceu
         ├─ CNES ─── CNES (SIH.SP)         → procedimentos por hospital
         ├─ CNES ─── CNES_EXEC (SIA.PS)    → atendimento ambulatorial
         └─ CNES ─── CODESTAB (SIM.DO)     → hospital onde ocorreu o óbito

CNES.LT ─── CNES ─── CNES (SIH.RD)         → leitos disponíveis × ocupação
CNES.HB ─── CNES ─── CNES (SIH.RD)         → habilitações × tipo de internação realizada
CNES.PF ─── CNES ─── CNES (SIH.SP.SP_CNES) → profissional × procedimento
```

## Caveats que economizam tempo

1. **`COMPETEN` é `YYYYMM`** — não `YYYY-MM-DD`. Pra date arithmetic, parse antes.
2. **Mesma `CNES` aparece em todos os 13 grupos.** Use a `CNES` como pivot pra cruzar (ex.: ST + LT + HB pra ter "hospital + leitos + habilitações").
3. **`NIV_DEP=3` significa estabelecimento dependente** (mesma mantenedora) — pode ter `CPF_CNPJ=00000000000000` e usar a `CNPJ_MAN`.
4. **`CMPT_FIM=999999`** em HB/EF/IN/RC/GM/EE significa que a habilitação/incentivo está ativo.
5. **Mudanças cadastrais entre competências são frequentes** — um hospital pode mudar `CLIENTEL` ou `TPGESTAO`. Pra análise temporal, fixe a competência de referência ou use snapshot mensal.
6. **`QTLEIT*` no ST é resumo agregado; o LT é a fonte da verdade** pra leitos detalhados.
7. **Estabelecimentos descredenciados** continuam aparecendo em competências futuras com `DT_ATUAL` antigo — filtre por `COMPETEN == DT_ATUAL` se quiser só os ativos no mês.
8. **`CODUFMUN`**: 6 dígitos IBGE — usar como chave de join com IBGE pra dados populacionais.
