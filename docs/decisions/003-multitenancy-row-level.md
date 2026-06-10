# ADR-003 — Multi-tenancy por campo empresa (Row-Level)

- **Data:** 2026-05 (início do projeto)
- **Status:** Aceito

---

## Contexto

O Formuca ERP atende múltiplas empresas de logística na mesma instância.
É preciso garantir isolamento total entre os dados de cada empresa.

Existem três padrões principais de multi-tenancy:

| Padrão | Descrição |
|--------|-----------|
| **Database-per-tenant** | Cada empresa tem seu banco separado |
| **Schema-per-tenant** | Cada empresa tem schema PostgreSQL separado |
| **Row-level tenancy** | Tudo no mesmo banco, filtrado por coluna |

## Decisão

**Row-level tenancy** com campo `empresa` (FK para `core.Empresa`) em todos os modelos de negócio.

### Regra obrigatória em todas as views:
```python
# CORRETO — sempre filtrar por empresa do usuário autenticado
def get_queryset(self):
    return Romaneio.objects.filter(empresa=self.request.user.empresa)

# ERRADO — vaza dados entre empresas
def get_queryset(self):
    return Romaneio.objects.all()
```

### Regra obrigatória no create:
```python
def perform_create(self, serializer):
    serializer.save(empresa=self.request.user.empresa)
```

## Motivo

- **Simplicidade operacional:** um banco, um backup, uma migration
- **Performance suficiente:** com índice em `empresa_id`, queries são eficientes
- **Tamanho do projeto:** database-per-tenant só compensa com >100 tenants ou requisitos de compliance muito rígidos (ex: dados médicos, financeiros regulados)

## Consequências

- **Positivo:** Deploy simples, sem lógica de roteamento de banco
- **Negativo:** Um bug de filtragem vaza dados de todas as empresas — risco alto
- **Mitigação do risco:**
  - Testes de isolamento em todos os módulos (empresa_a não vê dados de empresa_b)
  - Code review obrigatório para qualquer `objects.all()` ou `objects.filter()` sem `empresa=`
  - CI testa isolamento automaticamente

## Nota futura

Se o produto crescer para >50 empresas grandes, avaliar migração para schema-per-tenant com `django-tenants`. A estrutura atual facilita essa migração pois o campo `empresa` já está em todos os modelos.
