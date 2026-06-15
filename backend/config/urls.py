from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from apps.core import ui_views as core_ui_views

urlpatterns = [
    # Dashboard Principal
    path("", core_ui_views.dashboard, name="dashboard"),
    # Admin
    path("admin/", admin.site.urls),

    # JWT Auth
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/token/verify/", TokenVerifyView.as_view(), name="token_verify"),

    # Módulos (APIs)
    path("api/core/", include("apps.core.urls")),
    path("api/wms/", include("apps.wms.urls")),
    path("api/tms/", include("apps.tms.urls")),
    path("api/crm/", include("apps.crm.urls")),

    # Módulos (UI)
    path("wms/", include("apps.wms.ui_urls")),
    path("tms/", include("apps.tms.ui_urls")),
    path("crm/", include("apps.crm.ui_urls")),

    # OpenAPI / Swagger
    path("api/schema/",         SpectacularAPIView.as_view(),                          name="schema"),
    path("api/schema/swagger/", SpectacularSwaggerView.as_view(url_name="schema"),     name="swagger-ui"),
    path("api/schema/redoc/",   SpectacularRedocView.as_view(url_name="schema"),       name="redoc"),
]

from django.conf import settings
if settings.DEBUG:
    import debug_toolbar
    urlpatterns = [
        path('__debug__/', include(debug_toolbar.urls)),
    ] + urlpatterns
