# ADR-001 — Modelo de Usuário Customizado (AbstractBaseUser)

- **Data:** 2026-05 (início do projeto)
- **Status:** Aceito

---

## Contexto

Django oferece três opções para o modelo de usuário:
1. Usar `User` padrão do Django direto
2. Estender com `AbstractUser` (mantém username, first_name, etc.)
3. Criar do zero com `AbstractBaseUser` (controle total)

O projeto precisava de:
- Login por **e-mail** (não username)
- Campo `empresa` como FK obrigatória para multi-tenancy
- Sem campos desnecessários (`first_name`, `last_name` separados)
- `nome_completo` como campo único

## Opções consideradas

| Opção | Vantagem | Problema |
|-------|----------|---------|
| `User` padrão | Zero config | Não tem email como login, sem `empresa` |
| `AbstractUser` | Fácil extensão | Herda `username` indesejado, complexidade de manter ambos |
| `AbstractBaseUser` | Controle total | Mais código inicial |

## Decisão

**`AbstractBaseUser` com `PermissionsMixin`**, definido em `apps.core.models.Usuario`.

```python
AUTH_USER_MODEL = "core.Usuario"
USERNAME_FIELD = "email"
REQUIRED_FIELDS = ["nome_completo"]
```

## Motivo

- O sistema é multi-tenant — o campo `empresa` na raiz do usuário é fundamental
- Email como identificador é o padrão moderno para ERPs B2B
- `AbstractBaseUser` evita campos mortos que confundem desenvolvedores futuros

## Consequências

- **Positivo:** Schema limpo, sem campos legados do Django padrão
- **Negativo:** Requer `UsuarioManager` customizado com `create_user()` e `create_superuser()`
- **Atenção:** Não é possível mudar `AUTH_USER_MODEL` depois da primeira migration — decisão irreversível
