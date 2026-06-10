"""
Factories e fixtures compartilhados para todos os testes do projeto Formuca ERP.
Coloca-se na raiz do backend para ficar disponível a todos os apps.
"""
import pytest
from datetime import date, timedelta
import factory
from factory.django import DjangoModelFactory
from django.utils import timezone

from apps.core.models import Empresa, Filial, Usuario
from apps.tms.models import (
    Veiculo, TipoVeiculo, StatusVeiculo,
    Motorista,
    Romaneio, StatusRomaneio,
    ItemRomaneio, StatusEntregaItem,
    Ocorrencia, TipoOcorrencia,
    POD,
)
from apps.crm.models import (
    Cliente, StatusCliente, SegmentoCliente,
    Contato, Oportunidade, EtapaOportunidade,
    HistoricoInteracao, TipoInteracao,
    Contrato, ServicoContratado,
)
from apps.wms.models import (
    Armazem, Posicao, Produto,
    EntradaMercadoria, StatusEntrada, ItemEntrada,
    SaidaMercadoria, StatusSaida, ItemSaida,
    MovimentacaoEstoque,
)


# ─── Core factories ───────────────────────────────────────────────────────────

class EmpresaFactory(DjangoModelFactory):
    class Meta:
        model = Empresa

    razao_social    = factory.Sequence(lambda n: f"Empresa Teste {n} Ltda")
    cnpj            = factory.Sequence(lambda n: f"{n:014d}")
    email_principal = factory.LazyAttribute(lambda o: f"contato@{o.razao_social.lower().replace(' ', '')}.com.br")
    ativo           = True


class FilialFactory(DjangoModelFactory):
    class Meta:
        model = Filial

    empresa         = factory.SubFactory(EmpresaFactory)
    nome            = factory.Sequence(lambda n: f"Filial {n}")
    cnpj            = factory.Sequence(lambda n: f"{n + 1000:014d}")
    matriz          = False
    ativa           = True


class UsuarioFactory(DjangoModelFactory):
    class Meta:
        model = Usuario

    empresa      = factory.SubFactory(EmpresaFactory)
    nome_completo = factory.Sequence(lambda n: f"Usuário Teste {n}")
    email        = factory.Sequence(lambda n: f"usuario{n}@teste.com")
    ativo        = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        """Usa create_user para garantir hash de senha."""
        return model_class.objects.create_user(
            password="senha@Teste123",
            **kwargs,
        )


# ─── TMS factories ────────────────────────────────────────────────────────────

class VeiculoFactory(DjangoModelFactory):
    class Meta:
        model = Veiculo

    empresa       = factory.SubFactory(EmpresaFactory)
    placa         = factory.Sequence(lambda n: f"TST{n:04d}")
    tipo          = TipoVeiculo.PROPRIO
    modelo        = "VW Delivery"
    ano           = 2022
    capacidade_kg = factory.LazyFunction(lambda: 1000)
    status        = StatusVeiculo.DISPONIVEL
    ativo         = True


class MotoristaFactory(DjangoModelFactory):
    class Meta:
        model = Motorista

    empresa       = factory.SubFactory(EmpresaFactory)
    nome_completo = factory.Sequence(lambda n: f"Motorista {n}")
    cpf           = factory.Sequence(lambda n: f"{n:011d}")
    cnh           = factory.Sequence(lambda n: f"CNH{n:08d}")
    categoria_cnh = "B"
    validade_cnh  = factory.LazyFunction(lambda: date.today() + timedelta(days=365))
    telefone      = "(11) 99999-0000"
    ativo         = True


class RomaneioFactory(DjangoModelFactory):
    class Meta:
        model = Romaneio

    empresa             = factory.SubFactory(EmpresaFactory)
    veiculo             = factory.SubFactory(VeiculoFactory, empresa=factory.SelfAttribute("..empresa"))
    motorista           = factory.SubFactory(MotoristaFactory, empresa=factory.SelfAttribute("..empresa"))
    status              = StatusRomaneio.ABERTO
    data_saida_prevista = factory.LazyFunction(lambda: timezone.now() + timedelta(hours=2))


