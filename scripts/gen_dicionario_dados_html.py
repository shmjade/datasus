"""Gera docs/dicionario_dados.html consolidando todos os dicionários markdown.

Lê:
    docs/dicionarios_index.md   (intro)
    docs/sih_dicionario.md
    docs/cnes_dicionario.md
    docs/sia_dicionario.md
    docs/sim_dicionario.md
    docs/sinasc_dicionario.md
    docs/sinan_dicionario.md
    docs/joins_guia.md

Escreve:
    docs/dicionario_dados.html

Uso:
    python scripts/gen_dicionario_dados_html.py

Dependências: markdown (pip install markdown)
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import markdown  # type: ignore[import-untyped]

DOCS = Path(__file__).parent.parent / "docs"

# Ordem das seções no HTML final
SECOES: list[tuple[str, str, str | None]] = [
    ("intro", "Introdução", "dicionarios_index.md"),
    ("resumo-joins", "Resumo dos joins", None),  # custom inline
    ("sih", "SIH — Internações Hospitalares", "sih_dicionario.md"),
    ("cnes", "CNES — Cadastro de Estabelecimentos", "cnes_dicionario.md"),
    ("sia", "SIA — Produção Ambulatorial", "sia_dicionario.md"),
    ("sim", "SIM — Mortalidade", "sim_dicionario.md"),
    ("sinasc", "SINASC — Nascidos Vivos", "sinasc_dicionario.md"),
    ("sinan", "SINAN — Doenças de Notificação", "sinan_dicionario.md"),
    ("joins", "Guia completo de joins", "joins_guia.md"),
]

# Conteúdo do "Resumo dos joins" — gerado inline, não tem md correspondente
RESUMO_JOINS_MD = """
## Modelo mental — 3 tiers de join

| Tier | Granularidade | Chave | Confiabilidade |
|---|---|---|---|
| **1. Estabelecimento** | unidade × competência | `CNES + COMPETEN` | exato |
| **2. Geografia** | município × período | `codmun IBGE (6 dígitos) + ano/mês` | exato (em agregação) |
| **3. Pessoa** | indivíduo | composto: `(data nasc, sexo, município, ...)` | **probabilístico** |

## Mapa de chaves principais

### Por estabelecimento (CNES) — Tier 1

| Tabela origem | Chave de junção | → tabela alvo |
|---|---|---|
| SIH.RD / RJ / ER | `CNES` | CNES.ST |
| SIH.SP | `SP_CNES` | CNES.ST |
| SIA.PA | `PA_CODUNI` | CNES.ST |
| SIA.BI | `CODUNI` | CNES.ST |
| SIA.PS / SAD | `CNES_EXEC` | CNES.ST |
| SIM.DO | `CODESTAB` (se `LOCOCOR=1`) | CNES.ST |
| SINASC.DN | `CODESTAB` (se `LOCNASC=1`) | CNES.ST |
| SINAN.* | `ID_UNIDADE` | CNES.ST |
| CNES.LT / PF / EQ / HB / SR / etc. | `(CNES, COMPETEN)` | CNES.ST |

**Dentro do SIH:** RD ↔ SP por `N_AIH = SP_NAIH` (1:N).

### Por geografia (município IBGE 6 dígitos) — Tier 2

| Dataset | Residência (paciente) | Ocorrência (onde foi feito) |
|---|---|---|
| SIH.RD | `MUNIC_RES` | `MUNIC_MOV` |
| SIH.SP | `SP_M_PAC` | `SP_M_HOSP` |
| SIA.PA | `PA_MUNPCN` | `PA_UFMUN` |
| SIA.BI / PS / SAD | `MUNPAC` | `UFMUN` |
| SIM.DO | `CODMUNRES` | `CODMUNOCOR` |
| SINASC.DN | `CODMUNRES` | `CODMUNNASC` |
| SINAN.* | `ID_MN_RESI` | `ID_MUNICIP` |
| CNES.ST | — | `CODUFMUN` |

**Regra prática:**
- Para **taxa de incidência** (por habitante) → use **residência**.
- Para **utilização de serviço** → use **ocorrência**.

## Tipos de join recomendados por cenário

