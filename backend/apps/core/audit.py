"""
Middleware de AuditLog — registra automaticamente ações de escrita na API.
"""
import json
import logging
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)

AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
AUDIT_SKIP_PATHS = {"/api/token/", "/api/token/refresh/", "/api/token/verify/"}


class AuditLogMiddleware(MiddlewareMixin):
    """
    Intercepta respostas de sucesso em métodos de escrita e persiste no AuditLog.
    Adicionar em MIDDLEWARE após AuthenticationMiddleware.
    """

    def process_response(self, request, response):
        if request.method not in AUDIT_METHODS:
            return response

        if request.path in AUDIT_SKIP_PATHS:
            return response

        if response.status_code >= 400:
            return response

        user = getattr(request, "user", None)
        if not user or not user.is_authenticated:
            return response

        try:
            from .models import AuditLog

            # Extrai módulo da URL: /api/wms/entradas/ → modulo="wms"
            path_parts = request.path.strip("/").split("/")
            modulo = path_parts[1] if len(path_parts) > 1 else "desconhecido"

            # Tenta parsear o body
            payload = None
            if request.content_type == "application/json":
                try:
                    payload = json.loads(request.body.decode("utf-8"))
                except Exception:
                    pass

            AuditLog.objects.create(
                usuario=user,
                modulo=modulo,
                acao=request.method,
                objeto_tipo=request.path,
                payload_depois=payload,
                ip=_get_client_ip(request),
            )
        except Exception as e:
            # AuditLog nunca deve travar a resposta
            logger.error("AuditLog middleware error: %s", e)

        return response


def _get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        return x_forwarded_for.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def audit(usuario, modulo: str, acao: str, objeto_tipo: str, objeto_id=None,
          payload_antes=None, payload_depois=None, ip: str = None):
    """
    Helper para criar AuditLog manualmente dentro de uma view ou service.

    Uso:
        audit(request.user, "wms", "entrada.criar", "EntradaMercadoria",
              objeto_id=entrada.id, payload_depois={"nf": "041823"})
    """
    from .models import AuditLog
    AuditLog.objects.create(
        usuario=usuario,
        modulo=modulo,
        acao=acao,
        objeto_tipo=objeto_tipo,
        objeto_id=objeto_id,
        payload_antes=payload_antes,
        payload_depois=payload_depois,
        ip=ip,
    )
