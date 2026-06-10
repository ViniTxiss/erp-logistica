"""
Models do app CRM — Customer Relationship Management.

Foco no contexto logístico: clientes que contratam frete e armazenagem.

Fluxo principal:
  Cliente (status=lead)
    → qualificação → Oportunidade (funil: prospeccao → fechado_ganho)
    → fechar_ganho() → Cliente (status=ativo) + Contrato
    → HistoricoInteracao em cada etapa
    → Cliente ativo pode ser vinculado a ItemRomaneio (TMS)
"""
import uuid
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import Empresa, Filial, Usuario


# ─── Choices ──────────────────────────────────────────────────────────────────

class SegmentoCliente(models.TextChoices):
    INDUSTRIA     = "industria",     "Indústria"
    VAREJO        = "varejo",        "Varejo"
    DISTRIBUICAO  = "distribuicao",  "Distribuição"
    ECOMMERCE     = "ecommerce",     "E-commerce"
    AGRONEGOCIO   = "agronegocio",   "Agronegócio"
    SAUDE         = "saude",         "Saúde"
    OUTRO         = "outro",         "Outro"


class StatusCliente(models.TextChoices):
    LEAD      = "lead",      "Lead"
    ATIVO     = "ativo",     "Ativo"
    INATIVO   = "inativo",   "Inativo"
    BLOQUEADO = "bloqueado", "Bloqueado"


class EtapaOportunidade(models.TextChoices):
    PROSPECCAO      = "prospeccao",      "Prospecção"
    QUALIFICACAO    = "qualificacao",    "Qualificação"
    PROPOSTA        = "proposta",        "Proposta enviada"
    NEGOCIACAO      = "negociacao",      "Em negociação"
    FECHADO_GANHO   = "fechado_ganho",   "Fechado — ganho"
    FECHADO_PERDIDO = "fechado_perdido", "Fechado — perdido"


class TipoInteracao(models.TextChoices):
    LIGACAO  = "ligacao",  "Ligação telefônica"
    EMAIL    = "email",    "E-mail"
    REUNIAO  = "reuniao",  "Reunião"
    VISITA   = "visita",   "Visita presencial"
    PROPOSTA = "proposta", "Envio de proposta"
    OUTRO    = "outro",    "Outro"


class ServicoContratado(models.TextChoices):
    ARMAZENAGEM = "armazenagem", "Armazenagem"
    FRETE       = "frete",       "Frete"
    AMBOS       = "ambos",       "Armazenagem + Frete"


# ─── Cliente ──────────────────────────────────────────────────────────────────

class Cliente(models.Model):
    """
    Empresa cliente que contrata serviços logísticos (frete, armazenagem).
    Nasce como lead e evolui para ativo após fechamento de oportunidade.
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="clientes_crm")
    # Dados da empresa cliente
    cnpj           = models.CharField(max_length=18, blank=True)
    razao_social   = models.CharField(max_length=255)
    nome_fantasia  = models.CharField(max_length=255, blank=True)
    segmento       = models.CharField(
        max_length=20, choices=SegmentoCliente.choices, default=SegmentoCliente.OUTRO
    )
    status         = models.CharField(
        max_length=20, choices=StatusCliente.choices, default=StatusCliente.LEAD
    )
    # Endereço (desnormalizado para simplicidade no MVP)
    cidade         = models.CharField(max_length=100, blank=True)
    uf             = models.CharField(max_length=2, blank=True)
    # Comunicação
    site           = models.URLField(blank=True)
    email_principal = models.EmailField(blank=True)
    telefone       = models.CharField(max_length=20, blank=True)
    # Gestão interna
    responsavel    = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="clientes_responsavel",
        help_text="Consultor/vendedor responsável pelo cliente"
    )
    observacoes    = models.TextField(blank=True)
    created_at     = models.DateTimeField(auto_now_add=True)
    updated_at     = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Cliente"
        verbose_name_plural = "Clientes"
        ordering            = ["razao_social"]
        # CNPJ único por empresa operadora (pode ter mesmo CNPJ em empresas diferentes)
        unique_together     = [("empresa", "cnpj")]

    def __str__(self):
        nome = self.nome_fantasia or self.razao_social
        return f"{nome} [{self.get_status_display()}]"


# ─── Contato ──────────────────────────────────────────────────────────────────

class Contato(models.Model):
    """
    Pessoa física de contato dentro de uma empresa cliente.
    Pode ser marcado como decisor (quem assina contratos).
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente       = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contatos")
    nome_completo = models.CharField(max_length=255)
    cargo         = models.CharField(max_length=100, blank=True)
    email         = models.EmailField(blank=True)
    telefone      = models.CharField(max_length=20, blank=True)
    whatsapp      = models.CharField(max_length=20, blank=True)
    decisor       = models.BooleanField(
        default=False,
        help_text="Indica se esta pessoa tem poder de decisão sobre contratos"
    )
    ativo         = models.BooleanField(default=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Contato"
        verbose_name_plural = "Contatos"
        ordering            = ["-decisor", "nome_completo"]

    def __str__(self):
        decisor_label = " ★" if self.decisor else ""
        return f"{self.nome_completo}{decisor_label} — {self.cliente.razao_social}"


# ─── Oportunidade ─────────────────────────────────────────────────────────────

class Oportunidade(models.Model):
    """
    Negociação em andamento com um cliente.
    Progride por etapas de funil até fechamento (ganho ou perdido).
    """
    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente              = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="oportunidades")
    titulo               = models.CharField(max_length=255)
    servico              = models.CharField(
        max_length=20, choices=ServicoContratado.choices, default=ServicoContratado.FRETE
    )
    valor_estimado       = models.DecimalField(
        max_digits=12, decimal_places=2, null=True, blank=True,
        help_text="Valor mensal estimado do contrato (R$)"
    )
    etapa                = models.CharField(
        max_length=20, choices=EtapaOportunidade.choices, default=EtapaOportunidade.PROSPECCAO
    )
    probabilidade        = models.PositiveSmallIntegerField(
        default=10,
        help_text="Probabilidade de fechamento (0-100%)"
    )
    responsavel          = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="oportunidades_responsavel"
    )
    previsao_fechamento  = models.DateField(null=True, blank=True)
    motivo_perda         = models.CharField(max_length=255, blank=True)
    observacoes          = models.TextField(blank=True)
    created_at           = models.DateTimeField(auto_now_add=True)
    updated_at           = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Oportunidade"
        verbose_name_plural = "Oportunidades"
        ordering            = ["-created_at"]

    def __str__(self):
        return f"{self.titulo} — {self.cliente.razao_social} [{self.get_etapa_display()}]"

    @transaction.atomic
    def fechar_ganho(self, usuario=None):
        """
        Fecha a oportunidade como GANHO.
        Muda o cliente para ATIVO automaticamente.
        """
        if self.etapa in (EtapaOportunidade.FECHADO_GANHO, EtapaOportunidade.FECHADO_PERDIDO):
            raise ValueError(f"Oportunidade já encerrada: {self.get_etapa_display()}")

        self.etapa = EtapaOportunidade.FECHADO_GANHO
        self.probabilidade = 100
        self.save(update_fields=["etapa", "probabilidade", "updated_at"])

        # Ativa o cliente
        Cliente.objects.filter(pk=self.cliente_id).update(
            status=StatusCliente.ATIVO,
            updated_at=timezone.now(),
        )

    @transaction.atomic
    def fechar_perdido(self, motivo: str = "", usuario=None):
        """Fecha a oportunidade como PERDIDO."""
        if self.etapa in (EtapaOportunidade.FECHADO_GANHO, EtapaOportunidade.FECHADO_PERDIDO):
            raise ValueError(f"Oportunidade já encerrada: {self.get_etapa_display()}")

        self.etapa = EtapaOportunidade.FECHADO_PERDIDO
        self.probabilidade = 0
        self.motivo_perda = motivo
        self.save(update_fields=["etapa", "probabilidade", "motivo_perda", "updated_at"])


