# ADR-002 — Autenticação: JWT via SimpleJWT (não Session)

- **Data:** 2026-05 (início do projeto)
- **Status:** Aceito

---

## Contexto

O sistema é uma API REST consumida por:
- Futuros frontends web (SPA)
- App mobile (v2.0 do roadmap)
- Integrações B2B (NF-e, parceiros)

Django oferece autenticação por **session cookie** nativamente.
A alternativa padrão para APIs REST é **JWT (JSON Web Token)**.

## Opções consideradas

| Opção | Vantagem | Problema |
|-------|----------|---------|
| Session cookie | Nativo no Django, revogação fácil | Não funciona para mobile/SPA sem CSRF complexo |
| JWT (SimpleJWT) | Stateless, multi-client, padrão de mercado | Revogação requer blacklist |
| OAuth2 (django-oauth-toolkit) | Completo para integrações | Complexidade excessiva para MVP |

## Decisão

**JWT via `djangorestframework-simplejwt`** com:
- Access token: 60 minutos (configurável via `.env`)
- Refresh token: 7 dias (configurável via `.env`)
- `ROTATE_REFRESH_TOKENS = True` — novo refresh token a cada renovação
- `BLACKLIST_AFTER_ROTATION = True` — invalida refresh token antigo

```python
# config/settings/base.py
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}
```

## Motivo

- O roadmap inclui app mobile — JWT é a única opção viável
- SPAs modernas não usam cookies de sessão por padrão (CORS + CSRF complexo)
- SimpleJWT é o padrão consolidado no ecossistema DRF

## Consequências

- **Positivo:** API pode ser consumida por qualquer cliente sem estado no servidor
- **Negativo:** Revogação imediata requer blacklist (se `BLACKLIST_AFTER_ROTATION=True`, o refresh rotacionado é invalidado — mas o access token válido ainda funciona até expirar)
- **Atenção:** Access token de 60min significa que logout real no frontend deve limpar o token localmente — o servidor não pode invalidar um access token válido sem blacklist de access tokens (não implementado)
