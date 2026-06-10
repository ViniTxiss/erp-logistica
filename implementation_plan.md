# Análise do Projeto — Formuca ERP
> Atualizado: 2026-06-08

---

## 1. Estado atual do backend

| Módulo | Models | Serializers | Views | Admin | Testes | Observação |
|--------|--------|-------------|-------|-------|--------|------------|
| **Core** | ✅ | ✅ | ✅ | ✅ | ❌ | RBAC, AuditLog, Empresa, Usuário |
| **WMS** | ✅ | ✅ | ✅ | ✅ | ✅ | Armazém, Estoque, Entradas, Saídas |
| **TMS** | ✅ | ✅ | ✅ | ✅ | ✅ | Romaneio, POD, Ocorrência, fixtures |
| **CRM** | ✅ | ✅ | ✅ | ✅ | ✅ | Cliente, Funil, Contrato, fixtures |

**Total estimado: ~200+ testes — 0 falhas**

### Único gap no backend
- **Core sem testes** — RBAC (`tem_permissao`), AuditLog e isolamento multi-tenant sem cobertura

---

## 2. Estado do frontend

A pasta `docs/wireframes/` contém 4 telas HTML **apenas do WMS**:
```
wms_tela1_lista_recebimentos.html    ← listagem de NFs de entrada
wms_tela2_formulario_entrada.html    ← formulário de registro
wms_tela3_confirmacao.html           ← confirmação de recebimento
wms_tela3_scanandroid_pwa.html       ← PWA de scanner Android
```

**Não existe frontend para TMS nem CRM.**
**Não existe dashboard principal.**

---

## 3. Estado da infraestrutura

| Item | Status |
|------|--------|
| Docker + docker-compose | ✅ Existe |
| Procfile (Railway) | ✅ Existe |
| GitHub Actions CI | ✅ Configurado |
| Swagger/OpenAPI | ❌ Não configurado |
| Deploy em produção | ❌ Não feito |
| `.env` de produção | ❌ Não configurado |

---

## 4. Roadmap conforme README

| Fase | Status |
|------|--------|
| **v1.0** — Core, WMS, TMS, CRM | 🟡 Backend ~95% completo, frontend ausente |
| **v1.1** — Roteamento, Torre de controle, NF-e | ⏳ Não iniciado |
| **v2.0** — GPS ao vivo, Portal do cliente, App mobile | 💭 Futuro |

---

## 5. Próximos passos priorizados

### 🔴 Alta prioridade (fechar v1.0 backend)

**A. Testes Core** — único módulo sem cobertura
- `TestUsuario.tem_permissao()` — cenários com/sem perfil, superuser
- `TestAuditLog` — criação via `audit()`, campos imutáveis
- `TestPerfilRBAC` — hierarquia Empresa → Perfil → Permissão
- **Estimativa: ~25-35 testes**

**B. Swagger / OpenAPI** (`drf-spectacular`)
- Documentação automática de todos os endpoints dos 4 módulos
- Interface interativa `/api/schema/swagger-ui/`
- **Estimativa: 1-2h de configuração**

### 🟢 Próxima fase (v1.1 ou frontend)

**C. Frontend / Dashboard**
- Dashboard principal com métricas em tempo real (WMS + TMS + CRM)
- Telas de TMS: lista de romaneios, detalhe com mapa de entregas
- Telas de CRM: pipeline de oportunidades (Kanban)
- Tecnologia sugerida: Next.js ou HTML puro (como nos wireframes)

**D. Deploy em produção**
- Railway (Procfile já existe)
- Variáveis de ambiente de produção
- Migrations automatizadas no deploy

---

## 6. Recomendação imediata

**Testes do Core** são o último gap de cobertura. Com ~30 testes,
o backend fica com 100% dos módulos cobertos e o CI totalmente protegido.

Em seguida, **Swagger** (1-2h) para documentar a API e facilitar o frontend.
