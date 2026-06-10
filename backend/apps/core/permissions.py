"""
Permissões customizadas do app Core — RBAC por código de permissão.
"""
from rest_framework.permissions import BasePermission


class HasModulePermission(BasePermission):
    """
    Uso nas views:
        permission_classes = [IsAuthenticated, HasModulePermission]
        required_permission = "wms.entrada.criar"

    Ou passando o código diretamente via fábrica:
        permission_classes = [IsAuthenticated, require_permission("wms.entrada.criar")]
    """
    required_permission: str = ""

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        # Pega o código da view ou do atributo da classe
        code = getattr(view, "required_permission", self.required_permission)
        if not code:
            return True  # sem código definido → só requer autenticação
        return request.user.tem_permissao(code)


def require_permission(code: str):
    """
    Fábrica de permissão. Uso:
        permission_classes = [IsAuthenticated, require_permission("wms.entrada.criar")]
    """
    return type(
        f"Perm_{code.replace('.', '_')}",
        (HasModulePermission,),
        {"required_permission": code},
    )
