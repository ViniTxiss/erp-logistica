"""
Models do app TMS — Transportation Management System.

Fluxo principal:
  Romaneio (aberto)
    → vincula ItemRomaneio  (liga a SaidaMercadoria do WMS)
    → designa Veiculo + Motorista
    → status: aberto → em_rota → concluido | com_ocorrencia | cancelado
    → cada ItemRomaneio recebe POD (Proof of Delivery)
    → Ocorrencia pode ser registrada a qualquer momento durante o transporte
"""
import uuid
from django.db import models, transaction
from django.utils import timezone

from apps.core.models import Empresa, Filial, Usuario
from apps.core.base_models import TenantModel


# ─── Veículo ──────────────────────────────────────────────────────────────────

class TipoVeiculo(models.TextChoices):
    PROPRIO    = "proprio",     "Próprio"
    TERCEIRO   = "terceiro",    "Terceirizado"
    MOTO       = "moto",        "Moto"
    FURGAO     = "furgao",      "Furgão"
    CAMINHAO   = "caminhao",    "Caminhão"


class StatusVeiculo(models.TextChoices):
    DISPONIVEL  = "disponivel",  "Disponível"
    EM_ROTA     = "em_rota",     "Em rota"
    MANUTENCAO  = "manutencao",  "Em manutenção"
    INATIVO     = "inativo",     "Inativo"


