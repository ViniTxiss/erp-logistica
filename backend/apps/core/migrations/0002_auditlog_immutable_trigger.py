from django.db import migrations


def create_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("""
            CREATE OR REPLACE FUNCTION prevent_auditlog_mutation()
            RETURNS TRIGGER AS $$
            BEGIN
                RAISE EXCEPTION 'AuditLog é imutável. Operação %% negada.', TG_OP;
                RETURN NULL;
            END;
            $$ LANGUAGE plpgsql;
        """)
        schema_editor.execute("""
            CREATE TRIGGER auditlog_immutable
            BEFORE UPDATE OR DELETE ON core_auditlog
            FOR EACH ROW EXECUTE FUNCTION prevent_auditlog_mutation();
        """)
    elif schema_editor.connection.vendor == "sqlite":
        schema_editor.execute("""
            CREATE TRIGGER IF NOT EXISTS auditlog_no_update
            BEFORE UPDATE ON core_auditlog
            BEGIN
                SELECT RAISE(FAIL, 'AuditLog é imutável. Operação UPDATE negada.');
            END;
        """)
        schema_editor.execute("""
            CREATE TRIGGER IF NOT EXISTS auditlog_no_delete
            BEFORE DELETE ON core_auditlog
            BEGIN
                SELECT RAISE(FAIL, 'AuditLog é imutável. Operação DELETE negada.');
            END;
        """)


def drop_trigger(apps, schema_editor):
    if schema_editor.connection.vendor == "postgresql":
        schema_editor.execute("DROP TRIGGER IF EXISTS auditlog_immutable ON core_auditlog;")
        schema_editor.execute("DROP FUNCTION IF EXISTS prevent_auditlog_mutation();")
    elif schema_editor.connection.vendor == "sqlite":
        schema_editor.execute("DROP TRIGGER IF EXISTS auditlog_no_update;")
        schema_editor.execute("DROP TRIGGER IF EXISTS auditlog_no_delete;")


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(
            create_trigger,
            reverse_code=drop_trigger,
        ),
    ]
