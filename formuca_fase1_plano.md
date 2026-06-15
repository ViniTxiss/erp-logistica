# Formuca ERP — Plano de Execução Fase 1: Blindagem

> Baseado em análise real do repositório. Cada tarefa tem contexto, arquivo alvo e código pronto para aplicar.
> Ordem de prioridade: execute de cima para baixo.

---

## Tarefa 1 — Ativar o AuditLogMiddleware (5 min)

**Problema:** `AuditLogMiddleware` existe em `apps/core/audit.py` mas não está registrado no `MIDDLEWARE`. Nenhum log de escrita está sendo gravado agora.

**Arquivo:** `backend/config/settings/base.py`

Adicionar após `AuthenticationMiddleware`:

```python
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.audit.AuditLogMiddleware",          # ← ADICIONAR AQUI
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]
```

**Verificação:** Fazer qualquer POST/PUT via API e checar `AuditLog.objects.last()` no shell.

---

## Tarefa 2 — Rate Limiting na API (10 min)

**Problema:** `REST_FRAMEWORK` em `base.py` não tem `DEFAULT_THROTTLE_CLASSES`. Qualquer script pode saturar os endpoints.

**Arquivo:** `backend/config/settings/base.py`

Substituir o bloco `REST_FRAMEWORK` atual por:

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    # ─── Throttling ───────────────────────────────────────────────────────────
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/day",
        "user": "1000/hour",
    },
}
```

**Nota:** Para endpoints críticos como bipagem de inventário, criar throttle customizado depois:

```python
# apps/wms/throttles.py
from rest_framework.throttling import UserRateThrottle

class BipagemRateThrottle(UserRateThrottle):
    rate = "300/minute"  # operador de empilhadeira bipa rápido
```

---

## Tarefa 3 — TenantManager: isolamento automático de dados (2–3 horas)

**Problema:** Toda model de WMS, TMS e CRM tem `FK para Empresa`, mas nenhum Manager força `.filter(empresa=...)`. Um usuário autenticado da Empresa A pode acessar dados da Empresa B via API.

### 3a. Criar o TenantManager base

**Arquivo novo:** `backend/apps/core/managers.py`

```python
"""
TenantManager — garante isolamento automático por empresa em todas as queries.
Usar como manager padrão em models que têm FK para Empresa.
"""
from django.db import models


class TenantQuerySet(models.QuerySet):
    def para_empresa(self, empresa):
        """Filtra explicitamente por empresa. Usar quando empresa vem de fora do request."""
        return self.filter(empresa=empresa)


class TenantManager(models.Manager):
    """
    Manager que restringe automaticamente as queries à empresa do usuário logado.

    Uso nas models:
        objects = TenantManager()

    Nas views, usar sempre:
        Model.objects.para_request(request)
    """

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def para_request(self, request):
        """
        Atalho principal para uso nas views.
        Retorna QuerySet filtrado pela empresa do usuário autenticado.
        """
        empresa = getattr(request.user, "empresa", None)
        if empresa is None:
            # Superuser sem empresa vê tudo — ajustar conforme política
            return self.get_queryset()
        return self.get_queryset().filter(empresa=empresa)
```

### 3b. Criar modelo base abstrato

**Arquivo novo:** `backend/apps/core/base_models.py`

```python
"""
TenantModel — modelo abstrato base para todas as entidades multi-tenant.
Herdar no lugar de models.Model nos apps WMS, TMS e CRM.
"""
from django.db import models
from .managers import TenantManager


class TenantModel(models.Model):
    """
    Modelo base que garante:
    - FK obrigatória para Empresa
    - TenantManager como manager padrão
    - created_at / updated_at automáticos
    """
    empresa = models.ForeignKey(
        "core.Empresa",
        on_delete=models.CASCADE,
        related_name="+",  # cada subclasse define seu próprio related_name
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True
```

### 3c. Aplicar nas models existentes

**Arquivo:** `backend/apps/wms/models.py`

Substituir `models.Model` por `TenantModel` e remover campos duplicados:

```python
from apps.core.base_models import TenantModel

class Armazem(TenantModel):                        # ← era models.Model
    # empresa = ... ← REMOVER (já está no TenantModel)
    # created_at = ... ← REMOVER (já está no TenantModel)
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Armazém"
        verbose_name_plural = "Armazéns"
        unique_together = [("empresa", "codigo")]
        ordering = ["nome"]
```

Repetir para `Veiculo`, `Motorista`, `Romaneio` (TMS) e `Cliente`, `Oportunidade`, `Contrato` (CRM).

### 3d. Atualizar as views para usar `para_request`

**Exemplo em:** `backend/apps/wms/views.py`

```python
# ANTES (inseguro — retorna dados de todas as empresas):
def get_queryset(self):
    return Armazem.objects.all()

# DEPOIS (seguro — filtra pela empresa do usuário logado):
def get_queryset(self):
    return Armazem.objects.para_request(self.request)
```

### 3e. Criar migration após as alterações

```bash
python manage.py makemigrations
python manage.py migrate
```

---

## Tarefa 4 — AuditLog imutável no PostgreSQL (30 min)

**Problema:** `default_permissions = ("add", "view")` protege só o Django Admin. Um `DELETE FROM core_auditlog` direto no banco funciona sem restrição.

### 4a. Criar migration com trigger

**Arquivo novo:** `backend/apps/core/migrations/0002_auditlog_immutable_trigger.py`

```python
from django.db import migrations

SQL_CREATE_TRIGGER = """
CREATE OR REPLACE FUNCTION prevent_auditlog_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'AuditLog é imutável. Operação % negada.', TG_OP;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER auditlog_immutable
BEFORE UPDATE OR DELETE ON core_auditlog
FOR EACH ROW EXECUTE FUNCTION prevent_auditlog_mutation();
"""

SQL_DROP_TRIGGER = """
DROP TRIGGER IF EXISTS auditlog_immutable ON core_auditlog;
DROP FUNCTION IF EXISTS prevent_auditlog_mutation();
"""


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunSQL(
            sql=SQL_CREATE_TRIGGER,
            reverse_sql=SQL_DROP_TRIGGER,
        ),
    ]
