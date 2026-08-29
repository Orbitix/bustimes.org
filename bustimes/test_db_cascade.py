from datetime import UTC, date, datetime, timedelta

from django.db import transaction
from django.test import TransactionTestCase

from busstops.models import DataSource, StopPoint
from vehicles.models import Vehicle, VehicleJourney

from .models import Note, Route, StopTime, Trip


class DatabaseCascadeTest(TransactionTestCase):
    """The foreign keys from route down to stop time use on_delete=DB_CASCADE.

    Django's collector doesn't visit those rows at all, so nothing in Python
    checks that the database will actually let them go.  A missing ON DELETE on
    any of the tables involved - the implicit many-to-many tables especially -
    only shows up as an integrity error at COMMIT.
    """

    def test_deleting_a_route_cascades(self):
        source = DataSource.objects.create(name="test")
        route = Route.objects.create(source=source, code="test")
        trip = Trip.objects.create(
            route=route, start=timedelta(0), end=timedelta(minutes=1)
        )
        stop = StopPoint.objects.create(
            atco_code="test", common_name="Test Stop", active=True
        )
        stop_time = StopTime.objects.create(trip=trip, stop=stop, sequence=0)

        note = Note.objects.create(code="X", text="explanatory")
        trip.notes.add(note)
        stop_time.notes.add(note)

        vehicle = Vehicle.objects.create()
        journey = VehicleJourney.objects.create(
            trip=trip,
            vehicle=vehicle,
            source=source,
            datetime=datetime(2026, 8, 18, 9, tzinfo=UTC),
            date=date(2026, 8, 18),
        )

        # a transaction of its own, so a deferred constraint gets to fail
        with transaction.atomic():
            self.assertEqual(
                Route.objects.filter(id=route.id).delete(), (1, {"bustimes.Route": 1})
            )

        self.assertFalse(Trip.objects.filter(id=trip.id).exists())
        self.assertFalse(StopTime.objects.filter(id=stop_time.id).exists())
        self.assertFalse(Trip.notes.through.objects.exists())
        self.assertFalse(StopTime.notes.through.objects.exists())

        # the note itself is not a casualty
        self.assertTrue(Note.objects.filter(id=note.id).exists())

        # journey history survives, minus the link to the trip
        journey.refresh_from_db()
        self.assertIsNone(journey.trip_id)
