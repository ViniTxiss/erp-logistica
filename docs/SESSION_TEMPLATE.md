# Template de Sessão com IA — Formuca ERP

> Copie este template no início de cada nova sessão com qualquer IA.
> Preencha as seções marcadas com `← PREENCHER`.

---

## Como usar

1. **Abrir sessão** → Cole o bloco `[ABERTURA]` completo
2. **Trabalhar** → A IA tem contexto claro e escopo delimitado
3. **Fechar sessão** → Peça o bloco `[FECHAMENTO]` e aplique o diff

---

## [ABERTURA DE SESSÃO]

```
Você é um assistente de desenvolvimento do projeto Formuca ERP.
Antes de qualquer coisa, leia o arquivo CONTEXT.md na raiz do repositório.
Ele contém a arquitetura, convenções obrigatórias e estado atual do projeto.

[CONTEXTO]
— Arquivo principal: CONTEXT.md (leia inteiro)
— Stack: Django 4.x + DRF + SimpleJWT + pytest + factory_boy
— Multi-tenant obrigatório: toda query filtra por empresa=request.user.empresa
— Testes: pytest, fixtures em backend/conftest.py, padrão test_models.py + test_api.py

[OBJETIVO DA SESSÃO]
← PREENCHER: descreva o que quer implementar hoje em 1-2 frases
Exemplo: "Implementar testes do módulo Core cobrindo RBAC e AuditLog"

[RESTRIÇÕES]
← PREENCHER: o que a IA NÃO deve tocar ou sugerir
Exemplos padrão (remova os que não se aplicam):
— Não altere arquivos fora de apps/core/
— Não mude o conftest.py sem avisar primeiro
— Não adicione novas dependências sem listar e pedir aprovação
— Não crie migrations novas
— Não refatore código que não está no escopo

[ENTREGÁVEL ESPERADO]
← PREENCHER: o que deve existir ao final da sessão
Exemplo: "Arquivo apps/core/tests/test_models.py e test_api.py com X testes passando"

[CONVENÇÕES QUE DEVEM SER SEGUIDAS]
1. Todo teste usa @pytest.mark.django_db
2. Factories do conftest.py — não crie factories inline nos testes
3. Isolamento multi-tenant: sempre testar que empresa_a não vê dados de empresa_b
4. audit() para ações de negócio, AuditLogMiddleware para HTTP genérico
5. require_permission("codigo") para RBAC nas views
```

---

## [FECHAMENTO DE SESSÃO]

Ao final de cada sessão, peça à IA:

```
Sessão encerrada. Gere o diff do CONTEXT.md com o que mudou hoje.
Formato:

### O que foi feito
- [lista do que foi implementado]

### Checklist — atualizar no CONTEXT.md
- [ ] mudar linha X de "❌" para "✅"
- [ ] adicionar factory Y na seção 4.5
- [ ] marcar item Z como [x] no checklist final

### Próximos passos atualizados
- [próximo passo concreto com estimativa]
```

---

## Exemplos de sessões típicas

### Sessão: Testes do Core
```
[OBJETIVO] Implementar testes unitários do módulo Core:
  - Usuario.tem_permissao() — 4 cenários
  - AuditLog via helper audit() — 3 cenários
  - RBAC hierárquico — Empresa → Perfil → Permissão → Usuario

[RESTRIÇÕES]
— Não altere modelos, serializers ou views
— Não crie novas migrations
— Factories novas devem ir no conftest.py, não inline

[ENTREGÁVEL]
apps/core/tests/test_models.py com ≥25 testes passando
```

### Sessão: Swagger/OpenAPI
```
[OBJETIVO] Configurar drf-spectacular para documentar todos os endpoints

[RESTRIÇÕES]
— Adicionar drf-spectacular no requirements/base.txt
— Rota: /api/schema/swagger-ui/
— Não altere nenhum ViewSet existente

[ENTREGÁVEL]
Swagger funcional em /api/schema/swagger-ui/ com todos os 4 módulos documentados
```

### Sessão: Frontend Dashboard
```
[OBJETIVO] Criar dashboard HTML com métricas dos 4 módulos

[RESTRIÇÕES]
— HTML/CSS/JS puro (sem framework)
— Seguir o estilo dos wireframes em docs/wireframes/
— Consumir a API via fetch() com JWT no header

[ENTREGÁVEL]
docs/wireframes/dashboard.html funcional com cards de métricas
```

---

## Dicas de uso

- **Sessões curtas vencem sessões longas** — prefira 1 objetivo por sessão
- **Cole o CONTEXT.md inteiro** — não resuma, a IA precisa do detalhe
- **Seja explícito nas restrições** — IA tende a "ajudar demais"
- **Aplique o diff antes de fechar** — não deixe para a próxima sessão
- **Gere o `export_context`** antes de começar: `python manage.py export_context`
  Isso garante que o CONTEXT.md está sincronizado com o código real
