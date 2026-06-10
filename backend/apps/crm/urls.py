"""
URLs do app CRM.

Endpoints disponíveis:
  GET/POST        /api/crm/clientes/
  GET/PUT/PATCH   /api/crm/clientes/<id>/
  GET             /api/crm/clientes/<id>/contatos/
  GET             /api/crm/clientes/<id>/oportunidades/
  GET             /api/crm/clientes/<id>/historico/
  GET             /api/crm/clientes/<id>/contrato/

  GET/POST        /api/crm/contatos/         (?cliente= ?ativo= ?decisor=)
  GET/PUT/PATCH   /api/crm/contatos/<id>/

  GET/POST        /api/crm/oportunidades/    (?cliente= ?etapa= ?responsavel=)
  GET/PUT/PATCH   /api/crm/oportunidades/<id>/
  POST            /api/crm/oportunidades/<id>/fechar-ganho/
  POST            /api/crm/oportunidades/<id>/fechar-perdido/

  GET/POST        /api/crm/historico/        (?cliente= ?oportunidade= ?tipo=)
  GET             /api/crm/historico/<id>/

  GET/POST        /api/crm/contratos/        (?cliente= ?ativo=)
  GET/PUT/PATCH   /api/crm/contratos/<id>/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    ClienteViewSet, ContatoViewSet,
    OportunidadeViewSet,
    HistoricoInteracaoViewSet,
    ContratoViewSet,
)

router = DefaultRouter()
router.register(r"clientes",     ClienteViewSet,            basename="cliente")
router.register(r"contatos",     ContatoViewSet,            basename="contato")
router.register(r"oportunidades", OportunidadeViewSet,      basename="oportunidade")
router.register(r"historico",    HistoricoInteracaoViewSet, basename="historico")
router.register(r"contratos",    ContratoViewSet,           basename="contrato")

urlpatterns = [
    path("", include(router.urls)),
]