| Cenário | Tipo de join | Por quê |
|---|---|---|
| Enriquecer fato com cadastro (SIH + CNES.ST) | **LEFT JOIN** | Manter todas as internações; nem todo CNES estará cadastrado em todo mês |
| Capacidade × demanda (CNES.LT × SIH.RD agregados) | **INNER JOIN** após agregação | Comparar só onde há ambos os lados |
| Indicadores per capita (IBGE × *) | **LEFT JOIN** sobre IBGE | População é o denominador master |
| SIH.RD + SIH.RJ (todas tentativas) | **UNION ALL** + flag de origem | Não há overlap; concatenar |
| SINAN multi-doença | **UNION ALL** (só colunas comuns) | 58 doenças com schemas diferentes |
| Linkage SIH ↔ SIM (mortalidade pós-alta) | **INNER probabilístico** | Sem chave; aceita perda de recall |

## Pegadinhas que custam horas

1. **`SEXO` diverge**: SIM/SINASC/SINAN usam `2`=fem, SIH usa `3`=fem. **Normalize antes de qualquer join cruzado.**
2. **Datas**: SIM/SINASC usam `DDMMYYYY`; SIH/SINAN usam `YYYYMMDD`.
3. **CNES é snapshot mensal** — características mudam. Use sempre `(CNES, COMPETEN)`, não só `CNES`.
4. **CNES.PF** tem N linhas por profissional (1 por vínculo). Dedupe por `(CNES, CPFUNICO)` antes de contar.
5. **SIA.PA é gigante** (~4M linhas/mês no RS). Agregue **antes** de qualquer join.
6. **SINAN é Brasil-wide** — filtre por `SG_UF_NOT == 43` (RS) **antes** de tudo.
7. **`MUNIC_*` é 6 dígitos IBGE**. CSVs externos às vezes usam 7 (com dígito verificador). Trunque ou conserte.
8. **`IDADE` no SIM/SINAN é codificada** (4 dígitos, 1º = unidade temporal). `4028` = 28 anos.

## Receita típica para NF01006 (estabelecimentos × mortalidade no RS)

```
IBGE.populacao (master, denominador)
  ⟕ CNES.ST + CNES.LT       → leitos por município
  ⟕ SIH.RD                   → internações (numerador)
  ⟕ SIM.DO                   → óbitos (numerador)
  → join via (codmun, ano)
  → indicadores per capita
```

Indicadores derivados:
- `leitos_per_1000 = leitos_sus / populacao * 1000`
- `taxa_internacao = internacoes / populacao * 1000`
- `taxa_mortalidade = obitos / populacao * 1000`
- `letalidade_hosp = obitos_hosp / internacoes`

Receitas completas em pandas na seção **Guia completo de joins** abaixo.
"""

CSS = """
:root {
    --bg: #fdfdfd;
    --text: #222;
    --muted: #666;
    --accent: #2563eb;
    --code-bg: #f5f5f5;
    --border: #e5e5e5;
    --table-stripe: #fafafa;
    --hl: #fff8c5;
}
* { box-sizing: border-box; }
html { scroll-padding-top: 1rem; scroll-behavior: smooth; }
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    max-width: 1200px;
    margin: 0 auto;
    padding: 2rem;
    color: var(--text);
    background: var(--bg);
    line-height: 1.55;
    font-size: 15px;
}
.layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 2.5rem;
}
nav.toc {
    position: sticky;
    top: 1rem;
    align-self: start;
    font-size: 13.5px;
    max-height: calc(100vh - 2rem);
    overflow-y: auto;
    padding-right: 1rem;
    border-right: 1px solid var(--border);
}
nav.toc h2 {
    font-size: 12px;
    text-transform: uppercase;
    color: var(--muted);
    letter-spacing: 0.08em;
    margin: 0 0 0.6em;
    border: none;
    padding: 0;
}
nav.toc ol { list-style: none; padding-left: 0; margin: 0; }
nav.toc li { margin: 0.45rem 0; }
nav.toc a { color: var(--text); text-decoration: none; }
nav.toc a:hover { color: var(--accent); }
main { min-width: 0; }
h1, h2, h3, h4, h5 {
    line-height: 1.25;
    margin-top: 1.8em;
    margin-bottom: 0.6em;
    font-weight: 600;
}
h1 {
    font-size: 1.9em;
    border-bottom: 3px solid var(--accent);
    padding-bottom: 0.3em;
    margin-top: 2em;
}
section > h1:first-child { margin-top: 0; }
h2 {
    font-size: 1.35em;
    border-bottom: 1px solid var(--border);
    padding-bottom: 0.2em;
    margin-top: 2em;
}
h3 { font-size: 1.12em; }
h4 { font-size: 1em; color: var(--muted); }
code {
    font-family: ui-monospace, "SF Mono", Menlo, Monaco, Consolas, monospace;
    font-size: 0.88em;
    background: var(--code-bg);
    padding: 0.1em 0.4em;
    border-radius: 3px;
}
pre {
    background: var(--code-bg);
    border: 1px solid var(--border);
    border-radius: 5px;
    padding: 0.9em 1.1em;
    overflow-x: auto;
    line-height: 1.45;
    font-size: 13px;
}
pre code { background: transparent; padding: 0; font-size: inherit; }
table {
    border-collapse: collapse;
    margin: 1em 0;
    font-size: 0.93em;
    width: 100%;
    table-layout: auto;
}
th, td {
    text-align: left;
    padding: 0.5em 0.8em;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}
