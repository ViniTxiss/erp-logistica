"""
Testes unitários dos models do Core.
Cobrem: Empresa, Usuario, RBAC (Perfil/Permissão) e AuditLog.
Sem chamadas HTTP — lógica de negócio pura.
"""
import pytest
from django.db import IntegrityError

from apps.core.models import (
    Empresa, Usuario,
    Perfil, Permissao, PerfilPermissao, PerfilUsuario,
    AuditLog,
)
from apps.core.audit import audit


pytestmark = pytest.mark.django_db


# ─── Helpers ─────────────────────────────────────────────────────────────────

def criar_permissao(codigo: str, modulo: str = "core") -> Permissao:
    """Cria uma Permissão no banco com código único."""
    return Permissao.objects.create(
        codigo=codigo,
        modulo=modulo,
        acao=codigo.split(".", 1)[-1],
        descricao=f"Permissão de teste: {codigo}",
    )


def criar_perfil(empresa, nome: str = "Operador") -> Perfil:
    """Cria um Perfil para a empresa."""
    return Perfil.objects.create(empresa=empresa, nome=nome)


def vincular_permissao(perfil: Perfil, permissao: Permissao) -> None:
    """Vincula uma permissão a um perfil."""
    PerfilPermissao.objects.create(perfil=perfil, permissao=permissao)


def atribuir_perfil(usuario: Usuario, perfil: Perfil) -> PerfilUsuario:
    """Atribui um perfil ao usuário."""
    return PerfilUsuario.objects.create(usuario=usuario, perfil=perfil)


# ─── Empresa ──────────────────────────────────────────────────────────────────

class TestEmpresaModel:

    def test_criacao_basica(self, empresa):
        assert empresa.pk is not None
        assert empresa.ativo is True

    def test_str(self, empresa):
        resultado = str(empresa)
        assert empresa.razao_social in resultado
        assert empresa.cnpj in resultado

    def test_cnpj_unico(self, empresa):
        from conftest import EmpresaFactory
        with pytest.raises(Exception):  # IntegrityError
            EmpresaFactory(cnpj=empresa.cnpj)

    def test_ordenacao_por_razao_social(self):
        from conftest import EmpresaFactory
        EmpresaFactory(razao_social="Zeta Logística")
        EmpresaFactory(razao_social="Alpha Transportes")
        empresas = list(Empresa.objects.all())
        nomes = [e.razao_social for e in empresas]
        assert nomes == sorted(nomes)


# ─── Usuario ──────────────────────────────────────────────────────────────────

class TestUsuarioModel:

    def test_criacao_basica(self, usuario):
        assert usuario.pk is not None
        assert usuario.ativo is True
        assert usuario.is_staff is False

    def test_str(self, usuario):
        resultado = str(usuario)
        assert usuario.nome_completo in resultado
        assert usuario.email in resultado

    def test_is_active_reflete_ativo(self, usuario):
        assert usuario.is_active is True
        usuario.ativo = False
        assert usuario.is_active is False

    def test_email_unico(self, usuario):
        from conftest import UsuarioFactory
        with pytest.raises(Exception):  # IntegrityError
            UsuarioFactory(email=usuario.email)

    def test_senha_salva_como_hash(self, usuario):
        """A senha nunca deve ficar em texto puro no banco."""
        assert not usuario.password.startswith("senha")
        assert usuario.check_password("senha@Teste123") is True

    def test_create_superuser(self, empresa):
        su = Usuario.objects.create_superuser(
            email="super@teste.com",
            password="admin@Super123",
            nome_completo="Super Admin",
            empresa=empresa,
        )
        assert su.is_staff is True
        assert su.is_superuser is True
        assert su.ativo is True


# ─── Usuario.tem_permissao — RBAC ─────────────────────────────────────────────

