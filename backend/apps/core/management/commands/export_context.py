"""
Comando Django: python manage.py export_context

Gera um snapshot em Markdown do estado real do projeto — migrations,
models, testes e cobertura por módulo. Usado para atualizar o CONTEXT.md
automaticamente sem depender de memória humana ou da IA.

Uso:
    python manage.py export_context              # imprime no stdout
    python manage.py export_context > CONTEXT_AUTO.md  # salva em arquivo
    python manage.py export_context --patch CONTEXT.md # atualiza seção no arquivo
"""
import os
import subprocess
from datetime import datetime
from pathlib import Path

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import connection


# Módulos que fazem parte do projeto (excluindo apps Django/terceiros)
LOCAL_APPS = ["core", "wms", "tms", "crm"]

# Raiz do backend
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent


class Command(BaseCommand):
    help = "Gera snapshot do estado atual do projeto para o CONTEXT.md"

    def add_arguments(self, parser):
        parser.add_argument(
            "--patch",
            metavar="ARQUIVO",
            help="Atualiza a seção '## 3. Estado atual dos módulos' no arquivo especificado",
        )
        parser.add_argument(
            "--section",
            choices=["all", "modules", "migrations", "tests"],
            default="all",
            help="Qual seção gerar (padrão: all)",
        )

    def handle(self, *args, **options):
        section = options["section"]
        patch_file = options.get("patch")

        lines = []
        lines.append(f"<!-- gerado por: python manage.py export_context -->")
        lines.append(f"<!-- data: {datetime.now().strftime('%Y-%m-%d %H:%M')} -->")
        lines.append("")

        if section in ("all", "modules"):
            lines += self._section_modules()

        if section in ("all", "migrations"):
            lines += self._section_migrations()

        if section in ("all", "tests"):
            lines += self._section_tests()

        output = "\n".join(lines)

        if patch_file:
            self._patch_file(patch_file, output)
            self.stdout.write(self.style.SUCCESS(f"✅  {patch_file} atualizado"))
        else:
            self.stdout.write(output)

    # ─── Seção: Estado dos módulos ────────────────────────────────────────────

    def _section_modules(self):
        lines = ["## 3. Estado atual dos módulos", ""]
        lines.append(
            "| Módulo | Models | Serializers | Views | Admin | Testes | Fixtures |"
        )
        lines.append(
            "|--------|:------:|:-----------:|:-----:|:-----:|:------:|:--------:|"
        )

        for app_label in LOCAL_APPS:
            row = self._check_app(app_label)
            lines.append(
                f"| **{app_label.upper()}** "
                f"| {row['models']} "
                f"| {row['serializers']} "
                f"| {row['views']} "
                f"| {row['admin']} "
                f"| {row['tests']} "
                f"| {row['fixtures']} |"
            )

        # Total de testes
        total = self._count_total_tests()
        lines.append("")
        lines.append(f"**Total de testes coletados pelo pytest:** {total}")
        lines.append("")
        return lines

    def _check_app(self, app_label):
        app_dir = BACKEND_DIR / "apps" / app_label

        def exists(filename):
            f = app_dir / filename
            return "✅" if f.exists() and f.stat().st_size > 50 else "❌"

        def check_tests():
            test_dir = app_dir / "tests"
            if not test_dir.exists():
                return "❌"
            test_files = list(test_dir.glob("test_*.py"))
            if not test_files:
                return "❌"
            total_lines = sum(
                len(tf.read_text(encoding="utf-8").splitlines())
                for tf in test_files
            )
            return f"✅ {len(test_files)}arq/{total_lines}L"

        def check_fixtures():
            fixture_dir = app_dir / "fixtures"
            if not fixture_dir.exists():
                return "❌"
            fixtures = list(fixture_dir.glob("*.json"))
            return f"✅ {len(fixtures)}" if fixtures else "❌"

        return {
            "models":      exists("models.py"),
            "serializers": exists("serializers.py"),
            "views":       exists("views.py"),
            "admin":       exists("admin.py"),
            "tests":       check_tests(),
            "fixtures":    check_fixtures(),
        }

    def _count_total_tests(self):
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "apps/", "--collect-only", "-q",
                 "--no-header", "--settings=config.settings.test"],
                capture_output=True, text=True,
                cwd=str(BACKEND_DIR),
                timeout=30,
            )
            # Última linha: "X tests collected" ou similar
            for line in reversed(result.stdout.splitlines()):
                if "test" in line and ("selected" in line or "collected" in line):
                    return line.strip()
            return "N/A (execute pytest manualmente)"
        except Exception:
            return "N/A (pytest não disponível)"

    # ─── Seção: Migrations ────────────────────────────────────────────────────

    def _section_migrations(self):
        lines = ["## Migrations por módulo", ""]
        for app_label in LOCAL_APPS:
            migration_dir = BACKEND_DIR / "apps" / app_label / "migrations"
            if not migration_dir.exists():
                lines.append(f"- **{app_label}**: sem pasta migrations")
                continue
            migrations = sorted(
                f.name for f in migration_dir.glob("*.py")
                if f.name != "__init__.py"
            )
            lines.append(f"- **{app_label}** ({len(migrations)} migration(s)):")
            for m in migrations:
                lines.append(f"  - `{m}`")
        lines.append("")
        return lines

    # ─── Seção: Testes ────────────────────────────────────────────────────────

    def _section_tests(self):
        lines = ["## Cobertura de testes por módulo", ""]
        for app_label in LOCAL_APPS:
            test_dir = BACKEND_DIR / "apps" / app_label / "tests"
            if not test_dir.exists():
                lines.append(f"- **{app_label}**: ❌ sem testes")
                continue
            test_files = list(test_dir.glob("test_*.py"))
            if not test_files:
                lines.append(f"- **{app_label}**: ❌ pasta existe mas sem arquivos test_*.py")
                continue

            lines.append(f"- **{app_label}**: ✅")
            for tf in sorted(test_files):
                content = tf.read_text(encoding="utf-8")
                n_classes = content.count("\nclass Test")
                n_defs = content.count("\n    def test_")
                lines.append(
                    f"  - `{tf.name}` — {n_classes} classe(s), {n_defs} teste(s)"
                )
        lines.append("")
        return lines

    # ─── Patch: substitui seção no CONTEXT.md ────────────────────────────────

    def _patch_file(self, filepath, new_content):
        target = Path(filepath)
        if not target.exists():
            target.write_text(new_content, encoding="utf-8")
            return

        original = target.read_text(encoding="utf-8")
        start_marker = "## 3. Estado atual dos módulos"
        end_marker = "\n## "  # próxima seção de nível 2

        start_idx = original.find(start_marker)
        if start_idx == -1:
            # Seção não encontrada → acrescenta ao final
            target.write_text(original + "\n\n" + new_content, encoding="utf-8")
            return

        end_idx = original.find(end_marker, start_idx + len(start_marker))
        if end_idx == -1:
            end_idx = len(original)

        updated = original[:start_idx] + new_content + original[end_idx:]
        target.write_text(updated, encoding="utf-8")