class Veiculo(TenantModel):
    """
    Representa um veículo da frota (própria ou terceirizada).
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="veiculos")
    placa          = models.CharField(max_length=10)
    tipo           = models.CharField(max_length=20, choices=TipoVeiculo.choices, default=TipoVeiculo.PROPRIO)
    modelo         = models.CharField(max_length=100, blank=True)
    ano            = models.PositiveSmallIntegerField(null=True, blank=True)
    capacidade_kg  = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True,
                                         help_text="Capacidade de carga em quilogramas")
    status         = models.CharField(max_length=20, choices=StatusVeiculo.choices,
                                      default=StatusVeiculo.DISPONIVEL)
    ativo          = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Veículo"
        verbose_name_plural = "Veículos"
        unique_together     = [("empresa", "placa")]
        ordering            = ["placa"]

    def __str__(self):
        return f"{self.placa} — {self.get_tipo_display()} [{self.get_status_display()}]"


# ─── Motorista ────────────────────────────────────────────────────────────────

class CategoriasCNH(models.TextChoices):
    A  = "A",  "A"
    B  = "B",  "B"
    AB = "AB", "AB"
    C  = "C",  "C"
    D  = "D",  "D"
    E  = "E",  "E"


class Motorista(TenantModel):
    """
    Motorista vinculado à empresa. Pode ser colaborador próprio ou terceirizado.
    """
    id             = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa        = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="motoristas")
    nome_completo  = models.CharField(max_length=255)
    cpf            = models.CharField(max_length=14)                   # "000.000.000-00"
    cnh            = models.CharField(max_length=20)
    categoria_cnh  = models.CharField(max_length=5, choices=CategoriasCNH.choices, default=CategoriasCNH.B)
    validade_cnh   = models.DateField()
    telefone       = models.CharField(max_length=20, blank=True)
    ativo          = models.BooleanField(default=True)

    class Meta:
        verbose_name        = "Motorista"
        verbose_name_plural = "Motoristas"
        unique_together     = [("empresa", "cpf")]
        ordering            = ["nome_completo"]

    def __str__(self):
        return f"{self.nome_completo} (CNH {self.cnh} — cat. {self.categoria_cnh})"


# ─── Romaneio ─────────────────────────────────────────────────────────────────

class StatusRomaneio(models.TextChoices):
    ABERTO          = "aberto",          "Aberto"
    EM_ROTA         = "em_rota",         "Em rota"
    CONCLUIDO       = "concluido",       "Concluído"
    COM_OCORRENCIA  = "com_ocorrencia",  "Com ocorrência"
    CANCELADO       = "cancelado",       "Cancelado"


class Romaneio(TenantModel):
    """
    Documento de carga — agrupa pedidos (ItemRomaneio) para uma rota de entrega.

    Ciclo de vida:
      aberto → em_rota (via iniciar_rota()) → concluido (via concluir())
      A qualquer momento pode mudar para com_ocorrencia ou cancelado.
    """
    id                   = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa              = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="romaneios")
    filial               = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True)
    numero               = models.CharField(max_length=50, blank=True,
                                            help_text="Número sequencial do romaneio (pode ser gerado automaticamente)")
    veiculo              = models.ForeignKey(
        Veiculo, on_delete=models.SET_NULL, null=True, blank=True, related_name="romaneios"
    )
    motorista            = models.ForeignKey(
        Motorista, on_delete=models.SET_NULL, null=True, blank=True, related_name="romaneios"
    )
    status               = models.CharField(
        max_length=20, choices=StatusRomaneio.choices, default=StatusRomaneio.ABERTO
    )
    data_saida_prevista  = models.DateTimeField(null=True, blank=True)
    data_saida_real      = models.DateTimeField(null=True, blank=True)
    data_conclusao       = models.DateTimeField(null=True, blank=True)
    responsavel          = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="romaneios_responsavel"
    )
    observacoes          = models.TextField(blank=True)

    class Meta:
        verbose_name        = "Romaneio"
        verbose_name_plural = "Romaneios"
        ordering            = ["-created_at"]

    def __str__(self):
        numero = self.numero or str(self.id)[:8]
        return f"Romaneio {numero} — {self.get_status_display()}"

    def save(self, *args, **kwargs):
        """Gera número sequencial por empresa se não informado."""
        if not self.numero:
            ultimo = (
                Romaneio.objects.filter(empresa=self.empresa)
                .order_by("-created_at")
                .values_list("numero", flat=True)
                .first()
            )
            try:
                proximo = int(ultimo or 0) + 1
            except (ValueError, TypeError):
                proximo = 1
            self.numero = str(proximo).zfill(6)   # e.g. "000001"
        super().save(*args, **kwargs)

    @transaction.atomic
    def iniciar_rota(self, usuario=None):
        """
        Muda o romaneio para EM_ROTA e registra data de saída real.
        Marca o veículo como em_rota.
        """
        if self.status != StatusRomaneio.ABERTO:
            raise ValueError(f"Romaneio não pode ser iniciado — status atual: {self.get_status_display()}")

        self.status = StatusRomaneio.EM_ROTA
        self.data_saida_real = timezone.now()
        self.save(update_fields=["status", "data_saida_real", "updated_at"])

        if self.veiculo:
            Veiculo.objects.filter(pk=self.veiculo_id).update(status=StatusVeiculo.EM_ROTA)

    @transaction.atomic
    def concluir(self, usuario=None):
        """
        Conclui o romaneio.
        Libera o veículo (volta a 'disponivel').
        """
        if self.status not in (StatusRomaneio.EM_ROTA, StatusRomaneio.COM_OCORRENCIA):
            raise ValueError(f"Romaneio não pode ser concluído — status atual: {self.get_status_display()}")

        self.status = StatusRomaneio.CONCLUIDO
        self.data_conclusao = timezone.now()
        self.save(update_fields=["status", "data_conclusao", "updated_at"])

        if self.veiculo:
            Veiculo.objects.filter(pk=self.veiculo_id).update(status=StatusVeiculo.DISPONIVEL)

    @transaction.atomic
    def cancelar(self, usuario=None):
        """Cancela o romaneio e libera o veículo."""
        if self.status == StatusRomaneio.CONCLUIDO:
            raise ValueError("Romaneio já concluído não pode ser cancelado.")

        self.status = StatusRomaneio.CANCELADO
        self.save(update_fields=["status", "updated_at"])

        if self.veiculo:
            Veiculo.objects.filter(pk=self.veiculo_id).update(status=StatusVeiculo.DISPONIVEL)


# ─── Item do Romaneio ─────────────────────────────────────────────────────────

class StatusEntregaItem(models.TextChoices):
    PENDENTE   = "pendente",   "Pendente"
    ENTREGUE   = "entregue",   "Entregue"
    TENTATIVA  = "tentativa",  "Tentativa sem sucesso"
    DEVOLVIDO  = "devolvido",  "Devolvido"


class ItemRomaneio(models.Model):
    """
    Linha do romaneio — representa um ponto de entrega.
    Vincula-se a uma SaidaMercadoria do WMS (opcional no MVP, obrigatório na produção).
    """
    id               = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    romaneio         = models.ForeignKey(Romaneio, on_delete=models.CASCADE, related_name="itens")
    # Vínculo com o CRM (Cliente)
    cliente_crm      = models.ForeignKey(
        "crm.Cliente",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="itens_romaneio",
        help_text="Cliente CRM destinatário desta entrega (opcional)"
    )
    # Vínculo com o WMS (SaidaMercadoria)
    saida_wms        = models.ForeignKey(
        "wms.SaidaMercadoria",
        on_delete=models.SET_NULL, null=True, blank=True,
        related_name="itens_romaneio",
        help_text="Saída de mercadoria correspondente no WMS"
    )
    destinatario     = models.CharField(max_length=255)
    # Endereço de entrega (desnormalizado para facilitar impressão e GPS)
    logradouro       = models.CharField(max_length=255, blank=True)
    numero_end       = models.CharField(max_length=20, blank=True)
    bairro           = models.CharField(max_length=100, blank=True)
    cidade           = models.CharField(max_length=100, blank=True)
    uf               = models.CharField(max_length=2, blank=True)
    cep              = models.CharField(max_length=9, blank=True)
    latitude         = models.FloatField(null=True, blank=True)
    longitude        = models.FloatField(null=True, blank=True)
    # Controle de rota
    ordem_entrega    = models.PositiveSmallIntegerField(default=0,
                                                        help_text="Ordem de parada na rota (0 = não definida)")
    status_entrega   = models.CharField(
        max_length=20, choices=StatusEntregaItem.choices, default=StatusEntregaItem.PENDENTE
    )
    observacao       = models.CharField(max_length=255, blank=True)
    created_at       = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Item de Romaneio"
        verbose_name_plural = "Itens de Romaneio"
        ordering            = ["romaneio", "ordem_entrega"]

    def __str__(self):
        return f"{self.destinatario} [{self.get_status_entrega_display()}] — Romaneio {self.romaneio.numero}"


# ─── Ocorrência ───────────────────────────────────────────────────────────────

class TipoOcorrencia(models.TextChoices):
    AVARIA      = "avaria",      "Avaria / dano"
    ATRASO      = "atraso",      "Atraso"
    TENTATIVA   = "tentativa",   "Tentativa de entrega sem sucesso"
    ROUBO       = "roubo",       "Roubo / furto"
    ACIDENTE    = "acidente",    "Acidente"
    RECUSA      = "recusa",      "Recusa do destinatário"
    OUTRO       = "outro",       "Outro"


class Ocorrencia(models.Model):
    """
    Registro de evento/problema durante o transporte.
    Pode estar associada ao romaneio inteiro ou a um item específico.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    romaneio      = models.ForeignKey(Romaneio, on_delete=models.CASCADE, related_name="ocorrencias")
    item          = models.ForeignKey(
        ItemRomaneio, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ocorrencias",
        help_text="Item específico ao qual a ocorrência se refere (opcional)"
    )
    tipo          = models.CharField(max_length=20, choices=TipoOcorrencia.choices)
    descricao     = models.TextField()
    registrado_por = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="ocorrencias_registradas"
    )
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Ocorrência"
        verbose_name_plural = "Ocorrências"
        ordering            = ["-created_at"]

    def save(self, *args, **kwargs):
        """Atualiza status do romaneio para com_ocorrencia automaticamente."""
        super().save(*args, **kwargs)
        if self.romaneio.status == StatusRomaneio.EM_ROTA:
            Romaneio.objects.filter(pk=self.romaneio_id).update(
                status=StatusRomaneio.COM_OCORRENCIA,
                updated_at=timezone.now(),
            )

    def __str__(self):
        return f"[{self.get_tipo_display()}] Romaneio {self.romaneio.numero} — {self.created_at:%d/%m/%Y %H:%M}"


