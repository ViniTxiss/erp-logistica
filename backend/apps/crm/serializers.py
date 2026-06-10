"""
Serializers do app CRM.
"""
from rest_framework import serializers
from .models import (
    Cliente, Contato,
    Oportunidade, HistoricoInteracao, Contrato,
)


# ─── Contato ──────────────────────────────────────────────────────────────────

class ContatoSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Contato
        fields = [
            "id", "cliente", "nome_completo", "cargo",
            "email", "telefone", "whatsapp",
            "decisor", "ativo", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ─── Cliente — detalhe (com contatos aninhados) ───────────────────────────────

class ClienteSerializer(serializers.ModelSerializer):
    contatos            = ContatoSerializer(many=True, read_only=True)
    status_display      = serializers.CharField(source="get_status_display", read_only=True)
    segmento_display    = serializers.CharField(source="get_segmento_display", read_only=True)
    responsavel_nome    = serializers.CharField(source="responsavel.nome_completo", read_only=True)
    total_oportunidades = serializers.SerializerMethodField()
    contrato_ativo      = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = [
            "id", "cnpj", "razao_social", "nome_fantasia",
            "segmento", "segmento_display",
            "status", "status_display",
            "cidade", "uf", "site", "email_principal", "telefone",
            "responsavel", "responsavel_nome",
            "observacoes",
            "total_oportunidades", "contrato_ativo",
            "created_at", "updated_at",
            "contatos",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_total_oportunidades(self, obj):
        return obj.oportunidades.count()

    def get_contrato_ativo(self, obj):
        contrato = obj.contratos.filter(ativo=True).first()
        if contrato:
            return {"id": str(contrato.id), "numero": contrato.numero, "vigente": contrato.vigente}
        return None


# ─── Cliente — listagem leve (sem contatos aninhados) ─────────────────────────

class ClienteListSerializer(serializers.ModelSerializer):
    status_display   = serializers.CharField(source="get_status_display", read_only=True)
    segmento_display = serializers.CharField(source="get_segmento_display", read_only=True)
    responsavel_nome = serializers.CharField(source="responsavel.nome_completo", read_only=True)
    total_contatos   = serializers.SerializerMethodField()

    class Meta:
        model  = Cliente
        fields = [
            "id", "razao_social", "nome_fantasia", "cnpj",
            "segmento", "segmento_display",
            "status", "status_display",
            "cidade", "uf",
            "responsavel_nome",
            "total_contatos", "created_at",
        ]

    def get_total_contatos(self, obj):
        return obj.contatos.count()


# ─── Oportunidade ─────────────────────────────────────────────────────────────

class OportunidadeSerializer(serializers.ModelSerializer):
    etapa_display       = serializers.CharField(source="get_etapa_display", read_only=True)
    servico_display     = serializers.CharField(source="get_servico_display", read_only=True)
    responsavel_nome    = serializers.CharField(source="responsavel.nome_completo", read_only=True)
    cliente_nome        = serializers.CharField(source="cliente.razao_social", read_only=True)

    class Meta:
        model  = Oportunidade
        fields = [
            "id", "cliente", "cliente_nome",
            "titulo", "servico", "servico_display",
            "valor_estimado",
            "etapa", "etapa_display",
            "probabilidade",
            "responsavel", "responsavel_nome",
            "previsao_fechamento",
            "motivo_perda", "observacoes",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at", "motivo_perda"]


# ─── Histórico de Interação ───────────────────────────────────────────────────

class HistoricoInteracaoSerializer(serializers.ModelSerializer):
    tipo_display          = serializers.CharField(source="get_tipo_display", read_only=True)
    registrado_por_nome   = serializers.CharField(source="registrado_por.nome_completo", read_only=True)
    cliente_nome          = serializers.CharField(source="cliente.razao_social", read_only=True)
    contato_nome          = serializers.CharField(source="contato.nome_completo", read_only=True)

    class Meta:
        model  = HistoricoInteracao
        fields = [
            "id", "cliente", "cliente_nome",
            "oportunidade", "contato", "contato_nome",
            "tipo", "tipo_display",
            "resumo", "data_interacao",
            "registrado_por", "registrado_por_nome",
            "created_at",
        ]
        read_only_fields = ["id", "created_at"]


# ─── Contrato ─────────────────────────────────────────────────────────────────

class ContratoSerializer(serializers.ModelSerializer):
    servico_display  = serializers.CharField(source="get_servico_display", read_only=True)
    cliente_nome     = serializers.CharField(source="cliente.razao_social", read_only=True)
    vigente          = serializers.ReadOnlyField()

    class Meta:
        model  = Contrato
        fields = [
            "id", "cliente", "cliente_nome",
            "numero", "servico", "servico_display",
            "valor_mensal",
            "vigencia_inicio", "vigencia_fim",
            "sla_prazo_entrega_horas",
            "objeto", "ativo", "vigente",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]
