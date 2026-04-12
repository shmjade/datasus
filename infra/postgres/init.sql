-- =============================================================================
-- DataSUS — DDL Inicial do Banco Relacional
-- Padrão Medallion adaptado: raw → trusted → refined
--
-- raw:     dados ingeridos com mínima transformação (1:1 com fonte)
-- trusted: dados limpos, tipados e validados
-- refined: agregações e views analíticas para consultas de decisão
-- =============================================================================

-- ---------------------------------------------------------------------------
-- Schemas
-- ---------------------------------------------------------------------------
CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS trusted;
CREATE SCHEMA IF NOT EXISTS refined;

COMMENT ON SCHEMA raw     IS 'Dados ingeridos diretamente das fontes (SIH, CNES, IBGE) sem transformação significativa.';
COMMENT ON SCHEMA trusted IS 'Dados limpos, tipados e com regras de negócio aplicadas.';
COMMENT ON SCHEMA refined IS 'Visões analíticas e agregações para suporte à decisão.';

-- ---------------------------------------------------------------------------
-- Extensões
-- ---------------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";   -- geração de UUIDs
CREATE EXTENSION IF NOT EXISTS "unaccent";    -- normalização de strings com acentos

-- ===========================================================================
-- SCHEMA: raw
-- Tabelas espelho das fontes externas — estrutura próxima ao original
-- ===========================================================================

