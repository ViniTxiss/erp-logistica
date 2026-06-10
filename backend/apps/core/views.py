"""
Views do app Core — ViewSets DRF com RBAC integrado.
"""
from rest_framework import viewsets, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from .models import Empresa, Filial, Endereco, Usuario, Perfil, Permissao, AuditLog
from .serializers import (
    EmpresaSerializer, FilialSerializer, EnderecoSerializer,
    UsuarioSerializer, UsuarioCreateSerializer, UsuarioMeSerializer,
    PerfilSerializer, PermissaoSerializer, AuditLogSerializer,
)
from .permissions import require_permission


class EmpresaViewSet(viewsets.ModelViewSet):
    queryset = Empresa.objects.all()
    serializer_class = EmpresaSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get_queryset(self):
        # Não-admins veem apenas sua própria empresa
        user = self.request.user
        if user.is_superuser:
            return Empresa.objects.all()
        if user.empresa_id:
            return Empresa.objects.filter(id=user.empresa_id)
        return Empresa.objects.none()


class FilialViewSet(viewsets.ModelViewSet):
    serializer_class = FilialSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Filial.objects.select_related("empresa", "endereco").all()
        return Filial.objects.select_related("empresa", "endereco").filter(
            empresa=user.empresa
        )


class UsuarioViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return UsuarioCreateSerializer
        return UsuarioSerializer

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Usuario.objects.prefetch_related("perfis").all()
        return Usuario.objects.prefetch_related("perfis").filter(empresa=user.empresa)

    @action(detail=False, methods=["get"], url_path="me")
    def me(self, request):
        """GET /api/core/usuarios/me/ — retorna o usuário autenticado."""
        serializer = UsuarioMeSerializer(request.user, context={"request": request})
        return Response(serializer.data)

    @action(detail=True, methods=["post"], url_path="ativar")
    def ativar(self, request, pk=None):
        usuario = self.get_object()
        usuario.ativo = True
        usuario.save(update_fields=["ativo"])
        return Response({"status": "ativado"})

    @action(detail=True, methods=["post"], url_path="desativar")
    def desativar(self, request, pk=None):
        usuario = self.get_object()
        usuario.ativo = False
        usuario.save(update_fields=["ativo"])
        return Response({"status": "desativado"})


class PerfilViewSet(viewsets.ModelViewSet):
    serializer_class = PerfilSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        if user.is_superuser:
            return Perfil.objects.prefetch_related("permissoes").all()
        return Perfil.objects.prefetch_related("permissoes").filter(empresa=user.empresa)


class PermissaoViewSet(viewsets.ReadOnlyModelViewSet):
    """Permissões são somente leitura — criadas via migration/fixtures."""
    queryset = Permissao.objects.all()
    serializer_class = PermissaoSerializer
    permission_classes = [IsAuthenticated]


class AuditLogViewSet(viewsets.ReadOnlyModelViewSet):
    """AuditLog é read-only — nunca editável."""
    serializer_class = AuditLogSerializer
    permission_classes = [IsAuthenticated, require_permission("core.auditlog.ver")]

    def get_queryset(self):
        user = self.request.user
        qs = AuditLog.objects.select_related("usuario").all()
        if not user.is_superuser:
            qs = qs.filter(usuario__empresa=user.empresa)

        # Filtros opcionais via query params
        modulo = self.request.query_params.get("modulo")
        if modulo:
            qs = qs.filter(modulo=modulo)

        return qs.order_by("-created_at")