# ─── Histórico de Interações ──────────────────────────────────────────────────

class HistoricoInteracao(models.Model):
    """
    Log imutável de interações com o cliente.
    Nunca editar nem deletar — apenas inserir.
    """
    id              = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente         = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="historico")
    oportunidade    = models.ForeignKey(
        Oportunidade, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="historico",
        help_text="Oportunidade relacionada à interação (opcional)"
    )
    contato         = models.ForeignKey(
        Contato, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="historico",
        help_text="Contato com quem a interação foi realizada (opcional)"
    )
    tipo            = models.CharField(max_length=20, choices=TipoInteracao.choices)
    resumo          = models.TextField()
    data_interacao  = models.DateTimeField(default=timezone.now)
    registrado_por  = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="interacoes_registradas"
    )
    created_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Histórico de Interação"
        verbose_name_plural = "Histórico de Interações"
        ordering            = ["-data_interacao"]
        default_permissions = ("add", "view")   # nunca change / delete

    def __str__(self):
        return f"[{self.get_tipo_display()}] {self.cliente.razao_social} — {self.data_interacao:%d/%m/%Y}"


# ─── Contrato ─────────────────────────────────────────────────────────────────

class Contrato(models.Model):
    """
    Contrato comercial ativo entre a empresa operadora e o cliente.
    Um cliente pode ter mais de um contrato vigente (ex: frete + armazenagem).
    """
    id                       = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente                  = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name="contratos")
    numero                   = models.CharField(max_length=50)
    servico                  = models.CharField(
        max_length=20, choices=ServicoContratado.choices, default=ServicoContratado.AMBOS
    )
    valor_mensal             = models.DecimalField(
        max_digits=12, decimal_places=2,
        help_text="Valor mensal do contrato (R$)"
    )
    vigencia_inicio          = models.DateField()
    vigencia_fim             = models.DateField(null=True, blank=True,
                                                help_text="Deixar em branco para contrato por prazo indeterminado")
    sla_prazo_entrega_horas  = models.PositiveSmallIntegerField(
        default=48,
        help_text="Prazo máximo de entrega acordado em horas"
    )
    objeto                   = models.TextField(
        blank=True,
        help_text="Descrição do objeto do contrato"
    )
    ativo                    = models.BooleanField(default=True)
    created_at               = models.DateTimeField(auto_now_add=True)
    updated_at               = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = "Contrato"
        verbose_name_plural = "Contratos"
        ordering            = ["-vigencia_inicio"]

    def __str__(self):
        return f"Contrato {self.numero} — {self.cliente.razao_social} ({self.get_servico_display()})"

    @property
    def vigente(self) -> bool:
        """Retorna True se o contrato está dentro do prazo de vigência."""
        hoje = timezone.now().date()
        if hoje < self.vigencia_inicio:
            return False
        if self.vigencia_fim and hoje > self.vigencia_fim:
            return False
        return self.ativo
