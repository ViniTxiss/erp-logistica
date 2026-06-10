"""
Testes de integração da API REST do módulo CRM.
"""
import pytest
from datetime import date, timedelta

from apps.crm.models import (
    Cliente, StatusCliente,
    Contato, Oportunidade, EtapaOportunidade,
    HistoricoInteracao, Contrato,
)


pytestmark = pytest.mark.django_db


# ─── Clientes ─────────────────────────────────────────────────────────────────

class TestClienteAPI:

    def test_listar_clientes(self, auth_client, cliente_crm):
        res = auth_client.get("/api/crm/clientes/")
        assert res.status_code == 200
        assert res.data["count"] == 1
        # Listagem usa serializer leve — sem contatos aninhados
        assert "contatos" not in res.data["results"][0]
        assert "razao_social" in res.data["results"][0]
        assert "status_display" in res.data["results"][0]

    def test_detalhe_inclui_contatos(self, auth_client, cliente_crm):
        from conftest import ContatoFactory
        ContatoFactory(cliente=cliente_crm)
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/")
        assert res.status_code == 200
        assert "contatos" in res.data
        assert len(res.data["contatos"]) == 1

    def test_detalhe_inclui_total_oportunidades(self, auth_client, cliente_crm, oportunidade):
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/")
        assert res.data["total_oportunidades"] == 1

    def test_criar_cliente(self, auth_client, empresa):
        payload = {
            "empresa": str(empresa.id),
            "razao_social": "Nova Logística Ltda",
            "nome_fantasia": "NovaLog",
            "cnpj": "88888888000188",
            "segmento": "distribuicao",
            "cidade": "Campinas",
            "uf": "SP",
        }
        res = auth_client.post("/api/crm/clientes/", payload, format="json")
        assert res.status_code == 201
        assert res.data["status"] == "lead"  # sempre nasce como lead

    def test_filtrar_por_status(self, auth_client, cliente_crm):
        res = auth_client.get("/api/crm/clientes/?status=lead")
        assert res.data["count"] == 1
        res2 = auth_client.get("/api/crm/clientes/?status=ativo")
        assert res2.data["count"] == 0

    def test_filtrar_por_segmento(self, auth_client, cliente_crm):
        res = auth_client.get(f"/api/crm/clientes/?segmento={cliente_crm.segmento}")
        assert res.data["count"] == 1

    def test_busca_por_nome(self, auth_client, cliente_crm):
        trecho = cliente_crm.razao_social[:5].lower()
        res = auth_client.get(f"/api/crm/clientes/?q={trecho}")
        assert res.data["count"] == 1

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        ClienteFactory(empresa=outra)
        res = auth_client.get("/api/crm/clientes/")
        assert res.data["count"] == 0

    def test_nao_autenticado_retorna_401(self, api_client):
        res = api_client.get("/api/crm/clientes/")
        assert res.status_code == 401


# ─── Sub-recursos do Cliente ──────────────────────────────────────────────────

class TestClienteSubRecursos:

    def test_listar_contatos_do_cliente(self, auth_client, cliente_crm):
        from conftest import ContatoFactory
        ContatoFactory(cliente=cliente_crm, decisor=True)
        ContatoFactory(cliente=cliente_crm, decisor=False)
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/contatos/")
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_listar_oportunidades_do_cliente(self, auth_client, cliente_crm, oportunidade):
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/oportunidades/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["titulo"] == oportunidade.titulo

    def test_listar_historico_do_cliente(self, auth_client, cliente_crm, usuario):
        HistoricoInteracao.objects.create(
            cliente=cliente_crm, tipo="ligacao", resumo="Primeiro contato"
        )
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/historico/")
        assert res.status_code == 200
        assert len(res.data) == 1

    def test_contrato_ativo_do_cliente(self, auth_client, cliente_crm):
        from conftest import ContratoFactory
        contrato = ContratoFactory(cliente=cliente_crm, ativo=True)
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/contrato/")
        assert res.status_code == 200
        assert res.data["numero"] == contrato.numero

    def test_contrato_retorna_404_sem_contrato(self, auth_client, cliente_crm):
        res = auth_client.get(f"/api/crm/clientes/{cliente_crm.id}/contrato/")
        assert res.status_code == 404


# ─── Contatos ─────────────────────────────────────────────────────────────────