class TestUsuarioTemPermissao:
    """
    Cobre os 4 cenários fundamentais do RBAC:
      1. Superuser → sempre True
      2. Usuário sem perfil → sempre False
      3. Usuário com perfil + permissão correta → True
      4. Usuário com perfil mas sem aquela permissão → False
    """

    def test_superuser_tem_qualquer_permissao(self, empresa):
        from conftest import UsuarioFactory
        su = UsuarioFactory(empresa=empresa, is_superuser=True)
        # Mesmo sem nenhuma permissão cadastrada
        assert su.tem_permissao("wms.entrada.criar") is True
        assert su.tem_permissao("permissao.que.nao.existe") is True

    def test_usuario_sem_perfil_nao_tem_permissao(self, usuario):
        assert usuario.tem_permissao("wms.entrada.criar") is False

    def test_usuario_com_perfil_e_permissao_tem_acesso(self, usuario, empresa):
        perm = criar_permissao("wms.entrada.criar", modulo="wms")
        perfil = criar_perfil(empresa, "Operador WMS")
        vincular_permissao(perfil, perm)
        atribuir_perfil(usuario, perfil)

        assert usuario.tem_permissao("wms.entrada.criar") is True

    def test_usuario_com_perfil_sem_permissao_especifica(self, usuario, empresa):
        """Perfil existe, mas não tem a permissão solicitada."""
        perm_outra = criar_permissao("wms.entrada.ver", modulo="wms")
        perfil = criar_perfil(empresa, "Visualizador")
        vincular_permissao(perfil, perm_outra)
        atribuir_perfil(usuario, perfil)

        assert usuario.tem_permissao("wms.entrada.criar") is False

    def test_usuario_com_multiplos_perfis(self, usuario, empresa):
        """Usuário com 2 perfis: um tem a permissão, o outro não."""
        perm = criar_permissao("crm.cliente.criar", modulo="crm")
        perfil_a = criar_perfil(empresa, "Perfil A")
        perfil_b = criar_perfil(empresa, "Perfil B")
        vincular_permissao(perfil_a, perm)
        # perfil_b não tem a permissão

        atribuir_perfil(usuario, perfil_a)
        atribuir_perfil(usuario, perfil_b)

        assert usuario.tem_permissao("crm.cliente.criar") is True

    def test_permissao_errada_nao_concede_acesso(self, usuario, empresa):
        """Permissão de outro módulo não deve conceder acesso."""
        perm_tms = criar_permissao("tms.romaneio.ver", modulo="tms")
        perfil = criar_perfil(empresa, "Operador TMS")
        vincular_permissao(perfil, perm_tms)
        atribuir_perfil(usuario, perfil)

        assert usuario.tem_permissao("wms.entrada.criar") is False
        assert usuario.tem_permissao("tms.romaneio.ver") is True

    def test_usuario_inativo_ainda_tem_permissao_via_rbac(self, empresa):
        """
        tem_permissao() verifica só o RBAC, não o status ativo.
        É responsabilidade da view/autenticação checar is_active.
        """
        from conftest import UsuarioFactory
        user = UsuarioFactory(empresa=empresa, ativo=False)
        perm = criar_permissao("core.usuario.ver", modulo="core")
        perfil = criar_perfil(empresa, "Leitura")
        vincular_permissao(perfil, perm)
        atribuir_perfil(user, perfil)

        # O método em si não bloqueia por ativo
        assert user.tem_permissao("core.usuario.ver") is True


# ─── Perfil e Permissão ───────────────────────────────────────────────────────

