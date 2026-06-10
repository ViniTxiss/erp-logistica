"""
Admin do app CRM — Django Admin com inlines e status colorido.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Cliente, Contato,
    Oportunidade, HistoricoInteracao, Contrato,
)


# ─── Inlines ──────────────────────────────────────────────────────────────────

class ContatoInline(admin.TabularInline):
    model         = Contato
    extra         = 0
    fields        = ["nome_completo", "cargo", "email", "telefone", "decisor", "ativo"]
    ordering      = ["-decisor", "nome_completo"]


class OportunidadeInline(admin.TabularInline):
    model         = Oportunidade
    extra         = 0
    fields        = ["titulo", "servico", "etapa", "valor_estimado", "probabilidade", "previsao_fechamento"]
    ordering      = ["-created_at"]


class ContratoInline(admin.TabularInline):
    model         = Contrato
    extra         = 0
    fields        = ["numero", "servico", "valor_mensal", "vigencia_inicio", "vigencia_fim", "ativo"]
    readonly_fields = []


# ─── Cliente ──────────────────────────────────────────────────────────────────

@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display    = [
        "razao_social", "nome_fantasia", "cnpj",
        "segmento", "status_badge", "cidade", "uf",
        "responsavel", "created_at",
    ]
    list_filter     = ["status", "segmento", "empresa", "uf"]
    search_fields   = ["razao_social", "nome_fantasia", "cnpj"]
    ordering        = ["razao_social"]
    readonly_fields = ["created_at", "updated_at"]
    inlines         = [ContatoInline, OportunidadeInline, ContratoInline]

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "lead":      "#888",
            "ativo":     "green",
            "inativo":   "orange",
            "bloqueado": "red",
        }
        cor = cores.get(obj.status, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_status_display()
        )


# ─── Contato ──────────────────────────────────────────────────────────────────

@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display  = ["nome_completo", "cliente", "cargo", "email", "telefone", "decisor", "ativo"]
    list_filter   = ["decisor", "ativo", "cliente__empresa"]
    search_fields = ["nome_completo", "email", "cliente__razao_social"]
    ordering      = ["-decisor", "nome_completo"]


# ─── Oportunidade ─────────────────────────────────────────────────────────────

@admin.register(Oportunidade)
class OportunidadeAdmin(admin.ModelAdmin):
    list_display  = [
        "titulo", "cliente", "servico", "etapa_badge",
        "valor_estimado", "probabilidade", "responsavel", "previsao_fechamento",
    ]
    list_filter   = ["etapa", "servico", "cliente__empresa"]
    search_fields = ["titulo", "cliente__razao_social"]
    ordering      = ["-created_at"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Etapa")
    def etapa_badge(self, obj):
        cores = {
            "prospeccao":      "#aaa",
            "qualificacao":    "#4a90d9",
            "proposta":        "#f5a623",
            "negociacao":      "#7ed321",
            "fechado_ganho":   "green",
            "fechado_perdido": "red",
        }
        cor = cores.get(obj.etapa, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_etapa_display()
        )


# ─── Histórico de Interação ───────────────────────────────────────────────────

@admin.register(HistoricoInteracao)
class HistoricoInteracaoAdmin(admin.ModelAdmin):
    list_display  = ["tipo", "cliente", "contato", "data_interacao", "registrado_por"]
    list_filter   = ["tipo", "cliente__empresa"]
    search_fields = ["resumo", "cliente__razao_social"]
    readonly_fields = ["created_at"]
    ordering      = ["-data_interacao"]


# ─── Contrato ─────────────────────────────────────────────────────────────────

@admin.register(Contrato)
class ContratoAdmin(admin.ModelAdmin):
    list_display  = [
        "numero", "cliente", "servico",
        "valor_mensal", "vigencia_inicio", "vigencia_fim",
        "sla_prazo_entrega_horas", "ativo",
    ]
    list_filter   = ["servico", "ativo", "cliente__empresa"]
    search_fields = ["numero", "cliente__razao_social"]
    readonly_fields = ["created_at", "updated_at"]
