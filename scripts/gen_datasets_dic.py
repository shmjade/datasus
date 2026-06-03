"""Gera docs/datasets_dic.html — catálogo dos datasets disponíveis no pysus.

Cobertura: SIH, CNES, SIM, SINASC, SINAN, SIA, PNI, CIHA, IBGE.

Para cada dataset:
  - Overview (nome, descrição, cadência, volume típico, arquivos)
  - Utilidade no projeto (alinhamento com Silêncio Epidemiológico / Janela de Risco)
  - Tabela das colunas principais (curadas a partir da especificação DataSUS)

Para SIH/RD, o catálogo completo (116 cols + estatísticas reais) está em data_dict.html.
Esse arquivo é planejamento — para decidir quais bases adicionar à ingestão.
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

OUTPUT = "/app/docs/datasets_dic.html"

# =============================================================================
# Catálogo curado dos datasets
# =============================================================================
DATASETS = {
    "SIH": {
        "tier": 1,
        "tier_label": "✅ Em uso",
        "tier_color": "verde",
        "full_name": "Sistema de Informações Hospitalares",
        "descricao": (
            "Registros de internações financiadas pelo SUS via Autorização de Internação "
            "Hospitalar (AIH). Cobre todas as internações da rede SUS desde 1992."
        ),
        "cadencia": "Mensal (publicação no mês +2)",
        "volume_rs_ano": "~700 mil AIH (RD)",
        "arquivos": [
            ("RD", "AIH Reduzida — internação completa com diagnósticos, valores e desfecho"),
            ("SP", "Serviços Profissionais — procedimentos por AIH"),
            ("RJ", "AIHs Rejeitadas"),
            ("ER", "Estabelecimentos Rejeitados"),
        ],
        "uso_projeto": (
            "Foco do projeto. Base do Silêncio Epidemiológico (F5) e da Janela de Risco (F6). "
            "Já ingerido e analisado — dicionário completo em data_dict.html."
        ),
        "colunas": [
            ("N_AIH",      "varchar(13)", "Número da AIH — anonimizar via SHA-256"),
            ("IDENT",      "char(1)",     "Tipo: 1=Normal, 5=Longa permanência"),
            ("CNES",       "varchar(7)",  "Código CNES do hospital — FK para CNES.ST"),
            ("CGC_HOSP",   "varchar(14)", "CNPJ do hospital"),
            ("ESPEC",      "char(2)",     "Especialidade do leito (01=cirurgia, 02=obst, 03=clín...)"),
            ("MUNIC_RES",  "char(6)",     "Município de residência (IBGE 6 dígitos)"),
            ("MUNIC_MOV",  "char(6)",     "Município de atendimento (IBGE 6 dígitos)"),
            ("NASC",       "date",        "Data de nascimento (AAAAMMDD)"),
            ("SEXO",       "char(1)",     "1=Masculino, 3=Feminino"),
            ("RACA_COR",   "char(2)",     "01=Branca, 02=Preta, 03=Parda, 04=Amarela, 05=Indígena"),
            ("DT_INTER",   "date",        "Data de internação"),
            ("DT_SAIDA",   "date",        "Data de saída/óbito"),
            ("DIAG_PRINC", "varchar(4)",  "CID-10 do diagnóstico principal"),
            ("CAR_INT",    "char(2)",     "01=Eletivo, 02=Urgência, 03-06=Trauma/outros"),
            ("MORTE",      "smallint",    "0=Sobreviveu, 1=Óbito hospitalar"),
            ("VAL_TOT",    "numeric",     "Valor total da AIH (R$)"),
            ("UTI_INT_TO", "smallint",    "Total de dias em UTI na internação"),
            ("MARCA_UTI",  "char(2)",     "Tipo de UTI usada (00=sem, 75=adulto, 76=ped...)"),
            ("COMPLEX",    "char(2)",     "02=Média complex., 03=Alta complex."),
            ("FINANC",     "char(2)",     "04=Estratégico, 06=Média/alta complex."),
            ("…",          "—",           "116 colunas no total. Ver data_dict.html para a lista completa."),
        ],
    },

    "CNES": {
        "tier": 1,
        "tier_label": "⭐ Planejado",
        "tier_color": "azul",
        "full_name": "Cadastro Nacional de Estabelecimentos de Saúde",
        "descricao": (
            "Cadastro de todos os estabelecimentos de saúde (públicos e privados) do país com "
            "infraestrutura, leitos, equipamentos, profissionais e serviços ofertados."
        ),
        "cadencia": "Mensal (snapshot da competência)",
        "volume_rs_ano": "~12 mil estabelecimentos · ~85 mil leitos (dez/2024)",
        "arquivos": [
            ("ST", "Estabelecimentos — dados gerais (nome, CNPJ, tipo, gestão, coord. geográficas)"),
            ("LT", "Leitos — quantidade por tipo, com e sem SUS"),
            ("PF", "Profissionais cadastrados (CBO + CNS)"),
            ("EQ", "Equipamentos médico-hospitalares"),
            ("SR", "Serviços especializados ofertados"),
            ("EP", "Equipes (ESF, NASF, etc.)"),
            ("IN", "Instalações físicas (salas cirúrgicas, etc.)"),
            ("GM", "Gestão e metas"),
        ],
        "uso_projeto": (
            "Essencial para a F3 do artigo (leitos SUS / 1.000 hab por município). "
            "Identifica hospitais de referência candidatos a destino no motor F6. "
            "Junta com SIH via CNES (chave) e MUNIC_MOV (geografia)."
        ),
        "colunas": [
            ("CNES",            "varchar(7)",   "Código CNES (chave primária)"),
            ("CODUFMUN",        "char(6)",      "Código IBGE do município"),
            ("NOM_ESTAB",       "varchar(150)", "Nome do estabelecimento"),
            ("CGC_HOSP",        "varchar(14)",  "CNPJ"),
            ("COD_TIPO_UNIDADE","char(2)",      "Tipo (05=hospital geral, 07=UPA, 02=UBS, 36=esp.)"),
            ("TP_GESTAO",       "char(1)",      "M=Municipal, E=Estadual, D=Dupla"),
            ("VINC_SUS",        "char(1)",      "S=Vinculado ao SUS, N=Não"),
            ("LATITUDE",        "numeric",      "Latitude (graus decimais)"),
            ("LONGITUDE",       "numeric",      "Longitude"),
            ("NIV_HIER",        "char(2)",      "Nível hierárquico (01-08, por complexidade)"),
            ("ATIVIDADE",       "char(2)",      "Tipo de atividade principal"),
            ("TP_LEITO",        "char(2)",      "Tipo de leito (LT): 01=cirúrgico, 02=clínico, 07=UTI..."),
            ("QT_EXIST",        "smallint",     "Quantidade total de leitos do tipo (LT)"),
            ("QT_SUS",          "smallint",     "Quantidade disponível ao SUS — indicador-chave (LT)"),
            ("QT_CONTR",        "smallint",     "Quantidade contratada (LT)"),
            ("CO_CBO",          "char(6)",      "CBO do profissional (PF)"),
            ("VINCULAC",        "char(2)",      "Tipo de vínculo do profissional (PF)"),
        ],
    },

    "SIM": {
        "tier": 1,
        "tier_label": "🔥 Tier 1 — Recomendado",
        "tier_color": "vermelho",
        "full_name": "Sistema de Informações sobre Mortalidade",
        "descricao": (
            "Declarações de Óbito (DO). Capta TODOS os óbitos do país (hospital, casa, via "
            "pública), com causa básica em CID-10. Complementa o SIH — que só vê óbito "
            "intra-hospitalar."
        ),
        "cadencia": "Anual (publicação no ano +1, dado oficial; dado preliminar trimestral)",
        "volume_rs_ano": "~80 mil óbitos/ano (RS)",
        "arquivos": [
            ("DO", "Declarações de óbito gerais (DOXX2024.dbc)"),
            ("DOEXT", "Causas externas (acidentes, violência) — versão expandida"),
            ("DOFET", "Óbitos fetais"),
            ("DOINF", "Óbitos infantis (<1 ano)"),
            ("DOMAT", "Óbitos maternos"),
        ],
        "uso_projeto": (
            "🔥 Transforma o cálculo de mortalidade do projeto. Permite (1) taxa de "
            "mortalidade REAL por município (não só hospitalar) → muda o Silêncio "
            "Epidemiológico. (2) Óbitos fora do hospital de quem deveria ter sido internado "
            "— mede o buraco da regulação. (3) Janela de Risco verdadeira: cruzar "
            "SIH.DT_SAIDA × SIM.DTOBITO ≤ 30 dias = mortalidade pós-alta."
        ),
        "colunas": [
            ("NUMERODO",   "varchar(8)",   "Número da DO (anonimizar)"),
            ("DTOBITO",    "date",         "Data do óbito (DDMMAAAA — atenção, formato distinto)"),
            ("HORAOBITO",  "char(4)",      "Hora do óbito (HHMM)"),
            ("NATURAL",    "char(3)",      "Naturalidade (UF de nascimento)"),
            ("CODMUNNATU", "char(6)",      "Município de naturalidade"),
            ("DTNASC",     "date",         "Data de nascimento"),
            ("IDADE",      "char(3)",      "Idade com unidade codificada (similar SIH)"),
            ("SEXO",       "char(1)",      "0=ignorado, 1=masc, 2=fem"),
            ("RACACOR",    "char(1)",      "1=Branca a 5=Indígena (codificação distinta do SIH!)"),
            ("ESTCIV",     "char(1)",      "Estado civil"),
            ("ESC",        "char(1)",      "Escolaridade (1=nenhuma a 5=>12 anos)"),
            ("OCUP",       "varchar(6)",   "Ocupação (CBO)"),
            ("CODMUNRES",  "char(6)",      "Município de residência (IBGE 6 dígitos)"),
            ("LOCOCOR",    "char(1)",      "Local do óbito: 1=Hospital, 2=Out.unid.saúde, 3=Domicílio, 4=Via pública..."),
            ("CODESTAB",   "varchar(7)",   "CNES do estabelecimento do óbito (se hospital)"),
            ("CODMUNOCOR", "char(6)",      "Município de ocorrência do óbito"),
            ("IDADEMAE",   "char(3)",      "Idade da mãe (para óbitos <1 ano)"),
            ("GRAVIDEZ",   "char(1)",     "Tipo de gravidez (única, dupla, tripla)"),
            ("GESTACAO",   "char(1)",      "Semanas de gestação (1=<22 a 6=42+)"),
            ("PARTO",      "char(1)",      "1=Vaginal, 2=Cesário"),
            ("OBITOPARTO", "char(1)",      "1=Antes, 2=Durante, 3=Depois do parto"),
            ("PESO",       "smallint",     "Peso ao nascer (gramas — óbitos perinatais)"),
            ("ASSISTMED",  "char(1)",      "Recebeu assistência médica?"),
            ("CIRURGIA",   "char(1)",      "Cirurgia foi realizada?"),
            ("NECROPSIA",  "char(1)",      "Houve necropsia?"),
            ("CAUSABAS",   "varchar(4)",   "Causa básica do óbito (CID-10) — campo central"),
            ("LINHAA",     "varchar(80)",  "Linha A — causa imediata"),
            ("LINHAB",     "varchar(80)",  "Linha B — antecedentes"),
            ("LINHAC",     "varchar(80)",  "Linha C — outros estados patológicos"),
            ("LINHAD",     "varchar(80)",  "Linha D — causa básica"),
            ("CAUSABAS_O", "varchar(4)",   "Causa básica original (antes da seleção)"),
            ("CIRCOBITO",  "char(1)",      "Circunstância (acidente, suicídio, homicídio)"),
            ("ACIDTRAB",   "char(1)",      "Acidente de trabalho?"),
            ("FONTE",      "char(1)",      "Fonte da informação"),
        ],
    },

    "SINASC": {
        "tier": 1,
        "tier_label": "🔥 Tier 1 — Recomendado",
        "tier_color": "vermelho",
        "full_name": "Sistema de Informações sobre Nascidos Vivos",
        "descricao": (
            "Declarações de Nascido Vivo (DN). Cada nascimento gera um registro com peso, "
            "Apgar, idade gestacional, escolaridade da mãe, pré-natal, tipo de parto."
        ),
        "cadencia": "Anual (oficial); preliminar trimestral",
        "volume_rs_ano": "~110 mil nascimentos/ano (RS)",
        "arquivos": [
            ("DN", "Declaração de nascido vivo (DNXX2024.dbc) — arquivo único"),
        ],
        "uso_projeto": (
            "🔥 Cross SINASC × SIM<1ano permite calcular taxa de mortalidade infantil — "
            "indicador-chave da OMS para inequidade em saúde. SINASC também valida a "
            "qualidade de parto SUS (você viu que O800 — parto cefálico — é a #1 internação, "
            "com 0% mortalidade no SIH; mas qual a complicação pós-alta?)."
        ),
        "colunas": [
            ("CODESTAB",  "varchar(7)",  "CNES do estabelecimento do nascimento"),
            ("CODMUNNASC","char(6)",     "Município do nascimento"),
            ("LOCNASC",   "char(1)",     "1=Hospital, 2=Outro estab.saúde, 3=Domicílio, 4=Outros"),
            ("IDADEMAE",  "smallint",    "Idade da mãe em anos"),
            ("ESTCIVMAE", "char(1)",     "Estado civil da mãe"),
            ("ESCMAE",    "char(1)",     "Escolaridade da mãe (1=nenhuma a 5=>12 anos)"),
            ("CODOCUPMAE","varchar(6)",  "CBO da ocupação da mãe"),
            ("QTDFILVIVO","smallint",    "Filhos vivos antes deste"),
            ("QTDFILMORT","smallint",    "Filhos mortos antes deste"),
            ("CODMUNRES", "char(6)",     "Município de residência da mãe (IBGE 6 dígitos)"),
            ("GESTACAO",  "char(1)",     "Semanas de gestação (1=<22 a 6=42+)"),
            ("GRAVIDEZ",  "char(1)",     "Tipo de gravidez (1=única, 2=dupla, 3=tripla)"),
            ("PARTO",     "char(1)",     "1=Vaginal, 2=Cesário"),
            ("CONSULTAS", "char(1)",     "Número de consultas pré-natal (1=nenhuma a 4=7+)"),
            ("DTNASC",    "date",        "Data do nascimento"),
            ("SEXO",      "char(1)",     "Sexo do RN"),
            ("APGAR1",    "smallint",    "Apgar no 1º minuto (0-10)"),
            ("APGAR5",    "smallint",    "Apgar no 5º minuto"),
            ("RACACOR",   "char(1)",     "Raça/cor do RN"),
            ("PESO",      "smallint",    "Peso ao nascer (gramas)"),
            ("IDANOMAL",  "char(1)",     "Anomalia congênita identificada"),
            ("CODANOMAL", "varchar(4)",  "CID-10 da anomalia"),
            ("MESPRENAT", "smallint",    "Mês de gestação que iniciou pré-natal (1-9)"),
            ("STCESPARTO","char(1)",     "Cesárea ocorreu antes do trabalho de parto?"),
            ("STTRABPART","char(1)",     "Trabalho de parto induzido?"),
            ("RACACORMAE","char(1)",     "Raça/cor da mãe"),
            ("TPMETESTIM","char(1)",     "Método de estimativa da idade gestacional"),
            ("DTRECORIGA","date",        "Data do recebimento da DN original"),
        ],
    },

    "SINAN": {
        "tier": 2,
        "tier_label": "📊 Tier 2 — Complementar",
        "tier_color": "azul",
        "full_name": "Sistema de Informação de Agravos de Notificação",
        "descricao": (
            "Doenças e agravos de notificação compulsória. Cobre dengue, COVID, tuberculose, "
            "sífilis, leptospirose, violência interpessoal, intoxicações, hepatites, "
            "leishmaniose, malária — cada agravo em arquivo separado."
        ),
        "cadencia": "Semanal (dado preliminar) / Anual (oficial)",
        "volume_rs_ano": "Varia muito — dengue: ~50k, TB: ~6k, sífilis: ~30k, violência: ~80k",
        "arquivos": [
            ("DENG", "Dengue"),
            ("ZIKA", "Zika"),
            ("CHIK", "Chikungunya"),
            ("COVI", "COVID-19"),
            ("TUBE", "Tuberculose"),
            ("SIFI", "Sífilis adquirida"),
            ("SIFG", "Sífilis em gestante"),
            ("SIFC", "Sífilis congênita"),
            ("LEPT", "Leptospirose"),
            ("VIOL", "Violência interpessoal e autoprovocada"),
            ("INTX", "Intoxicações exógenas"),
            ("HEPA", "Hepatites virais"),
            ("LEIV", "Leishmaniose visceral"),
            ("LTAN", "Leishmaniose tegumentar"),
            ("MALA", "Malária"),
            ("AIDS", "Aids em adulto"),
            ("ACBI", "Acidente biológico"),
        ],
        "uso_projeto": (
            "Complementa a análise de internações por causa: A419 (sepse) ocupa 40,9% da "
            "mortalidade no SIH — muitas precedidas por agravos notificáveis (TB, sífilis). "
            "Violência (capítulo XX do CID) tem registro detalhado aqui (agressor, "
            "reincidência) — enriquece análise de causas externas."
        ),
        "colunas": [
            ("TP_NOT",     "char(1)",     "Tipo de notificação (1=individual, 2=surto)"),
            ("ID_AGRAVO",  "varchar(4)",  "CID-10 do agravo notificado"),
            ("DT_NOTIFIC", "date",        "Data da notificação"),
            ("SEM_NOT",    "char(6)",     "Semana epidemiológica da notificação"),
            ("NU_ANO",     "smallint",    "Ano da notificação"),
            ("SG_UF_NOT",  "char(2)",     "UF da unidade notificadora"),
            ("ID_MUNICIP", "char(6)",     "Município da unidade notificadora"),
            ("ID_REGIONA", "char(4)",     "Regional de saúde"),
            ("ID_UNIDADE", "varchar(7)",  "CNES da unidade notificadora"),
            ("DT_SIN_PRI", "date",        "Data dos primeiros sintomas"),
            ("DT_NASC",    "date",        "Data de nascimento do paciente"),
            ("NU_IDADE_N", "char(4)",     "Idade com código de unidade"),
            ("CS_SEXO",    "char(1)",     "Sexo (M/F/I)"),
            ("CS_GESTANT", "char(1)",     "Gestante? (1-6 trimestres, 9=ign.)"),
            ("CS_RACA",    "char(1)",     "Raça/cor"),
            ("CS_ESCOL_N", "char(2)",     "Escolaridade"),
            ("SG_UF",      "char(2)",     "UF de residência"),
            ("ID_MN_RESI", "char(6)",     "Município de residência"),
            ("CS_ZONA",    "char(1)",     "Zona (urbana/rural)"),
            ("EVOLUCAO",   "char(1)",     "Evolução: 1=Cura, 2=Óbito, 3=Sequela..."),
            ("DT_OBITO",   "date",        "Data do óbito (se evolução=2)"),
            ("CLASSI_FIN", "char(1)",     "Classificação final do caso"),
            ("CRITERIO",   "char(1)",     "Critério de confirmação (clínico, laboratório, vínculo)"),
            ("DT_ENCERRA", "date",        "Data de encerramento do caso"),
        ],
    },

    "SIA": {
        "tier": 2,
        "tier_label": "📊 Tier 2 — Complementar",
        "tier_color": "azul",
        "full_name": "Sistema de Informações Ambulatoriais",
        "descricao": (
            "Procedimentos ambulatoriais financiados pelo SUS: consultas, exames, terapias, "
            "fisioterapia, oncologia, hemodiálise. Conjunto MASSIVO — bilhões de linhas/ano "
            "nacional."
        ),
        "cadencia": "Mensal",
        "volume_rs_ano": "~150 milhões procedimentos (PA)",
        "arquivos": [
            ("PA", "Produção ambulatorial individualizada — principal e mais volumoso"),
            ("AB", "APAC — Boletim — quimio/radio/diálise/etc."),
            ("ABO", "APAC — Acompanhamento de Pós-cirurgia"),
            ("ACF", "APAC — Confecção de fístula"),
            ("AD",  "APAC — Laudos diversos"),
            ("AM",  "APAC — Medicamentos"),
            ("AN",  "APAC — Nefrologia"),
            ("AQ",  "APAC — Quimioterapia"),
            ("AR",  "APAC — Radioterapia"),
            ("ATD", "APAC — Tratamento dialítico"),
            ("BI",  "BPA Individualizado"),
            ("PS",  "RAAS Psicossocial"),
            ("SAD", "RAAS Atenção Domiciliar"),
        ],
        "uso_projeto": (
            "Permite mapear o fluxo PRÉ-internação: pacientes em hemodiálise (AN/ATD) que "
            "depois internam = identificação de coorte de alto risco. Município com baixo "
            "SIA/hab + alto SIH/hab = falha da atenção básica empurrando casos pra "
            "hospital. Ressalva: VOLUME enorme — só ingerir se for foco. "
        ),
        "colunas": [
            ("PA_CODUNI",  "varchar(7)", "CNES da unidade prestadora"),
            ("PA_GESTAO",  "char(6)",    "Código do gestor"),
            ("PA_CONDIC",  "char(2)",    "Condição da gestão"),
            ("PA_UFMUN",   "char(6)",    "Município de execução"),
            ("PA_REGCT",   "char(4)",    "Regra contratual"),
            ("PA_INCOUT",  "char(4)",    "Incremento outros"),
            ("PA_INCURG",  "char(4)",    "Incremento urgência"),
            ("PA_TPUPS",   "char(2)",    "Tipo da unidade"),
            ("PA_TIPPRE",  "char(2)",    "Tipo do prestador"),
            ("PA_MN_IND",  "char(1)",    "Estabelecimento mantido?"),
            ("PA_PROC_ID", "char(10)",   "Procedimento (código SIGTAP)"),
            ("PA_DOCORIG", "char(1)",    "Documento de origem (BPA/APAC/RAAS)"),
            ("PA_MVM",     "char(6)",    "Mês de movimento"),
            ("PA_CMP",     "char(6)",    "Competência"),
            ("PA_QTDPRO",  "integer",    "Quantidade produzida"),
            ("PA_QTDAPR",  "integer",    "Quantidade aprovada"),
            ("PA_VALPRO",  "numeric",    "Valor produzido (R$)"),
            ("PA_VALAPR",  "numeric",    "Valor aprovado (R$)"),
            ("PA_UFDIF",   "char(1)",    "UF residência diferente da execução?"),
            ("PA_MNDIF",   "char(1)",    "Município diferente?"),
            ("PA_DIF_VAL", "numeric",    "Valor diferença"),
            ("PA_IDADE",   "smallint",   "Idade do paciente"),
            ("PA_SEXO",    "char(1)",    "Sexo"),
            ("PA_RACACOR", "char(2)",    "Raça/cor"),
            ("PA_MUNPCN",  "char(6)",    "Município de residência"),
            ("PA_CIDPRI",  "varchar(4)", "CID principal (quando aplicável)"),
        ],
    },

    "PNI": {
        "tier": 3,
        "tier_label": "💧 Tier 3 — Marginal",
        "tier_color": "cinza",
        "full_name": "Programa Nacional de Imunizações",
        "descricao": (
            "Doses de vacinas aplicadas, agregadas por município, idade e produto. "
            "Cobertura vacinal por imunobiológico."
        ),
        "cadencia": "Mensal (a partir de 2019, antes era anual)",
        "volume_rs_ano": "~5 milhões doses",
        "arquivos": [
            ("CPNI", "Cobertura PNI — agregado por município/ano/vacina"),
        ],
        "uso_projeto": (
            "Cobertura de vacina gripe num município é proxy de demanda esperada de "
            "internação respiratória (J189 = top mortalidade no seu SIH). Cobertura BCG/HepB "
            "= indicador socioeconômico complementar pro Silêncio Epidemiológico. Valor "
            "marginal — só vale se entrar no modelo preditivo."
        ),
        "colunas": [
            ("MUNIC_RES",   "char(6)",    "Município de residência"),
            ("UF_RES",      "char(2)",    "UF de residência"),
            ("VACINA",      "varchar(4)", "Código do imunobiológico"),
            ("DT_DOSE",     "date",       "Data de aplicação"),
            ("IDADE",       "smallint",   "Idade"),
            ("SEXO",        "char(1)",    "Sexo"),
            ("DOSE_ATUAL",  "char(2)",    "Dose (1ª, 2ª, reforço...)"),
            ("CODGRUPOAT",  "varchar",    "Grupo de atendimento (gestante, idoso...)"),
        ],
    },

    "CIHA": {
        "tier": 3,
        "tier_label": "💧 Tier 3 — Marginal",
        "tier_color": "cinza",
        "full_name": "Comunicação de Internação Hospitalar e Ambulatorial",
        "descricao": (
            "Atendimentos hospitalares e ambulatoriais realizados em estabelecimentos "
            "filantrópicos NÃO-SUS. Dimensiona o setor privado/filantrópico."
        ),
        "cadencia": "Mensal",
        "volume_rs_ano": "~150 mil internações não-SUS",
        "arquivos": [
            ("CIHA", "Comunicação de internação/atendimento"),
        ],
        "uso_projeto": (
            "Útil pra dimensionar o 'buraco' do SIH em municípios com forte presença "
            "privada (Porto Alegre, Caxias). Mas o foco do artigo é SUS — valor marginal."
        ),
        "colunas": [
            ("CNES",       "varchar(7)", "CNES do estabelecimento"),
            ("DT_INTER",   "date",       "Data de internação"),
            ("DT_SAIDA",   "date",       "Data de saída"),
            ("MUNIC_RES",  "char(6)",    "Município de residência"),
            ("MUNIC_MOV",  "char(6)",    "Município de atendimento"),
            ("ESPEC",      "char(2)",    "Especialidade"),
            ("CGC_HOSP",   "varchar(14)","CNPJ"),
            ("DIAG_PRINC", "varchar(4)", "CID-10 principal"),
            ("CAR_INT",    "char(2)",    "Caráter (eletivo/urgência)"),
            ("MORTE",      "smallint",   "Indicador de óbito"),
            ("SEXO",       "char(1)",    "Sexo"),
            ("IDADE",      "smallint",   "Idade"),
            ("VAL_TOT",    "numeric",    "Valor total"),
        ],
    },

    "IBGE": {
        "tier": 1,
        "tier_label": "⭐ Planejado",
        "tier_color": "azul",
        "full_name": "Instituto Brasileiro de Geografia e Estatística",
        "descricao": (
            "Indicadores demográficos e socioeconômicos por setor censitário e município "
            "(Censo 2022 — quando disponível). Disponível via pysus.ibge.*"
        ),
        "cadencia": "Decenal (censo) + projeções intercensitárias anuais",
        "volume_rs_ano": "~47k setores censitários (RS, censo 2022)",
        "arquivos": [
            ("POP", "Projeção populacional por município/ano (todos os anos)"),
            ("CENSO22", "Resultados do Censo Demográfico 2022 por setor"),
            ("AGREG", "Tabelas agregadas (renda, escolaridade, saneamento por bairro/setor)"),
        ],
        "uso_projeto": (
            "Essencial para o cálculo do Silêncio Epidemiológico (F5): mortalidade × leitos "
            "× renda × IDHM. Também necessário pro denominador de qualquer taxa "
            "populacional (mortalidade/1000hab, leitos/1000hab). Integração via "
            "MUNIC × CD_GEOCODM (truncar 7→6 dígitos)."
        ),
        "colunas": [
            ("CD_GEOCODM",   "char(7)",    "Código IBGE do município (7 dígitos com DV)"),
            ("CD_GEOCODS",   "varchar(15)","Código do setor censitário"),
            ("NM_MUNICIPIO", "varchar",    "Nome do município"),
            ("NM_BAIRRO",    "varchar",    "Nome do bairro (para municípios grandes)"),
            ("POP_TOTAL",    "integer",    "População total"),
            ("POP_URBANA",   "integer",    "População urbana"),
            ("POP_RURAL",    "integer",    "População rural"),
            ("DOMICILIOS",   "integer",    "Número de domicílios particulares permanentes"),
            ("RENDA_MEDIA",  "numeric",    "Renda média domiciliar (R$)"),
            ("IDHM",         "numeric",    "IDH Municipal"),
            ("V_RENDA_LT_1SM","integer",   "Domicílios com renda < 1 SM"),
            ("V_SANEAMENTO", "numeric",    "% com saneamento básico"),
            ("V_ALFABETIZACAO","numeric",  "% alfabetização >15 anos"),
            ("V_ENERGIA",    "numeric",    "% com energia elétrica"),
        ],
    },
}


# =============================================================================
# Render HTML
# =============================================================================
def render() -> str:
    gerado_em = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    # Cards summary
    n_total = len(DATASETS)
    n_tier1 = sum(1 for d in DATASETS.values() if d["tier"] == 1)
    n_tier2 = sum(1 for d in DATASETS.values() if d["tier"] == 2)
    n_tier3 = sum(1 for d in DATASETS.values() if d["tier"] == 3)

    # Top nav
    nav = " · ".join(
        f'<a href="#ds-{key}">{key}</a>'
        for key in DATASETS
    )

    # Dataset sections
    sections = []
    for key, d in DATASETS.items():
        cor = d["tier_color"]
        arquivos_html = "".join(
            f'<tr><td><code>{html.escape(p)}</code></td><td>{html.escape(desc)}</td></tr>'
            for p, desc in d["arquivos"]
        )
        cols_html = "".join(
            f'<tr><td><code class="col-name">{html.escape(c)}</code></td>'
            f'<td><span class="tipo">{html.escape(t)}</span></td>'
            f'<td>{html.escape(desc)}</td></tr>'
            for c, t, desc in d["colunas"]
        )

        sections.append(f"""
