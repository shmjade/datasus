# Guia de Contribuição

Obrigado por considerar contribuir com o projeto DataSUS! Este guia descreve o fluxo de trabalho, convenções e padrões de qualidade que adotamos.

---

## Índice

- [Pré-requisitos](#pré-requisitos)
- [Fluxo de Trabalho](#fluxo-de-trabalho)
- [Nomenclatura de Branches](#nomenclatura-de-branches)
- [Convenção de Commits](#convenção-de-commits)
- [Padrões de Código](#padrões-de-código)
- [Testes](#testes)
- [Pull Requests](#pull-requests)
- [Reportando Issues](#reportando-issues)

---

## Pré-requisitos

- Python 3.11+
- Docker Desktop (v4.x+)
- Git configurado com seu nome e email

```bash
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"
```

---

## Fluxo de Trabalho

1. **Fork** o repositório no GitHub
2. **Clone** o fork localmente:
   ```bash
   git clone git@github.com:SEU_USUARIO/datasus.git
   cd datasus
   ```
3. **Configure** o upstream:
   ```bash
   git remote add upstream git@github.com:shmjade/datasus.git
   ```
4. **Crie uma branch** a partir de `main` (ver nomenclatura abaixo)
5. **Faça as alterações**, seguindo os padrões de código
6. **Execute o lint e os testes** antes de commitar
7. **Abra um Pull Request** para a branch `main` do upstream

### Mantendo seu fork atualizado

```bash
git fetch upstream
git checkout main
git merge upstream/main
```

---

## Nomenclatura de Branches

Use o padrão `tipo/descricao-curta`:

| Tipo | Uso | Exemplo |
|---|---|---|
| `feat/` | Nova funcionalidade | `feat/pipeline-ingestao-sih` |
| `fix/` | Correção de bug | `fix/encoding-dbc-windows` |
| `docs/` | Documentação apenas | `docs/dicionario-cnes` |
| `refactor/` | Refatoração sem mudança de comportamento | `refactor/spark-session-manager` |
| `test/` | Adição/correção de testes | `test/validacao-schema-trusted` |
| `ci/` | Mudanças no CI/CD | `ci/adicionar-teste-integracao` |
| `chore/` | Manutenção, deps, config | `chore/atualizar-pyspark-3.5.1` |

---

## Convenção de Commits

Adotamos o padrão [Conventional Commits](https://www.conventionalcommits.org/).

### Formato

```
<tipo>(<escopo>): <descrição curta em imperativo>

[corpo opcional — explica o "por quê", não o "o quê"]

[rodapé opcional — refs de issues: Closes #123]
```

### Tipos

| Tipo | Quando usar |
|---|---|
| `feat` | Nova funcionalidade |
| `fix` | Correção de bug |
| `docs` | Mudanças em documentação |
| `style` | Formatação (sem mudança de lógica) |
| `refactor` | Refatoração de código existente |
| `test` | Adição ou correção de testes |
| `ci` | Mudanças em CI/CD |
| `chore` | Tarefas de manutenção |
| `perf` | Melhoria de performance |

### Exemplos

```
feat(batch): adicionar leitura de arquivos DBC do SIH

Implementa função parse_sih_dbc() usando biblioteca pysus para
converter arquivos .dbc do SIH em DataFrames Spark.

Closes #12
```

```
fix(postgres): corrigir divergência de código IBGE (6 vs 7 dígitos)
```

```
docs(data-dict): adicionar campo LAT/LON do CNES com nota de qualidade
```

### Regras

- Use o **imperativo** na descrição: "adicionar", não "adicionado" ou "adicionando"
- Máximo de **72 caracteres** na primeira linha
- Não termine com ponto final
- Referencie a issue quando aplicável: `Closes #N` ou `Refs #N`

---

## Padrões de Código

### Linting obrigatório

O CI bloqueia merges com erros de lint. Execute localmente antes de cada commit:

```bash
ruff check .          # verificar
ruff check . --fix    # corrigir automaticamente o que for possível
mypy pipelines/       # verificação de tipos
```

### Configuração já definida em `pyproject.toml`

- **Ruff:** linha máxima 100 chars, regras E/F/W/I/UP/B/SIM ativas
- **mypy:** `warn_return_any = true`, `ignore_missing_imports = true`

### Boas práticas

- **Docstrings:** use Google style para funções públicas de pipelines
- **Type hints:** obrigatório em todas as funções dos módulos `pipelines/`
- **Constantes:** UPPER_SNAKE_CASE em módulo separado `config.py`
- **Sem magic numbers:** extraia para constantes com nome descritivo
- **SQL:** escreva em UPPER CASE para keywords, lower_case para nomes de tabela/coluna

---

## Testes

```bash
pytest                          # roda todos os testes
pytest -v                       # saída verbosa
pytest tests/unit/              # apenas testes unitários
pytest tests/ --cov=pipelines   # com cobertura
```

### Organização

```
tests/
├── unit/           # testes de funções isoladas (sem I/O)
├── integration/    # testes com banco real (requerem docker compose up)
└── fixtures/       # dados de exemplo para testes
    ├── sih_sample.parquet
    └── cnes_sample.parquet
```

### Regras

- Testes unitários **não devem** conectar ao banco ou ao Kafka
- Testes de integração usam um banco PostgreSQL de teste (schema separado `test_*`)
- Cobertura mínima: **70%** nos módulos `pipelines/`

---

## Pull Requests

### Checklist antes de abrir o PR

- [ ] Branch atualizada com `main`
- [ ] `ruff check .` sem erros
- [ ] `mypy pipelines/` sem erros
- [ ] `pytest` passando
- [ ] Documentação atualizada (se aplicável)
- [ ] Commit messages seguem Conventional Commits

### Título do PR

Siga o mesmo padrão dos commits: `feat(batch): descrição curta`

### Descrição

Use o template gerado automaticamente pelo GitHub (`.github/PULL_REQUEST_TEMPLATE.md`).

---

## Reportando Issues

Use os templates de issue disponíveis no GitHub:

- **Bug Report:** para comportamentos inesperados
- **Feature Request:** para sugestões de novas funcionalidades
- **Dados:** para inconsistências encontradas nas fontes SIH/CNES/IBGE

Ao reportar um bug relacionado a dados do DataSUS, inclua:
- UF e competência (ex: RS, 202401)
- Exemplo do registro problemático (anonimizado)
- Comportamento esperado vs. observado
