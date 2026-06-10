"""
Testes unitários dos models do WMS.
Foco: lógica de negócio, side-effects, propriedades calculadas.
"""
import pytest
from decimal import Decimal
from django.utils import timezone

from apps.wms.models import (
    Armazem, Posicao, Produto,
    EntradaMercadoria, ItemEntrada, StatusEntrada,
    SaidaMercadoria, ItemSaida, StatusSaida,
    MovimentacaoEstoque, TipoMovimentacao,
    Corredor, Bay, Nivel,
)


pytestmark = pytest.mark.django_db


# ─── Armazém ──────────────────────────────────────────────────────────────────

class TestArmazemModel:

    def test_criacao_basica(self, armazem):
        assert armazem.pk is not None
        assert armazem.ativo is True

    def test_str(self, armazem):
        resultado = str(armazem)
        assert armazem.codigo in resultado
        assert armazem.nome in resultado

    def test_codigo_unico_por_empresa(self, empresa):
        from conftest import ArmazemFactory
        ArmazemFactory(empresa=empresa, codigo="CD99")
        with pytest.raises(Exception):
            ArmazemFactory(empresa=empresa, codigo="CD99")

    def test_mesmo_codigo_empresas_diferentes(self, empresa):
        from conftest import ArmazemFactory, EmpresaFactory
        outra = EmpresaFactory()
        a1 = ArmazemFactory(empresa=empresa, codigo="CD01")
        a2 = ArmazemFactory(empresa=outra, codigo="CD01")
        assert a1.pk != a2.pk


# ─── Posição — geração de código e saldo ──────────────────────────────────────

class TestPosicaoModel:

    def _criar_posicao_completa(self, armazem, corredor_cod="A", bay_num="01", nivel_num="01"):
        corredor = Corredor.objects.create(armazem=armazem, codigo=corredor_cod)
        bay = Bay.objects.create(corredor=corredor, numero=bay_num)
        nivel = Nivel.objects.create(bay=bay, numero=nivel_num)
        posicao = Posicao.objects.create(nivel=nivel)
        return posicao

    def test_codigo_gerado_automaticamente(self, armazem):
        posicao = self._criar_posicao_completa(armazem)
        assert posicao.codigo != ""
        assert armazem.codigo in posicao.codigo

    def test_codigo_formato_correto(self, armazem):
        """Formato esperado: CD01-A-01-01"""
        posicao = self._criar_posicao_completa(armazem)
        partes = posicao.codigo.split("-")
        assert len(partes) == 4

    def test_str(self, armazem):
        posicao = self._criar_posicao_completa(armazem)
        assert posicao.codigo in str(posicao)

    def test_saldo_inicial_zero(self, armazem):
        posicao = self._criar_posicao_completa(armazem)
        assert posicao.saldo_atual == 0

    def test_saldo_soma_movimentacoes(self, armazem, produto):
        posicao = self._criar_posicao_completa(armazem)
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("100"),
        )
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.SAIDA, quantidade=Decimal("-30"),
        )
        assert posicao.saldo_atual == Decimal("70")


# ─── Produto ──────────────────────────────────────────────────────────────────

class TestProdutoModel:

    def test_criacao_basica(self, produto):
        assert produto.pk is not None
        assert produto.ativo is True

    def test_str(self, produto):
        resultado = str(produto)
        assert produto.sku in resultado
        assert produto.descricao in resultado

    def test_sku_unico_por_empresa(self, empresa):
        from conftest import ProdutoFactory
        ProdutoFactory(empresa=empresa, sku="SKU-UNICO")
        with pytest.raises(Exception):
            ProdutoFactory(empresa=empresa, sku="SKU-UNICO")


# ─── EntradaMercadoria.concluir() ─────────────────────────────────────────────

class TestEntradaConcluir:

    def _setup_entrada_com_item(self, armazem, produto):
        corredor = Corredor.objects.create(armazem=armazem, codigo="B")
        bay = Bay.objects.create(corredor=corredor, numero="01")
        nivel = Nivel.objects.create(bay=bay, numero="01")
        posicao = Posicao.objects.create(nivel=nivel)

        entrada = EntradaMercadoria.objects.create(
            armazem=armazem,
            numero_nf="NF-TESTE-001",
            fornecedor="Fornecedor ABC",
            status=StatusEntrada.PENDENTE,
            chegada_em=timezone.now(),
        )
        item = ItemEntrada.objects.create(
            entrada=entrada,
            produto=produto,
            posicao=posicao,
            quantidade_esperada=Decimal("50"),
            quantidade_conferida=Decimal("50"),
        )
        return entrada, item, posicao

    def test_concluir_muda_status(self, armazem, produto, usuario):
        entrada, _, _ = self._setup_entrada_com_item(armazem, produto)
        entrada.concluir(usuario=usuario)
        entrada.refresh_from_db()
        assert entrada.status == StatusEntrada.CONCLUIDO

    def test_concluir_registra_data(self, armazem, produto, usuario):
        before = timezone.now()
        entrada, _, _ = self._setup_entrada_com_item(armazem, produto)
        entrada.concluir(usuario=usuario)
        entrada.refresh_from_db()
        assert entrada.concluida_em is not None
        assert entrada.concluida_em >= before

    def test_concluir_cria_movimentacao_de_estoque(self, armazem, produto, usuario):
        entrada, _, posicao = self._setup_entrada_com_item(armazem, produto)
        assert MovimentacaoEstoque.objects.count() == 0
        entrada.concluir(usuario=usuario)
        assert MovimentacaoEstoque.objects.filter(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA
        ).count() == 1

    def test_concluir_usa_quantidade_conferida(self, armazem, produto, usuario):
        entrada, item, posicao = self._setup_entrada_com_item(armazem, produto)
        item.quantidade_conferida = Decimal("45")  # menos que o esperado
        item.save()
        entrada.concluir(usuario=usuario)
        mov = MovimentacaoEstoque.objects.get(posicao=posicao, produto=produto)
        assert mov.quantidade == Decimal("45")

    def test_concluir_nao_cria_mov_sem_posicao(self, armazem, produto, usuario):
        """Itens sem posição definida não geram movimentação."""
        entrada = EntradaMercadoria.objects.create(
            armazem=armazem, numero_nf="NF-SEM-POS",
            fornecedor="X", status=StatusEntrada.PENDENTE,
            chegada_em=timezone.now(),
        )
        ItemEntrada.objects.create(
            entrada=entrada, produto=produto,
            posicao=None,  # sem posição
            quantidade_esperada=Decimal("10"),
        )
        entrada.concluir(usuario=usuario)
        assert MovimentacaoEstoque.objects.count() == 0

    def test_str_entrada(self, entrada):
        resultado = str(entrada)
        assert entrada.numero_nf in resultado
        assert entrada.fornecedor in resultado


