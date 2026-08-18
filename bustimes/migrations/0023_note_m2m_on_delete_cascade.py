from django.db import migrations

# Django hardcodes a Python-level CASCADE on the foreign keys of an implicit
# many-to-many table, so it creates them with no referential action at all.  Now
# that trips and stop times are deleted by the database, Django's collector
# never visits these rows: a NO ACTION constraint fails at COMMIT, long after
# the offending DELETE, and no constraint at all leaves them orphaned forever.
# Auto created models are exempt from the system checks, so nothing warns about
# either.  Give the constraints the ON DELETE CASCADE that the collector would
# otherwise have performed.

TABLES = (
    (
        "bustimes_trip_notes",
        "trip_id",
        "bustimes_trip",
        "id",
        "bustimes_trip_notes_trip_id_d43ae6a4_fk_bustimes_trip_id",
    ),
    (
        "bustimes_stoptime_notes",
        "stoptime_id",
        "bustimes_stoptime",
        "id",
        "bustimes_stoptime_no_stoptime_id_af3804eb_fk_bustimes_",
    ),
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
        ("bustimes", "0022_db_on_delete_trip_stoptime"),
    ]

    operations = [
        migrations.RunSQL(alter(*table), alter(*table, action="")) for table in TABLES
    ]