<section id="ds-{key}" class="dataset" data-key="{key}">
  <div class="ds-header">
    <h2><span class="ds-key">{key}</span> · {html.escape(d["full_name"])}</h2>
    <span class="tier tier-{cor}">{html.escape(d["tier_label"])}</span>
  </div>

  <p class="ds-desc">{html.escape(d["descricao"])}</p>

  <div class="ds-meta">
    <div><strong>Cadência</strong><br/>{html.escape(d["cadencia"])}</div>
    <div><strong>Volume RS/ano</strong><br/>{html.escape(d["volume_rs_ano"])}</div>
    <div><strong>Arquivos</strong><br/>{len(d["arquivos"])}</div>
  </div>

  <div class="ds-uso"><strong>Utilidade no projeto:</strong> {html.escape(d["uso_projeto"])}</div>

  <h3>Arquivos da base</h3>
  <table class="dict small">
    <thead><tr><th>Sigla</th><th>Conteúdo</th></tr></thead>
    <tbody>{arquivos_html}</tbody>
  </table>

  <h3>Colunas principais ({len(d["colunas"])})</h3>
  <table class="dict">
    <thead><tr><th>Coluna</th><th>Tipo</th><th>Descrição</th></tr></thead>
    <tbody>{cols_html}</tbody>
  </table>
