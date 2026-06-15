# Formuca ERP — Documento de Contexto (Handoff)

> **Para a IA:** Leia este arquivo inteiro antes de fazer qualquer coisa.
> Ele resume o estado atual do projeto, convenções, decisões e próximos passos.
> Última atualização: 2026-06-15

> **Para manter atualizado:** `python manage.py export_context --patch CONTEXT.md`
> **Template de sessão:** `docs/SESSION_TEMPLATE.md`
> **Decisões arquiteturais:** `docs/decisions/`

---

## 1. O que é este projeto

**Formuca ERP** — sistema de gestão logística multi-tenant construído com:

- **Frontend:** Django Templates + HTMX + Alpine.js + Tailwind CSS (Zero Build)
- **Backend:** Django 4.x + Django REST Framework + SimpleJWT
- **Banco:** PostgreSQL em produção, SQLite `:memory:` em testes
- **Testes:** pytest + pytest-django + factory_boy
- **CI:** GitHub Actions (`.github/workflows/ci.yml`)
- **Deploy:** Railway (Procfile já existe)
- **Autenticação:** JWT via `rest_framework_simplejwt`

O sistema é **multi-tenant**: cada `Empresa` tem seus próprios dados, e **todas as queries devem filtrar por `empresa=request.user.empresa`**.

---

## 2. Estrutura de pastas

```
erp logistica/
├── backend/
│   ├── apps/
│   │   ├── core/          ← Empresa, Usuário, RBAC, AuditLog
│   │   ├── wms/           ← Armazém, Estoque, Entradas, Saídas
│   │   ├── tms/           ← Veículo, Motorista, Romaneio, POD
│   │   └── crm/           ← Cliente, Oportunidade, Contrato
│   ├── config/            ← settings (base, development, test, production)
│   ├── templates/         ← [NOVO] UI Templates base (base.html, sidebar.html)
│   ├── conftest.py        ← Factories e fixtures compartilhados (FONTE DA VERDADE)
│   ├── manage.py
│   └── requirements/
│       ├── base.txt
│       └── development.txt
├── docs/wireframes/       ← Wireframes de referência
├── CONTEXT.md             ← este arquivo
├── implementation_plan.md ← roadmap atualizado
└── .github/workflows/ci.yml
```

---

> ⚡ Esta seção pode ser regenerada automaticamente:
> `python manage.py export_context --section modules --patch CONTEXT.md`

## 3. Estado atual dos módulos (2026-06-08)

| Módulo | Models | Serializers | Views | Admin | UI/HTMX | Testes | Fixtures/Permissões |
|--------|:------:|:-----------:|:-----:|:-----:|:-------:|:------:|:-------------------:|
| **Core** | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ 62 testes | ❌ |
| **WMS** | ✅ | ✅ | ✅ | ✅ | ✅ (MVP) | ✅ | ❌ |
| **TMS** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ `tms_permissions.json` |
| **CRM** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ `crm_permissions.json` |

**Total de testes: 260 passando, 1 falha pré-existente no WMS (test_saldo_endpoint)**

### Nenhum gap restante no backend
Todos os 4 módulos têm cobertura completa.

---

## 4. Arquitetura e convenções críticas

### 4.1 Multi-tenancy
- **Regra obrigatória:** TODA query de dados filtra por empresa.
  ```python
  # CORRETO
  qs = Romaneio.objects.filter(empresa=request.user.empresa)
  # ERRADO
  qs = Romaneio.objects.all()
  ```

### 4.2 RBAC (Role-Based Access Control)
```python
# models.py → Usuario
def tem_permissao(self, codigo: str) -> bool:
    if self.is_superuser:
        return True
    return PerfilUsuario.objects.filter(
        usuario=self,
        perfil__perfilpermissao__permissao__codigo=codigo,
    ).exists()

# permissions.py → como usar nas views
permission_classes = [IsAuthenticated, require_permission("wms.entrada.criar")]

# Ou com atributo na view:
class EntradaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, HasModulePermission]
    required_permission = "wms.entrada.criar"
```

### 4.3 AuditLog
Existem duas formas de registrar:
```python
# 1. Middleware automático (POST/PUT/PATCH/DELETE com status < 400)
# Configurado em MIDDLEWARE no settings

# 2. Helper manual (preferido para ações de negócio com nome semântico)
from apps.core.audit import audit
audit(
    request.user, "tms", "romaneio.iniciar_rota",
    "Romaneio", objeto_id=romaneio.id,
    payload_depois={"status": romaneio.status},
)
```

### 4.4 Padrão de testes
- Framework: `pytest` com `@pytest.mark.django_db`
- Fixtures definidas em `backend/conftest.py` (disponíveis em todos os apps)
- Factories usam `factory_boy` com `DjangoModelFactory`
- Autenticação via JWT nos testes de API:
  ```python
  @pytest.fixture
  def auth_client(api_client, usuario):
      from rest_framework_simplejwt.tokens import RefreshToken
      refresh = RefreshToken.for_user(usuario)
      api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
      return api_client
  ```
- Isolamento multi-tenant testado criando 2 empresas e verificando que cada uma só vê seus dados

