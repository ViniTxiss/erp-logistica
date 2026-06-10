"""
URLs do app TMS.

Endpoints disponíveis:
  GET/POST       /api/tms/veiculos/
  GET/PUT/PATCH  /api/tms/veiculos/<id>/

  GET/POST       /api/tms/motoristas/
  GET/PUT/PATCH  /api/tms/motoristas/<id>/

  GET/POST       /api/tms/romaneios/
  GET/PUT/PATCH  /api/tms/romaneios/<id>/
  POST           /api/tms/romaneios/<id>/iniciar-rota/
  POST           /api/tms/romaneios/<id>/concluir/
  POST           /api/tms/romaneios/<id>/cancelar/
  GET            /api/tms/romaneios/<id>/ocorrencias/

  GET/POST       /api/tms/itens-romaneio/       (?romaneio=<uuid>)
  GET/PUT/PATCH  /api/tms/itens-romaneio/<id>/

  GET/POST       /api/tms/ocorrencias/           (?romaneio=<uuid>)
  GET            /api/tms/ocorrencias/<id>/

  GET/POST       /api/tms/pods/                  (?item=<uuid> | ?romaneio=<uuid>)
  GET            /api/tms/pods/<id>/
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    VeiculoViewSet, MotoristaViewSet,
    RomaneioViewSet, ItemRomaneioViewSet,
    OcorrenciaViewSet, PODViewSet,
)

router = DefaultRouter()
router.register(r"veiculos",        VeiculoViewSet,       basename="veiculo")
router.register(r"motoristas",      MotoristaViewSet,     basename="motorista")
router.register(r"romaneios",       RomaneioViewSet,      basename="romaneio")
router.register(r"itens-romaneio",  ItemRomaneioViewSet,  basename="itemromaneio")
router.register(r"ocorrencias",     OcorrenciaViewSet,    basename="ocorrencia")
router.register(r"pods",            PODViewSet,           basename="pod")

urlpatterns = [
    path("", include(router.urls)),
]
