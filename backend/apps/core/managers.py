"""
TenantManager — garante isolamento automático por empresa em todas as queries.
Usar como manager padrão em models que têm FK para Empresa.
"""
from django.db import models


class TenantQuerySet(models.QuerySet):
    def para_empresa(self, empresa):
        """Filtra explicitamente por empresa. Usar quando empresa vem de fora do request."""
        return self.filter(empresa=empresa)


class TenantManager(models.Manager):
    """
    Manager que restringe automaticamente as queries à empresa do usuário logado.

    Uso nas models:
        objects = TenantManager()

    Nas views, usar sempre:
        Model.objects.para_request(request)
    """

    def get_queryset(self):
        return TenantQuerySet(self.model, using=self._db)

    def para_request(self, request):
        """
        Atalho principal para uso nas views.
        Retorna QuerySet filtrado pela empresa do usuário autenticado.
        """
        empresa = getattr(request.user, "empresa", None)
        if empresa is None:
            # Superuser ou usuário sem empresa: em desenvolvimento/admin pode ver tudo
            return self.get_queryset()
        return self.get_queryset().filter(empresa=empresa)
