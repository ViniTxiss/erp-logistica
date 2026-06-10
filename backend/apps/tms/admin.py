"""
Admin do app TMS — Django Admin com inlines.
"""
from django.contrib import admin
from django.utils.html import format_html

from .models import (
    Veiculo, Motorista,
    Romaneio, ItemRomaneio,
    Ocorrencia, POD,
)


# ─── Veículo ──────────────────────────────────────────────────────────────────

@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display   = ["placa", "tipo", "modelo", "ano", "capacidade_kg", "status_badge", "ativo"]
    list_filter    = ["tipo", "status", "ativo", "empresa"]
    search_fields  = ["placa", "modelo"]
    ordering       = ["placa"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "disponivel":  "green",
            "em_rota":     "blue",
            "manutencao":  "orange",
            "inativo":     "gray",
        }
        cor = cores.get(obj.status, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_status_display()
        )


# ─── Motorista ────────────────────────────────────────────────────────────────

@admin.register(Motorista)
class MotoristaAdmin(admin.ModelAdmin):
    list_display   = ["nome_completo", "cpf", "cnh", "categoria_cnh", "validade_cnh", "ativo"]
    list_filter    = ["categoria_cnh", "ativo", "empresa"]
    search_fields  = ["nome_completo", "cpf", "cnh"]
    ordering       = ["nome_completo"]


# ─── Romaneio ─────────────────────────────────────────────────────────────────

class ItemRomaneioInline(admin.TabularInline):
    model          = ItemRomaneio
    extra          = 0
    fields         = ["ordem_entrega", "destinatario", "cidade", "uf", "saida_wms", "status_entrega"]
    ordering       = ["ordem_entrega"]


class OcorrenciaInline(admin.TabularInline):
    model          = Ocorrencia
    extra          = 0
    fields         = ["tipo", "descricao", "registrado_por", "created_at"]
    readonly_fields = ["created_at"]


@admin.register(Romaneio)
class RomaneioAdmin(admin.ModelAdmin):
    list_display   = [
        "numero", "status_badge", "veiculo", "motorista",
        "data_saida_prevista", "data_saida_real", "total_itens",
    ]
    list_filter    = ["status", "empresa"]
    search_fields  = ["numero", "motorista__nome_completo", "veiculo__placa"]
    ordering       = ["-created_at"]
    inlines        = [ItemRomaneioInline, OcorrenciaInline]
    readonly_fields = ["numero", "data_saida_real", "data_conclusao", "created_at", "updated_at"]

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "aberto":          "#888",
            "em_rota":         "blue",
            "concluido":       "green",
            "com_ocorrencia":  "orange",
            "cancelado":       "red",
        }
        cor = cores.get(obj.status, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_status_display()
        )

    @admin.display(description="Itens")
    def total_itens(self, obj):
        return obj.itens.count()


# ─── Item de Romaneio ─────────────────────────────────────────────────────────

@admin.register(ItemRomaneio)
class ItemRomaneioAdmin(admin.ModelAdmin):
    list_display   = ["destinatario", "romaneio", "cidade", "uf", "ordem_entrega", "status_entrega"]
    list_filter    = ["status_entrega", "romaneio__empresa"]
    search_fields  = ["destinatario", "romaneio__numero"]
    ordering       = ["romaneio", "ordem_entrega"]


# ─── Ocorrência ───────────────────────────────────────────────────────────────

@admin.register(Ocorrencia)
class OcorrenciaAdmin(admin.ModelAdmin):
    list_display   = ["tipo", "romaneio", "item", "registrado_por", "created_at"]
    list_filter    = ["tipo", "romaneio__empresa"]
    search_fields  = ["descricao", "romaneio__numero"]
    readonly_fields = ["created_at"]


# ─── POD ─────────────────────────────────────────────────────────────────────

@admin.register(POD)
class PODAdmin(admin.ModelAdmin):
    list_display   = ["item", "assinado_por", "latitude", "longitude", "created_at"]
    search_fields  = ["item__destinatario", "assinado_por"]
    readonly_fields = ["created_at"]
