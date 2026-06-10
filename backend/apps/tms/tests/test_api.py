"""
Testes de integração da API REST do módulo TMS.
Usa APIClient autenticado via JWT.
"""
import pytest
from django.urls import reverse

from apps.tms.models import (
    Romaneio, StatusRomaneio,
    Veiculo, StatusVeiculo,
    ItemRomaneio, StatusEntregaItem,
    Ocorrencia, POD,
)


pytestmark = pytest.mark.django_db


# ─── helpers ──────────────────────────────────────────────────────────────────

def url(name, **kwargs):
    return reverse(name, kwargs=kwargs if kwargs else None)


# ─── Veículos ─────────────────────────────────────────────────────────────────

class TestVeiculoAPI:

    def test_listar_veiculos(self, auth_client, veiculo):
        res = auth_client.get("/api/tms/veiculos/")
        assert res.status_code == 200
        assert res.data["count"] == 1
        assert res.data["results"][0]["placa"] == veiculo.placa

    def test_nao_lista_veiculos_de_outra_empresa(self, auth_client, usuario):
        from conftest import VeiculoFactory, EmpresaFactory
        outra = EmpresaFactory()
        VeiculoFactory(empresa=outra, placa="OUT0001")
        res = auth_client.get("/api/tms/veiculos/")
        assert res.status_code == 200
        assert res.data["count"] == 0

    def test_criar_veiculo(self, auth_client, empresa):
        payload = {
            "empresa": str(empresa.id),
            "placa": "NEW0001",
            "tipo": "proprio",
            "modelo": "Sprinter",
            "capacidade_kg": "500.00",
        }
        res = auth_client.post("/api/tms/veiculos/", payload, format="json")
        assert res.status_code == 201
        assert Veiculo.objects.filter(placa="NEW0001").exists()

    def test_filtrar_por_status(self, auth_client, veiculo):
        res = auth_client.get("/api/tms/veiculos/?status=disponivel")
        assert res.status_code == 200
        assert res.data["count"] == 1

        res2 = auth_client.get("/api/tms/veiculos/?status=em_rota")
        assert res2.data["count"] == 0

    def test_filtrar_por_tipo(self, auth_client, veiculo):
        res = auth_client.get(f"/api/tms/veiculos/?tipo={veiculo.tipo}")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_detalhe_veiculo(self, auth_client, veiculo):
        res = auth_client.get(f"/api/tms/veiculos/{veiculo.id}/")
        assert res.status_code == 200
        assert res.data["placa"] == veiculo.placa
        assert "tipo_display" in res.data
        assert "status_display" in res.data

    def test_nao_autenticado_retorna_401(self, api_client, veiculo):
        res = api_client.get("/api/tms/veiculos/")
        assert res.status_code == 401


# ─── Motoristas ───────────────────────────────────────────────────────────────

class TestMotoristaAPI:

    def test_listar_motoristas(self, auth_client, motorista):
        res = auth_client.get("/api/tms/motoristas/")
        assert res.status_code == 200
        assert res.data["count"] == 1

    def test_nao_lista_motoristas_de_outra_empresa(self, auth_client):
        from conftest import MotoristaFactory, EmpresaFactory
        outra = EmpresaFactory()
        MotoristaFactory(empresa=outra)
        res = auth_client.get("/api/tms/motoristas/")
        assert res.data["count"] == 0

    def test_criar_motorista(self, auth_client, empresa):
        from datetime import date
        payload = {
            "empresa": str(empresa.id),
            "nome_completo": "Carlos Souza",
            "cpf": "99988877766",
            "cnh": "12345678901",
            "categoria_cnh": "E",
            "validade_cnh": str(date.today().replace(year=date.today().year + 2)),
            "telefone": "(11) 91234-5678",
        }
        res = auth_client.post("/api/tms/motoristas/", payload, format="json")
        assert res.status_code == 201
        assert res.data["nome_completo"] == "Carlos Souza"

    def test_detalhe_motorista(self, auth_client, motorista):
        res = auth_client.get(f"/api/tms/motoristas/{motorista.id}/")
        assert res.status_code == 200
        assert res.data["cnh"] == motorista.cnh
        assert "categoria_display" in res.data


# ─── Romaneios ────────────────────────────────────────────────────────────────

