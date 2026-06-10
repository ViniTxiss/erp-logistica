# Formuca ERP — Sistema de Gestão Logística

> ERP modular para operações de armazém (WMS), transporte (TMS) e clientes (CRM).

## 📁 Estrutura do projeto

```
erp logistica/
├── backend/                  ← API Django (backend principal)
│   ├── apps/
│   │   ├── core/             ← Empresa, Filial, Usuario, RBAC, AuditLog
│   │   ├── wms/              ← Warehouse Management System
│   │   ├── tms/              ← Transportation Management System
│   │   └── crm/              ← Customer Relationship Management
│   ├── config/
│   │   ├── settings/
│   │   │   ├── base.py
│   │   │   ├── development.py
│   │   │   ├── local.py      ← SQLite para dev sem Docker
│   │   │   └── production.py
│   │   ├── celery.py
│   │   └── urls.py
│   ├── requirements/
│   │   ├── base.txt
│   │   ├── development.txt
│   │   └── production.txt
│   ├── manage.py
│   ├── Dockerfile
│   ├── docker-compose.yml    ← web + db + redis + worker + beat
│   └── Procfile              ← Railway deploy
│
└── docs/
    ├── arquitetura/          ← diagramas de arquitetura e ERD
    ├── mvp/                  ← definição do MVP por fase
    └── wireframes/           ← telas HTML do sistema
```

## 🚀 Rodando localmente (sem Docker)

```bash
cd backend

# 1. Criar e ativar virtualenv
python -m venv .venv
.\.venv\Scripts\activate        # Windows
# source .venv/bin/activate     # Linux/Mac

# 2. Instalar dependências
pip install -r requirements/development.txt

# 3. Rodar migrations
python manage.py migrate --settings=config.settings.local

# 4. Criar superuser
python manage.py createsuperuser --settings=config.settings.local

# 5. Subir servidor
python manage.py runserver --settings=config.settings.local
```

## 🐳 Rodando com Docker (recomendado)

```bash
cd backend

# Build e subida de todos os serviços
docker compose up --build

# Em outra aba: migrations e superuser
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

## 🔑 Endpoints principais

| Método | URL | Descrição |
|--------|-----|-----------|
| `POST` | `/api/token/` | Login — retorna JWT |
| `POST` | `/api/token/refresh/` | Renovar token |
| `GET` | `/api/core/usuarios/me/` | Dados do usuário logado |
| `GET` | `/api/core/empresas/` | Lista empresas |
| `GET` | `/api/wms/entradas/` | Recebimentos WMS |
| `GET` | `/api/wms/posicoes/` | Posições do armazém |
| `GET` | `/api/tms/romaneios/` | Romaneios TMS |
| `GET` | `/api/crm/clientes/` | Clientes CRM |
| `GET` | `/admin/` | Django Admin |

## 🗺️ Roadmap MVP

| Fase | Status | Módulo |
|------|--------|--------|
| v1.0 | 🟡 Em construção | Core/RBAC, WMS, TMS, CRM |
| v1.1 | ⏳ Planejado | Roteamento, Torre de controle, NF-e |
| v2.0 | 💭 Futuro | GPS ao vivo, Portal do cliente, App mobile |

## 🛠️ Stack

- **Backend**: Django 5.1 + Django REST Framework
- **Auth**: SimpleJWT
- **Banco**: PostgreSQL 16
- **Cache/Broker**: Redis 7
- **Tasks**: Celery + Celery Beat
- **Deploy**: Railway (Procfile) / Docker
