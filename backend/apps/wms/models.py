"""
Models do app WMS — Warehouse Management System.

Hierarquia física do armazém:
  Armazem → Corredor → Bay → Nivel → Posicao

Fluxo de estoque:
  EntradaMercadoria → ItemEntrada → MovimentacaoEstoque
  SaidaMercadoria   → ItemSaida   → MovimentacaoEstoque
"""
import uuid
from django.db import models
from django.db import transaction
from apps.core.models import Empresa, Filial, Usuario


# ─── Estrutura física do armazém ──────────────────────────────────────────────

class Armazem(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="armazens")
    filial = models.ForeignKey(Filial, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=100)
    codigo = models.CharField(max_length=20)
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Armazém"
        verbose_name_plural = "Armazéns"
        unique_together = [("empresa", "codigo")]
        ordering = ["nome"]

    def __str__(self):
        return f"{self.codigo} — {self.nome}"


class Corredor(models.Model):
    """Rua / corredor dentro do armazém. Ex: A, B, C"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    armazem = models.ForeignKey(Armazem, on_delete=models.CASCADE, related_name="corredores")
    codigo = models.CharField(max_length=10)  # A, B, C...

    class Meta:
        verbose_name = "Corredor"
        unique_together = [("armazem", "codigo")]
        ordering = ["codigo"]

    def __str__(self):
        return f"{self.armazem.codigo}-{self.codigo}"


class Bay(models.Model):
    """Coluna / bay dentro de um corredor. Ex: 01, 02, 03"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    corredor = models.ForeignKey(Corredor, on_delete=models.CASCADE, related_name="bays")
    numero = models.CharField(max_length=10)  # 01, 02...

    class Meta:
        verbose_name = "Bay"
        unique_together = [("corredor", "numero")]
        ordering = ["numero"]

    def __str__(self):
        return f"{self.corredor}-{self.numero}"


class Nivel(models.Model):
    """Nível de altura dentro de um bay. Ex: 01, 02, 03"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    bay = models.ForeignKey(Bay, on_delete=models.CASCADE, related_name="niveis")
    numero = models.CharField(max_length=10)  # 01, 02...

    class Meta:
        verbose_name = "Nível"
        verbose_name_plural = "Níveis"
        unique_together = [("bay", "numero")]
        ordering = ["numero"]

    def __str__(self):
        return f"{self.bay}-{self.numero}"


class Posicao(models.Model):
    """
    Endereço físico completo: Armazem-Corredor-Bay-Nivel.
    Ex: CD01-A-03-02 = Armazém CD01, Corredor A, Bay 03, Nível 02.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nivel = models.OneToOneField(Nivel, on_delete=models.CASCADE, related_name="posicao")
    codigo = models.CharField(max_length=30, unique=True)  # gerado automaticamente
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Posição"
        verbose_name_plural = "Posições"
        ordering = ["codigo"]

    def save(self, *args, **kwargs):
        if not self.codigo:
            n = self.nivel
            self.codigo = f"{n.bay.corredor.armazem.codigo}-{n.bay.corredor.codigo}-{n.bay.numero}-{n.numero}"
        super().save(*args, **kwargs)

    def __str__(self):
        return self.codigo

    @property
    def saldo_atual(self):
        """Retorna o saldo total de itens nesta posição."""
        return self.movimentacoes.aggregate(
            total=models.Sum("quantidade")
        )["total"] or 0


# ─── Produtos (referência simples para MVP) ───────────────────────────────────

class Produto(models.Model):
    """
    Cadastro básico de produto para o MVP.
    Em versões futuras pode ser um módulo separado com SKU completo.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="produtos")
    sku = models.CharField(max_length=50)
    descricao = models.CharField(max_length=255)
    unidade = models.CharField(max_length=10, default="un")  # un, kg, cx, ...
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Produto"
        unique_together = [("empresa", "sku")]
        ordering = ["descricao"]

    def __str__(self):
        return f"[{self.sku}] {self.descricao}"


# ─── Entrada de mercadorias ───────────────────────────────────────────────────

class StatusEntrada(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    EM_ANDAMENTO = "em_andamento", "Em andamento"
    CONCLUIDO = "concluido", "Concluído"
    DIVERGENCIA = "divergencia", "Divergência"


class EntradaMercadoria(models.Model):
    """
    Cabeçalho do recebimento. Corresponde a uma NF de entrada.
    Uma entrada pode ter vários itens (ItemEntrada).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    armazem = models.ForeignKey(Armazem, on_delete=models.PROTECT, related_name="entradas")
    numero_nf = models.CharField(max_length=50)
    fornecedor = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=StatusEntrada.choices,
        default=StatusEntrada.PENDENTE,
    )
    responsavel = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="entradas_responsavel"
    )
    observacoes = models.TextField(blank=True)
    chegada_em = models.DateTimeField()
    concluida_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Entrada de Mercadoria"
        verbose_name_plural = "Entradas de Mercadoria"
        ordering = ["-chegada_em"]

    def __str__(self):
        return f"NF {self.numero_nf} — {self.fornecedor} [{self.get_status_display()}]"

    @transaction.atomic
    def concluir(self, usuario):
        """
        Conclui o recebimento:
        1. Muda status para CONCLUIDO
        2. Cria MovimentacaoEstoque para cada item confirmado
        """
        from django.utils import timezone
        self.status = StatusEntrada.CONCLUIDO
        self.concluida_em = timezone.now()
        self.save(update_fields=["status", "concluida_em", "updated_at"])

        for item in self.itens.filter(posicao__isnull=False):
            MovimentacaoEstoque.objects.create(
                posicao=item.posicao,
                produto=item.produto,
                tipo=TipoMovimentacao.ENTRADA,
                quantidade=item.quantidade_conferida or item.quantidade_esperada,
                origem_entrada=self,
                usuario=usuario,
            )