class TestRomaneioAPI:

    def test_listar_retorna_serializer_leve(self, auth_client, romaneio):
        res = auth_client.get("/api/tms/romaneios/")
        assert res.status_code == 200
        assert res.data["count"] == 1
        data = res.data["results"][0]
        # Versão leve não contém itens aninhados
        assert "itens" not in data
        assert "numero" in data
        assert "status_display" in data
        assert "veiculo_placa" in data
        assert "motorista_nome" in data
        assert "total_itens" in data
        assert "itens_entregues" in data

    def test_detalhe_retorna_itens(self, auth_client, romaneio):
        from conftest import ItemRomaneioFactory
        ItemRomaneioFactory(romaneio=romaneio)
        res = auth_client.get(f"/api/tms/romaneios/{romaneio.id}/")
        assert res.status_code == 200
        assert "itens" in res.data
        assert len(res.data["itens"]) == 1

    def test_criar_romaneio(self, auth_client, empresa, veiculo, motorista):
        from django.utils import timezone
        payload = {
            "empresa": str(empresa.id),
            "veiculo": str(veiculo.id),
            "motorista": str(motorista.id),
            "data_saida_prevista": timezone.now().isoformat(),
            "observacoes": "Rota do dia",
        }
        res = auth_client.post("/api/tms/romaneios/", payload, format="json")
        assert res.status_code == 201
        assert res.data["status"] == "aberto"
        assert res.data["numero"] != ""

    def test_filtrar_por_status(self, auth_client, romaneio):
        res = auth_client.get("/api/tms/romaneios/?status=aberto")
        assert res.data["count"] == 1

        res2 = auth_client.get("/api/tms/romaneios/?status=concluido")
        assert res2.data["count"] == 0

    def test_filtrar_por_motorista(self, auth_client, romaneio, motorista):
        res = auth_client.get(f"/api/tms/romaneios/?motorista={motorista.id}")
        assert res.data["count"] == 1

    def test_isolamento_multi_tenant(self, auth_client):
        from conftest import RomaneioFactory, EmpresaFactory, VeiculoFactory, MotoristaFactory
        outra = EmpresaFactory()
        RomaneioFactory(
            empresa=outra,
            veiculo=VeiculoFactory(empresa=outra),
            motorista=MotoristaFactory(empresa=outra),
        )
        res = auth_client.get("/api/tms/romaneios/")
        assert res.data["count"] == 0


# ─── Action: iniciar-rota ─────────────────────────────────────────────────────

class TestIniciarRota:

    def test_iniciar_rota_sucesso(self, auth_client, romaneio, veiculo):
        res = auth_client.post(f"/api/tms/romaneios/{romaneio.id}/iniciar-rota/")
        assert res.status_code == 200
        assert res.data["status"] == "em_rota"
        assert res.data["data_saida_real"] is not None

        veiculo.refresh_from_db()
        assert veiculo.status == StatusVeiculo.EM_ROTA

    def test_iniciar_rota_ja_em_rota_retorna_400(self, auth_client, romaneio_em_rota):
        res = auth_client.post(f"/api/tms/romaneios/{romaneio_em_rota.id}/iniciar-rota/")
        assert res.status_code == 400
        assert "erro" in res.data

    def test_iniciar_rota_de_outra_empresa_retorna_404(self, auth_client):
        from conftest import RomaneioFactory, EmpresaFactory, VeiculoFactory, MotoristaFactory
        outra = EmpresaFactory()
        rom_outra = RomaneioFactory(
            empresa=outra,
            veiculo=VeiculoFactory(empresa=outra),
            motorista=MotoristaFactory(empresa=outra),
        )
        res = auth_client.post(f"/api/tms/romaneios/{rom_outra.id}/iniciar-rota/")
        assert res.status_code == 404


# ─── Action: concluir ─────────────────────────────────────────────────────────

