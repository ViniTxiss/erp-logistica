import pytest
from django.urls import reverse

pytestmark = pytest.mark.django_db

def test_dashboard_redirects_if_not_logged_in(client):
    url = reverse("dashboard")
    response = client.get(url)
    assert response.status_code == 302
    assert "/admin/login/" in response.url

def test_dashboard_renders_for_logged_in_user(client, usuario):
    client.force_login(usuario)
    url = reverse("dashboard")
    response = client.get(url)
    assert response.status_code == 200
    assert "core/dashboard.html" in [t.name for t in response.templates]
    assert "metrics" in response.context
    assert response.context["empresa_nome"] == usuario.empresa.razao_social
