from django.urls import path
from . import ui_views

app_name = "crm_ui"

urlpatterns = [
    # Clientes
    path("clientes/", ui_views.clientes_list, name="clientes_list"),
    path("clientes/criar/", ui_views.cliente_criar, name="cliente_criar"),

    # Oportunidades
    path("oportunidades/", ui_views.oportunidades_list, name="oportunidades_list"),
    path("oportunidades/criar/", ui_views.oportunidade_criar, name="oportunidade_criar"),
]