th {
    background: var(--code-bg);
    font-weight: 600;
}
tr:nth-child(even) td { background: var(--table-stripe); }
a { color: var(--accent); text-decoration: none; }
a:hover { text-decoration: underline; }
hr { border: 0; border-top: 1px solid var(--border); margin: 2.5em 0; }
header.doc-header {
    padding-bottom: 1.5em;
    margin-bottom: 1.5em;
    border-bottom: 1px solid var(--border);
}
header.doc-header h1 {
    margin-top: 0;
    border: none;
    padding: 0;
    font-size: 2em;
}
header.doc-header .meta {
    color: var(--muted);
    font-size: 14px;
    margin-top: 0.5em;
}
section { margin-bottom: 3em; padding-top: 0.5em; }
blockquote {
    border-left: 4px solid var(--accent);
    margin: 1em 0;
    padding: 0.5em 1em;
    background: var(--code-bg);
    color: var(--muted);
}
ul, ol { padding-left: 1.5em; }
li { margin: 0.2em 0; }
strong { color: #000; }
.tier-1 { background: #ecfdf5; }
.tier-2 { background: #eff6ff; }
.tier-3 { background: #fef3c7; }
@media (max-width: 800px) {
    .layout { grid-template-columns: 1fr; }
    nav.toc {
        position: static;
        border-right: none;
        border-bottom: 1px solid var(--border);
        padding: 0 0 1em;
        max-height: none;
        margin-bottom: 1.5em;
    }
}
@media print {
    nav.toc { display: none; }
    .layout { grid-template-columns: 1fr; }
    body { max-width: 100%; padding: 1cm; font-size: 11pt; }
    pre { page-break-inside: avoid; }
    h1, h2 { page-break-after: avoid; }
}
"""

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Dicionário de Dados — DataSUS</title>
<style>{css}</style>
</head>
<body>
<header class="doc-header">
<h1>Dicionário de Dados — DataSUS</h1>
<div class="meta">Gerado em {data} · projeto NF01006 (UFRGS) · 6 datasets · ~150 colunas em SIH.RD, ~208 em CNES.ST</div>
</header>
<div class="layout">
<nav class="toc">
<h2>Índice</h2>
<ol>{toc}</ol>
</nav>
<main>
{conteudo}
</main>
</div>
</body>
</html>
"""


def renderiza_md(md_text: str) -> str:
    """Converte markdown → HTML usando python-markdown com extensões necessárias."""
    md = markdown.Markdown(
        extensions=["tables", "fenced_code", "sane_lists"],
        output_format="html5",
    )
    return md.convert(md_text)


def remove_h1_principal(md_text: str) -> str:
    """Remove o H1 inicial do md — vamos usar o título da seção do TOC."""
    lines = md_text.split("\n")
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    return "\n".join(lines).lstrip()


def main() -> None:
    secoes_html: list[str] = []
    toc_items: list[str] = []

    for slug, titulo, md_filename in SECOES:
        if md_filename is None:
            md_text = RESUMO_JOINS_MD
        else:
            md_path = DOCS / md_filename
            md_text = md_path.read_text(encoding="utf-8")

        md_text = remove_h1_principal(md_text)
        html_content = renderiza_md(md_text)

        section_html = (
            f'<section id="{slug}">\n'
            f'<h1>{titulo}</h1>\n'
            f"{html_content}\n"
            f"</section>"
        )
        secoes_html.append(section_html)

        toc_items.append(f'<li><a href="#{slug}">{titulo}</a></li>')

    output = HTML_TEMPLATE.format(
        css=CSS,
        data=date.today().isoformat(),
        toc="\n".join(toc_items),
        conteudo="\n\n".join(secoes_html),
    )

    out_path = DOCS / "dicionario_dados.html"
    out_path.write_text(output, encoding="utf-8")
    size_kb = len(output) // 1024
    print(f"Gerado: {out_path} ({size_kb} KB, {len(SECOES)} seções)")


if __name__ == "__main__":
    main()