class ItemRomaneioFactory(DjangoModelFactory):
    class Meta:
        model = ItemRomaneio

    romaneio       = factory.SubFactory(RomaneioFactory)
    destinatario   = factory.Sequence(lambda n: f"Cliente {n}")
    logradouro     = "Rua das Flores"
    numero_end     = factory.Sequence(lambda n: str(n + 1))
    bairro         = "Centro"
    cidade         = "São Paulo"
    uf             = "SP"
    cep            = "01310-100"
    ordem_entrega  = factory.Sequence(lambda n: n + 1)
    status_entrega = StatusEntregaItem.PENDENTE


class OcorrenciaFactory(DjangoModelFactory):
    class Meta:
        model = Ocorrencia

    romaneio = factory.SubFactory(RomaneioFactory, status=StatusRomaneio.EM_ROTA)
    tipo     = TipoOcorrencia.ATRASO
    descricao = "Trânsito intenso na via"


class PODFactory(DjangoModelFactory):
    class Meta:
        model = POD

    item         = factory.SubFactory(ItemRomaneioFactory)
    assinado_por = "João da Silva"
    observacao   = "Entregue na portaria"
    latitude     = -23.5505
    longitude    = -46.6333


# ─── CRM factories ────────────────────────────────────────────────────────────

class ClienteFactory(DjangoModelFactory):
    class Meta:
        model = Cliente

    empresa       = factory.SubFactory(EmpresaFactory)
    cnpj          = factory.Sequence(lambda n: f"{n + 2000:014d}")
    razao_social  = factory.Sequence(lambda n: f"Cliente Logística {n} Ltda")
    nome_fantasia = factory.Sequence(lambda n: f"LogiCliente {n}")
    segmento      = SegmentoCliente.DISTRIBUICAO
    status        = StatusCliente.LEAD
    cidade        = "São Paulo"
    uf            = "SP"


class ContatoFactory(DjangoModelFactory):
    class Meta:
        model = Contato

    cliente       = factory.SubFactory(ClienteFactory)
    nome_completo = factory.Sequence(lambda n: f"Contato {n}")
    cargo         = "Gerente de Logística"
    email         = factory.Sequence(lambda n: f"contato{n}@logistica.com")
    telefone      = "(11) 98765-4321"
    decisor       = False
    ativo         = True


class OportunidadeFactory(DjangoModelFactory):
    class Meta:
        model = Oportunidade

    cliente              = factory.SubFactory(ClienteFactory)
    titulo               = factory.Sequence(lambda n: f"Oportunidade de Frete {n}")
    servico              = ServicoContratado.FRETE
    valor_estimado       = factory.LazyFunction(lambda: 5000)
    etapa                = EtapaOportunidade.PROSPECCAO
    probabilidade        = 20


class ContratoFactory(DjangoModelFactory):
    class Meta:
        model = Contrato

    cliente                  = factory.SubFactory(ClienteFactory, status=StatusCliente.ATIVO)
    numero                   = factory.Sequence(lambda n: f"CONT-{n:04d}")
    servico                  = ServicoContratado.FRETE
    valor_mensal             = factory.LazyFunction(lambda: 8000)
    vigencia_inicio          = factory.LazyFunction(lambda: date.today())
    sla_prazo_entrega_horas  = 48
    ativo                    = True


# ─── pytest fixtures ──────────────────────────────────────────────────────────

@pytest.fixture
def empresa():
    return EmpresaFactory()


@pytest.fixture
def usuario(empresa):
    return UsuarioFactory(empresa=empresa)


@pytest.fixture
def veiculo(empresa):
    return VeiculoFactory(empresa=empresa)


@pytest.fixture
def motorista(empresa):
    return MotoristaFactory(empresa=empresa)


