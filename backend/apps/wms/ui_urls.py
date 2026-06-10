from django.urls import path
from . import ui_views

app_name = "wms_ui"

urlpatterns = [
    path("recebimentos/", ui_views.recebimentos_list, name="recebimentos_list"),
    path("recebimentos/criar/", ui_views.recebimento_criar, name="recebimento_criar"),
]