### 4.5 Factories disponíveis (todas em `conftest.py`)
```python
# Core
EmpresaFactory()
FilialFactory(empresa=...)
UsuarioFactory(empresa=...)

# TMS
VeiculoFactory(empresa=...)
MotoristaFactory(empresa=...)
RomaneioFactory(empresa=..., veiculo=..., motorista=...)
ItemRomaneioFactory(romaneio=...)
OcorrenciaFactory(romaneio=...)
PODFactory(item=...)

# CRM
ClienteFactory(empresa=...)
ContatoFactory(cliente=...)
OportunidadeFactory(cliente=...)
ContratoFactory(cliente=...)

# WMS
ArmazemFactory(empresa=...)
ProdutoFactory(empresa=...)
PosicaoFactory(nivel_armazem=armazem)  # cria hierarquia Corredor→Bay→Nivel
EntradaMercadoriaFactory(armazem=...)
SaidaMercadoriaFactory(armazem=...)
```

### 4.6 Como rodar os testes
```bash
cd "erp logistica/backend"

# Todos os testes
pytest apps/ -v

# Só um módulo
pytest apps/tms/tests/ -v
pytest apps/crm/tests/ -v
pytest apps/wms/tests/ -v

# Com cobertura
pytest apps/ --cov=apps --cov-report=term-missing
```

### 4.7 CI
- Roda em `push`/`PR` para `main`/`develop`
- Lint com `flake8` (só erros críticos bloqueiam)
- `pytest` cobrindo todos os módulos
- Python 3.11 e 3.12 em matrix

---

## 5. Modelos importantes — resumo rápido

### Core
```
Empresa → Filial → Usuario
Perfil → Permissao (via PerfilPermissao)
Usuario → Perfil (via PerfilUsuario, com valido_ate para perfis temporários)
Usuario → AuditLog
```

### TMS — ciclo de vida do Romaneio
```
StatusRomaneio: ABERTO → EM_ROTA → CONCLUIDO
                              ↘ COM_OCORRENCIA → CONCLUIDO
                ABERTO → CANCELADO (qualquer estado não-concluído)

Métodos de negócio em Romaneio:
  romaneio.iniciar_rota(usuario)   → ABERTO → EM_ROTA
  romaneio.concluir(usuario)       → EM_ROTA/COM_OCORRENCIA → CONCLUIDO
  romaneio.cancelar(usuario)       → qualquer → CANCELADO
```

### WMS — ciclo de vida das entradas
```
EntradaMercadoria.concluir()  → PENDENTE → CONCLUIDA (atualiza estoque)
SaidaMercadoria.expedir()     → PENDENTE → EXPEDIDA (baixa estoque)
Posicao.saldo_atual           → property calculada
```

### CRM — ciclo de vida das oportunidades
```
EtapaOportunidade: PROSPECCAO → QUALIFICACAO → PROPOSTA → NEGOCIACAO
                                                              ↓
                                              FECHADO_GANHO / FECHADO_PERDIDO

Métodos:
  oportunidade.fechar_ganho(usuario)                → ativa o Cliente
  oportunidade.fechar_perdido(motivo, usuario)       → mantém Cliente como LEAD
```

---

## 6. Próximos passos (em ordem de prioridade)

### ✅ Deploy em produção (Railway) — CONCLUÍDO (2026-06-15)
- URL: `https://erp-logistica-production-8958.up.railway.app`
- Admin: `vini17brito@gmail.com` / var `ADMIN_PASS` no Railway
- **Quirk Railway:** vars com `PASSWORD` no nome são filtradas do `os.environ` do container.
  Solução: usar `ADMIN_PASS` (sem a palavra PASSWORD) e ler via `os.environ.get("ADMIN_PASS")`.

### 🟢 DEPOIS: Cadastro de Veículos e Refinamentos
- Adicionar gestão de veículos (CRUD) na interface do TMS.
- Adicionar Drag and Drop (SortableJS) no Kanban do CRM.

---

## 7. Decisões arquiteturais (ADRs)

| # | Decisão | Status |
|---|---------|--------|
| [001](docs/decisions/001-usuario-abstractbaseuser.md) | Modelo de usuário: AbstractBaseUser | ✅ Aceito |
| [002](docs/decisions/002-autenticacao-jwt.md) | Autenticação: JWT (SimpleJWT) | ✅ Aceito |
| [003](docs/decisions/003-multitenancy-row-level.md) | Multi-tenancy: row-level por campo empresa | ✅ Aceito |
| [004](docs/decisions/004-testes-pytest-factoryboy.md) | Testes: pytest + factory_boy + SQLite | ✅ Aceito |
| [005](docs/decisions/005-deploy-railway.md) | Deploy: Railway com Procfile | ⏳ Pendente |
| **[006]** | **Frontend: Django Templates + HTMX + Alpine.js + Tailwind** | ✅ Aceito |

---

## 8. Checklist de entrega (v1.0 backend)

- [x] Core — Models, Serializers, Views, Admin
- [x] WMS — Models, Serializers, Views, Admin, Testes
- [x] TMS — Models, Serializers, Views, Admin, Testes, Fixtures
- [x] CRM — Models, Serializers, Views, Admin, Testes, Fixtures
- [x] **Core — Testes** ← concluído em 2026-06-08 (62 testes)
- [x] WMS — corrigir test_saldo_endpoint (falha pré-existente)
- [x] Swagger/OpenAPI
- [x] CI cobrindo todos os 4 módulos
- [x] **Frontend:** WMS MVP (HTMX + Tailwind Premium)
- [x] **Frontend:** TMS
- [x] **Frontend:** CRM
- [x] Deploy em produção (Railway) ← concluído em 2026-06-15