# ─── POD — Proof of Delivery ──────────────────────────────────────────────────

class POD(models.Model):
    """
    Comprovante de entrega (Proof of Delivery).
    Imutável: criado uma única vez por ItemRomaneio.
    Pode armazenar coordenadas GPS para auditoria.
    """
    id            = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    item          = models.OneToOneField(
        ItemRomaneio, on_delete=models.CASCADE, related_name="pod"
    )
    assinado_por  = models.CharField(max_length=255, blank=True,
                                     help_text="Nome de quem recebeu a mercadoria")
    observacao    = models.TextField(blank=True)
    latitude      = models.FloatField(null=True, blank=True,
                                      help_text="GPS no momento da entrega")
    longitude     = models.FloatField(null=True, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name        = "Comprovante de Entrega (POD)"
        verbose_name_plural = "Comprovantes de Entrega (POD)"
        # Nunca permitir edição
        default_permissions = ("add", "view")

    def save(self, *args, **kwargs):
        """Ao criar o POD, marca o item como ENTREGUE."""
        super().save(*args, **kwargs)
        ItemRomaneio.objects.filter(pk=self.item_id).update(
            status_entrega=StatusEntregaItem.ENTREGUE
        )

    def __str__(self):
        return f"POD — {self.item.destinatario} em {self.created_at:%d/%m/%Y %H:%M}"
