from django.db import migrations

# Django hardcodes a Python-level CASCADE on the foreign keys of an implicit
# many-to-many table, so it creates them with no referential action at all.  Now
# that trips and stop times are deleted by the database, those NO ACTION
# constraints would fail at COMMIT, long after the offending DELETE.  Auto
# created models are also exempt from the system checks, so nothing warns about
# it.  Give the constraints the ON DELETE CASCADE that Django's collector would
# otherwise have performed.

TABLES = (
    ("bustimes_trip_notes", "trip_id"),
    ("bustimes_stoptime_notes", "stoptime_id"),
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
        ("bustimes", "0022_db_on_delete_trip_stoptime"),
    ]

    operations = [
        migrations.RunSQL(alter(table, column), alter(table, column, "", "a"))
        for table, column in TABLES
    ]
