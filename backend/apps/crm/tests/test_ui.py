import pytest
from django.urls import reverse
from apps.crm.models import Cliente, Oportunidade

pytestmark = pytest.mark.django_db

def test_clientes_list_view(client, usuario):
    client.force_login(usuario)
    url = reverse("crm_ui:clientes_list")
    
    response = client.get(url)
    assert response.status_code == 200
    assert "crm/clientes.html" in [t.name for t in response.templates]

    response_htmx = client.get(url, HTTP_HX_REQUEST="true")
    assert response_htmx.status_code == 200
    assert "crm/partials/tabela_clientes.html" in [t.name for t in response_htmx.templates]

def test_cliente_criar_view(client, usuario):
    client.force_login(usuario)
    url = reverse("crm_ui:cliente_criar")
    
    data = {
        "razao_social": "Cliente Novo SA",
        "cnpj": "12.345.678/0001-99",
        "segmento": "industria",
        "email": "contato@clientenovo.com",
        "telefone": "11988888888"
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert "crm/partials/tabela_clientes.html" in [t.name for t in response.templates]
    
    assert Cliente.objects.filter(razao_social="Cliente Novo SA", empresa=usuario.empresa).exists()

def test_oportunidades_list_view(client, usuario):
    client.force_login(usuario)
    url = reverse("crm_ui:oportunidades_list")
    
    response = client.get(url)
    assert response.status_code == 200
    assert "crm/oportunidades.html" in [t.name for t in response.templates]

    response_htmx = client.get(url, HTTP_HX_REQUEST="true")
    assert response_htmx.status_code == 200
    assert "crm/partials/kanban_oportunidades.html" in [t.name for t in response_htmx.templates]

def test_oportunidade_criar_view(client, usuario, cliente_crm):
    client.force_login(usuario)
    url = reverse("crm_ui:oportunidade_criar")
    
    data = {
        "cliente_id": cliente_crm.id,
        "titulo": "Novo Negócio",
        "servico": "ambos",
        "valor_estimado": "10000.50"
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert "crm/partials/kanban_oportunidades.html" in [t.name for t in response.templates]
    
    assert Oportunidade.objects.filter(titulo="Novo Negócio", cliente=cliente_crm).exists()
