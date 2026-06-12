"""
Models do app Core — exatamente o ERD que você desenhou.

Hierarquia:
  Empresa → Filial → Usuario
  Perfil → Permissao (via PerfilPermissao)
  Usuario → Perfil (via PerfilUsuario)
  Usuario → AuditLog
"""
import uuid
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin


# ─── Endereço ─────────────────────────────────────────────────────────────────

class Endereco(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cep = models.CharField(max_length=9)
    logradouro = models.CharField(max_length=255)
    numero = models.CharField(max_length=20, blank=True)
    complemento = models.CharField(max_length=100, blank=True)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    uf = models.CharField(max_length=2)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)

    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"

    def __str__(self):
        return f"{self.logradouro}, {self.numero} — {self.cidade}/{self.uf}"


# ─── Empresa ──────────────────────────────────────────────────────────────────

class Empresa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    razao_social = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    inscricao_estadual = models.CharField(max_length=30, blank=True)
    email_principal = models.EmailField()
    ativo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Empresa"
        verbose_name_plural = "Empresas"
        ordering = ["razao_social"]

    def __str__(self):
        return f"{self.razao_social} ({self.cnpj})"


# ─── Filial ───────────────────────────────────────────────────────────────────

class Filial(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="filiais")
    endereco = models.OneToOneField(Endereco, on_delete=models.SET_NULL, null=True, blank=True)
    nome = models.CharField(max_length=255)
    cnpj = models.CharField(max_length=18, unique=True)
    codigo_interno = models.CharField(max_length=30, blank=True)
    matriz = models.BooleanField(default=False)
    ativa = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Filial"
        verbose_name_plural = "Filiais"
        ordering = ["-matriz", "nome"]

    def __str__(self):
        label = "MATRIZ" if self.matriz else "Filial"
        return f"{self.nome} [{label}] — {self.empresa.razao_social}"


# ─── RBAC: Perfil e Permissão ─────────────────────────────────────────────────

class Permissao(models.Model):
    """
    Granularidade: módulo + ação.
    Ex: código='wms.entrada.criar', módulo='wms', ação='entrada.criar'
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    codigo = models.CharField(max_length=100, unique=True)
    modulo = models.CharField(max_length=50)
    acao = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Permissão"
        verbose_name_plural = "Permissões"
        ordering = ["modulo", "acao"]

    def __str__(self):
        return self.codigo


class Perfil(models.Model):
    """
    Perfil de acesso. Ex: 'Operador WMS', 'Gerente TMS', 'Admin'.
    sistema=True → criado automaticamente, não pode ser deletado.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(Empresa, on_delete=models.CASCADE, related_name="perfis")
    nome = models.CharField(max_length=100)
    descricao = models.CharField(max_length=255, blank=True)
    sistema = models.BooleanField(default=False)
    permissoes = models.ManyToManyField(
        Permissao,
        through="PerfilPermissao",
        related_name="perfis",
    )

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural = "Perfis"
        unique_together = [("empresa", "nome")]

    def __str__(self):
        return f"{self.nome} — {self.empresa.razao_social}"


class PerfilPermissao(models.Model):
    """Tabela de junção Perfil ↔ Permissão."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    permissao = models.ForeignKey(Permissao, on_delete=models.CASCADE)

    class Meta:
        verbose_name = "Perfil → Permissão"
        verbose_name_plural = "Perfil → Permissões"
        unique_together = [("perfil", "permissao")]


# ─── Usuario (custom AbstractBaseUser) ────────────────────────────────────────

class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email é obrigatório")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("ativo", True)
        return self.create_user(email, password, **extra_fields)


class Usuario(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    empresa = models.ForeignKey(
        Empresa, on_delete=models.CASCADE, related_name="usuarios",
        null=True, blank=True  # superusers podem não ter empresa
    )
    filial = models.ForeignKey(
        Filial, on_delete=models.SET_NULL, related_name="usuarios",
        null=True, blank=True
    )
    nome_completo = models.CharField(max_length=255)
    email = models.EmailField(unique=True)
    telefone = models.CharField(max_length=20, blank=True)
    cargo = models.CharField(max_length=100, blank=True)
    ativo = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    perfis = models.ManyToManyField(
        Perfil,
        through="PerfilUsuario",
        related_name="usuarios",
        blank=True,
    )
    ultimo_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nome_completo"]

    class Meta:
        verbose_name = "Usuário"
        verbose_name_plural = "Usuários"
        ordering = ["nome_completo"]

    def __str__(self):
        return f"{self.nome_completo} <{self.email}>"

    @property
    def is_active(self):
        return self.ativo

    def tem_permissao(self, codigo: str) -> bool:
        """Verifica se o usuário possui um código de permissão via seus perfis com cache em memória."""
        if self.is_superuser:
            return True

        if not hasattr(self, "_permissoes_cache"):
            self._permissoes_cache = set(
                PerfilUsuario.objects
                .filter(usuario=self)
                .select_related("perfil")
                .prefetch_related("perfil__permissoes")
                .values_list("perfil__perfilpermissao__permissao__codigo", flat=True)
            )
        return codigo in self._permissoes_cache


class PerfilUsuario(models.Model):
    """
    Tabela de junção Usuario ↔ Perfil.
    valido_ate permite perfis temporários.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    perfil = models.ForeignKey(Perfil, on_delete=models.CASCADE)
    valido_ate = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Usuário → Perfil"
        verbose_name_plural = "Usuário → Perfis"
        unique_together = [("usuario", "perfil")]


# ─── AuditLog ─────────────────────────────────────────────────────────────────

class AuditLog(models.Model):
    """
    Registro imutável de toda ação relevante no sistema.
    Nunca deletar, nunca atualizar — só inserir.
    """
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.ForeignKey(
        Usuario, on_delete=models.SET_NULL, null=True, related_name="audit_logs"
    )
    modulo = models.CharField(max_length=50)
    acao = models.CharField(max_length=100)
    objeto_tipo = models.CharField(max_length=100)
    objeto_id = models.UUIDField(null=True, blank=True)
    payload_antes = models.JSONField(null=True, blank=True)
    payload_depois = models.JSONField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Audit Log"
        verbose_name_plural = "Audit Logs"
        ordering = ["-created_at"]
        # Nunca permitir update ou delete
        default_permissions = ("add", "view")

    def __str__(self):
        return f"[{self.modulo}] {self.acao} por {self.usuario} em {self.created_at:%d/%m/%Y %H:%M}"
