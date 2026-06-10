# ADR-004 — Estratégia de testes: pytest + factory_boy + SQLite em memória

- **Data:** 2026-05 (início do projeto)
- **Status:** Aceito

---

## Contexto

Precisamos de uma estratégia de testes que seja:
- Rápida (rodar no CI sem banco PostgreSQL real)
- Legível (setup de dados declarativo, não imperativo)
- Isolada (cada teste parte de banco limpo)

## Decisão

**pytest-django** + **factory_boy** + **SQLite `:memory:`** para testes.

### Stack de testes
```
pytest                  — runner e marcadores (@pytest.mark.django_db)
pytest-django           — integração com Django
factory_boy             — factories declarativas para criar objetos
faker                   — dados realistas nas factories
```

### Banco de dados nos testes
```python
# config/settings/test.py
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
    }
}
```

### Localização das factories
**Centralizado em `backend/conftest.py`** — disponível para todos os apps sem import.

### Padrão de arquivo de teste
```
apps/<modulo>/tests/
  __init__.py
  test_models.py   ← testa lógica de negócio dos models (sem HTTP)
  test_api.py      ← testa endpoints via APIClient com JWT
```

## Motivo

- **pytest vs unittest:** pytest tem fixtures compostas, markers, parametrize — mais expressivo
- **factory_boy vs fixtures JSON:** factories são código — refatoram junto com os models
- **SQLite em testes vs PostgreSQL:** SQLite `:memory:` é 10x mais rápido; diferenças relevantes (JSON, arrays) são testadas em staging com PostgreSQL real
- **conftest.py centralizado:** evita copiar factories entre apps

## Consequências

- **Positivo:** Suite de 200+ testes roda em ~3s localmente
- **Negativo:** SQLite tem comportamentos diferentes do PostgreSQL (ex: `icontains` case-sensitivity, JSON queries)
- **Mitigação:** Queries críticas com comportamento PostgreSQL-específico são marcadas com comentário `# PostgreSQL-only behavior`
- **CI:** GitHub Actions com Python 3.11 e 3.12 em matrix

## Como rodar

```bash
cd "erp logistica/backend"

# Todos
pytest apps/ -v

# Só um módulo
pytest apps/tms/tests/ -v

# Com cobertura
pytest apps/ --cov=apps --cov-report=term-missing

# Só testes de model
pytest apps/ -k "TestModelo" -v
```