class TestConcluir:

    def test_concluir_sucesso(self, auth_client, romaneio_em_rota, veiculo):
        res = auth_client.post(f"/api/tms/romaneios/{romaneio_em_rota.id}/concluir/")
        assert res.status_code == 200
        assert res.data["status"] == "concluido"
        assert res.data["data_conclusao"] is not None

        veiculo.refresh_from_db()
        assert veiculo.status == StatusVeiculo.DISPONIVEL

    def test_concluir_romaneio_aberto_retorna_400(self, auth_client, romaneio):
        res = auth_client.post(f"/api/tms/romaneios/{romaneio.id}/concluir/")
        assert res.status_code == 400

    def test_concluir_com_ocorrencia_funciona(self, auth_client, romaneio_em_rota, usuario):
        # Cria ocorrência → muda status para com_ocorrencia
        Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            tipo="atraso",
            descricao="Problema no trânsito",
        )
        romaneio_em_rota.refresh_from_db()
        assert romaneio_em_rota.status == StatusRomaneio.COM_OCORRENCIA

        res = auth_client.post(f"/api/tms/romaneios/{romaneio_em_rota.id}/concluir/")
        assert res.status_code == 200
        assert res.data["status"] == "concluido"


# ─── Action: cancelar ─────────────────────────────────────────────────────────

class TestCancelar:

    def test_cancelar_romaneio_aberto(self, auth_client, romaneio):
        res = auth_client.post(f"/api/tms/romaneios/{romaneio.id}/cancelar/")
        assert res.status_code == 200
        assert res.data["status"] == "cancelado"

    def test_cancelar_romaneio_concluido_retorna_400(self, auth_client, romaneio_em_rota):
        auth_client.post(f"/api/tms/romaneios/{romaneio_em_rota.id}/concluir/")
        res = auth_client.post(f"/api/tms/romaneios/{romaneio_em_rota.id}/cancelar/")
        assert res.status_code == 400


# ─── Action: listar ocorrências ───────────────────────────────────────────────

class TestListarOcorrencias:

    def test_listar_ocorrencias_do_romaneio(self, auth_client, romaneio_em_rota):
        Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            tipo="atraso",
            descricao="Trânsito",
        )
        Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            tipo="avaria",
            descricao="Caixa amassada",
        )
        res = auth_client.get(f"/api/tms/romaneios/{romaneio_em_rota.id}/ocorrencias/")
        assert res.status_code == 200
        assert len(res.data) == 2

    def test_ocorrencias_vazias_retorna_lista_vazia(self, auth_client, romaneio):
        res = auth_client.get(f"/api/tms/romaneios/{romaneio.id}/ocorrencias/")
        assert res.status_code == 200
        assert res.data == []


# ─── Itens de Romaneio ────────────────────────────────────────────────────────

class TestItemRomaneioAPI:

    def test_listar_itens_por_romaneio(self, auth_client, romaneio):
        from conftest import ItemRomaneioFactory
        ItemRomaneioFactory(romaneio=romaneio)
        ItemRomaneioFactory(romaneio=romaneio)
        res = auth_client.get(f"/api/tms/itens-romaneio/?romaneio={romaneio.id}")
        assert res.status_code == 200
        assert res.data["count"] == 2

    def test_criar_item_romaneio(self, auth_client, romaneio):
        payload = {
            "romaneio": str(romaneio.id),
            "destinatario": "Empresa ABC Ltda",
            "logradouro": "Av. Paulista",
            "numero_end": "1000",
            "bairro": "Bela Vista",
            "cidade": "São Paulo",
            "uf": "SP",
            "cep": "01310-100",
            "ordem_entrega": 1,
        }
        res = auth_client.post("/api/tms/itens-romaneio/", payload, format="json")
        assert res.status_code == 201
        assert res.data["destinatario"] == "Empresa ABC Ltda"
        assert res.data["status_entrega"] == "pendente"
        assert res.data["tem_pod"] is False

    def test_filtrar_por_status_entrega(self, auth_client, romaneio):
        from conftest import ItemRomaneioFactory
        item1 = ItemRomaneioFactory(romaneio=romaneio, status_entrega=StatusEntregaItem.PENDENTE)
        item2 = ItemRomaneioFactory(romaneio=romaneio, status_entrega=StatusEntregaItem.ENTREGUE)

        res = auth_client.get("/api/tms/itens-romaneio/?status_entrega=pendente")
        assert res.data["count"] == 1

    def test_item_de_outra_empresa_nao_visivel(self, auth_client):
        from conftest import ItemRomaneioFactory, RomaneioFactory, EmpresaFactory, VeiculoFactory, MotoristaFactory
        outra = EmpresaFactory()
        rom_outra = RomaneioFactory(
            empresa=outra,
            veiculo=VeiculoFactory(empresa=outra),
            motorista=MotoristaFactory(empresa=outra),
        )
        ItemRomaneioFactory(romaneio=rom_outra)
        res = auth_client.get("/api/tms/itens-romaneio/")
        assert res.data["count"] == 0


