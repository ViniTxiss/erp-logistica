"""
Testes unitários dos models do CRM.
"""
import pytest
from datetime import date, timedelta
from django.utils import timezone

from apps.crm.models import (
    Cliente, StatusCliente,
    Oportunidade, EtapaOportunidade,
    HistoricoInteracao, Contrato,
)


pytestmark = pytest.mark.django_db


# ─── Cliente ──────────────────────────────────────────────────────────────────

class TestClienteModel:

    def test_criacao_basica(self, cliente_crm):
        assert cliente_crm.pk is not None
        assert cliente_crm.status == StatusCliente.LEAD

    def test_str_usa_nome_fantasia(self, empresa):
        from conftest import ClienteFactory
        c = ClienteFactory(empresa=empresa, razao_social="ABC Ltda", nome_fantasia="ABC Express")
        assert "ABC Express" in str(c)

    def test_str_usa_razao_social_sem_nome_fantasia(self, empresa):
        from conftest import ClienteFactory
        c = ClienteFactory(empresa=empresa, razao_social="XYZ Distribuidora", nome_fantasia="")
        assert "XYZ Distribuidora" in str(c)

    def test_cnpj_unico_por_empresa(self, empresa):
        from conftest import ClienteFactory
        ClienteFactory(empresa=empresa, cnpj="12345678000100")
        with pytest.raises(Exception):
            ClienteFactory(empresa=empresa, cnpj="12345678000100")

    def test_mesmo_cnpj_empresas_diferentes(self, empresa):
        from conftest import ClienteFactory, EmpresaFactory
        outra = EmpresaFactory()
        c1 = ClienteFactory(empresa=empresa, cnpj="99999999000199")
        c2 = ClienteFactory(empresa=outra, cnpj="99999999000199")
        assert c1.pk != c2.pk


# ─── Contato ──────────────────────────────────────────────────────────────────

class TestContatoModel:

    def test_criacao_basica(self, cliente_crm):
        from conftest import ContatoFactory
        c = ContatoFactory(cliente=cliente_crm)
        assert c.pk is not None
        assert c.ativo is True
        assert c.decisor is False

    def test_str_com_decisor(self, cliente_crm):
        from conftest import ContatoFactory
        c = ContatoFactory(cliente=cliente_crm, nome_completo="Maria Diretora", decisor=True)
        resultado = str(c)
        assert "Maria Diretora" in resultado
        assert "★" in resultado

    def test_str_sem_decisor(self, cliente_crm):
        from conftest import ContatoFactory
        c = ContatoFactory(cliente=cliente_crm, nome_completo="João Operador", decisor=False)
        assert "★" not in str(c)


# ─── Oportunidade — ciclo de vida ─────────────────────────────────────────────

class TestOportunidadeFecharGanho:

    def test_fechar_ganho_muda_etapa(self, oportunidade, usuario):
        oportunidade.fechar_ganho(usuario=usuario)
        oportunidade.refresh_from_db()
        assert oportunidade.etapa == EtapaOportunidade.FECHADO_GANHO

    def test_fechar_ganho_muda_probabilidade_para_100(self, oportunidade, usuario):
        oportunidade.fechar_ganho(usuario=usuario)
        oportunidade.refresh_from_db()
        assert oportunidade.probabilidade == 100

    def test_fechar_ganho_ativa_o_cliente(self, oportunidade, cliente_crm, usuario):
        assert cliente_crm.status == StatusCliente.LEAD
        oportunidade.fechar_ganho(usuario=usuario)
        cliente_crm.refresh_from_db()
        assert cliente_crm.status == StatusCliente.ATIVO

    def test_fechar_ganho_falha_se_ja_encerrada(self, oportunidade, usuario):
        oportunidade.fechar_ganho(usuario=usuario)
        with pytest.raises(ValueError, match="encerrada"):
            oportunidade.fechar_ganho(usuario=usuario)

    def test_fechar_ganho_falha_se_perdida(self, oportunidade, usuario):
        oportunidade.fechar_perdido(motivo="Preço alto", usuario=usuario)
        with pytest.raises(ValueError, match="encerrada"):
            oportunidade.fechar_ganho(usuario=usuario)


