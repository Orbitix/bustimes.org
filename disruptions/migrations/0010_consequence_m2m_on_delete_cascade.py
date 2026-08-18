from django.db import migrations

# As in bustimes/migrations/0023_note_m2m_on_delete_cascade.py: consequences are
# now deleted by the database (via situation, via data source), so the implicit
# many-to-many tables need a referential action of their own.

TABLES = tuple(
    (
        f"disruptions_consequence_{name}",
        "consequence_id",
        "disruptions_consequence",
        "id",
        constraint,
    )
    for name, constraint in (
        ("stops", "disruptions_conseque_consequence_id_36e20315_fk_disruptio"),
        ("services", "disruptions_conseque_consequence_id_1ade66e4_fk_disruptio"),
        ("operators", "disruptions_conseque_consequence_id_b2fb2b34_fk_disruptio"),
    )
)


def alter(table, column, ref_table, ref_column, constraint, action="ON DELETE CASCADE"):
    """Give a foreign key a referential action, creating it if need be.

    Finds the existing constraint by column rather than by name, and leaves it
    alone if it's already right.  A database restored without its referenced
    table has no constraint here at all - and so may have collected rows that
    would fail to validate - so tidy those away first.
    """
    deltype = "c" if action else "a"
    return f"""
DO $$
DECLARE
    name text;
    deltype "char";
BEGIN
    SELECT c.conname, c.confdeltype INTO name, deltype
    FROM pg_constraint c
    JOIN pg_attribute col ON col.attrelid = c.conrelid AND col.attnum = c.conkey[1]
    WHERE c.contype = 'f'
        AND c.conrelid = to_regclass('{table}')
        AND col.attname = '{column}';

    IF name IS NOT NULL AND deltype = '{deltype}' THEN
        RETURN;
    ELSIF name IS NULL THEN
        DELETE FROM {table} t
        WHERE NOT EXISTS (
            SELECT FROM {ref_table} r WHERE r.{ref_column} = t.{column}
        );
    ELSE
        EXECUTE format('ALTER TABLE {table} DROP CONSTRAINT %I', name);
    END IF;

    ALTER TABLE {table} ADD CONSTRAINT "{constraint}"
        FOREIGN KEY ({column}) REFERENCES {ref_table} ({ref_column})
        {action} DEFERRABLE INITIALLY DEFERRED;
END $$;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("disruptions", "0009_alter_affectedjourney_situation_and_more"),
    ]

    operations = [
        migrations.RunSQL(alter(*table), alter(*table, action="")) for table in TABLES
    ]
