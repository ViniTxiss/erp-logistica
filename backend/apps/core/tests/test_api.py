"""
Testes de API do app Core.
Cobrem: endpoints REST de Usuario, Perfil, Permissão, AuditLog e RBAC via HTTP.
"""
import pytest
from rest_framework import status

from apps.core.models import AuditLog, Perfil, Permissao, PerfilPermissao, PerfilUsuario
from apps.core.audit import audit


pytestmark = pytest.mark.django_db


# ─── Helpers reutilizados ─────────────────────────────────────────────────────

def criar_permissao(codigo, modulo="core"):
    return Permissao.objects.create(
        codigo=codigo, modulo=modulo,
        acao=codigo.split(".", 1)[-1],
    )


def criar_perfil_com_perm(empresa, nome, codigo_perm, modulo="core"):
    perm = criar_permissao(codigo_perm, modulo)
    perfil = Perfil.objects.create(empresa=empresa, nome=nome)
    PerfilPermissao.objects.create(perfil=perfil, permissao=perm)
    return perfil


def autenticar(api_client, usuario):
    from rest_framework_simplejwt.tokens import RefreshToken
    refresh = RefreshToken.for_user(usuario)
    api_client.credentials(HTTP_AUTHORIZATION=f"Bearer {refresh.access_token}")
    return api_client


# ─── Autenticação JWT ─────────────────────────────────────────────────────────