class ItemEntrada(models.Model):
    """Linha de produto dentro de uma Entrada de Mercadoria."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    entrada = models.ForeignKey(EntradaMercadoria, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="itens_entrada")
    posicao = models.ForeignKey(
        Posicao, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="itens_entrada",
        help_text="Posição onde o item será armazenado"
    )
    quantidade_esperada = models.DecimalField(max_digits=10, decimal_places=3)
    quantidade_conferida = models.DecimalField(max_digits=10, decimal_places=3, null=True, blank=True)
    observacao = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Item de Entrada"
        verbose_name_plural = "Itens de Entrada"

    def __str__(self):
        return f"{self.produto.sku} × {self.quantidade_esperada} {self.produto.unidade}"

    @property
    def tem_divergencia(self):
        if self.quantidade_conferida is None:
            return False
        return self.quantidade_conferida != self.quantidade_esperada


# ─── Saída de mercadorias ─────────────────────────────────────────────────────

class StatusSaida(models.TextChoices):
    PENDENTE = "pendente", "Pendente"
    EM_SEPARACAO = "em_separacao", "Em separação"
    SEPARADO = "separado", "Separado"
    EXPEDIDO = "expedido", "Expedido"


class SaidaMercadoria(models.Model):
    """
    Cabeçalho de expedição — pode ser vinculada a um Romaneio (TMS).
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    armazem = models.ForeignKey(Armazem, on_delete=models.PROTECT, related_name="saidas")
    numero_pedido = models.CharField(max_length=50, blank=True)
    destinatario = models.CharField(max_length=255)
    status = models.CharField(
        max_length=20,
        choices=StatusSaida.choices,
        default=StatusSaida.PENDENTE,
    )
    responsavel = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, blank=True,
        related_name="saidas_responsavel"
    )
    expedida_em = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Saída de Mercadoria"
        verbose_name_plural = "Saídas de Mercadoria"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Pedido {self.numero_pedido or self.id} — {self.destinatario}"

    @transaction.atomic
    def expedir(self, usuario):
        from django.utils import timezone
        self.status = StatusSaida.EXPEDIDO
        self.expedida_em = timezone.now()
        self.save(update_fields=["status", "expedida_em", "updated_at"])

        for item in self.itens.all():
            MovimentacaoEstoque.objects.create(
                posicao=item.posicao,
                produto=item.produto,
                tipo=TipoMovimentacao.SAIDA,
                quantidade=-item.quantidade,  # negativo = saída
                origem_saida=self,
                usuario=usuario,
            )


class ItemSaida(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    saida = models.ForeignKey(SaidaMercadoria, on_delete=models.CASCADE, related_name="itens")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    posicao = models.ForeignKey(Posicao, on_delete=models.PROTECT, related_name="itens_saida")
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)

    class Meta:
        verbose_name = "Item de Saída"

    def __str__(self):
        return f"{self.produto.sku} × {self.quantidade}"


# ─── Movimentação de Estoque (ledger imutável) ────────────────────────────────

class TipoMovimentacao(models.TextChoices):
    ENTRADA = "entrada", "Entrada"
    SAIDA = "saida", "Saída"
    AJUSTE = "ajuste", "Ajuste de inventário"
    TRANSFERENCIA = "transferencia", "Transferência"


class MovimentacaoEstoque(models.Model):
    """
    Ledger imutável de todas as movimentações.
    NUNCA deletar ou editar — o saldo é calculado somando as quantidades.
    Quantidade positiva = entrada | Quantidade negativa = saída.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    posicao = models.ForeignKey(Posicao, on_delete=models.PROTECT, related_name="movimentacoes")
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT, related_name="movimentacoes")
    tipo = models.CharField(max_length=20, choices=TipoMovimentacao.choices)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    origem_entrada = models.ForeignKey(
        EntradaMercadoria, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="movimentacoes"
    )
    origem_saida = models.ForeignKey(
        SaidaMercadoria, on_delete=models.SET_NULL,
        null=True, blank=True, related_name="movimentacoes"
    )
    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Movimentação de Estoque"
        verbose_name_plural = "Movimentações de Estoque"
        ordering = ["-created_at"]
        default_permissions = ("add", "view")  # nunca change/delete

    def __str__(self):
        sinal = "+" if self.quantidade > 0 else ""
        return f"{self.tipo} | {self.produto.sku} | {sinal}{self.quantidade} | {self.posicao}"
