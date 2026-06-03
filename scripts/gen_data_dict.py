"""Gera docs/data_dict.html — dicionário de dados SIH/RD.

Cruza:
  1. Catálogo curado DataSUS (descrição, categoria, mapa de valores)
  2. Estatísticas reais do bronze (nulos, cardinalidade, top 3 valores)
  3. Sugestão de tipo destino para Silver
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession, functions as F

BRONZE = "/app/data/lake/bronze/sih_rd"
OUTPUT = "/app/docs/data_dict.html"

# =============================================================================
# Catálogo curado a partir da especificação oficial DataSUS SIH/RD
# Categorias: id, hosp, paciente, data, clinico, uti, valor, aux
# =============================================================================
CATALOG: dict[str, dict] = {
    # ---- Identificação ----
    "UF_ZI":     {"cat": "id", "desc": "UF da Zona de Internação (código IBGE 2 dígitos)", "tipo": "char(2)"},
    "ANO_CMPT":  {"cat": "id", "desc": "Ano de competência da AIH (AAAA)", "tipo": "smallint"},
    "MES_CMPT":  {"cat": "id", "desc": "Mês de competência da AIH (MM)", "tipo": "smallint"},
    "N_AIH":     {"cat": "id", "desc": "Número da AIH (13 dígitos) — anonimizar via SHA-256 na Silver (LGPD)", "tipo": "varchar(13)"},
    "IDENT":     {"cat": "id", "desc": "Tipo da AIH", "tipo": "char(1)",
                  "valores": {"1": "Normal", "5": "Longa permanência"}},
    "SEQUENCIA": {"cat": "id", "desc": "Sequencial da AIH na remessa", "tipo": "integer"},
    "REMESSA":   {"cat": "id", "desc": "Identificação da remessa do arquivo", "tipo": "varchar"},
    "SEQ_AIH5":  {"cat": "id", "desc": "Sequência AIH 5 (longa permanência)", "tipo": "varchar"},

    # ---- Hospital / Estabelecimento ----
    "CGC_HOSP":  {"cat": "hosp", "desc": "CNPJ do hospital (14 dígitos)", "tipo": "varchar(14)"},
    "CNES":      {"cat": "hosp", "desc": "Código CNES do hospital (7 dígitos) — FK p/ CNES", "tipo": "varchar(7)"},
    "CNPJ_MANT": {"cat": "hosp", "desc": "CNPJ da mantenedora", "tipo": "varchar(14)"},
    "ESPEC":     {"cat": "hosp", "desc": "Especialidade do leito", "tipo": "char(2)",
                  "valores": {"01":"Cirurgia","02":"Obstetrícia","03":"Clínica médica",
                              "04":"Crônicos","05":"Psiquiatria","06":"Tisiologia",
                              "07":"Pediatria","08":"Reabilitação","09":"Hospital-dia",
                              "10":"Pediatria cirúrgica","87":"Outros"}},
    "NATUREZA":  {"cat": "hosp", "desc": "Natureza do estabelecimento (público/privado/etc.)", "tipo": "char(2)"},
    "NAT_JUR":   {"cat": "hosp", "desc": "Natureza jurídica (Receita Federal)", "tipo": "char(4)"},
    "GESTAO":    {"cat": "hosp", "desc": "Tipo de gestão da unidade", "tipo": "char(1)",
                  "valores": {"1":"Estadual","2":"Municipal","3":"Dupla"}},
    "COMPLEX":   {"cat": "hosp", "desc": "Complexidade do atendimento", "tipo": "char(2)",
                  "valores": {"02":"Média complexidade","03":"Alta complexidade"}},
    "FINANC":    {"cat": "hosp", "desc": "Tipo de financiamento", "tipo": "char(2)",
                  "valores": {"04":"Estratégico","05":"Atenção básica",
                              "06":"Média/alta complexidade","07":"Alta complexidade",
                              "08":"FAEC"}},
    "REGCT":     {"cat": "hosp", "desc": "Regra contratual (código)", "tipo": "char(4)"},
    "GESTOR_COD":{"cat": "hosp", "desc": "Código do gestor da AIH", "tipo": "varchar"},
    "GESTOR_TP": {"cat": "hosp", "desc": "Tipo do gestor", "tipo": "char(1)",
                  "valores": {"1":"Estadual","2":"Municipal"}},
    "GESTOR_CPF":{"cat": "hosp", "desc": "CPF do gestor", "tipo": "varchar(11)"},
    "GESTOR_DT": {"cat": "hosp", "desc": "Data do gestor (AAAAMMDD)", "tipo": "char(8)"},

    # ---- Paciente ----
    "CEP":       {"cat": "paciente", "desc": "CEP do paciente (8 dígitos)", "tipo": "varchar(8)"},
    "MUNIC_RES": {"cat": "paciente", "desc": "Município de residência (IBGE 6 dígitos)", "tipo": "char(6)"},
    "MUNIC_MOV": {"cat": "paciente", "desc": "Município de atendimento (IBGE 6 dígitos) — diferença vs MUNIC_RES indica transferência", "tipo": "char(6)"},
    "NASC":      {"cat": "paciente", "desc": "Data de nascimento (AAAAMMDD)", "tipo": "date"},
    "SEXO":      {"cat": "paciente", "desc": "Sexo", "tipo": "char(1)",
                  "valores": {"1":"Masculino","3":"Feminino"}},
    "COD_IDADE": {"cat": "paciente", "desc": "Unidade da idade", "tipo": "char(1)",
                  "valores": {"2":"Dias","3":"Meses","4":"Anos","5":"Anos > 100"}},
    "IDADE":     {"cat": "paciente", "desc": "Idade do paciente (valor numérico, ler com COD_IDADE)", "tipo": "smallint"},
    "RACA_COR":  {"cat": "paciente", "desc": "Raça/cor declarada", "tipo": "char(2)",
                  "valores": {"01":"Branca","02":"Preta","03":"Parda","04":"Amarela",
                              "05":"Indígena","99":"Sem informação"}},
    "ETNIA":     {"cat": "paciente", "desc": "Código de etnia indígena (FUNASA) — só preenchido para RACA_COR=5", "tipo": "char(4)"},
    "INSTRU":    {"cat": "paciente", "desc": "Grau de instrução", "tipo": "char(1)",
                  "valores": {"0":"Sem informação","1":"Analfabeto","2":"Fund. incompleto",
                              "3":"Fund. completo","4":"Médio completo","5":"Superior"}},
    "NACIONAL":  {"cat": "paciente", "desc": "Nacionalidade (010=brasileira)", "tipo": "char(3)"},
    "HOMONIMO":  {"cat": "paciente", "desc": "Indicador de homônimo", "tipo": "char(1)",
                  "valores": {"0":"Não","1":"Sim, conferido","2":"Sim, não conferido"}},
    "NUM_FILHOS":{"cat": "paciente", "desc": "Número de filhos (para gestantes)", "tipo": "smallint"},
    "INSC_PN":   {"cat": "paciente", "desc": "Inscrição no pré-natal (SISPRENATAL)", "tipo": "varchar"},
    "GESTRISCO": {"cat": "paciente", "desc": "Indicador de gestação de risco", "tipo": "char(1)",
                  "valores": {"0":"Não","1":"Sim"}},
    "CONTRACEP1":{"cat": "paciente", "desc": "Contraceptivo principal", "tipo": "char(2)"},
    "CONTRACEP2":{"cat": "paciente", "desc": "Contraceptivo secundário", "tipo": "char(2)"},
    "CBOR":      {"cat": "paciente", "desc": "CBO — Classificação Brasileira de Ocupações", "tipo": "char(6)"},
    "CNAER":     {"cat": "paciente", "desc": "CNAE — Atividade econômica", "tipo": "char(4)"},
    "VINCPREV":  {"cat": "paciente", "desc": "Vínculo previdenciário", "tipo": "char(1)"},

    # ---- Datas / Permanência ----
    "DT_INTER":  {"cat": "data", "desc": "Data de internação (AAAAMMDD)", "tipo": "date"},
    "DT_SAIDA":  {"cat": "data", "desc": "Data de saída — null para óbito sem registro de saída", "tipo": "date"},
    "DIAS_PERM": {"cat": "data", "desc": "Dias de permanência (calculado pelo DataSUS)", "tipo": "smallint"},

    # ---- Diagnóstico / Procedimento ----
    "DIAG_PRINC":{"cat": "clinico", "desc": "CID-10 do diagnóstico principal (4 caracteres)", "tipo": "varchar(4)"},
    "DIAG_SECUN":{"cat": "clinico", "desc": "CID-10 do diagnóstico secundário principal", "tipo": "varchar(4)"},
    "DIAGSEC1":  {"cat": "clinico", "desc": "CID-10 secundário adicional 1", "tipo": "varchar(4)"},
    "DIAGSEC2":  {"cat": "clinico", "desc": "CID-10 secundário adicional 2", "tipo": "varchar(4)"},
    "DIAGSEC3":  {"cat": "clinico", "desc": "CID-10 secundário adicional 3", "tipo": "varchar(4)"},
    "DIAGSEC4":  {"cat": "clinico", "desc": "CID-10 secundário adicional 4", "tipo": "varchar(4)"},
    "DIAGSEC5":  {"cat": "clinico", "desc": "CID-10 secundário adicional 5", "tipo": "varchar(4)"},
    "DIAGSEC6":  {"cat": "clinico", "desc": "CID-10 secundário adicional 6", "tipo": "varchar(4)"},
    "DIAGSEC7":  {"cat": "clinico", "desc": "CID-10 secundário adicional 7", "tipo": "varchar(4)"},
    "DIAGSEC8":  {"cat": "clinico", "desc": "CID-10 secundário adicional 8", "tipo": "varchar(4)"},
    "DIAGSEC9":  {"cat": "clinico", "desc": "CID-10 secundário adicional 9", "tipo": "varchar(4)"},
    "TPDISEC1":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 1 (relação com principal)", "tipo": "char(1)"},
    "TPDISEC2":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 2", "tipo": "char(1)"},
    "TPDISEC3":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 3", "tipo": "char(1)"},
    "TPDISEC4":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 4", "tipo": "char(1)"},
    "TPDISEC5":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 5", "tipo": "char(1)"},
    "TPDISEC6":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 6", "tipo": "char(1)"},
    "TPDISEC7":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 7", "tipo": "char(1)"},
    "TPDISEC8":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 8", "tipo": "char(1)"},
    "TPDISEC9":  {"cat": "clinico", "desc": "Tipo do diagnóstico secundário 9", "tipo": "char(1)"},
    "CID_ASSO":  {"cat": "clinico", "desc": "CID-10 associado", "tipo": "varchar(4)"},
    "CID_MORTE": {"cat": "clinico", "desc": "CID-10 da causa de morte (quando MORTE=1)", "tipo": "varchar(4)"},
    "CID_NOTIF": {"cat": "clinico", "desc": "CID-10 de notificação compulsória", "tipo": "varchar(4)"},
    "PROC_SOLIC":{"cat": "clinico", "desc": "Procedimento solicitado (código SIGTAP, 10 dígitos)", "tipo": "varchar(10)"},
    "PROC_REA":  {"cat": "clinico", "desc": "Procedimento realizado (código SIGTAP, 10 dígitos)", "tipo": "varchar(10)"},
    "CAR_INT":   {"cat": "clinico", "desc": "Caráter da internação", "tipo": "char(2)",
                  "valores": {"01":"Eletivo","02":"Urgência",
                              "03":"Acid. trabalho típico","04":"Acid. trajeto",
                              "05":"Outros traumas","06":"Outros tipos"}},
    "COBRANCA":  {"cat": "clinico", "desc": "Motivo da cobrança/saída (alta, transferência, óbito)", "tipo": "char(2)"},
    "MORTE":     {"cat": "clinico", "desc": "Indicador de óbito", "tipo": "smallint",
                  "valores": {"0":"Sobreviveu","1":"Óbito"}},
    "MARCA_UTI": {"cat": "clinico", "desc": "Tipo de UTI utilizada (00 = não usou)", "tipo": "char(2)",
                  "valores": {"00":"Sem UTI","75":"UTI adulto","76":"UTI pediátrica",
                              "78":"UTI neonatal","81":"UTI coronariana","82":"UTI queimados"}},
    "MARCA_UCI": {"cat": "clinico", "desc": "Tipo de UCI (Unidade de Cuidados Intermediários)", "tipo": "char(2)"},
    "IND_VDRL":  {"cat": "clinico", "desc": "VDRL realizado (sífilis em gestantes)", "tipo": "char(1)",
                  "valores": {"0":"Não","1":"Sim"}},
    "FAEC_TP":   {"cat": "clinico", "desc": "Tipo FAEC (Fundo de Ações Estratégicas)", "tipo": "char(2)"},
    "AUD_JUST":  {"cat": "clinico", "desc": "Justificativa do auditor", "tipo": "varchar"},
    "SIS_JUST":  {"cat": "clinico", "desc": "Justificativa do sistema", "tipo": "varchar"},
    "INFEHOSP":  {"cat": "clinico", "desc": "Indicador de infecção hospitalar", "tipo": "char(1)"},
    "CPF_AUT":   {"cat": "clinico", "desc": "CPF do autorizador", "tipo": "varchar(11)"},
    "NUM_PROC":  {"cat": "clinico", "desc": "Número do processo administrativo", "tipo": "varchar"},

    # ---- UTI (intervalos) ----
    "UTI_MES_IN":{"cat": "uti", "desc": "Dia de entrada na UTI no mês", "tipo": "smallint"},
    "UTI_MES_AN":{"cat": "uti", "desc": "Dia anterior à UTI no mês", "tipo": "smallint"},
    "UTI_MES_AL":{"cat": "uti", "desc": "Dia de alta da UTI no mês", "tipo": "smallint"},
    "UTI_MES_TO":{"cat": "uti", "desc": "Total de dias em UTI no mês", "tipo": "smallint"},
    "UTI_INT_IN":{"cat": "uti", "desc": "Dia de entrada na UTI (internação completa)", "tipo": "smallint"},
    "UTI_INT_AN":{"cat": "uti", "desc": "Dia anterior à UTI (internação)", "tipo": "smallint"},
    "UTI_INT_AL":{"cat": "uti", "desc": "Dia de alta da UTI (internação)", "tipo": "smallint"},
    "UTI_INT_TO":{"cat": "uti", "desc": "Total de dias em UTI na internação", "tipo": "smallint"},

    # ---- Valores monetários ----
    "VAL_SH":    {"cat": "valor", "desc": "Valor de serviços hospitalares (R$)", "tipo": "numeric(12,2)"},
    "VAL_SP":    {"cat": "valor", "desc": "Valor de serviços profissionais (R$)", "tipo": "numeric(12,2)"},
    "VAL_SADT":  {"cat": "valor", "desc": "Valor SADT (Serviços Auxiliares de Diagnóstico e Terapia)", "tipo": "numeric(12,2)"},
    "VAL_RN":    {"cat": "valor", "desc": "Valor recém-nascido", "tipo": "numeric(12,2)"},
    "VAL_ACOMP": {"cat": "valor", "desc": "Valor diárias de acompanhante", "tipo": "numeric(12,2)"},
    "VAL_ORTP":  {"cat": "valor", "desc": "Valor órtese/prótese", "tipo": "numeric(12,2)"},
    "VAL_SANGUE":{"cat": "valor", "desc": "Valor sangue/hemoderivados", "tipo": "numeric(12,2)"},
    "VAL_SADTSR":{"cat": "valor", "desc": "Valor SADT sem registro", "tipo": "numeric(12,2)"},
    "VAL_TRANSP":{"cat": "valor", "desc": "Valor transporte", "tipo": "numeric(12,2)"},
    "VAL_OBSANG":{"cat": "valor", "desc": "Valor observação sanguínea", "tipo": "numeric(12,2)"},
    "VAL_PED1AC":{"cat": "valor", "desc": "Valor pediatria primeiro acolhimento", "tipo": "numeric(12,2)"},
    "VAL_TOT":   {"cat": "valor", "desc": "Valor total da AIH (R$)", "tipo": "numeric(12,2)"},
    "VAL_UTI":   {"cat": "valor", "desc": "Valor cobrado pela UTI (R$)", "tipo": "numeric(12,2)"},
    "VAL_UCI":   {"cat": "valor", "desc": "Valor cobrado pela UCI (R$)", "tipo": "numeric(12,2)"},
    "VAL_SH_FED":{"cat": "valor", "desc": "Valor SH federal", "tipo": "numeric(12,2)"},
    "VAL_SP_FED":{"cat": "valor", "desc": "Valor SP federal", "tipo": "numeric(12,2)"},
    "VAL_SH_GES":{"cat": "valor", "desc": "Valor SH gestor", "tipo": "numeric(12,2)"},
    "VAL_SP_GES":{"cat": "valor", "desc": "Valor SP gestor", "tipo": "numeric(12,2)"},
    "US_TOT":    {"cat": "valor", "desc": "Valor total em US$ (taxa de conversão DataSUS)", "tipo": "numeric(12,2)"},
    "TOT_PT_SP": {"cat": "valor", "desc": "Total de pontos de serviços profissionais", "tipo": "numeric(12,2)"},
    "RUBRICA":   {"cat": "valor", "desc": "Rubrica orçamentária", "tipo": "char(4)"},
    "QT_DIARIAS":{"cat": "valor", "desc": "Quantidade de diárias cobradas", "tipo": "smallint"},
    "DIAR_ACOM": {"cat": "valor", "desc": "Diárias de acompanhante cobradas", "tipo": "smallint"},

    # ---- Auxiliares / Partição (gerados pelo pysus) ----
    "uf":  {"cat": "aux", "desc": "Partição (UF, gerado pelo pysus)", "tipo": "char(2)"},
    "ano": {"cat": "aux", "desc": "Partição (ano, gerado pelo pysus)", "tipo": "smallint"},
    "mes": {"cat": "aux", "desc": "Partição (mês, gerado pelo pysus)", "tipo": "smallint"},
}

CATEGORIA_INFO = {
    "id":       ("Identificação",          "AIH, sequência, competência."),
    "hosp":     ("Hospital / Estabelecimento", "CNPJ, CNES, gestão, complexidade."),
    "paciente": ("Paciente",                "Demografia, residência, sociais."),
    "data":     ("Datas e permanência",    "Internação, saída, dias internado."),
    "clinico":  ("Clínico (CID, procedimento, desfecho)", "Diagnósticos, procedimentos, óbito, UTI."),
    "uti":      ("UTI — uso e duração",    "Dias em UTI no mês e na internação completa."),
    "valor":    ("Valores monetários",     "Componentes do custo da AIH."),
    "aux":      ("Auxiliares (partição)",   "Campos adicionados pelo pysus."),
}


def coleta_stats(spark: SparkSession) -> tuple[dict, int]:
    """Para cada coluna: nulos+vazios, cardinalidade, top 3 valores."""
    df = spark.read.parquet(BRONZE)
    total = df.count()
    cols = df.columns

    # 1 pass para nulos + cardinalidade
    exprs = []
    for c in cols:
        exprs.append(F.count(F.when(F.col(c).isNull() | (F.col(c) == ""), c)).alias(f"null_{c}"))
        exprs.append(F.approx_count_distinct(c).alias(f"card_{c}"))
    summary = df.agg(*exprs).collect()[0].asDict()

    # top 3 valores por coluna (loop — não vetorizamos pra evitar 116*N joins)
    stats = {}
    for c in cols:
        top = (df.groupBy(c).count()
                 .orderBy(F.desc("count")).limit(3).collect())
        stats[c] = {
            "nulos": summary[f"null_{c}"],
            "card": summary[f"card_{c}"],
            "top3": [(r[c] if r[c] not in (None, "") else "(vazio)", r["count"]) for r in top],
        }
    return stats, total


def render_html(stats: dict, total: int) -> str:
    cols_in_data = set(stats.keys())
    cols_in_catalog = set(CATALOG.keys())

    extras = sorted(cols_in_data - cols_in_catalog)
    if extras:
        for c in extras:
            CATALOG[c] = {"cat": "aux", "desc": "Coluna não documentada no catálogo curado", "tipo": "?"}

    # Tabela por categoria
    grupos: dict[str, list[str]] = {k: [] for k in CATEGORIA_INFO}
    for c, meta in CATALOG.items():
        if c in cols_in_data:
            grupos.setdefault(meta["cat"], []).append(c)
    for cat in grupos:
        grupos[cat].sort()

    n_total_cols = len(cols_in_data)
    n_100_nulas = sum(1 for c in cols_in_data if stats[c]["nulos"] == total)
    n_constantes = sum(1 for c in cols_in_data if stats[c]["card"] == 1 and stats[c]["nulos"] < total)
    n_uteis = n_total_cols - n_100_nulas - n_constantes

    gerado_em = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    def fmt_top3(top3):
        parts = []
        for v, n in top3:
            pct = n / total * 100
            parts.append(f"<code>{html.escape(str(v))}</code> <span class='pct'>{n:,} ({pct:.1f}%)</span>")
        return "<br/>".join(parts)

    def fmt_valores(mapa):
        if not mapa:
            return ""
        items = "".join(
            f"<li><code>{html.escape(k)}</code> {html.escape(v)}</li>"
            for k, v in mapa.items()
        )
        return f"<ul class='valores'>{items}</ul>"

    def status_badge(c):
        s = stats[c]
        if s["nulos"] == total:
            return '<span class="badge badge-red">100% nula</span>'
        if s["card"] == 1:
            return '<span class="badge badge-orange">constante</span>'
        pct_nulo = s["nulos"] / total * 100
        if pct_nulo > 50:
            return f'<span class="badge badge-yellow">{pct_nulo:.1f}% nula</span>'
        if pct_nulo > 0:
            return f'<span class="badge badge-blue">{pct_nulo:.2f}% nula</span>'
        return '<span class="badge badge-green">100% preenchida</span>'

    # ============= HTML =============
    rows_html = []
    for cat, (titulo_cat, sub) in CATEGORIA_INFO.items():
        colunas = grupos.get(cat, [])
        if not colunas:
            continue
        rows_html.append(
            f'<h2 id="cat-{cat}" data-cat="{cat}">{html.escape(titulo_cat)} '
            f'<small>{html.escape(sub)} · {len(colunas)} colunas</small></h2>'
        )
        rows_html.append('<table class="dict"><thead><tr>'
                         '<th>Coluna</th><th>Tipo (DataSUS)</th>'
                         '<th>Descrição / Valores</th><th>Stats</th>'
                         '<th>Top 3 valores</th></tr></thead><tbody>')
        for c in colunas:
            meta = CATALOG[c]
            s = stats[c]
            valores_html = fmt_valores(meta.get("valores"))
            rows_html.append(
                f'<tr data-col="{c}" data-cat="{cat}">'
                f'<td><code class="col-name">{html.escape(c)}</code></td>'
                f'<td><span class="tipo">{html.escape(meta["tipo"])}</span></td>'
                f'<td>{html.escape(meta["desc"])}{valores_html}</td>'
                f'<td>{status_badge(c)}<br/>'
                f'<small>{s["card"]:,} distintos</small></td>'
                f'<td>{fmt_top3(s["top3"])}</td>'
                f'</tr>'
            )
        rows_html.append('</tbody></table>')

    rows = "\n".join(rows_html)

    cat_nav = " · ".join(
        f'<a href="#cat-{cat}">{html.escape(titulo)}</a>'
        for cat, (titulo, _) in CATEGORIA_INFO.items()
        if grupos.get(cat)
    )

    return f"""<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Dicionário SIH/RD — DataSUS / RS</title>