class TestAutenticacaoJWT:

    def test_obter_token_com_credenciais_validas(self, api_client, usuario):
        resp = api_client.post("/api/token/", {
            "email": usuario.email,
            "password": "senha@Teste123",
        }, format="json")
        assert resp.status_code == status.HTTP_200_OK
        assert "access" in resp.data
        assert "refresh" in resp.data

    def test_token_invalido_retorna_401(self, api_client, usuario):
        resp = api_client.post("/api/token/", {
            "email": usuario.email,
            "password": "senha_errada",
        }, format="json")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_endpoint_sem_token_retorna_401(self, api_client):
        resp = api_client.get("/api/core/usuarios/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_refresh_token(self, api_client, usuario):
        resp_login = api_client.post("/api/token/", {
            "email": usuario.email,
            "password": "senha@Teste123",
        }, format="json")
        refresh = resp_login.data["refresh"]

        resp_refresh = api_client.post("/api/token/refresh/", {"refresh": refresh}, format="json")
        assert resp_refresh.status_code == status.HTTP_200_OK
        assert "access" in resp_refresh.data


# ─── /api/core/usuarios/me/ ───────────────────────────────────────────────────

class TestUsuarioMe:

    def test_me_retorna_usuario_autenticado(self, api_client, usuario):
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/usuarios/me/")
        assert resp.status_code == status.HTTP_200_OK
        assert resp.data["email"] == usuario.email
        assert resp.data["nome_completo"] == usuario.nome_completo

    def test_me_sem_autenticacao_retorna_401(self, api_client):
        resp = api_client.get("/api/core/usuarios/me/")
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    def test_me_inclui_perfis(self, api_client, usuario, empresa):
        perfil = Perfil.objects.create(empresa=empresa, nome="Gerente")
        PerfilUsuario.objects.create(usuario=usuario, perfil=perfil)
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/usuarios/me/")
        assert resp.status_code == status.HTTP_200_OK
        nomes = [p["nome"] for p in resp.data["perfis"]]
        assert "Gerente" in nomes


# ─── /api/core/usuarios/ — isolamento multi-tenant ───────────────────────────

class TestUsuarioViewSetIsolamento:

    def test_lista_apenas_usuarios_da_propria_empresa(self, api_client, usuario, empresa):
        from conftest import EmpresaFactory, UsuarioFactory
        outra = EmpresaFactory()
        user_outra = UsuarioFactory(empresa=outra)

        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/usuarios/")
        assert resp.status_code == status.HTTP_200_OK

        emails = [u["email"] for u in resp.data["results"]]
        assert usuario.email in emails
        assert user_outra.email not in emails

    def test_ativar_usuario(self, api_client, usuario, empresa):
        from conftest import UsuarioFactory
        alvo = UsuarioFactory(empresa=empresa, ativo=False)
        autenticar(api_client, usuario)
        resp = api_client.post(f"/api/core/usuarios/{alvo.id}/ativar/")
        assert resp.status_code == status.HTTP_200_OK
        alvo.refresh_from_db()
        assert alvo.ativo is True

    def test_desativar_usuario(self, api_client, usuario, empresa):
        from conftest import UsuarioFactory
        alvo = UsuarioFactory(empresa=empresa, ativo=True)
        autenticar(api_client, usuario)
        resp = api_client.post(f"/api/core/usuarios/{alvo.id}/desativar/")
        assert resp.status_code == status.HTTP_200_OK
        alvo.refresh_from_db()
        assert alvo.ativo is False

    def test_nao_acessa_usuario_de_outra_empresa(self, api_client, usuario):
        from conftest import EmpresaFactory, UsuarioFactory
        outra = EmpresaFactory()
        user_outra = UsuarioFactory(empresa=outra)
        autenticar(api_client, usuario)
        resp = api_client.get(f"/api/core/usuarios/{user_outra.id}/")
        assert resp.status_code == status.HTTP_404_NOT_FOUND


# ─── /api/core/perfis/ ───────────────────────────────────────────────────────

class TestPerfilViewSet:

    def test_lista_perfis_da_empresa(self, api_client, usuario, empresa):
        Perfil.objects.create(empresa=empresa, nome="Operador")
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/perfis/")
        assert resp.status_code == status.HTTP_200_OK
        nomes = [p["nome"] for p in resp.data["results"]]
        assert "Operador" in nomes

    def test_nao_lista_perfis_de_outra_empresa(self, api_client, usuario, empresa):
        from conftest import EmpresaFactory
        outra = EmpresaFactory()
        Perfil.objects.create(empresa=outra, nome="PerfilSecreto")
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/perfis/")
        nomes = [p["nome"] for p in resp.data["results"]]
        assert "PerfilSecreto" not in nomes

    def test_cria_perfil(self, api_client, usuario, empresa):
        autenticar(api_client, usuario)
        resp = api_client.post("/api/core/perfis/", {
            "empresa": str(empresa.id),
            "nome": "Gestor Financeiro",
            "descricao": "Acesso ao financeiro",
        }, format="json")
        assert resp.status_code == status.HTTP_201_CREATED
        assert Perfil.objects.filter(nome="Gestor Financeiro", empresa=empresa).exists()


# ─── /api/core/permissoes/ — somente leitura ─────────────────────────────────

class TestPermissaoViewSet:

    def test_lista_permissoes(self, api_client, usuario):
        criar_permissao("wms.saida.ver", "wms")
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/permissoes/")
        assert resp.status_code == status.HTTP_200_OK
        assert len(resp.data["results"]) >= 1

    def test_nao_permite_criacao(self, api_client, usuario):
        """Permissões são somente leitura — criadas via fixtures."""
        autenticar(api_client, usuario)
        resp = api_client.post("/api/core/permissoes/", {
            "codigo": "hack.permissao.criar",
            "modulo": "hack",
            "acao": "permissao.criar",
        }, format="json")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_nao_permite_delecao(self, api_client, usuario):
        perm = criar_permissao("core.del.test")
        autenticar(api_client, usuario)
        resp = api_client.delete(f"/api/core/permissoes/{perm.id}/")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED


# ─── /api/core/audit/ — AuditLog somente leitura ─────────────────────────────

class TestAuditLogViewSet:

    def test_lista_apenas_logs_da_empresa(self, api_client, usuario, empresa):
        from conftest import EmpresaFactory, UsuarioFactory
        outra = EmpresaFactory()
        user_outra = UsuarioFactory(empresa=outra)

        audit(usuario, "wms", "acao_minha", "Modelo")
        audit(user_outra, "crm", "acao_outra", "Modelo")

        # Dar permissão para ver audit
        perm = criar_permissao("core.auditlog.ver")
        perfil = Perfil.objects.create(empresa=empresa, nome="Auditor")
        PerfilPermissao.objects.create(perfil=perfil, permissao=perm)
        PerfilUsuario.objects.create(usuario=usuario, perfil=perfil)

        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/audit/")
        assert resp.status_code == status.HTTP_200_OK
        acoes = [log["acao"] for log in resp.data["results"]]
        assert "acao_minha" in acoes
        assert "acao_outra" not in acoes

    def test_sem_permissao_auditlog_retorna_403(self, api_client, usuario):
        """Usuário sem perfil não acessa AuditLog."""
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/audit/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_nao_permite_criacao_via_api(self, api_client, usuario, empresa):
        perm = criar_permissao("core.auditlog.ver")
        perfil = Perfil.objects.create(empresa=empresa, nome="Auditor2")
        PerfilPermissao.objects.create(perfil=perfil, permissao=perm)
        PerfilUsuario.objects.create(usuario=usuario, perfil=perfil)

        autenticar(api_client, usuario)
        resp = api_client.post("/api/core/audit/", {
            "modulo": "hack", "acao": "injecao", "objeto_tipo": "X"
        }, format="json")
        assert resp.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

    def test_filtra_por_modulo(self, api_client, usuario, empresa):
        audit(usuario, "wms", "wms.acao", "Modelo")
        audit(usuario, "tms", "tms.acao", "Modelo")

        # A view exige exatamente o código "core.auditlog.ver"
        perm, _ = Permissao.objects.get_or_create(
            codigo="core.auditlog.ver",
            defaults={"modulo": "core", "acao": "auditlog.ver"},
        )
        perfil = Perfil.objects.create(empresa=empresa, nome="Auditor Filtro")
        PerfilPermissao.objects.create(perfil=perfil, permissao=perm)
        PerfilUsuario.objects.create(usuario=usuario, perfil=perfil)

        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/audit/?modulo=wms")
        assert resp.status_code == status.HTTP_200_OK
        for log in resp.data["results"]:
            assert log["modulo"] == "wms"


# ─── HasModulePermission e require_permission ─────────────────────────────────

class TestHasModulePermission:
    """
    Testa indiretamente o RBAC via endpoint real que usa require_permission.
    AuditLogViewSet usa: require_permission("core.auditlog.ver")
    """

    def test_sem_permissao_retorna_403(self, api_client, usuario):
        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/audit/")
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_com_permissao_retorna_200(self, api_client, usuario, empresa):
        perm = criar_permissao("core.auditlog.ver.2")
        perfil = Perfil.objects.create(empresa=empresa, nome="AuditorRBAC")
        PerfilPermissao.objects.create(perfil=perfil, permissao=perm)
        PerfilUsuario.objects.create(usuario=usuario, perfil=perfil)

        # Precisa ter a permissão exata que a view exige
        perm_certa = Permissao.objects.create(
            codigo="core.auditlog.ver",
            modulo="core",
            acao="auditlog.ver",
        )
        PerfilPermissao.objects.create(perfil=perfil, permissao=perm_certa)

        autenticar(api_client, usuario)
        resp = api_client.get("/api/core/audit/")
        assert resp.status_code == status.HTTP_200_OK

    def test_superuser_acessa_sem_permissao_explicita(self, api_client, empresa):
        from conftest import UsuarioFactory
        su = UsuarioFactory(empresa=empresa, is_superuser=True, is_staff=True)
        autenticar(api_client, su)
        resp = api_client.get("/api/core/audit/")
        assert resp.status_code == status.HTTP_200_OK