# ─── Ocorrências ─────────────────────────────────────────────────────────────

class TestOcorrenciaAPI:

    def test_criar_ocorrencia(self, auth_client, romaneio_em_rota):
        payload = {
            "romaneio": str(romaneio_em_rota.id),
            "tipo": "atraso",
            "descricao": "Congestionamento na rodovia",
        }
        res = auth_client.post("/api/tms/ocorrencias/", payload, format="json")
        assert res.status_code == 201
        assert res.data["tipo"] == "atraso"
        assert res.data["registrado_por"] is not None  # preenchido automaticamente pela view

        # Romaneio muda para com_ocorrencia
        romaneio_em_rota.refresh_from_db()
        assert romaneio_em_rota.status == StatusRomaneio.COM_OCORRENCIA

    def test_nao_permite_put_patch_delete(self, auth_client, romaneio_em_rota):
        oc = Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            tipo="outro",
            descricao="Teste",
        )
        assert auth_client.put(f"/api/tms/ocorrencias/{oc.id}/").status_code == 405
        assert auth_client.patch(f"/api/tms/ocorrencias/{oc.id}/").status_code == 405
        assert auth_client.delete(f"/api/tms/ocorrencias/{oc.id}/").status_code == 405

    def test_filtrar_por_romaneio(self, auth_client, romaneio_em_rota):
        from conftest import RomaneioFactory
        Ocorrencia.objects.create(romaneio=romaneio_em_rota, tipo="atraso", descricao="A")
        # Outra ocorrência em outro romaneio
        outro_rom = Romaneio.objects.create(
            empresa=romaneio_em_rota.empresa,
            status=StatusRomaneio.EM_ROTA,
        )
        Ocorrencia.objects.create(romaneio=outro_rom, tipo="avaria", descricao="B")

        res = auth_client.get(f"/api/tms/ocorrencias/?romaneio={romaneio_em_rota.id}")
        assert res.data["count"] == 1


# ─── POD ─────────────────────────────────────────────────────────────────────

class TestPODAPI:

    def test_criar_pod(self, auth_client, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        payload = {
            "item": str(item.id),
            "assinado_por": "Pedro Alves",
            "observacao": "Recebido na portaria",
            "latitude": -23.5505,
            "longitude": -46.6333,
        }
        res = auth_client.post("/api/tms/pods/", payload, format="json")
        assert res.status_code == 201
        assert res.data["assinado_por"] == "Pedro Alves"
        assert res.data["item_destinatario"] == item.destinatario

        # Item marcado como entregue automaticamente
        item.refresh_from_db()
        assert item.status_entrega == StatusEntregaItem.ENTREGUE

    def test_nao_permite_put_patch_delete(self, auth_client, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        pod = POD.objects.create(item=item, assinado_por="Ana")
        assert auth_client.put(f"/api/tms/pods/{pod.id}/").status_code == 405
        assert auth_client.patch(f"/api/tms/pods/{pod.id}/").status_code == 405
        assert auth_client.delete(f"/api/tms/pods/{pod.id}/").status_code == 405

    def test_filtrar_pods_por_romaneio(self, auth_client, romaneio):
        from conftest import ItemRomaneioFactory
        item1 = ItemRomaneioFactory(romaneio=romaneio)
        item2 = ItemRomaneioFactory(romaneio=romaneio)
        POD.objects.create(item=item1, assinado_por="A")
        POD.objects.create(item=item2, assinado_por="B")
        res = auth_client.get(f"/api/tms/pods/?romaneio={romaneio.id}")
        assert res.data["count"] == 2

    def test_pod_de_outra_empresa_nao_visivel(self, auth_client):
        from conftest import (ItemRomaneioFactory, RomaneioFactory,
                               EmpresaFactory, VeiculoFactory, MotoristaFactory)
        outra = EmpresaFactory()
        rom_outra = RomaneioFactory(
            empresa=outra,
            veiculo=VeiculoFactory(empresa=outra),
            motorista=MotoristaFactory(empresa=outra),
        )
        item = ItemRomaneioFactory(romaneio=rom_outra)
        POD.objects.create(item=item, assinado_por="X")
        res = auth_client.get("/api/tms/pods/")
        assert res.data["count"] == 0