<meta name="viewport" content="width=device-width,initial-scale=1">
<style>
  :root {{
    --azul: #2563eb;
    --cinza-claro: #f3f4f6;
    --cinza: #6b7280;
    --vermelho: #dc2626;
    --laranja: #ea580c;
    --amarelo: #d97706;
    --verde: #16a34a;
  }}
  * {{ box-sizing: border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
    margin: 0; color: #111827; line-height: 1.45;
  }}
  header {{
    background: #1e3a8a; color: white; padding: 24px 32px;
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
  .card .num {{ font-size: 24px; font-weight: 600; color: var(--azul); }}
  .card .label {{ font-size: 12px; color: var(--cinza); text-transform: uppercase; letter-spacing: .04em; }}
  nav.cats {{ background: white; padding: 12px 0; border-bottom: 1px solid #e5e7eb;
              position: sticky; top: 0; z-index: 10; margin: -24px -32px 24px; padding-left: 32px; padding-right: 32px; }}
  nav.cats a {{ color: var(--azul); text-decoration: none; margin-right: 6px; font-size: 13px; }}
  nav.cats a:hover {{ text-decoration: underline; }}
  .search {{
    display: flex; gap: 10px; align-items: center; margin: 16px 0 24px;
  }}
  .search input {{
    flex: 1; padding: 8px 12px; font-size: 14px; border: 1px solid #d1d5db; border-radius: 6px;
  }}
  h2 {{
    margin: 32px 0 12px; padding-bottom: 6px; border-bottom: 2px solid #e5e7eb;
    font-size: 18px;
  }}
  h2 small {{ font-weight: 400; color: var(--cinza); font-size: 13px; margin-left: 8px; }}
  table.dict {{
    width: 100%; border-collapse: collapse; font-size: 13px; margin-bottom: 8px;
  }}
  table.dict th, table.dict td {{
    text-align: left; padding: 10px 12px; border-bottom: 1px solid #e5e7eb;
    vertical-align: top;
  }}
  table.dict th {{
    background: #f9fafb; font-weight: 600; font-size: 12px;
    text-transform: uppercase; letter-spacing: .04em; color: var(--cinza);
  }}
  table.dict tr:hover td {{ background: #fafafa; }}
  code {{
    background: #f3f4f6; padding: 1px 5px; border-radius: 3px;
    font-family: "SF Mono", Consolas, monospace; font-size: 12px;
  }}
  code.col-name {{ font-weight: 600; color: #111827; background: none; padding: 0; }}
  .tipo {{
    background: #ede9fe; color: #6d28d9; padding: 2px 6px; border-radius: 4px;
    font-size: 11px; font-family: monospace;
  }}
  .badge {{
    display: inline-block; padding: 2px 8px; border-radius: 12px; font-size: 11px;
    font-weight: 500;
  }}
  .badge-red    {{ background: #fee2e2; color: var(--vermelho); }}
  .badge-orange {{ background: #ffedd5; color: var(--laranja); }}
  .badge-yellow {{ background: #fef3c7; color: var(--amarelo); }}
  .badge-blue   {{ background: #dbeafe; color: var(--azul); }}
  .badge-green  {{ background: #dcfce7; color: var(--verde); }}
  ul.valores {{
    margin: 6px 0 0; padding-left: 20px; font-size: 12px; color: #374151;
  }}
  ul.valores li {{ margin: 2px 0; }}
  .pct {{ color: var(--cinza); font-size: 11px; }}
  tr.hidden {{ display: none; }}
  footer {{
    margin: 48px 0 24px; padding-top: 16px; border-top: 1px solid #e5e7eb;
    color: var(--cinza); font-size: 12px; text-align: center;
  }}
</style>
</head>
<body>
<header>
  <h1>📊 Dicionário de Dados — SIH/RD (Autorização de Internação Hospitalar)</h1>
  <div class="meta">
    Fonte: <code>pysus</code> 2.1.0 · DataSUS · camada <strong>bronze</strong> do projeto DataSUS-POA<br/>
    Estatísticas geradas a partir de {total:,} linhas reais do RS · {gerado_em}
  </div>
</header>

<div class="container">
  <div class="summary">
    <div class="card"><div class="num">{n_total_cols}</div><div class="label">Colunas no bronze</div></div>
    <div class="card"><div class="num">{n_uteis}</div><div class="label">Úteis</div></div>
    <div class="card"><div class="num">{n_constantes}</div><div class="label">Constantes (cardinalidade=1)</div></div>
    <div class="card"><div class="num">{n_100_nulas}</div><div class="label">100% nulas</div></div>
  </div>

  <nav class="cats">{cat_nav}</nav>

  <div class="search">
    <input id="q" type="search" placeholder="Filtrar por nome, descrição ou categoria... (ex: CID, sepse, valor)">
    <span id="q-count" class="pct"></span>
  </div>

  {rows}

  <footer>
    Gerado por <code>scripts/gen_data_dict.py</code> ·
    Especificação oficial: DataSUS &mdash;
    Estrutura do Arquivo de Saída SIH/SUS RD
  </footer>
</div>

<script>
  const q = document.getElementById('q');
  const count = document.getElementById('q-count');
  const rows = Array.from(document.querySelectorAll('table.dict tbody tr'));
  function filtrar() {{
    const v = q.value.toLowerCase().trim();
    let visible = 0;
    rows.forEach(r => {{
      const txt = r.textContent.toLowerCase();
      const match = !v || txt.includes(v);
      r.classList.toggle('hidden', !match);
      if (match) visible++;
    }});
    count.textContent = v ? `${{visible}}/${{rows.length}} linhas visíveis` : '';
  }}
  q.addEventListener('input', filtrar);
</script>
</body>
</html>
"""


def main():
    spark = (SparkSession.builder.master("local[*]")
             .appName("gen_data_dict")
             .config("spark.sql.ansi.enabled", "false")
             .getOrCreate())
    spark.sparkContext.setLogLevel("ERROR")

    print("Coletando estatísticas...")
    stats, total = coleta_stats(spark)
    print(f"{total:,} linhas, {len(stats)} colunas")

    print("Renderizando HTML...")
    html_str = render_html(stats, total)

    out = Path(OUTPUT)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(html_str, encoding="utf-8")
    print(f"Gravado em {out} ({out.stat().st_size/1024:.1f} KB)")

    # Snapshot JSON também — útil para diffs em CI
    out_json = out.with_suffix(".json")
    out_json.write_text(json.dumps({
        "total_linhas": total,
        "colunas": {c: {**CATALOG[c], **stats[c]} for c in stats},
    }, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"Snapshot JSON: {out_json}")

    spark.stop()


if __name__ == "__main__":
    main()
