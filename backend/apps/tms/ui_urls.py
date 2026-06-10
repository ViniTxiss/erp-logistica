from django.urls import path
from . import ui_views

app_name = "tms_ui"

urlpatterns = [
    # Romaneios
    path("romaneios/", ui_views.romaneios_list, name="romaneios_list"),
    path("romaneios/criar/", ui_views.romaneio_criar, name="romaneio_criar"),

    # Motoristas
    path("motoristas/", ui_views.motoristas_list, name="motoristas_list"),
    path("motoristas/criar/", ui_views.motorista_criar, name="motorista_criar"),
]
