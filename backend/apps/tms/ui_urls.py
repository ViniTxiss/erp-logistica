from django.urls import path
from . import ui_views

app_name = "tms_ui"

urlpatterns = [
    # Romaneios
    path("romaneios/", ui_views.romaneios_list, name="romaneios_list"),
    path("romaneios/criar/", ui_views.romaneio_criar, name="romaneio_criar"),
    path("romaneios/<uuid:pk>/", ui_views.romaneio_detalhe, name="romaneio_detalhe"),
    path("romaneios/<uuid:pk>/iniciar/", ui_views.romaneio_iniciar, name="romaneio_iniciar"),
    path("romaneios/<uuid:pk>/concluir/", ui_views.romaneio_concluir_ui, name="romaneio_concluir"),

    # Motoristas
    path("motoristas/", ui_views.motoristas_list, name="motoristas_list"),
    path("motoristas/criar/", ui_views.motorista_criar, name="motorista_criar"),

    # Entregas & Ocorrências
    path("itens/<uuid:item_id>/confirmar-entrega/", ui_views.item_confirmar_entrega, name="item_confirmar_entrega"),
    path("romaneios/<uuid:romaneio_id>/ocorrencia/registrar/", ui_views.ocorrencia_registrar, name="ocorrencia_registrar"),
]