@pytest.fixture
def romaneio(empresa, veiculo, motorista):
    return RomaneioFactory(empresa=empresa, veiculo=veiculo, motorista=motorista)


@pytest.fixture
def romaneio_em_rota(romaneio, usuario):
    romaneio.iniciar_rota(usuario=usuario)
    romaneio.refresh_from_db()
    return romaneio


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def auth_client(api_client, usuario):
    """Cliente autenticado via JWT."""
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(usuario)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


@pytest.fixture
def cliente_crm(empresa, usuario):
    return ClienteFactory(empresa=empresa, responsavel=usuario)


@pytest.fixture
def oportunidade(cliente_crm, usuario):
    return OportunidadeFactory(cliente=cliente_crm, responsavel=usuario)


# ─── WMS fixtures ────────────────────────────────────────────────────────

class ArmazemFactory(DjangoModelFactory):
    class Meta:
        model = Armazem

    empresa = factory.SubFactory(EmpresaFactory)
    nome    = factory.Sequence(lambda n: f"Armazem {n}")
    codigo  = factory.Sequence(lambda n: f"CD{n:02d}")
    ativo   = True


class ProdutoFactory(DjangoModelFactory):
    class Meta:
        model = Produto

    empresa   = factory.SubFactory(EmpresaFactory)
    sku       = factory.Sequence(lambda n: f"SKU{n:05d}")
    descricao = factory.Sequence(lambda n: f"Produto Teste {n}")
    unidade   = "un"
    ativo     = True


class PosicaoFactory(DjangoModelFactory):
    """Cria uma Posicao completa com toda a hierarquia (Corredor, Bay, Nivel)."""
    class Meta:
        model = Posicao

    nivel = factory.LazyAttribute(lambda o: _criar_nivel(o.nivel_armazem))
    nivel_armazem = factory.SubFactory(ArmazemFactory)

    @classmethod
    def _after_postgeneration(cls, obj, create, results=None):
        if not obj.codigo:
            n = obj.nivel
            obj.codigo = f"{n.bay.corredor.armazem.codigo}-{n.bay.corredor.codigo}-{n.bay.numero}-{n.numero}"
            obj.save()


def _criar_nivel(armazem):
    """Helper: cria Corredor → Bay → Nivel dentro do armazem dado."""
    from apps.wms.models import Corredor, Bay, Nivel
    corredor = Corredor.objects.create(armazem=armazem, codigo="A")
    bay      = Bay.objects.create(corredor=corredor, numero="01")
    return Nivel.objects.create(bay=bay, numero="01")


class EntradaMercadoriaFactory(DjangoModelFactory):
    class Meta:
        model = EntradaMercadoria

    armazem     = factory.SubFactory(ArmazemFactory)
    numero_nf   = factory.Sequence(lambda n: f"NF-{n:06d}")
    fornecedor  = factory.Sequence(lambda n: f"Fornecedor {n}")
    status      = StatusEntrada.PENDENTE
    chegada_em  = factory.LazyFunction(timezone.now)


class SaidaMercadoriaFactory(DjangoModelFactory):
    class Meta:
        model = SaidaMercadoria

    armazem       = factory.SubFactory(ArmazemFactory)
    numero_pedido = factory.Sequence(lambda n: f"PED-{n:06d}")
    destinatario  = factory.Sequence(lambda n: f"Cliente {n}")
    status        = StatusSaida.PENDENTE


@pytest.fixture
def armazem(empresa):
    return ArmazemFactory(empresa=empresa)


@pytest.fixture
def produto(empresa):
    return ProdutoFactory(empresa=empresa)


@pytest.fixture
def entrada(armazem, usuario):
    return EntradaMercadoriaFactory(armazem=armazem, responsavel=usuario)


@pytest.fixture
def saida(armazem, usuario):
    return SaidaMercadoriaFactory(armazem=armazem, responsavel=usuario)
