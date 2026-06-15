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
        "cpf": "123.456.789-00",
        "cnh": "123456789",
        "categoria_cnh": "D",
        "validade_cnh": "2030-12-31",
        "telefone": "11999999999"
    }
    
    response = client.post(url, data)
    assert response.status_code == 200
    assert "tms/partials/tabela_motoristas.html" in [t.name for t in response.templates]
    
    assert Motorista.objects.filter(nome_completo="João Caminhoneiro", empresa=usuario.empresa).exists()


def test_romaneio_detalhe_view(client, usuario, veiculo, motorista):
    client.force_login(usuario)
    romaneio = Romaneio.objects.create(
        empresa=usuario.empresa,
        veiculo=veiculo,
        motorista=motorista,
        status="aberto"
    )
    url = reverse("tms_ui:romaneio_detalhe", kwargs={"pk": romaneio.id})
    response = client.get(url)
    assert response.status_code == 200
    assert "tms/romaneio_detalhe.html" in [t.name for t in response.templates]
    assert response.context["romaneio"] == romaneio


def test_romaneio_iniciar_rota(client, usuario, veiculo, motorista):
    client.force_login(usuario)
    romaneio = Romaneio.objects.create(
        empresa=usuario.empresa,
        veiculo=veiculo,
        motorista=motorista,
        status="aberto"
    )
    url = reverse("tms_ui:romaneio_iniciar", kwargs={"pk": romaneio.id})
    response = client.post(url)
    assert response.status_code == 302
    romaneio.refresh_from_db()
    assert romaneio.status == "em_rota"


def test_romaneio_concluir(client, usuario, veiculo, motorista):
    client.force_login(usuario)
    romaneio = Romaneio.objects.create(
        empresa=usuario.empresa,
        veiculo=veiculo,
        motorista=motorista,
        status="em_rota"
    )
    url = reverse("tms_ui:romaneio_concluir", kwargs={"pk": romaneio.id})
    response = client.post(url)
    assert response.status_code == 302
    romaneio.refresh_from_db()
    assert romaneio.status == "concluido"


def test_item_confirmar_entrega_workflow(client, usuario, veiculo, motorista):
    client.force_login(usuario)
    romaneio = Romaneio.objects.create(
        empresa=usuario.empresa,
        veiculo=veiculo,
        motorista=motorista,
        status="em_rota"
    )
    item = romaneio.itens.create(
        destinatario="Cliente Teste",
        cep="12345-678",
        logradouro="Rua Teste",
        numero_end="123",
        bairro="Bairro Teste",
        cidade="Cidade Teste",
        uf="SP",
        status_entrega="pendente"
    )
    
    url = reverse("tms_ui:item_confirmar_entrega", kwargs={"item_id": item.id})
    
    # GET modal form
    response_get = client.get(url)
    assert response_get.status_code == 200
    assert "tms/partials/modal_pod.html" in [t.name for t in response_get.templates]
    
    # POST register POD
    data = {
        "assinado_por": "Recebedor Fulano",
        "observacao": "Sem observações",
        "latitude": "-23.5505",
        "longitude": "-46.6333"
    }
    response_post = client.post(url, data, HTTP_HX_REQUEST="true")
    assert response_post.status_code == 200
    assert "tms/partials/detalhes_itens.html" in [t.name for t in response_post.templates]
    
    item.refresh_from_db()
    assert item.status_entrega == "entregue"
    assert item.pod.assinado_por == "Recebedor Fulano"
    assert item.pod.latitude == -23.5505


def test_ocorrencia_registrar_workflow(client, usuario, veiculo, motorista):
    client.force_login(usuario)
    romaneio = Romaneio.objects.create(
        empresa=usuario.empresa,
        veiculo=veiculo,
        motorista=motorista,
        status="em_rota"
    )
    
    url = reverse("tms_ui:ocorrencia_registrar", kwargs={"romaneio_id": romaneio.id})
    
    # GET modal form
    response_get = client.get(url)
    assert response_get.status_code == 200
    assert "tms/partials/modal_ocorrencia.html" in [t.name for t in response_get.templates]
    
    # POST occurrence
    data = {
        "tipo": "atraso",
        "descricao": "Chuva forte causou atraso na entrega.",
        "item_id": ""
    }
    response_post = client.post(url, data, HTTP_HX_REQUEST="true")
    assert response_post.status_code == 200
    
    romaneio.refresh_from_db()
    assert romaneio.status == "com_ocorrencia"
    assert romaneio.ocorrencias.filter(tipo="atraso").exists()