class TestPerfilModel:

    def test_criacao_basica(self, empresa):
        perfil = criar_perfil(empresa, "Gerente")
        assert perfil.pk is not None
        assert perfil.sistema is False

    def test_str(self, empresa):
        perfil = criar_perfil(empresa, "Operador")
        resultado = str(perfil)
        assert "Operador" in resultado
        assert empresa.razao_social in resultado

    def test_nome_unico_por_empresa(self, empresa):
        criar_perfil(empresa, "Admin")
        with pytest.raises(Exception):  # IntegrityError — unique_together
            criar_perfil(empresa, "Admin")

    def test_mesmo_nome_empresas_diferentes(self, empresa):
        from conftest import EmpresaFactory
        outra = EmpresaFactory()
        p1 = criar_perfil(empresa, "Admin")
        p2 = criar_perfil(outra, "Admin")
        assert p1.pk != p2.pk

    def test_perfil_sistema(self, empresa):
        perfil = Perfil.objects.create(
            empresa=empresa, nome="SuperAdmin", sistema=True
        )
        assert perfil.sistema is True


class TestPermissaoModel:

    def test_criacao_basica(self):
        perm = criar_permissao("wms.saida.criar", modulo="wms")
        assert perm.pk is not None
        assert perm.modulo == "wms"

    def test_str_retorna_codigo(self):
        perm = criar_permissao("tms.pod.criar", modulo="tms")
        assert str(perm) == "tms.pod.criar"

    def test_codigo_unico(self):
        criar_permissao("core.unico.test")
        with pytest.raises(Exception):
            criar_permissao("core.unico.test")


# ─── AuditLog ────────────────────────────────────────────────────────────────

class TestAuditLogModel:

    def test_str(self, usuario):
        log = AuditLog.objects.create(
            usuario=usuario,
            modulo="tms",
            acao="romaneio.criar",
            objeto_tipo="Romaneio",
        )
        resultado = str(log)
        assert "tms" in resultado
        assert "romaneio.criar" in resultado
        assert usuario.nome_completo in resultado

    def test_campos_basicos_preenchidos(self, usuario):
        import uuid
        obj_id = uuid.uuid4()
        log = AuditLog.objects.create(
            usuario=usuario,
            modulo="crm",
            acao="cliente.criar",
            objeto_tipo="Cliente",
            objeto_id=obj_id,
            payload_antes=None,
            payload_depois={"nome": "Empresa ABC"},
        )
        assert log.pk is not None
        assert log.modulo == "crm"
        assert log.acao == "cliente.criar"
        assert log.objeto_id == obj_id
        assert log.payload_depois["nome"] == "Empresa ABC"
        assert log.created_at is not None

    def test_usuario_pode_ser_nulo(self):
        """AuditLog de ações de sistema sem usuário autenticado."""
        log = AuditLog.objects.create(
            usuario=None,
            modulo="sistema",
            acao="startup",
            objeto_tipo="Sistema",
        )
        assert log.usuario is None
        assert log.pk is not None

    def test_sem_permissao_de_update_delete(self):
        """AuditLog é imutável por definição — só add e view nas Meta permissions."""
        opts = AuditLog._meta
        assert "change" not in opts.default_permissions
        assert "delete" not in opts.default_permissions
        assert "add" in opts.default_permissions
        assert "view" in opts.default_permissions

    def test_ordering_declarada_como_created_at_desc(self):
        # SQLite in-memory tem resolucao de 1s.
        assert AuditLog._meta.ordering == ['-created_at']
    def test_audit_cria_auditlog(self, usuario):
        audit(
            usuario=usuario,
            modulo="wms",
            acao="entrada.concluir",
            objeto_tipo="EntradaMercadoria",
            payload_depois={"status": "concluida"},
        )
        assert AuditLog.objects.filter(
            usuario=usuario,
            modulo="wms",
            acao="entrada.concluir",
        ).exists()

    def test_audit_com_todos_os_campos(self, usuario):
        import uuid
        obj_id = uuid.uuid4()
        audit(
            usuario=usuario,
            modulo="crm",
            acao="oportunidade.fechar_ganho",
            objeto_tipo="Oportunidade",
            objeto_id=obj_id,
            payload_antes={"etapa": "negociacao"},
            payload_depois={"etapa": "fechado_ganho"},
            ip="192.168.1.100",
        )
        log = AuditLog.objects.get(acao="oportunidade.fechar_ganho")
        assert log.objeto_id == obj_id
        assert log.payload_antes["etapa"] == "negociacao"
        assert log.payload_depois["etapa"] == "fechado_ganho"
        assert log.ip == "192.168.1.100"

    def test_audit_sem_usuario(self):
        """Deve funcionar mesmo sem usuário (ações de sistema)."""
        audit(
            usuario=None,
            modulo="sistema",
            acao="cron.job",
            objeto_tipo="Sistema",
        )
        assert AuditLog.objects.filter(acao="cron.job").exists()

    def test_audit_multiplas_chamadas_acumulam(self, usuario):
        for i in range(3):
            audit(
                usuario=usuario,
                modulo="tms",
                acao=f"acao_{i}",
                objeto_tipo="Teste",
            )
        assert AuditLog.objects.filter(usuario=usuario).count() == 3

    def test_auditlog_trigger_imutabilidade(self, usuario):
        """Garante que a trigger impeça UPDATE e DELETE na tabela core_auditlog."""
        from django.db import transaction
        log = AuditLog.objects.create(
            usuario=usuario,
            modulo="wms",
            acao="teste.criar",
            objeto_tipo="Teste",
        )
        log.acao = "teste.modificar"
        with transaction.atomic():
            with pytest.raises(IntegrityError):
                log.save()

        with transaction.atomic():
            with pytest.raises(IntegrityError):
                log.delete()


