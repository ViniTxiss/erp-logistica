from django.contrib import admin
from .models import (
    Empresa, Filial, Endereco, Usuario,
    Perfil, Permissao, PerfilUsuario, PerfilPermissao, AuditLog,
)


@admin.register(Empresa)
class EmpresaAdmin(admin.ModelAdmin):
    list_display = ["razao_social", "cnpj", "email_principal", "ativo", "created_at"]
    list_filter = ["ativo"]
    search_fields = ["razao_social", "cnpj"]


@admin.register(Filial)
class FilialAdmin(admin.ModelAdmin):
    list_display = ["nome", "cnpj", "empresa", "matriz", "ativa"]
    list_filter = ["ativa", "matriz", "empresa"]
    search_fields = ["nome", "cnpj"]
    raw_id_fields = ["empresa", "endereco"]


@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = ["logradouro", "numero", "cidade", "uf", "cep"]
    search_fields = ["cep", "cidade", "logradouro"]


@admin.register(Permissao)
class PermissaoAdmin(admin.ModelAdmin):
    list_display = ["codigo", "modulo", "acao", "descricao"]
    list_filter = ["modulo"]
    search_fields = ["codigo", "descricao"]


@admin.register(Perfil)
class PerfilAdmin(admin.ModelAdmin):
    list_display = ["nome", "empresa", "sistema"]
    list_filter = ["sistema", "empresa"]
    search_fields = ["nome"]
    # filter_horizontal não funciona com M2M que tem through explícito
    # Gerencie via PerfilPermissaoAdmin ou inline


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ["nome_completo", "email", "empresa", "filial", "ativo", "is_staff"]
    list_filter = ["ativo", "is_staff", "empresa"]
    search_fields = ["nome_completo", "email"]
    readonly_fields = ["created_at", "updated_at", "ultimo_login"]
    fieldsets = (
        ("Dados pessoais", {"fields": ("nome_completo", "email", "telefone", "cargo")}),
        ("Empresa", {"fields": ("empresa", "filial")}),
        ("Acesso", {"fields": ("ativo", "is_staff", "is_superuser")}),
        ("Datas", {"fields": ("created_at", "updated_at", "ultimo_login")}),
    )


@admin.register(PerfilUsuario)
class PerfilUsuarioAdmin(admin.ModelAdmin):
    list_display = ["usuario", "perfil", "valido_ate"]
    raw_id_fields = ["usuario", "perfil"]


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ["created_at", "usuario", "modulo", "acao", "objeto_tipo", "ip"]
    list_filter = ["modulo", "acao"]
    search_fields = ["usuario__email", "objeto_tipo"]
    readonly_fields = [f.name for f in AuditLog._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