</section>
""")

    body = "\n".join(sections)

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Catálogo de Datasets pysus — DataSUS / IBGE</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{
    --azul: #2563eb; --azul-escuro: #1e3a8a;
    --cinza-claro: #f3f4f6; --cinza: #6b7280; --cinza-escuro: #374151;
    --vermelho: #dc2626; --laranja: #ea580c; --verde: #16a34a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0; color: #111827; line-height: 1.5;
  }}
  header {{
    background: var(--azul-escuro); color: white; padding: 24px 32px;
    box-shadow: 0 2px 4px rgba(0,0,0,.1);
  }}
  header h1 {{ margin: 0; font-size: 22px; }}
  header .meta {{ margin-top: 6px; font-size: 13px; opacity: .9; }}
  .container {{ max-width: 1280px; margin: 0 auto; padding: 24px 32px; }}
  .summary {{
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 12px; margin: 16px 0 24px;
  }}
  .card {{
    background: var(--cinza-claro); padding: 14px 16px; border-radius: 8px;
  }}
  .card .num {{ font-size: 26px; font-weight: 600; color: var(--azul); }}
  .card .label {{ font-size: 12px; color: var(--cinza); text-transform: uppercase; letter-spacing: .04em; }}
  nav.cats {{
    background: white; padding: 14px 32px; border-bottom: 1px solid #e5e7eb;
    position: sticky; top: 0; z-index: 10; margin: -24px -32px 24px;
  }}
  nav.cats a {{
    color: var(--azul); text-decoration: none; margin: 0 6px; font-size: 13px;
    font-weight: 500;
  }}
  nav.cats a:hover {{ text-decoration: underline; }}
  .search {{ display: flex; gap: 10px; align-items: center; margin: 16px 0 24px; }}
  .search input {{
    flex: 1; padding: 9px 12px; font-size: 14px;
    border: 1px solid #d1d5db; border-radius: 6px;
  }}
  section.dataset {{
    margin: 40px 0; padding: 24px; background: white;
    border: 1px solid #e5e7eb; border-radius: 10px;
    box-shadow: 0 1px 2px rgba(0,0,0,.04);
  }}
  .ds-header {{
    display: flex; align-items: center; justify-content: space-between;
    flex-wrap: wrap; gap: 10px;
    border-bottom: 2px solid #e5e7eb; padding-bottom: 10px; margin-bottom: 14px;
  }}
  .ds-header h2 {{ margin: 0; font-size: 20px; }}
  .ds-key {{
    display: inline-block; background: var(--azul); color: white;
    padding: 4px 12px; border-radius: 6px; font-family: monospace;
    font-size: 18px; margin-right: 6px;
  }}
  .tier {{
    padding: 4px 10px; border-radius: 14px; font-size: 12px; font-weight: 500;
  }}
  .tier-vermelho {{ background: #fee2e2; color: var(--vermelho); }}
  .tier-azul     {{ background: #dbeafe; color: var(--azul); }}
  .tier-verde    {{ background: #dcfce7; color: var(--verde); }}
  .tier-cinza    {{ background: var(--cinza-claro); color: var(--cinza-escuro); }}
  .ds-desc {{ color: var(--cinza-escuro); font-size: 14px; margin: 0 0 14px; }}
  .ds-meta {{
    display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px;
    margin: 14px 0; padding: 12px; background: #f9fafb; border-radius: 6px;
    font-size: 13px;
  }}
  .ds-meta strong {{ color: var(--cinza); font-size: 11px; text-transform: uppercase; letter-spacing: .04em; }}
  .ds-uso {{
    margin: 14px 0; padding: 12px 14px; background: #fef3c7; border-left: 4px solid var(--laranja);
    border-radius: 4px; font-size: 13px;
  }}
  h3 {{ margin: 22px 0 8px; font-size: 14px; color: var(--cinza-escuro); text-transform: uppercase; letter-spacing: .04em; }}
  table.dict {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
  table.dict th, table.dict td {{
    text-align: left; padding: 8px 12px; border-bottom: 1px solid #e5e7eb;
    vertical-align: top;
  }}
  table.dict th {{
    background: #f9fafb; font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: .04em; color: var(--cinza);
  }}
  table.dict tr:hover td {{ background: #fafafa; }}
  table.small {{ font-size: 12px; }}
  code {{ background: #f3f4f6; padding: 1px 5px; border-radius: 3px;
          font-family: "SF Mono", Consolas, monospace; font-size: 12px; }}
  code.col-name {{ font-weight: 600; color: #111827; background: none; padding: 0; }}
  .tipo {{
    background: #ede9fe; color: #6d28d9; padding: 2px 6px; border-radius: 4px;
    font-size: 11px; font-family: monospace;
  }}
  .hidden {{ display: none !important; }}
  footer {{
    margin: 48px 0 24px; padding-top: 16px; border-top: 1px solid #e5e7eb;
    color: var(--cinza); font-size: 12px; text-align: center;
  }}
  footer a {{ color: var(--azul); }}
</style>
</head>
<body>
<header>
  <h1>📚 Catálogo de Datasets disponíveis no pysus 2.1</h1>
  <div class="meta">
    Visão geral de cada base + colunas principais (curadas) + utilidade para o projeto DataSUS-POA<br/>
    Gerado em {gerado_em}
  </div>
</header>

<div class="container">
  <div class="summary">
    <div class="card"><div class="num">{n_total}</div><div class="label">Datasets cobertos</div></div>
    <div class="card"><div class="num">{n_tier1}</div><div class="label">Tier 1 (em uso/planejado)</div></div>
    <div class="card"><div class="num">{n_tier2}</div><div class="label">Tier 2 (complementar)</div></div>
    <div class="card"><div class="num">{n_tier3}</div><div class="label">Tier 3 (marginal)</div></div>
  </div>

  <nav class="cats">{nav}</nav>

  <div class="search">
    <input id="q" type="search" placeholder="Buscar por coluna, descrição, agravo, sigla... (ex: óbito, CNES, leito, gestante)">
    <span id="q-count" class="pct" style="color:var(--cinza);font-size:12px"></span>
  </div>

  {body}

  <footer>
    Gerado por <code>scripts/gen_datasets_dic.py</code> ·
    Especificação detalhada do SIH/RD: <code>docs/data_dict.html</code><br/>
    Catálogos curados a partir das estruturas oficiais DataSUS &mdash;
    para o catálogo completo de cada base, consulte a documentação oficial em
    <a href="https://datasus.saude.gov.br/transferencia-de-arquivos/">datasus.saude.gov.br</a>.
  </footer>
</div>

<script>
  const q = document.getElementById('q');
  const count = document.getElementById('q-count');
  const sections = Array.from(document.querySelectorAll('section.dataset'));

  function filtrar() {{
    const v = q.value.toLowerCase().trim();
    let nLinhas = 0, nLinhasTotal = 0;
    sections.forEach(s => {{
      const rows = s.querySelectorAll('table.dict tbody tr');
      let visibleInSection = 0;
      rows.forEach(r => {{
        const match = !v || r.textContent.toLowerCase().includes(v);
        r.classList.toggle('hidden', !match);
        nLinhasTotal++;
        if (match) {{ visibleInSection++; nLinhas++; }}
      }});
      // mostra/esconde a seção inteira se nenhum match
      const headerMatches = !v || (s.dataset.key.toLowerCase().includes(v)
        || s.querySelector('.ds-desc').textContent.toLowerCase().includes(v)
        || s.querySelector('.ds-uso').textContent.toLowerCase().includes(v));
      s.classList.toggle('hidden', !!v && visibleInSection === 0 && !headerMatches);
    }});
    count.textContent = v ? `${{nLinhas}}/${{nLinhasTotal}} linhas` : '';
  }}
  q.addEventListener('input', filtrar);
</script>
</body>
</html>
"""


def main():
    out = Path(OUTPUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(), encoding="utf-8")
    print(f"Gravado em {out} ({out.stat().st_size/1024:.1f} KB)")
    print(f"{len(DATASETS)} datasets · {sum(len(d['colunas']) for d in DATASETS.values())} colunas curadas")


if __name__ == "__main__":
    main()