class TestOportunidadeFecharPerdido:

    def test_fechar_perdido_muda_etapa(self, oportunidade, usuario):
        oportunidade.fechar_perdido(motivo="Concorrente mais barato", usuario=usuario)
        oportunidade.refresh_from_db()
        assert oportunidade.etapa == EtapaOportunidade.FECHADO_PERDIDO

    def test_fechar_perdido_salva_motivo(self, oportunidade, usuario):
        motivo = "Prazo de entrega longo demais"
        oportunidade.fechar_perdido(motivo=motivo, usuario=usuario)
        oportunidade.refresh_from_db()
        assert oportunidade.motivo_perda == motivo

    def test_fechar_perdido_zera_probabilidade(self, oportunidade, usuario):
        oportunidade.fechar_perdido(usuario=usuario)
        oportunidade.refresh_from_db()
        assert oportunidade.probabilidade == 0

    def test_fechar_perdido_nao_muda_status_do_cliente(self, oportunidade, cliente_crm, usuario):
        oportunidade.fechar_perdido(usuario=usuario)
        cliente_crm.refresh_from_db()
        assert cliente_crm.status == StatusCliente.LEAD

    def test_str(self, oportunidade):
        resultado = str(oportunidade)
        assert oportunidade.titulo in resultado
        assert "Prospecção" in resultado


# ─── HistoricoInteracao ───────────────────────────────────────────────────────

class TestHistoricoInteracaoModel:

    def test_criacao_basica(self, cliente_crm, usuario):
        hi = HistoricoInteracao.objects.create(
            cliente=cliente_crm,
            tipo="ligacao",
            resumo="Primeiro contato realizado",
            registrado_por=usuario,
        )
        assert hi.pk is not None

    def test_str(self, cliente_crm):
        hi = HistoricoInteracao.objects.create(
            cliente=cliente_crm,
            tipo="reuniao",
            resumo="Reunião de apresentação",
        )
        resultado = str(hi)
        assert "Reunião" in resultado
        assert cliente_crm.razao_social in resultado

    def test_com_oportunidade_e_contato(self, cliente_crm, oportunidade, usuario):
        from conftest import ContatoFactory
        contato = ContatoFactory(cliente=cliente_crm)
        hi = HistoricoInteracao.objects.create(
            cliente=cliente_crm,
            oportunidade=oportunidade,
            contato=contato,
            tipo="proposta",
            resumo="Proposta enviada por e-mail",
            registrado_por=usuario,
        )
        assert hi.oportunidade == oportunidade
        assert hi.contato == contato


# ─── Contrato ─────────────────────────────────────────────────────────────────

class TestContratoModel:

    def test_vigente_true_dentro_do_prazo(self, cliente_crm):
        from conftest import ContratoFactory
        contrato = ContratoFactory(
            cliente=cliente_crm,
            vigencia_inicio=date.today() - timedelta(days=10),
            vigencia_fim=date.today() + timedelta(days=30),
            ativo=True,
        )
        assert contrato.vigente is True

    def test_vigente_false_apos_vencimento(self, cliente_crm):
        from conftest import ContratoFactory
        contrato = ContratoFactory(
            cliente=cliente_crm,
            vigencia_inicio=date.today() - timedelta(days=60),
            vigencia_fim=date.today() - timedelta(days=1),
            ativo=True,
        )
        assert contrato.vigente is False

    def test_vigente_false_se_inativo(self, cliente_crm):
        from conftest import ContratoFactory
        contrato = ContratoFactory(
            cliente=cliente_crm,
            vigencia_inicio=date.today(),
            ativo=False,
        )
        assert contrato.vigente is False

    def test_vigente_true_sem_data_fim(self, cliente_crm):
        from conftest import ContratoFactory
        contrato = ContratoFactory(
            cliente=cliente_crm,
            vigencia_inicio=date.today() - timedelta(days=5),
            vigencia_fim=None,
            ativo=True,
        )
        assert contrato.vigente is True

    def test_str(self, cliente_crm):
        from conftest import ContratoFactory
        contrato = ContratoFactory(cliente=cliente_crm, numero="CONT-0001")
        resultado = str(contrato)
        assert "CONT-0001" in resultado
        assert cliente_crm.razao_social in resultado
