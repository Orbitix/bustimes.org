import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import connection

logger = logging.getLogger(__name__)


def get_content(slug):
    content = f"[{slug}](https://bustimes.org/vehicles/{slug})"

    if slug[:4] in ("sndr", "obus", "scmy", "amsy", "kctb", "simo", "lynx"):
        content = f"{content} <@813528710404898817>"

    return content


class Command(BaseCommand):
    def handle(self, *args, **options):
        assert settings.NEW_VEHICLE_WEBHOOK_URL, "NEW_VEHICLE_WEBHOOK_URL is not set"

        session = requests.Session()

        with connection.cursor() as cursor:
            cursor.execute("""CREATE OR REPLACE FUNCTION notify_new_vehicle()
                           RETURNS trigger AS $$
                           BEGIN
                           PERFORM pg_notify('new_vehicle', NEW.slug);
                           RETURN NEW;
                           END;
                           $$ LANGUAGE plpgsql;""")
            cursor.execute("""CREATE OR REPLACE TRIGGER notify_new_vehicle
                           AFTER INSERT ON vehicles_vehicle
                           FOR EACH ROW
                           EXECUTE PROCEDURE notify_new_vehicle();""")

            cursor.execute("LISTEN new_vehicle")
            gen = cursor.connection.notifies()
            for notify in gen:
                logger.info(notify)

                if notify.payload.startswith("rtcsnv-") or len(notify.payload) > 40:
                    continue

                response = session.post(
                    settings.NEW_VEHICLE_WEBHOOK_URL,
                    json={
                        "username": "bot",
                        "content": get_content(notify.payload),
                    },
                    timeout=10,
                )

                logger.info("%s %s %s", response, response.headers, response.text)

                time.sleep(5)
