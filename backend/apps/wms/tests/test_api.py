"""
Testes de integração da API REST do módulo WMS.
"""
import pytest
from decimal import Decimal
from django.utils import timezone

from apps.wms.models import (
    EntradaMercadoria, StatusEntrada,
    SaidaMercadoria, StatusSaida,
    MovimentacaoEstoque, TipoMovimentacao,
    Corredor, Bay, Nivel, Posicao,
    ItemEntrada, ItemSaida,
)


pytestmark = pytest.mark.django_db


# ─── helpers ──────────────────────────────────────────────────────────────────

def criar_posicao(armazem, corredor_cod="X", bay_num="01", nivel_num="01"):
    corredor = Corredor.objects.create(armazem=armazem, codigo=corredor_cod)
    bay = Bay.objects.create(corredor=corredor, numero=bay_num)
    nivel = Nivel.objects.create(bay=bay, numero=nivel_num)
    return Posicao.objects.create(nivel=nivel)


# ─── Armazéns ─────────────────────────────────────────────────────────────────

class TestArmazemAPI:

    def test_listar_armazens(self, auth_client, armazem):
        res = auth_client.get("/api/wms/armazens/")
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["codigo"] == armazem.codigo

    def test_nao_lista_de_outra_empresa(self, auth_client):
        from conftest import ArmazemFactory, EmpresaFactory
        outra = EmpresaFactory()
        ArmazemFactory(empresa=outra)
        res = auth_client.get("/api/wms/armazens/")
        assert res.data["count"] == 0

    def test_criar_armazem(self, auth_client, empresa):
        payload = {
            "empresa": str(empresa.id),
            "nome": "Centro de Distribuição SP",
            "codigo": "CDSP",
        }
        res = auth_client.post("/api/wms/armazens/", payload, format="json")
        assert res.status_code == 201
        assert res.data["codigo"] == "CDSP"

    def test_nao_autenticado_retorna_401(self, api_client):
        res = api_client.get("/api/wms/armazens/")
        assert res.status_code == 401


# ─── Produtos ─────────────────────────────────────────────────────────────────

class TestProdutoAPI:

    def test_listar_produtos(self, auth_client, produto):
        res = auth_client.get("/api/wms/produtos/")
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["sku"] == produto.sku

    def test_criar_produto(self, auth_client, empresa):
        payload = {
            "empresa": str(empresa.id),
            "sku": "CAIXA-001",
            "descricao": "Caixa de Papelão 50x30",
            "unidade": "un",
        }
        res = auth_client.post("/api/wms/produtos/", payload, format="json")
        assert res.status_code == 201
        assert res.data["sku"] == "CAIXA-001"

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import ProdutoFactory, EmpresaFactory
        outra = EmpresaFactory()
        ProdutoFactory(empresa=outra)
        res = auth_client.get("/api/wms/produtos/")
        assert res.data["count"] == 0


# ─── Posições ─────────────────────────────────────────────────────────────────

class TestPosicaoAPI:

    def test_listar_posicoes(self, auth_client, armazem):
        criar_posicao(armazem, "A")
        res = auth_client.get("/api/wms/posicoes/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_filtrar_por_armazem(self, auth_client, armazem):
        from conftest import ArmazemFactory
        outro = ArmazemFactory(empresa=armazem.empresa)
        criar_posicao(armazem, "E")
        criar_posicao(outro, "F")
        res = auth_client.get(f"/api/wms/posicoes/?armazem={armazem.id}")
        assert res.data["count"] == 1

    def test_saldo_endpoint(self, auth_client, armazem, produto):
        posicao = criar_posicao(armazem, "G")
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("80"),
        )
        res = auth_client.get("/api/wms/posicoes/saldo/")
        assert res.status_code == 200
        assert len(res.data) == 1
        assert res.data[0]["produto_sku"] == produto.sku
        assert Decimal(str(res.data[0]["saldo"])) == Decimal("80")


# ─── Entradas ─────────────────────────────────────────────────────────────────

