from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ArmazemViewSet, PosicaoViewSet, ProdutoViewSet,
    EntradaMercadoriaViewSet, SaidaMercadoriaViewSet,
    MovimentacaoEstoqueViewSet,
)

router = DefaultRouter()
router.register("armazens", ArmazemViewSet, basename="armazem")
router.register("posicoes", PosicaoViewSet, basename="posicao")
router.register("produtos", ProdutoViewSet, basename="produto")
router.register("entradas", EntradaMercadoriaViewSet, basename="entrada")
router.register("saidas", SaidaMercadoriaViewSet, basename="saida")
router.register("movimentacoes", MovimentacaoEstoqueViewSet, basename="movimentacao")

urlpatterns = [
    path("", include(router.urls)),
]
