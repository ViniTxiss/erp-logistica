import os
from django.core.management.base import BaseCommand, CommandError
from apps.core.models import Usuario

class Command(BaseCommand):
    help = "Cria um superusuário administrador de forma segura (sem interatividade ou via variáveis de ambiente)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            help="E-mail do administrador.",
        )
        parser.add_argument(
            "--password",
            type=str,
            help="Senha do administrador.",
        )
        parser.add_argument(
            "--nome",
            type=str,
            default="Administrador",
            help="Nome completo do administrador.",
        )

    def handle(self, *args, **options):
        # 1. Tenta obter argumentos passados por parâmetro ou variáveis de ambiente
        email = options.get("email") or os.environ.get("DJANGO_SUPERUSER_EMAIL") or os.environ.get("ADMIN_EMAIL")
        password = options.get("password") or os.environ.get("DJANGO_SUPERUSER_PASSWORD") or os.environ.get("ADMIN_PASSWORD")
        nome = options.get("nome") or os.environ.get("DJANGO_SUPERUSER_NOME") or "Administrador"

        if not email or not password:
            self.stdout.write(
                self.style.WARNING(
                    "Aviso: E-mail ou Senha não foram fornecidos. "
                    "Use os argumentos '--email' e '--password' ou configure as variáveis de ambiente "
                    "'DJANGO_SUPERUSER_EMAIL' e 'DJANGO_SUPERUSER_PASSWORD'."
                )
            )
            # Como fallback, tenta rodar de forma interativa se possível
            try:
                if not email:
                    email = input("E-mail: ")
                if not password:
                    import getpass
                    password = getpass.getpass("Senha: ")
            except (KeyboardInterrupt, EOFError):
                self.stdout.write(
                    self.style.WARNING(
                        "Execução não-interativa ou cancelada detectada. "
                        "Criação/atualização de administrador pulada."
                    )
                )
                return

        if not email or not password:
            raise CommandError("E-mail e senha são obrigatórios para criar o administrador.")

        # 2. Verifica se o usuário já existe
        if Usuario.objects.filter(email=email).exists():
            user = Usuario.objects.get(email=email)
            user.set_password(password)
            user.nome_completo = nome
            user.is_superuser = True
            user.is_staff = True
            user.ativo = True
            user.save()
            self.stdout.write(
                self.style.SUCCESS(f"Superusuário '{email}' já existia. Senha e dados atualizados com sucesso!")
            )
        else:
            # 3. Cria o superusuário
            Usuario.objects.create_superuser(
                email=email,
                password=password,
                nome_completo=nome
            )
            self.stdout.write(
                self.style.SUCCESS(f"Superusuário '{email}' criado com sucesso!")
            )
