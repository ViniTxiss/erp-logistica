"""
Serializers do app WMS.
"""
from rest_framework import serializers
from .models import (
    Armazem, Corredor, Bay, Nivel, Posicao, Produto,
    EntradaMercadoria, ItemEntrada, SaidaMercadoria, ItemSaida,
    MovimentacaoEstoque,
)


class ArmazemSerializer(serializers.ModelSerializer):
    class Meta:
        model = Armazem
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class PosicaoSerializer(serializers.ModelSerializer):
    saldo_atual = serializers.ReadOnlyField()

    class Meta:
        model = Posicao
        fields = ["id", "codigo", "ativo", "saldo_atual"]


class ProdutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produto
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class ItemEntradaSerializer(serializers.ModelSerializer):
    produto_descricao = serializers.CharField(source="produto.descricao", read_only=True)
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    tem_divergencia = serializers.ReadOnlyField()

    class Meta:
        model = ItemEntrada
        fields = [
            "id", "produto", "produto_sku", "produto_descricao",
            "posicao", "quantidade_esperada", "quantidade_conferida",
            "observacao", "tem_divergencia",
        ]


class EntradaMercadoriaSerializer(serializers.ModelSerializer):
    itens = ItemEntradaSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    responsavel_nome = serializers.CharField(source="responsavel.nome_completo", read_only=True)

    class Meta:
        model = EntradaMercadoria
        fields = [
            "id", "armazem", "numero_nf", "fornecedor", "status", "status_display",
            "responsavel", "responsavel_nome", "observacoes",
            "chegada_em", "concluida_em", "created_at", "itens",
        ]
        read_only_fields = ["id", "created_at", "concluida_em"]


class EntradaMercadoriaListSerializer(serializers.ModelSerializer):
    """Versão leve para listagem (sem itens aninhados)."""
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    total_itens = serializers.SerializerMethodField()

    class Meta:
        model = EntradaMercadoria
        fields = [
            "id", "numero_nf", "fornecedor", "status", "status_display",
            "chegada_em", "total_itens",
        ]

    def get_total_itens(self, obj):
        return obj.itens.count()


class ItemSaidaSerializer(serializers.ModelSerializer):
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    posicao_codigo = serializers.CharField(source="posicao.codigo", read_only=True)

    class Meta:
        model = ItemSaida
        fields = ["id", "produto", "produto_sku", "posicao", "posicao_codigo", "quantidade"]


class SaidaMercadoriaSerializer(serializers.ModelSerializer):
    itens = ItemSaidaSerializer(many=True, read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model = SaidaMercadoria
        fields = [
            "id", "armazem", "numero_pedido", "destinatario", "status", "status_display",
            "responsavel", "expedida_em", "created_at", "itens",
        ]
        read_only_fields = ["id", "created_at", "expedida_em"]


class MovimentacaoEstoqueSerializer(serializers.ModelSerializer):
    produto_sku = serializers.CharField(source="produto.sku", read_only=True)
    posicao_codigo = serializers.CharField(source="posicao.codigo", read_only=True)
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = MovimentacaoEstoque
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class SaldoPorPosicaoSerializer(serializers.Serializer):
    """Serializer para o endpoint de saldo por posição/produto."""
    posicao = serializers.CharField(source="posicao_codigo")
    produto_sku = serializers.CharField()
    produto_descricao = serializers.CharField()
    saldo = serializers.DecimalField(max_digits=10, decimal_places=3)