-- SIH/DataSUS — Registros de internação (tabela RD)
CREATE TABLE IF NOT EXISTS raw.sih_internacoes (
    id             UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    uf_zi          CHAR(2),           -- UF de internação
    ano_cmpt       SMALLINT,          -- Ano de competência
    mes_cmpt       SMALLINT,          -- Mês de competência
    espec          CHAR(2),           -- Especialidade do leito
    cgc_hosp       VARCHAR(14),       -- CNPJ do hospital
    n_aih          VARCHAR(13),       -- Número da AIH (cifrado/anonimizado)
    ident          CHAR(1),           -- Tipo de AIH (1=normal, 5=longa permanência)
    cep            VARCHAR(8),        -- CEP do paciente
    munic_res      CHAR(6),           -- Município de residência (código IBGE)
    munic_mov      CHAR(6),           -- Município de atendimento
    nasc           DATE,              -- Data de nascimento
    sexo           CHAR(1),           -- Sexo (1=masc, 3=fem)
    dt_inter       DATE,              -- Data de internação
    dt_saida       DATE,              -- Data de saída
    diag_princ     VARCHAR(4),        -- CID-10 diagnóstico principal
    diag_secun     VARCHAR(4),        -- CID-10 diagnóstico secundário
    cobranca       SMALLINT,          -- Código de cobrança
    natureza       CHAR(2),           -- Natureza do estabelecimento
    gestao         CHAR(1),           -- Tipo de gestão
    morte          SMALLINT,          -- Indicador de óbito (0=não, 1=sim)
    val_tot        NUMERIC(12, 2),    -- Valor total da AIH
    ingested_at    TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.sih_internacoes IS 'Registros de Autorização de Internação Hospitalar (AIH) — SIH/DataSUS.';
COMMENT ON COLUMN raw.sih_internacoes.morte IS '1 = paciente foi a óbito durante a internação.';

-- CNES/DataSUS — Estabelecimentos de saúde
CREATE TABLE IF NOT EXISTS raw.cnes_estabelecimentos (
    id                UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    cnes              VARCHAR(7),     -- Código CNES
    codufmun          CHAR(6),        -- Código IBGE do município
    uf                CHAR(2),
    cod_tipo_unidade  CHAR(2),        -- Tipo de estabelecimento
    nom_estab         VARCHAR(150),   -- Nome do estabelecimento
    tp_gestao         CHAR(1),        -- Tipo de gestão (M=municipal, E=estadual, D=dupla)
    vinc_sus          CHAR(1),        -- Vínculo com o SUS (S/N)
    tp_unidade        CHAR(2),        -- Subtipo de unidade
    latitude          NUMERIC(10, 7),
    longitude         NUMERIC(10, 7),
    ingested_at       TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.cnes_estabelecimentos IS 'Cadastro Nacional de Estabelecimentos de Saúde (CNES).';

-- CNES — Leitos por estabelecimento
CREATE TABLE IF NOT EXISTS raw.cnes_leitos (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    cnes            VARCHAR(7),     -- FK → cnes_estabelecimentos
    tp_leito        CHAR(2),        -- Tipo de leito
    qt_exist        SMALLINT,       -- Quantidade existente
    qt_sus          SMALLINT,       -- Quantidade disponível ao SUS
    competencia     CHAR(6),        -- Competência (AAAAMM)
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.cnes_leitos IS 'Leitos hospitalares por estabelecimento — CNES.';

-- IBGE — Indicadores socioeconômicos por setor censitário / bairro
CREATE TABLE IF NOT EXISTS raw.ibge_indicadores (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    cod_setor       VARCHAR(15),    -- Código do setor censitário
    cod_municipio   CHAR(7),        -- Código IBGE do município
    nom_bairro      VARCHAR(100),
    renda_media     NUMERIC(10, 2), -- Renda média domiciliar
    idhm            NUMERIC(5, 4),  -- IDH Municipal
    pop_total       INTEGER,
    pop_vulneravel  INTEGER,        -- Pop. em situação de vulnerabilidade
    ano_ref         SMALLINT,       -- Ano de referência do censo
    ingested_at     TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE raw.ibge_indicadores IS 'Indicadores socioeconômicos do IBGE por setor censitário.';

-- ===========================================================================
-- SCHEMA: trusted
-- Dados limpos e normalizados — base para análises
-- ===========================================================================

CREATE TABLE IF NOT EXISTS trusted.internacoes (
    id                  UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    raw_id              UUID REFERENCES raw.sih_internacoes(id),
    n_aih_hash          VARCHAR(64),    -- Hash SHA-256 do n_aih (privacidade)
    cnes_hospital       VARCHAR(7),
    municipio_res       CHAR(6),
    municipio_atend     CHAR(6),
    uf                  CHAR(2),
    data_internacao     DATE,
    data_saida          DATE,
    dias_permanencia    SMALLINT GENERATED ALWAYS AS (
                            (data_saida - data_internacao)::SMALLINT
                        ) STORED,
    cid_principal       VARCHAR(4),
    obito               BOOLEAN,
    sexo                CHAR(1),
    faixa_etaria        VARCHAR(10),    -- Ex: '60-69', '70-79'
    competencia         CHAR(6),        -- AAAAMM
    processed_at        TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE trusted.internacoes IS 'Internações limpas e anonimizadas para análise.';
COMMENT ON COLUMN trusted.internacoes.n_aih_hash IS 'SHA-256 do número AIH — permite rastreabilidade sem expor dado sensível.';
COMMENT ON COLUMN trusted.internacoes.dias_permanencia IS 'Coluna computada: diferença entre data_saida e data_internacao.';

CREATE TABLE IF NOT EXISTS trusted.estabelecimentos (
    id              UUID DEFAULT uuid_generate_v4() PRIMARY KEY,
    cnes            VARCHAR(7) UNIQUE NOT NULL,
    nome            VARCHAR(150),
    municipio       CHAR(6),
    uf              CHAR(2),
    tipo_unidade    CHAR(2),
    vinc_sus        BOOLEAN,
    lat             NUMERIC(10, 7),
    lon             NUMERIC(10, 7),
    total_leitos_sus SMALLINT,
    processed_at    TIMESTAMPTZ DEFAULT NOW()
);

COMMENT ON TABLE trusted.estabelecimentos IS 'Estabelecimentos de saúde normalizados com contagem de leitos SUS.';

-- ===========================================================================
-- SCHEMA: refined
-- Agregações para suporte a decisão e dashboards
-- ===========================================================================

-- Taxa de mortalidade por município e competência
CREATE TABLE IF NOT EXISTS refined.mortalidade_por_municipio (
    municipio       CHAR(6),
    competencia     CHAR(6),
    total_internacoes INTEGER,
    total_obitos    INTEGER,
    taxa_mortalidade NUMERIC(8, 4) GENERATED ALWAYS AS (
                        CASE WHEN total_internacoes > 0
                        THEN (total_obitos::NUMERIC / total_internacoes) * 100
                        ELSE 0 END
                    ) STORED,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (municipio, competencia)
);

COMMENT ON TABLE refined.mortalidade_por_municipio IS 'Taxa de mortalidade hospitalar agregada por município e competência.';

-- Disponibilidade de leitos SUS por município
CREATE TABLE IF NOT EXISTS refined.disponibilidade_leitos (
    municipio       CHAR(6),
    competencia     CHAR(6),
    total_leitos_sus INTEGER,
    pop_estimada    INTEGER,
    leitos_por_1000hab NUMERIC(8, 4) GENERATED ALWAYS AS (
                        CASE WHEN pop_estimada > 0
                        THEN (total_leitos_sus::NUMERIC / pop_estimada) * 1000
                        ELSE 0 END
                    ) STORED,
    updated_at      TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (municipio, competencia)
);

COMMENT ON TABLE refined.disponibilidade_leitos IS 'Disponibilidade de leitos SUS por 1.000 habitantes — indicador assistencial.';

-- ===========================================================================
-- Índices críticos para performance das queries analíticas
-- ===========================================================================
CREATE INDEX IF NOT EXISTS idx_sih_munic_mov     ON raw.sih_internacoes(munic_mov);
CREATE INDEX IF NOT EXISTS idx_sih_dt_inter      ON raw.sih_internacoes(dt_inter);
CREATE INDEX IF NOT EXISTS idx_sih_morte         ON raw.sih_internacoes(morte);
CREATE INDEX IF NOT EXISTS idx_cnes_codufmun     ON raw.cnes_estabelecimentos(codufmun);
CREATE INDEX IF NOT EXISTS idx_internacoes_cnes  ON trusted.internacoes(cnes_hospital);
CREATE INDEX IF NOT EXISTS idx_internacoes_mun   ON trusted.internacoes(municipio_atend);
CREATE INDEX IF NOT EXISTS idx_internacoes_comp  ON trusted.internacoes(competencia);
