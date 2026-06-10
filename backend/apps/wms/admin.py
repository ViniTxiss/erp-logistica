"""
Admin do app WMS — Django Admin com inlines e status colorido.
"""
from django.contrib import admin
from django.utils.html import format_html
from django.db.models import Sum

from .models import (
    Armazem, Corredor, Bay, Nivel, Posicao,
    Produto,
    EntradaMercadoria, ItemEntrada,
    SaidaMercadoria, ItemSaida,
    MovimentacaoEstoque,
)


# ─── Estrutura física ──────────────────────────────────────────────────────────

class CorredorInline(admin.TabularInline):
    model  = Corredor
    extra  = 0
    fields = ["codigo"]


@admin.register(Armazem)
class ArmazemAdmin(admin.ModelAdmin):
    list_display  = ["codigo", "nome", "empresa", "filial", "ativo"]
    list_filter   = ["ativo", "empresa"]
    search_fields = ["codigo", "nome"]
    ordering      = ["nome"]
    inlines       = [CorredorInline]


@admin.register(Posicao)
class PosicaoAdmin(admin.ModelAdmin):
    list_display  = ["codigo", "armazem_codigo", "saldo_badge", "ativo"]
    list_filter   = ["ativo", "nivel__bay__corredor__armazem"]
    search_fields = ["codigo"]
    ordering      = ["codigo"]
    readonly_fields = ["codigo", "saldo_atual"]

    @admin.display(description="Armazém")
    def armazem_codigo(self, obj):
        return obj.nivel.bay.corredor.armazem.codigo

    @admin.display(description="Saldo")
    def saldo_badge(self, obj):
        saldo = obj.saldo_atual
        cor = "green" if saldo > 0 else ("#888" if saldo == 0 else "red")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>', cor, saldo
        )


# ─── Produtos ─────────────────────────────────────────────────────────────────

@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display  = ["sku", "descricao", "unidade", "empresa", "ativo"]
    list_filter   = ["ativo", "unidade", "empresa"]
    search_fields = ["sku", "descricao"]
    ordering      = ["descricao"]
    readonly_fields = ["created_at"]


# ─── Entradas de Mercadoria ───────────────────────────────────────────────────

class ItemEntradaInline(admin.TabularInline):
    model         = ItemEntrada
    extra         = 0
    fields        = [
        "produto", "posicao",
        "quantidade_esperada", "quantidade_conferida",
        "tem_divergencia_badge",
    ]
    readonly_fields = ["tem_divergencia_badge"]

    @admin.display(description="Divergência?")
    def tem_divergencia_badge(self, obj):
        if obj.tem_divergencia:
            return format_html('<span style="color:red;">⚠ Divergência</span>')
        if obj.quantidade_conferida is not None:
            return format_html('<span style="color:green;">✓ OK</span>')
        return "—"


@admin.register(EntradaMercadoria)
class EntradaMercadoriaAdmin(admin.ModelAdmin):
    list_display  = [
        "numero_nf", "fornecedor", "armazem",
        "status_badge", "chegada_em", "responsavel",
    ]
    list_filter   = ["status", "armazem__empresa", "armazem"]
    search_fields = ["numero_nf", "fornecedor"]
    ordering      = ["-chegada_em"]
    readonly_fields = ["created_at", "updated_at", "concluida_em"]
    inlines       = [ItemEntradaInline]

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "pendente":      "#888",
            "em_andamento":  "#f5a623",
            "concluido":     "green",
            "divergencia":   "red",
        }
        cor = cores.get(obj.status, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_status_display()
        )


# ─── Saídas de Mercadoria ─────────────────────────────────────────────────────

class ItemSaidaInline(admin.TabularInline):
    model  = ItemSaida
    extra  = 0
    fields = ["produto", "posicao", "quantidade"]


@admin.register(SaidaMercadoria)
class SaidaMercadoriaAdmin(admin.ModelAdmin):
    list_display  = [
        "numero_pedido", "destinatario", "armazem",
        "status_badge", "created_at", "expedida_em",
    ]
    list_filter   = ["status", "armazem__empresa", "armazem"]
    search_fields = ["numero_pedido", "destinatario"]
    ordering      = ["-created_at"]
    readonly_fields = ["created_at", "updated_at", "expedida_em"]
    inlines       = [ItemSaidaInline]

    @admin.display(description="Status")
    def status_badge(self, obj):
        cores = {
            "pendente":     "#888",
            "em_separacao": "#f5a623",
            "separado":     "#4a90d9",
            "expedido":     "green",
        }
        cor = cores.get(obj.status, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_status_display()
        )


# ─── Movimentação de Estoque (somente leitura) ────────────────────────────────

@admin.register(MovimentacaoEstoque)
class MovimentacaoEstoqueAdmin(admin.ModelAdmin):
    list_display  = [
        "tipo_badge", "produto", "quantidade_badge",
        "posicao", "usuario", "created_at",
    ]
    list_filter   = ["tipo", "posicao__nivel__bay__corredor__armazem"]
    search_fields = ["produto__sku", "produto__descricao"]
    ordering      = ["-created_at"]
    readonly_fields = [f.name for f in MovimentacaoEstoque._meta.get_fields()
                        if hasattr(f, "name")]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Tipo")
    def tipo_badge(self, obj):
        cores = {
            "entrada":      "green",
            "saida":        "red",
            "ajuste":       "#f5a623",
            "transferencia": "#4a90d9",
        }
        cor = cores.get(obj.tipo, "gray")
        return format_html(
            '<span style="color:{}; font-weight:bold;">{}</span>',
            cor, obj.get_tipo_display()
        )

    @admin.display(description="Quantidade")
    def quantidade_badge(self, obj):
        sinal = "+" if obj.quantidade > 0 else ""
        cor = "green" if obj.quantidade > 0 else "red"
        return format_html(
            '<span style="color:{};">{}{}</span>', cor, sinal, obj.quantidade
        )
