from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    EmpresaViewSet, FilialViewSet, UsuarioViewSet,
    PerfilViewSet, PermissaoViewSet, AuditLogViewSet,
)

router = DefaultRouter()
router.register("empresas", EmpresaViewSet, basename="empresa")
router.register("filiais", FilialViewSet, basename="filial")
router.register("usuarios", UsuarioViewSet, basename="usuario")
router.register("perfis", PerfilViewSet, basename="perfil")
router.register("permissoes", PermissaoViewSet, basename="permissao")
router.register("audit", AuditLogViewSet, basename="audit")

urlpatterns = [
    path("", include(router.urls)),
]