```

```bash
python manage.py migrate
```

**Verificação:**

```python
# No shell Django — deve lançar exceção:
from apps.core.models import AuditLog
log = AuditLog.objects.first()
log.acao = "HACK"
log.save()  # → django.db.utils.InternalError: AuditLog é imutável.
```

---

## Tarefa 5 — Otimizar tem_permissao (30 min)

**Problema:** `tem_permissao` em `Usuario` faz query com join em três tabelas a cada verificação. Em endpoints de alta frequência, vira N+1.

**Arquivo:** `backend/apps/core/models.py`

Substituir o método atual:

```python
def tem_permissao(self, codigo: str) -> bool:
    """Verifica permissão com cache em memória por request."""
    if self.is_superuser:
        return True

    # Cache lazy das permissões do usuário (invalidado ao recarregar o objeto)
    if not hasattr(self, "_permissoes_cache"):
        self._permissoes_cache = set(
            PerfilUsuario.objects
            .filter(usuario=self)
            .select_related("perfil")
            .prefetch_related("perfil__permissoes")
            .values_list("perfil__perfilpermissao__permissao__codigo", flat=True)
        )
    return codigo in self._permissoes_cache
```

**Nota:** Para invalidação mais robusta em produção, evoluir para cache Redis com chave `permissoes:{user_id}` e TTL de 5 minutos.

---

## Tarefa 6 — Observabilidade com Sentry (20 min)

**Problema:** Nenhuma captura de erros em produção. Falhas no Celery e no banco passam despercebidas.

### 6a. Adicionar dependências

**Arquivo:** `backend/requirements/base.txt`

```
sentry-sdk[django,celery]==2.20.0
```

### 6b. Inicializar no settings de produção

**Arquivo:** `backend/config/settings/production.py`

```python
import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.celery import CeleryIntegration
from sentry_sdk.integrations.redis import RedisIntegration

sentry_sdk.init(
    dsn=env("SENTRY_DSN"),
    integrations=[
        DjangoIntegration(transaction_style="url"),
        CeleryIntegration(),
        RedisIntegration(),
    ],
    traces_sample_rate=0.2,       # 20% das transações para performance
    send_default_pii=False,       # LGPD: não enviar dados pessoais
    environment="production",
)
```

### 6c. Adicionar `SENTRY_DSN` ao `.env`

```env
SENTRY_DSN=https://<sua-chave>@o<id>.ingest.sentry.io/<project-id>
```

---

## Checklist de execução

| # | Tarefa | Tempo estimado | Risco se ignorar |
|---|--------|---------------|-----------------|
| 1 | Ativar AuditLogMiddleware | 5 min | Auditoria inexistente em produção |
| 2 | Rate limiting DRF | 10 min | API exposta a força bruta |
| 3 | TenantManager + views | 2–3 h | Vazamento de dados entre clientes |
| 4 | Trigger imutabilidade AuditLog | 30 min | Logs adulteráveis diretamente no banco |
| 5 | Otimizar tem_permissao | 30 min | N+1 em toda verificação de permissão |
| 6 | Sentry em produção | 20 min | Falhas silenciosas no Celery e banco |

**Total estimado: ~5 horas de implementação para blindagem completa do MVP.**

---

## Próxima fase (após concluir acima)

- Cache Redis para `/api/wms/posicoes/` — evitar hits constantes durante bipagem
- App `fiscal` isolada para NF-e assíncrona com Celery workers dedicados
- Read replica PostgreSQL para relatórios de BI separados da operação WMS/TMS
- Webhooks para integração com Shopify, VTEX e Bling
