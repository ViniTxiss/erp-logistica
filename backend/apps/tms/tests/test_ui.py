import pytest
from django.urls import reverse
from apps.tms.models import Romaneio, Motorista

pytestmark = pytest.mark.django_db

def test_romaneios_list_view(client, usuario):
    client.force_login(usuario)
    url = reverse("tms_ui:romaneios_list")
    
    # Test GET renderiza template completo
    response = client.get(url)
    assert response.status_code == 200
    assert "tms/romaneios.html" in [t.name for t in response.templates]

    # Test GET HTMX renderiza partial
    response_htmx = client.get(url, HTTP_HX_REQUEST="true")
    assert response_htmx.status_code == 200
    assert "tms/partials/tabela_romaneios.html" in [t.name for t in response_htmx.templates]

def test_romaneio_criar_view(client, usuario, veiculo, motorista):
    client.force_login(usuario)
    url = reverse("tms_ui:romaneio_criar")
    
    data = {
        "numero": "ROM-12345",
        "veiculo_id": veiculo.id,
        "motorista_id": motorista.id,
        "previsao_saida": ""
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert "tms/partials/tabela_romaneios.html" in [t.name for t in response.templates]
    
    assert Romaneio.objects.filter(numero="ROM-12345", empresa=usuario.empresa).exists()

def test_motoristas_list_view(client, usuario):
    client.force_login(usuario)
    url = reverse("tms_ui:motoristas_list")
    
    response = client.get(url)
    assert response.status_code == 200
    assert "tms/motoristas.html" in [t.name for t in response.templates]

    response_htmx = client.get(url, HTTP_HX_REQUEST="true")
    assert response_htmx.status_code == 200
    assert "tms/partials/tabela_motoristas.html" in [t.name for t in response_htmx.templates]

def test_motorista_criar_view(client, usuario):
    client.force_login(usuario)
    url = reverse("tms_ui:motorista_criar")
    
    data = {
        "nome": "João Caminhoneiro",
        "cnh": "123456789",
        "telefone": "11999999999"
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert "tms/partials/tabela_motoristas.html" in [t.name for t in response.templates]
    
    assert Motorista.objects.filter(nome="João Caminhoneiro", empresa=usuario.empresa).exists()
