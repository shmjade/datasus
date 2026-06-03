# Dicionários de Dados — DataSUS

Documentação dos 6 datasets ingeridos via pysus. Cada arquivo cobre todos os tipos/grupos do dataset, com colunas, domínios, joins típicos e caveats.

| Dataset | Arquivo | Conteúdo | # tipos |
|---|---|---|---|
| **SIH** | [`sih_dicionario.md`](sih_dicionario.md) | Internações hospitalares (AIH) — base operacional do SUS hospitalar | 4 (RD, SP, RJ, ER) |
| **CNES** | [`cnes_dicionario.md`](cnes_dicionario.md) | Cadastro de estabelecimentos: tipologia, leitos, profissionais, equipes, equipamentos, habilitações, serviços | 13 |
| **SIA** | [`sia_dicionario.md`](sia_dicionario.md) | Produção ambulatorial (consultas, exames, procedimentos sem internação) | 4 (PA, BI, PS, SAD) |
| **SIM** | [`sim_dicionario.md`](sim_dicionario.md) | Mortalidade (Declaração de Óbito) — causas, demografia, local | 1 (DO) |
| **SINASC** | [`sinasc_dicionario.md`](sinasc_dicionario.md) | Nascidos vivos (DN) — mãe, gestação, parto, RN | 1 (DN) |
| **SINAN** | [`sinan_dicionario.md`](sinan_dicionario.md) | Doenças de notificação compulsória — 58 agravos, do dengue à violência | 58 |

## Cruzando os datasets

- [`joins_guia.md`](joins_guia.md) — **como fazer joins entre tudo**: 3 tiers (estabelecimento, geografia, pessoa), receitas em pandas, pegadinhas e priorização pro NF01006

## Convenções comuns a todos os datasets

- **Datas**: `YYYYMMDD` (string) no SIH, SINAN; `DDMMYYYY` no SIM, SINASC. Sempre como string pra preservar zeros à esquerda.
- **UF**: sigla IBGE 2 dígitos (`43`=RS, `42`=SC, `41`=PR).
- **Município**: código IBGE 6 dígitos (UF + 4).
- **CNES**: 7 dígitos, chave universal de estabelecimento.
- **CID-10**: 4 chars (letra + 3 dígitos).
- **CBO-2002**: 6 dígitos.
- **CNS** (Cartão Nacional de Saúde): 15 dígitos; aparece **ofuscado** nos parquets do pysus por questão de privacidade.
- **SEXO**: divergência famosa — SIH usa `1`=M, `3`=F; SIM/SINASC/SINAN usam `1`=M, `2`=F.

## Pra projeto NF01006 (SIH + CNES + IBGE)

Os dois dicionários centrais são:

1. **[SIH](sih_dicionario.md)** — fonte das internações. `RD` é o coração; `SP` adiciona detalhe de procedimentos.
2. **[CNES](cnes_dicionario.md)** — fonte da capacidade hospitalar. `ST` (estabelecimento) + `LT` (leitos) são suficientes pra maioria das análises de oferta.

Os outros 4 são **complementares**:
- **SIM** se entrar análise de mortalidade pós-alta.
- **SINASC** se entrar materno-infantil.
- **SIA** se entrar análise de cuidado ambulatorial prévio à internação.
- **SINAN** se entrar doenças específicas (ex.: dengue → internação).

## Como ler no Jupyter

```python
from IPython.display import Markdown
display(Markdown(open("/app/docs/sih_dicionario.md").read()))
```

ou navegar pelo VSCode/IDE — eles renderizam markdown nativamente.
