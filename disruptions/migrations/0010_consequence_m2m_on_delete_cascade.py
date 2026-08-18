from django.db import migrations

# As in bustimes/migrations/0023_note_m2m_on_delete_cascade.py: consequences are
# now deleted by the database (via situation, via data source), so the implicit
# many-to-many tables need a referential action of their own.

TABLES = (
    ("disruptions_consequence_stops", "consequence_id"),
    ("disruptions_consequence_services", "consequence_id"),
    ("disruptions_consequence_operators", "consequence_id"),
)


def alter(table, column, action="ON DELETE CASCADE", confdeltype="c"):
    """Recreate a foreign key with a different referential action.

    Finds it by column rather than by name, and leaves it alone if it's already
    right - or if it isn't there at all.
    """
    return f"""
DO $$
DECLARE
    name text;
    ref_table text;
    ref_column text;
BEGIN
    SELECT c.conname, c.confrelid::regclass::text, ref.attname
    INTO name, ref_table, ref_column
    FROM pg_constraint c
    JOIN pg_attribute col ON col.attrelid = c.conrelid AND col.attnum = c.conkey[1]
    JOIN pg_attribute ref ON ref.attrelid = c.confrelid AND ref.attnum = c.confkey[1]
    WHERE c.contype = 'f'
        AND c.conrelid = to_regclass('{table}')
        AND col.attname = '{column}'
        AND c.confdeltype <> '{confdeltype}';
    IF name IS NOT NULL THEN
        EXECUTE format('ALTER TABLE {table} DROP CONSTRAINT %I', name);
        EXECUTE format(
            'ALTER TABLE {table} ADD CONSTRAINT %I FOREIGN KEY ({column})'
            ' REFERENCES %s (%I) {action} DEFERRABLE INITIALLY DEFERRED',
            name, ref_table, ref_column
        );
    END IF;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("disruptions", "0009_alter_affectedjourney_situation_and_more"),
    ]

    operations = [
        migrations.RunSQL(alter(table, column), alter(table, column, "", "a"))
        for table, column in TABLES
    ]