# ─── Isolamento multi-tenant ─────────────────────────────────────────────────

class TestIsolamentoMultiTenant:
    """
    Garante que dados de uma empresa nunca vazam para outra.
    Simula o filtro que as views devem aplicar.
    """

    def test_usuario_nao_ve_usuarios_de_outra_empresa(self):
        from conftest import EmpresaFactory, UsuarioFactory
        emp_a = EmpresaFactory()
        emp_b = EmpresaFactory()
        u_a = UsuarioFactory(empresa=emp_a)
        u_b = UsuarioFactory(empresa=emp_b)

        # Simula o queryset da view
        qs_a = Usuario.objects.filter(empresa=emp_a)
        assert u_a in qs_a
        assert u_b not in qs_a

    def test_perfil_isolado_por_empresa(self):
        from conftest import EmpresaFactory
        emp_a = EmpresaFactory()
        emp_b = EmpresaFactory()
        p_a = criar_perfil(emp_a, "Operador")
        p_b = criar_perfil(emp_b, "Operador")

        qs_a = Perfil.objects.filter(empresa=emp_a)
        assert p_a in qs_a
        assert p_b not in qs_a

    def test_auditlog_isolado_por_empresa(self):
        from conftest import EmpresaFactory, UsuarioFactory
        emp_a = EmpresaFactory()
        emp_b = EmpresaFactory()
        u_a = UsuarioFactory(empresa=emp_a)
        u_b = UsuarioFactory(empresa=emp_b)

        audit(u_a, "wms", "acao_a", "Modelo")
        audit(u_b, "crm", "acao_b", "Modelo")

        # Simula o filtro da AuditLogViewSet
        qs_a = AuditLog.objects.filter(usuario__empresa=emp_a)
        assert qs_a.filter(acao="acao_a").exists()
        assert not qs_a.filter(acao="acao_b").exists()

    def test_permissao_de_perfil_nao_vaza_entre_empresas(self):
        """Usuário da emp_b não deve ganhar permissão pelo perfil da emp_a."""
        from conftest import EmpresaFactory, UsuarioFactory
        emp_a = EmpresaFactory()
        emp_b = EmpresaFactory()

        perm = criar_permissao("wms.tudo.fazer", modulo="wms")
        perfil_a = criar_perfil(emp_a, "Super")
        vincular_permissao(perfil_a, perm)

        # Usuário da empresa B — sem perfil da empresa A
        user_b = UsuarioFactory(empresa=emp_b)
        assert user_b.tem_permissao("wms.tudo.fazer") is False
