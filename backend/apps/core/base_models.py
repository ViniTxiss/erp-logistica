"""
TenantModel — modelo abstrato base para todas as entidades multi-tenant.
Herdar no lugar de models.Model nos apps WMS, TMS e CRM.
"""
from django.db import models
from .managers import TenantManager


class TenantModel(models.Model):
    """
    Modelo base que garante:
    - TenantManager como manager padrão
    - created_at / updated_at automáticos
    Subclasses devem definir seu próprio campo ForeignKey 'empresa' para personalizar related_name.
    """
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = TenantManager()

    class Meta:
        abstract = True
