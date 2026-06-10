"""
Serializers do app Core.
"""
from rest_framework import serializers
from .models import Empresa, Filial, Endereco, Usuario, Perfil, Permissao, AuditLog


class EnderecoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Endereco
        fields = "__all__"


class EmpresaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Empresa
        fields = "__all__"
        read_only_fields = ["id", "created_at", "updated_at"]


class FilialSerializer(serializers.ModelSerializer):
    endereco = EnderecoSerializer(read_only=True)
    endereco_id = serializers.UUIDField(write_only=True, required=False)

    class Meta:
        model = Filial
        fields = "__all__"
        read_only_fields = ["id", "created_at"]


class PermissaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permissao
        fields = "__all__"
        read_only_fields = ["id"]


class PerfilSerializer(serializers.ModelSerializer):
    permissoes = PermissaoSerializer(many=True, read_only=True)

    class Meta:
        model = Perfil
        fields = "__all__"
        read_only_fields = ["id"]


class UsuarioSerializer(serializers.ModelSerializer):
    """Serializer completo — usado para leitura e criação."""
    perfis = PerfilSerializer(many=True, read_only=True)
    empresa_nome = serializers.CharField(source="empresa.razao_social", read_only=True)
    filial_nome = serializers.CharField(source="filial.nome", read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "nome_completo", "email", "telefone", "cargo",
            "ativo", "empresa", "empresa_nome", "filial", "filial_nome",
            "perfis", "created_at",
        ]
        read_only_fields = ["id", "created_at"]


class UsuarioCreateSerializer(serializers.ModelSerializer):
    """Serializer para criação de usuário com senha."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = Usuario
        fields = [
            "nome_completo", "email", "password", "telefone",
            "cargo", "empresa", "filial",
        ]

    def create(self, validated_data):
        password = validated_data.pop("password")
        user = Usuario(**validated_data)
        user.set_password(password)
        user.save()
        return user


class UsuarioMeSerializer(serializers.ModelSerializer):
    """Dados do usuário autenticado — endpoint /api/core/me/"""
    perfis = PerfilSerializer(many=True, read_only=True)
    empresa = EmpresaSerializer(read_only=True)

    class Meta:
        model = Usuario
        fields = [
            "id", "nome_completo", "email", "telefone", "cargo",
            "empresa", "filial", "perfis",
        ]


class AuditLogSerializer(serializers.ModelSerializer):
    usuario_nome = serializers.CharField(source="usuario.nome_completo", read_only=True)

    class Meta:
        model = AuditLog
        fields = "__all__"
        read_only_fields = ["id", "created_at"]
