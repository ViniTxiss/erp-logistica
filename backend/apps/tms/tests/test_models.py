"""
Testes unitários dos models do TMS.
Testam lógica de negócio pura, sem chamadas HTTP.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone

from apps.tms.models import (
    Romaneio, StatusRomaneio,
    Veiculo, StatusVeiculo,
    ItemRomaneio, StatusEntregaItem,
    Ocorrencia, TipoOcorrencia,
    POD,
)


pytestmark = pytest.mark.django_db


# ─── Veículo ──────────────────────────────────────────────────────────────────

class TestVeiculoModel:

    def test_criacao_basica(self, veiculo):
        assert veiculo.pk is not None
        assert veiculo.status == StatusVeiculo.DISPONIVEL
        assert veiculo.ativo is True

    def test_str(self, veiculo):
        resultado = str(veiculo)
        assert veiculo.placa in resultado
        assert "Disponível" in resultado

    def test_placa_unica_por_empresa(self, empresa):
        from conftest import VeiculoFactory
        v1 = VeiculoFactory(empresa=empresa, placa="AAA0001")
        with pytest.raises(Exception):  # IntegrityError ou ValidationError
            VeiculoFactory(empresa=empresa, placa="AAA0001")

    def test_mesma_placa_empresas_diferentes(self, empresa):
        from conftest import VeiculoFactory, EmpresaFactory
        outra = EmpresaFactory()
        v1 = VeiculoFactory(empresa=empresa, placa="BBB9999")
        v2 = VeiculoFactory(empresa=outra, placa="BBB9999")  # deve funcionar
        assert v1.pk != v2.pk


# ─── Motorista ────────────────────────────────────────────────────────────────

class TestMotoristaModel:

    def test_criacao_basica(self, motorista):
        assert motorista.pk is not None
        assert motorista.ativo is True

    def test_str(self, motorista):
        resultado = str(motorista)
        assert motorista.nome_completo in resultado
        assert motorista.cnh in resultado

    def test_cpf_unico_por_empresa(self, empresa):
        from conftest import MotoristaFactory
        MotoristaFactory(empresa=empresa, cpf="12345678901")
        with pytest.raises(Exception):
            MotoristaFactory(empresa=empresa, cpf="12345678901")


# ─── Romaneio — geração de número ─────────────────────────────────────────────

class TestRomaneioNumero:

    def test_numero_gerado_automaticamente(self, romaneio):
        assert romaneio.numero != ""
        assert romaneio.numero == "000001"

    def test_numero_sequencial(self, empresa, veiculo, motorista):
        from conftest import RomaneioFactory
        r1 = RomaneioFactory(empresa=empresa, veiculo=veiculo, motorista=motorista)
        r2 = RomaneioFactory(empresa=empresa, veiculo=veiculo, motorista=motorista)
        assert int(r2.numero) == int(r1.numero) + 1

    def test_numero_independente_por_empresa(self):
        from conftest import RomaneioFactory, EmpresaFactory, VeiculoFactory, MotoristaFactory
        emp_a = EmpresaFactory()
        emp_b = EmpresaFactory()
        r_a = RomaneioFactory(
            empresa=emp_a,
            veiculo=VeiculoFactory(empresa=emp_a),
            motorista=MotoristaFactory(empresa=emp_a),
        )
        r_b = RomaneioFactory(
            empresa=emp_b,
            veiculo=VeiculoFactory(empresa=emp_b),
            motorista=MotoristaFactory(empresa=emp_b),
        )
        # Ambos começam em 000001, isolados por empresa
        assert r_a.numero == "000001"
        assert r_b.numero == "000001"

    def test_str(self, romaneio):
        resultado = str(romaneio)
        assert romaneio.numero in resultado
        assert "Aberto" in resultado


# ─── Romaneio — ciclo de vida ─────────────────────────────────────────────────

class TestRomaneioIniciarRota:

    def test_iniciar_rota_muda_status(self, romaneio, usuario):
        romaneio.iniciar_rota(usuario=usuario)
        romaneio.refresh_from_db()
        assert romaneio.status == StatusRomaneio.EM_ROTA

    def test_iniciar_rota_registra_data_saida_real(self, romaneio, usuario):
        before = timezone.now()
        romaneio.iniciar_rota(usuario=usuario)
        romaneio.refresh_from_db()
        assert romaneio.data_saida_real is not None
        assert romaneio.data_saida_real >= before

    def test_iniciar_rota_muda_status_veiculo(self, romaneio, veiculo, usuario):
        romaneio.iniciar_rota(usuario=usuario)
        veiculo.refresh_from_db()
        assert veiculo.status == StatusVeiculo.EM_ROTA

    def test_iniciar_rota_falha_se_nao_aberto(self, romaneio_em_rota, usuario):
        with pytest.raises(ValueError, match="status atual"):
            romaneio_em_rota.iniciar_rota(usuario=usuario)

    def test_iniciar_rota_sem_veiculo_nao_falha(self, empresa, motorista, usuario):
        from conftest import RomaneioFactory
        rom = RomaneioFactory(empresa=empresa, veiculo=None, motorista=motorista)
        rom.iniciar_rota(usuario=usuario)  # não deve levantar exceção
        rom.refresh_from_db()
        assert rom.status == StatusRomaneio.EM_ROTA


class TestRomaneioConcluir:

    def test_concluir_muda_status(self, romaneio_em_rota, usuario):
        romaneio_em_rota.concluir(usuario=usuario)
        romaneio_em_rota.refresh_from_db()
        assert romaneio_em_rota.status == StatusRomaneio.CONCLUIDO

    def test_concluir_registra_data_conclusao(self, romaneio_em_rota, usuario):
        before = timezone.now()
        romaneio_em_rota.concluir(usuario=usuario)
        romaneio_em_rota.refresh_from_db()
        assert romaneio_em_rota.data_conclusao is not None
        assert romaneio_em_rota.data_conclusao >= before

    def test_concluir_libera_veiculo(self, romaneio_em_rota, veiculo, usuario):
        romaneio_em_rota.concluir(usuario=usuario)
        veiculo.refresh_from_db()
        assert veiculo.status == StatusVeiculo.DISPONIVEL

    def test_concluir_falha_se_aberto(self, romaneio, usuario):
        with pytest.raises(ValueError, match="status atual"):
            romaneio.concluir(usuario=usuario)

    def test_concluir_funciona_com_ocorrencia(self, romaneio_em_rota, usuario):
        """Romaneio com_ocorrencia também pode ser concluído."""
        Romaneio.objects.filter(pk=romaneio_em_rota.pk).update(
            status=StatusRomaneio.COM_OCORRENCIA
        )
        romaneio_em_rota.refresh_from_db()
        romaneio_em_rota.concluir(usuario=usuario)
        romaneio_em_rota.refresh_from_db()
        assert romaneio_em_rota.status == StatusRomaneio.CONCLUIDO


class TestRomaneioCancelar:

    def test_cancelar_muda_status(self, romaneio, usuario):
        romaneio.cancelar(usuario=usuario)
        romaneio.refresh_from_db()
        assert romaneio.status == StatusRomaneio.CANCELADO

    def test_cancelar_libera_veiculo(self, romaneio_em_rota, veiculo, usuario):
        romaneio_em_rota.cancelar(usuario=usuario)
        veiculo.refresh_from_db()
        assert veiculo.status == StatusVeiculo.DISPONIVEL

    def test_cancelar_falha_se_concluido(self, romaneio_em_rota, usuario):
        romaneio_em_rota.concluir(usuario=usuario)
        romaneio_em_rota.refresh_from_db()
        with pytest.raises(ValueError, match="concluído"):
            romaneio_em_rota.cancelar(usuario=usuario)


# ─── Ocorrência — efeito colateral no Romaneio ────────────────────────────────

class TestOcorrencia:

    def test_ocorrencia_muda_romaneio_para_com_ocorrencia(self, romaneio_em_rota, usuario):
        Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            tipo=TipoOcorrencia.ATRASO,
            descricao="Trânsito intenso",
            registrado_por=usuario,
        )
        romaneio_em_rota.refresh_from_db()
        assert romaneio_em_rota.status == StatusRomaneio.COM_OCORRENCIA

    def test_ocorrencia_nao_muda_status_se_nao_em_rota(self, romaneio, usuario):
        """Se o romaneio estiver ABERTO, a ocorrência é salva mas o status não muda."""
        Romaneio.objects.filter(pk=romaneio.pk).update(status=StatusRomaneio.ABERTO)
        romaneio.refresh_from_db()
        Ocorrencia.objects.create(
            romaneio=romaneio,
            tipo=TipoOcorrencia.OUTRO,
            descricao="Teste",
        )
        romaneio.refresh_from_db()
        # Permanece ABERTO (a lógica só age em EM_ROTA)
        assert romaneio.status == StatusRomaneio.ABERTO

    def test_ocorrencia_com_item_especifico(self, romaneio_em_rota, usuario):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio_em_rota)
        oc = Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            item=item,
            tipo=TipoOcorrencia.AVARIA,
            descricao="Caixa amassada",
            registrado_por=usuario,
        )
        assert oc.item == item

    def test_str(self, romaneio_em_rota):
        oc = Ocorrencia.objects.create(
            romaneio=romaneio_em_rota,
            tipo=TipoOcorrencia.ATRASO,
            descricao="Atraso no trânsito",
        )
        resultado = str(oc)
        assert "Atraso" in resultado


# ─── POD — Proof of Delivery ──────────────────────────────────────────────────

class TestPOD:

    def test_pod_marca_item_como_entregue(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        assert item.status_entrega == StatusEntregaItem.PENDENTE

        POD.objects.create(
            item=item,
            assinado_por="Maria Souza",
            observacao="Entregue com sucesso",
        )
        item.refresh_from_db()
        assert item.status_entrega == StatusEntregaItem.ENTREGUE

    def test_pod_unico_por_item(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        POD.objects.create(item=item, assinado_por="João")
        with pytest.raises(Exception):
            POD.objects.create(item=item, assinado_por="Pedro")

    def test_pod_com_coordenadas_gps(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        pod = POD.objects.create(
            item=item,
            assinado_por="José",
            latitude=-23.5505,
            longitude=-46.6333,
        )
        assert pod.latitude == -23.5505
        assert pod.longitude == -46.6333

    def test_str(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        pod = POD.objects.create(item=item, assinado_por="Ana")
        resultado = str(pod)
        assert item.destinatario in resultado


# ─── ItemRomaneio ─────────────────────────────────────────────────────────────

class TestItemRomaneio:

    def test_criacao_basica(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        assert item.pk is not None
        assert item.status_entrega == StatusEntregaItem.PENDENTE

    def test_str(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio, destinatario="Empresa XYZ")
        resultado = str(item)
        assert "Empresa XYZ" in resultado
        assert romaneio.numero in resultado

    def test_tem_pod_false_sem_pod(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        assert not hasattr(item, "pod") or item.pod is None

    def test_tem_pod_true_com_pod(self, romaneio):
        from conftest import ItemRomaneioFactory
        item = ItemRomaneioFactory(romaneio=romaneio)
        POD.objects.create(item=item, assinado_por="Cliente")
        item.refresh_from_db()
        assert hasattr(item, "pod")