class TestContatoAPI:

    def test_listar_contatos(self, auth_client, cliente_crm):
        from conftest import ContatoFactory
        ContatoFactory(cliente=cliente_crm)
        res = auth_client.get("/api/crm/contatos/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_filtrar_por_cliente(self, auth_client, cliente_crm):
        from conftest import ContatoFactory, ClienteFactory
        outro_cliente = ClienteFactory(empresa=cliente_crm.empresa)
        ContatoFactory(cliente=cliente_crm)
        ContatoFactory(cliente=outro_cliente)
        res = auth_client.get(f"/api/crm/contatos/?cliente={cliente_crm.id}")
        assert res.data["count"] == 1

    def test_filtrar_decisores(self, auth_client, cliente_crm):
        from conftest import ContatoFactory
        ContatoFactory(cliente=cliente_crm, decisor=True)
        ContatoFactory(cliente=cliente_crm, decisor=False)
        res = auth_client.get("/api/crm/contatos/?decisor=true")
        assert res.data["count"] == 1

    def test_criar_contato(self, auth_client, cliente_crm):
        payload = {
            "cliente": str(cliente_crm.id),
            "nome_completo": "Ana Paula Diretora",
            "cargo": "Diretora Comercial",
            "email": "ana@empresa.com",
            "decisor": True,
        }
        res = auth_client.post("/api/crm/contatos/", payload, format="json")
        assert res.status_code == 201
        assert res.data["decisor"] is True

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import ContatoFactory, ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        outro_cliente = ClienteFactory(empresa=outra)
        ContatoFactory(cliente=outro_cliente)
        res = auth_client.get("/api/crm/contatos/")
        assert res.data["count"] == 0


# ─── Oportunidades ────────────────────────────────────────────────────────────

class TestOportunidadeAPI:

    def test_listar_oportunidades(self, auth_client, oportunidade):
        res = auth_client.get("/api/crm/oportunidades/")
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert "etapa_display" in res.data["results"][0]
        assert "cliente_nome" in res.data["results"][0]

    def test_criar_oportunidade(self, auth_client, cliente_crm):
        payload = {
            "cliente": str(cliente_crm.id),
            "titulo": "Contrato de Frete Mensal",
            "servico": "frete",
            "valor_estimado": "15000.00",
            "etapa": "qualificacao",
            "probabilidade": 40,
        }
        res = auth_client.post("/api/crm/oportunidades/", payload, format="json")
        assert res.status_code == 201
        assert res.data["etapa"] == "qualificacao"

    def test_filtrar_por_etapa(self, auth_client, oportunidade):
        res = auth_client.get("/api/crm/oportunidades/?etapa=prospeccao")
        assert res.data["count"] == 1
        res2 = auth_client.get("/api/crm/oportunidades/?etapa=fechado_ganho")
        assert res2.data["count"] == 0

    def test_filtrar_por_cliente(self, auth_client, cliente_crm, oportunidade):
        res = auth_client.get(f"/api/crm/oportunidades/?cliente={cliente_crm.id}")
        assert res.data["count"] == 1

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import OportunidadeFactory, ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        outro_cliente = ClienteFactory(empresa=outra)
        OportunidadeFactory(cliente=outro_cliente)
        res = auth_client.get("/api/crm/oportunidades/")
        assert res.data["count"] == 0


# ─── Action: fechar-ganho ─────────────────────────────────────────────────────

class TestFecharGanho:

    def test_fechar_ganho_sucesso(self, auth_client, oportunidade, cliente_crm):
        res = auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-ganho/")
        assert res.status_code == 200
        assert res.data["etapa"] == "fechado_ganho"
        assert res.data["probabilidade"] == 100

        cliente_crm.refresh_from_db()
        assert cliente_crm.status == StatusCliente.ATIVO

    def test_fechar_ganho_novamente_retorna_400(self, auth_client, oportunidade):
        auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-ganho/")
        res = auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-ganho/")
        assert res.status_code == 400
        assert "erro" in res.data

    def test_fechar_ganho_de_outra_empresa_retorna_404(self, auth_client):
        from conftest import OportunidadeFactory, ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        outro_cliente = ClienteFactory(empresa=outra)
        op_outra = OportunidadeFactory(cliente=outro_cliente)
        res = auth_client.post(f"/api/crm/oportunidades/{op_outra.id}/fechar-ganho/")
        assert res.status_code == 404


# ─── Action: fechar-perdido ───────────────────────────────────────────────────

class TestFecharPerdido:

    def test_fechar_perdido_sucesso(self, auth_client, oportunidade):
        payload = {"motivo": "Preço acima do mercado"}
        res = auth_client.post(
            f"/api/crm/oportunidades/{oportunidade.id}/fechar-perdido/",
            payload, format="json"
        )
        assert res.status_code == 200
        assert res.data["etapa"] == "fechado_perdido"

        oportunidade.refresh_from_db()
        assert oportunidade.motivo_perda == "Preço acima do mercado"

    def test_fechar_perdido_sem_motivo(self, auth_client, oportunidade):
        res = auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-perdido/")
        assert res.status_code == 200
        assert res.data["etapa"] == "fechado_perdido"

    def test_fechar_perdido_nao_ativa_cliente(self, auth_client, oportunidade, cliente_crm):
        auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-perdido/")
        cliente_crm.refresh_from_db()
        assert cliente_crm.status == StatusCliente.LEAD  # permanece como lead

    def test_fechar_perdido_duas_vezes_retorna_400(self, auth_client, oportunidade):
        auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-perdido/")
        res = auth_client.post(f"/api/crm/oportunidades/{oportunidade.id}/fechar-perdido/")
        assert res.status_code == 400


# ─── Histórico de Interação ───────────────────────────────────────────────────

class TestHistoricoAPI:

    def test_criar_historico(self, auth_client, cliente_crm):
        payload = {
            "cliente": str(cliente_crm.id),
            "tipo": "ligacao",
            "resumo": "Ligação de prospecção inicial",
        }
        res = auth_client.post("/api/crm/historico/", payload, format="json")
        assert res.status_code == 201
        assert res.data["tipo"] == "ligacao"
        assert res.data["registrado_por"] is not None

    def test_nao_permite_put_patch_delete(self, auth_client, cliente_crm):
        hi = HistoricoInteracao.objects.create(
            cliente=cliente_crm, tipo="email", resumo="E-mail enviado"
        )
        assert auth_client.put(f"/api/crm/historico/{hi.id}/").status_code == 405
        assert auth_client.patch(f"/api/crm/historico/{hi.id}/").status_code == 405
        assert auth_client.delete(f"/api/crm/historico/{hi.id}/").status_code == 405

    def test_filtrar_por_cliente(self, auth_client, cliente_crm):
        from conftest import ClienteFactory
        outro = ClienteFactory(empresa=cliente_crm.empresa)
        HistoricoInteracao.objects.create(cliente=cliente_crm, tipo="ligacao", resumo="A")
        HistoricoInteracao.objects.create(cliente=outro, tipo="email", resumo="B")
        res = auth_client.get(f"/api/crm/historico/?cliente={cliente_crm.id}")
        assert res.data["count"] == 1

    def test_filtrar_por_tipo(self, auth_client, cliente_crm):
        HistoricoInteracao.objects.create(cliente=cliente_crm, tipo="ligacao", resumo="A")
        HistoricoInteracao.objects.create(cliente=cliente_crm, tipo="reuniao", resumo="B")
        res = auth_client.get("/api/crm/historico/?tipo=ligacao")
        assert res.data["count"] == 1

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        outro_cliente = ClienteFactory(empresa=outra)
        HistoricoInteracao.objects.create(
            cliente=outro_cliente, tipo="email", resumo="X"
        )
        res = auth_client.get("/api/crm/historico/")
        assert res.data["count"] == 0


# ─── Contratos ────────────────────────────────────────────────────────────────

class TestContratoAPI:

    def test_criar_contrato(self, auth_client, cliente_crm):
        payload = {
            "cliente": str(cliente_crm.id),
            "numero": "CONT-TEST-001",
            "servico": "ambos",
            "valor_mensal": "12500.00",
            "vigencia_inicio": str(date.today()),
            "vigencia_fim": str(date.today() + timedelta(days=365)),
            "sla_prazo_entrega_horas": 24,
            "objeto": "Prestação de serviços de frete e armazenagem",
        }
        res = auth_client.post("/api/crm/contratos/", payload, format="json")
        assert res.status_code == 201
        assert res.data["numero"] == "CONT-TEST-001"
        assert res.data["vigente"] is True

    def test_listar_contratos(self, auth_client, cliente_crm):
        from conftest import ContratoFactory
        ContratoFactory(cliente=cliente_crm)
        res = auth_client.get("/api/crm/contratos/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_filtrar_por_cliente(self, auth_client, cliente_crm):
        from conftest import ContratoFactory, ClienteFactory
        outro = ClienteFactory(empresa=cliente_crm.empresa)
        ContratoFactory(cliente=cliente_crm)
        ContratoFactory(cliente=outro)
        res = auth_client.get(f"/api/crm/contratos/?cliente={cliente_crm.id}")
        assert res.data["count"] == 1

    def test_filtrar_apenas_ativos(self, auth_client, cliente_crm):
        from conftest import ContratoFactory
        ContratoFactory(cliente=cliente_crm, ativo=True)
        ContratoFactory(cliente=cliente_crm, ativo=False)
        res = auth_client.get("/api/crm/contratos/?ativo=true")
        assert res.data["count"] == 1

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import ContratoFactory, ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        outro_cliente = ClienteFactory(empresa=outra)
        ContratoFactory(cliente=outro_cliente)
        res = auth_client.get("/api/crm/contratos/")
        assert res.data["count"] == 0
