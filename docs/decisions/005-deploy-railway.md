# ADR-005 — Deploy: Railway com Procfile (não Docker em produção)

- **Data:** 2026-05 (início do projeto)
- **Status:** Aceito / Pendente de execução

---

## Contexto

O projeto precisa de um ambiente de produção para o MVP. As opções avaliadas:

| Opção | Custo | Complexidade |
|-------|-------|--------------|
| AWS ECS/EKS | Alto | Alta |
| DigitalOcean App Platform | Médio | Média |
| Heroku | Médio | Baixa |
| **Railway** | Baixo (free tier generoso) | Baixa |
| VPS própria | Baixo | Alta |

## Decisão

**Railway** com `Procfile` para declarar os processos.

```
# Procfile (já existe na raiz)
web: gunicorn config.wsgi:application --bind 0.0.0.0:$PORT
worker: celery -A config worker -l info
beat: celery -A config beat -l info
```

## Motivo

- **MVP-first:** Railway tem deploy em minutos com git push
- **PostgreSQL incluso:** Railway provisiona banco automaticamente
- **Procfile portável:** Se mudar de Railway para Heroku ou Render, o Procfile funciona igual
- **Sem overhead de Docker:** Para MVP de time pequeno, Dockerfile adiciona complexidade sem ganho real

## O que falta para fazer o deploy (pendente)

- [ ] Configurar variáveis de ambiente de produção no Railway:
  ```
  SECRET_KEY=<gerar com: python -c "import secrets; print(secrets.token_urlsafe(50))">
  DATABASE_URL=<provisionado pelo Railway>
  DEBUG=False
  ALLOWED_HOSTS=<dominio>.railway.app
  CELERY_BROKER_URL=<Redis do Railway>
  REDIS_URL=<Redis do Railway>
  ACCESS_TOKEN_LIFETIME_MINUTES=60
  REFRESH_TOKEN_LIFETIME_DAYS=7
  CORS_ALLOWED_ORIGINS=https://<dominio-frontend>
  ```
- [ ] Adicionar `release: python manage.py migrate` no Procfile
- [ ] Configurar `STATIC_ROOT` e `whitenoise` para arquivos estáticos
- [ ] Testar `python manage.py check --deploy`

## Consequências

- **Positivo:** Deploy funcional em <1h sem infra própria
- **Negativo:** Lock-in parcial no Railway (mas Procfile facilita migração)
- **Nota:** Para escala maior (>1000 usuários simultâneos), avaliar migração para ECS com RDS