# ─── ItemEntrada.tem_divergencia ──────────────────────────────────────────────

class TestItemEntradaDivergencia:

    def test_sem_conferencia_nao_e_divergencia(self, entrada, produto):
        item = ItemEntrada.objects.create(
            entrada=entrada, produto=produto,
            quantidade_esperada=Decimal("100"),
            quantidade_conferida=None,
        )
        assert item.tem_divergencia is False

    def test_conferida_igual_esperada_nao_e_divergencia(self, entrada, produto):
        item = ItemEntrada.objects.create(
            entrada=entrada, produto=produto,
            quantidade_esperada=Decimal("100"),
            quantidade_conferida=Decimal("100"),
        )
        assert item.tem_divergencia is False

    def test_conferida_diferente_e_divergencia(self, entrada, produto):
        item = ItemEntrada.objects.create(
            entrada=entrada, produto=produto,
            quantidade_esperada=Decimal("100"),
            quantidade_conferida=Decimal("90"),
        )
        assert item.tem_divergencia is True


# ─── SaidaMercadoria.expedir() ────────────────────────────────────────────────

class TestSaidaExpedir:

    def _setup_saida_com_item(self, armazem, produto):
        corredor = Corredor.objects.create(armazem=armazem, codigo="C")
        bay = Bay.objects.create(corredor=corredor, numero="01")
        nivel = Nivel.objects.create(bay=bay, numero="01")
        posicao = Posicao.objects.create(nivel=nivel)

        # Estoque inicial
        MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("100"),
        )

        saida = SaidaMercadoria.objects.create(
            armazem=armazem,
            numero_pedido="PED-TEST-001",
            destinatario="Cliente XYZ",
            status=StatusSaida.PENDENTE,
        )
        item = ItemSaida.objects.create(
            saida=saida, produto=produto,
            posicao=posicao, quantidade=Decimal("30"),
        )
        return saida, item, posicao

    def test_expedir_muda_status(self, armazem, produto, usuario):
        saida, _, _ = self._setup_saida_com_item(armazem, produto)
        saida.expedir(usuario=usuario)
        saida.refresh_from_db()
        assert saida.status == StatusSaida.EXPEDIDO

    def test_expedir_registra_data(self, armazem, produto, usuario):
        before = timezone.now()
        saida, _, _ = self._setup_saida_com_item(armazem, produto)
        saida.expedir(usuario=usuario)
        saida.refresh_from_db()
        assert saida.expedida_em is not None
        assert saida.expedida_em >= before

    def test_expedir_cria_movimentacao_negativa(self, armazem, produto, usuario):
        saida, _, posicao = self._setup_saida_com_item(armazem, produto)
        saida.expedir(usuario=usuario)
        mov_saida = MovimentacaoEstoque.objects.get(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.SAIDA
        )
        assert mov_saida.quantidade == Decimal("-30")

    def test_expedir_reduz_saldo(self, armazem, produto, usuario):
        saida, _, posicao = self._setup_saida_com_item(armazem, produto)
        saldo_antes = posicao.saldo_atual
        saida.expedir(usuario=usuario)
        assert posicao.saldo_atual == saldo_antes - Decimal("30")

    def test_str_saida(self, saida):
        resultado = str(saida)
        assert saida.destinatario in resultado


# ─── MovimentacaoEstoque (ledger imutável) ────────────────────────────────────

class TestMovimentacaoEstoque:

    def _criar_posicao(self, armazem):
        corredor = Corredor.objects.create(armazem=armazem, codigo="D")
        bay = Bay.objects.create(corredor=corredor, numero="01")
        nivel = Nivel.objects.create(bay=bay, numero="01")
        return Posicao.objects.create(nivel=nivel)

    def test_str_entrada(self, armazem, produto):
        posicao = self._criar_posicao(armazem)
        mov = MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.ENTRADA, quantidade=Decimal("50"),
        )
        resultado = str(mov)
        assert "+" in resultado
        assert produto.sku in resultado

    def test_str_saida(self, armazem, produto):
        posicao = self._criar_posicao(armazem)
        mov = MovimentacaoEstoque.objects.create(
            posicao=posicao, produto=produto,
            tipo=TipoMovimentacao.SAIDA, quantidade=Decimal("-10"),
        )
        resultado = str(mov)
        assert produto.sku in resultado