class TestEntradaAPI:

    def test_listar_entradas(self, auth_client, entrada):
        res = auth_client.get("/api/wms/entradas/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_listar_usa_serializer_leve(self, auth_client, entrada):
        res = auth_client.get("/api/wms/entradas/")
        data = res.data["results"][0]
        assert "numero_nf" in data
        assert "status" in data

    def test_detalhe_inclui_itens(self, auth_client, entrada, produto, armazem):
        posicao = criar_posicao(armazem, "H")
        ItemEntrada.objects.create(
            entrada=entrada, produto=produto,
            posicao=posicao, quantidade_esperada=Decimal("10"),
        )
        res = auth_client.get(f"/api/wms/entradas/{entrada.id}/")
        assert res.status_code == 200
        assert "itens" in res.data
        assert len(res.data["itens"]) == 1

    def test_criar_entrada(self, auth_client, armazem):
        payload = {
            "armazem": str(armazem.id),
            "numero_nf": "NF-API-001",
            "fornecedor": "Fornecedor Via API",
            "chegada_em": timezone.now().isoformat(),
        }
        res = auth_client.post("/api/wms/entradas/", payload, format="json")
        assert res.status_code == 201
        assert res.data["numero_nf"] == "NF-API-001"
        assert res.data["status"] == "pendente"

    def test_filtrar_por_status(self, auth_client, entrada):
        res = auth_client.get("/api/wms/entradas/?status=pendente")
        assert res.data["count"] == 1
        res2 = auth_client.get("/api/wms/entradas/?status=concluido")
        assert res2.data["count"] == 0

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import EntradaMercadoriaFactory, ArmazemFactory, EmpresaFactory
        outra = EmpresaFactory()
        arm_outra = ArmazemFactory(empresa=outra)
        EntradaMercadoriaFactory(armazem=arm_outra)
        res = auth_client.get("/api/wms/entradas/")
        assert res.data["count"] == 0


# ─── Action: concluir entrada ─────────────────────────────────────────────────

class TestConcluirEntrada:

    def test_concluir_sucesso(self, auth_client, entrada, produto, armazem):
        posicao = criar_posicao(armazem, "I")
        ItemEntrada.objects.create(
            entrada=entrada, produto=produto,
            posicao=posicao, quantidade_esperada=Decimal("20"),
            quantidade_conferida=Decimal("20"),
        )
        res = auth_client.post(f"/api/wms/entradas/{entrada.id}/concluir/")
        assert res.status_code == 200
        assert res.data["status"] == "concluido"

        assert MovimentacaoEstoque.objects.filter(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA,
        ).count() == 1

    def test_concluir_duas_vezes_retorna_400(self, auth_client, entrada):
        auth_client.post(f"/api/wms/entradas/{entrada.id}/concluir/")
        res = auth_client.post(f"/api/wms/entradas/{entrada.id}/concluir/")
        assert res.status_code == 400
        assert "erro" in res.data

    def test_concluir_de_outra_empresa_retorna_404(self, auth_client):
        from conftest import EntradaMercadoriaFactory, ArmazemFactory, EmpresaFactory
        outra = EmpresaFactory()
        arm = ArmazemFactory(empresa=outra)
        ent = EntradaMercadoriaFactory(armazem=arm)
        res = auth_client.post(f"/api/wms/entradas/{ent.id}/concluir/")
        assert res.status_code == 404

    def test_marcar_divergencia(self, auth_client, entrada):
        res = auth_client.post(f"/api/wms/entradas/{entrada.id}/marcar-divergencia/")
        assert res.status_code == 200
        entrada.refresh_from_db()
        assert entrada.status == "divergencia"


# ─── Saídas ───────────────────────────────────────────────────────────────────

class TestSaidaAPI:

    def test_listar_saidas(self, auth_client, saida):
        res = auth_client.get("/api/wms/saidas/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_criar_saida(self, auth_client, armazem):
        payload = {
            "armazem": str(armazem.id),
            "numero_pedido": "PED-API-001",
            "destinatario": "Cliente Via API",
        }
        res = auth_client.post("/api/wms/saidas/", payload, format="json")
        assert res.status_code == 201
        assert res.data["status"] == "pendente"

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import SaidaMercadoriaFactory, ArmazemFactory, EmpresaFactory
        outra = EmpresaFactory()
        arm = ArmazemFactory(empresa=outra)
        SaidaMercadoriaFactory(armazem=arm)
        res = auth_client.get("/api/wms/saidas/")
        assert res.data["count"] == 0


# ─── Action: expedir saída ────────────────────────────────────────────────────

class TestExpedirSaida:

    def test_expedir_sucesso(self, auth_client, saida, produto, armazem):
        posicao = criar_posicao(armazem, "J")
        # Estoque inicial
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("100"),
        )
        ItemSaida.objects.create(
            saida=saida, produto=produto,
            posicao=posicao, quantidade=Decimal("25"),
        )
        res = auth_client.post(f"/api/wms/saidas/{saida.id}/expedir/")
        assert res.status_code == 200
        assert res.data["status"] == "expedido"

        mov = MovimentacaoEstoque.objects.get(
            posicao=posicao, tipo=TipoMovimentacao.SAIDA
        )
        assert mov.quantidade == Decimal("-25")

    def test_expedir_duas_vezes_retorna_400(self, auth_client, saida):
        auth_client.post(f"/api/wms/saidas/{saida.id}/expedir/")
        res = auth_client.post(f"/api/wms/saidas/{saida.id}/expedir/")
        assert res.status_code == 400

    def test_expedir_de_outra_empresa_retorna_404(self, auth_client):
        from conftest import SaidaMercadoriaFactory, ArmazemFactory, EmpresaFactory
        outra = EmpresaFactory()
        arm = ArmazemFactory(empresa=outra)
        saida_outra = SaidaMercadoriaFactory(armazem=arm)
        res = auth_client.post(f"/api/wms/saidas/{saida_outra.id}/expedir/")
        assert res.status_code == 404


# ─── Movimentações (somente leitura) ─────────────────────────────────────────

class TestMovimentacoesAPI:

    def test_listar_movimentacoes(self, auth_client, armazem, produto):
        posicao = criar_posicao(armazem, "K")
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("10"),
        )
        res = auth_client.get("/api/wms/movimentacoes/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_filtrar_por_produto(self, auth_client, armazem, produto):
        from conftest import ProdutoFactory
        outro_prod = ProdutoFactory(empresa=armazem.empresa)
        posicao = criar_posicao(armazem, "L")
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("5"),
        )
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=outro_prod,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("5"),
        )
        res = auth_client.get(f"/api/wms/movimentacoes/?produto={produto.id}")
        assert res.data["count"] == 1

    def test_somente_leitura(self, auth_client, armazem, produto):
        """Movimentações não aceitam POST."""
        res = auth_client.post("/api/wms/movimentacoes/", {})
        assert res.status_code == 405

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import ArmazemFactory, ProdutoFactory, EmpresaFactory
        outra = EmpresaFactory()
        arm = ArmazemFactory(empresa=outra)
        prod = ProdutoFactory(empresa=outra)
        posicao = criar_posicao(arm, "M")
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=prod,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("50"),
        )
        res = auth_client.get("/api/wms/movimentacoes/")
        assert res.data["count"] == 0
