"""
Serializers do app TMS.
"""
from rest_framework import serializers
from .models import (
    Veiculo, Motorista,
    Romaneio, ItemRomaneio,
    Ocorrencia, POD,
)


# ─── Veículo ──────────────────────────────────────────────────────────────────

class VeiculoSerializer(serializers.ModelSerializer):
    tipo_display   = serializers.CharField(source="get_tipo_display", read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)

    class Meta:
        model  = Veiculo
        fields = [
            "id", "placa", "tipo", "tipo_display", "modelo", "ano",
            "capacidade_kg", "status", "status_display", "ativo",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ─── Motorista ────────────────────────────────────────────────────────────────

class MotoristaSerializer(serializers.ModelSerializer):
    categoria_display = serializers.CharField(source="get_categoria_cnh_display", read_only=True)

    class Meta:
        model  = Motorista
        fields = [
            "id", "nome_completo", "cpf", "cnh",
            "categoria_cnh", "categoria_display", "validade_cnh",
            "telefone", "ativo", "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]


# ─── Item de Romaneio ─────────────────────────────────────────────────────────

class ItemRomaneioSerializer(serializers.ModelSerializer):
    status_entrega_display = serializers.CharField(source="get_status_entrega_display", read_only=True)
    tem_pod                = serializers.SerializerMethodField()

    class Meta:
        model  = ItemRomaneio
        fields = [
            "id", "romaneio", "saida_wms",
            "destinatario",
            "logradouro", "numero_end", "bairro", "cidade", "uf", "cep",
            "latitude", "longitude",
            "ordem_entrega", "status_entrega", "status_entrega_display",
            "observacao", "tem_pod", "created_at",
        ]
        read_only_fields = ["id", "created_at"]

    def get_tem_pod(self, obj) -> bool:
        return hasattr(obj, "pod")


# ─── Romaneio — detalhe (com itens aninhados) ─────────────────────────────────

class RomaneioSerializer(serializers.ModelSerializer):
    itens               = ItemRomaneioSerializer(many=True, read_only=True)
    status_display      = serializers.CharField(source="get_status_display", read_only=True)
    motorista_nome      = serializers.CharField(source="motorista.nome_completo", read_only=True)
    veiculo_placa       = serializers.CharField(source="veiculo.placa", read_only=True)
    total_itens         = serializers.SerializerMethodField()
    itens_entregues     = serializers.SerializerMethodField()

    class Meta:
        model  = Romaneio
        fields = [
            "id", "numero", "status", "status_display",
            "veiculo", "veiculo_placa",
            "motorista", "motorista_nome",
            "data_saida_prevista", "data_saida_real", "data_conclusao",
            "responsavel", "observacoes",
            "total_itens", "itens_entregues",
            "created_at", "updated_at",
            "itens",
        ]
        read_only_fields = ["id", "numero", "created_at", "updated_at",
                            "data_saida_real", "data_conclusao"]

    def get_total_itens(self, obj):
        return obj.itens.count()

    def get_itens_entregues(self, obj):
        return obj.itens.filter(status_entrega="entregue").count()


# ─── Romaneio — listagem leve (sem itens aninhados) ──────────────────────────

class RomaneioListSerializer(serializers.ModelSerializer):
    status_display  = serializers.CharField(source="get_status_display", read_only=True)
    motorista_nome  = serializers.CharField(source="motorista.nome_completo", read_only=True)
    veiculo_placa   = serializers.CharField(source="veiculo.placa", read_only=True)
    total_itens     = serializers.SerializerMethodField()
    itens_entregues = serializers.SerializerMethodField()

    class Meta:
        model  = Romaneio
        fields = [
            "id", "numero", "status", "status_display",
            "veiculo_placa", "motorista_nome",
            "data_saida_prevista", "data_saida_real",
            "total_itens", "itens_entregues",
            "created_at",
        ]

    def get_total_itens(self, obj):
        return obj.itens.count()

    def get_itens_entregues(self, obj):
        return obj.itens.filter(status_entrega="entregue").count()


# ─── Ocorrência ───────────────────────────────────────────────────────────────

class OcorrenciaSerializer(serializers.ModelSerializer):
    tipo_display          = serializers.CharField(source="get_tipo_display", read_only=True)
    registrado_por_nome   = serializers.CharField(source="registrado_por.nome_completo", read_only=True)

    class Meta:
        model  = Ocorrencia
        fields = [
            "id", "romaneio", "item",
            "tipo", "tipo_display",
            "descricao",
            "registrado_por", "registrado_por_nome",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ─── POD ─────────────────────────────────────────────────────────────────────

class PODSerializer(serializers.ModelSerializer):
    item_destinatario = serializers.CharField(source="item.destinatario", read_only=True)

    class Meta:
        model  = POD
        fields = [
            "id", "item", "item_destinatario",
            "assinado_por", "observacao",
            "latitude", "longitude",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]
