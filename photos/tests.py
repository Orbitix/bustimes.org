from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import InMemoryStorage
from django.test import TestCase, override_settings
from PIL import Image

from busstops.models import Operator, Region
from vehicles.models import Vehicle

from .detect import get_subject
from .models import Photo
from .processors import SmartCrop


def make_jpeg(width, height, bus=None):
    """A red image, optionally with a blue "bus" in it (a box given as
    fractions of the image size)
    """
    image = Image.new("RGB", (width, height), "red")
    if bus:
        x1, y1, x2, y2 = bus
        image.paste(
            Image.new(
                "RGB", (round((x2 - x1) * width), round((y2 - y1) * height)), "blue"
            ),
            (round(x1 * width), round(y1 * height)),
        )
    buf = BytesIO()
    image.save(buf, "JPEG")
    return buf.getvalue()


def blueness(image):
    """What proportion of the pixels are more blue than red"""
    pixels = list(image.convert("RGB").getdata())
    return sum(b > r for r, g, b in pixels) / len(pixels)


class SmartCropTest(TestCase):
    def test_grows_box_to_aspect_ratio(self):
        image = Image.new("RGB", (1000, 1000))

        # a wide box in the middle, cropped to a square
        cropped = SmartCrop([0.3, 0.4, 0.7, 0.6], padding=0).process(image)
        self.assertEqual(cropped.size, (400, 400))

        # a tall box, cropped to 2:1
        cropped = SmartCrop([0.4, 0.2, 0.6, 0.8], aspect=2, padding=0).process(image)
        self.assertEqual(cropped.size, (1000, 500))

    def test_padding(self):
        image = Image.new("RGB", (1000, 500))
        cropped = SmartCrop([0.4, 0.4, 0.6, 0.6], aspect=1, padding=0.5).process(image)
        # 200 wide + 50% padding either side = 400, and square
        self.assertEqual(cropped.size, (400, 400))

    def test_stays_inside_the_image(self):
        image = Image.new("RGB", (1000, 500))

        # a box in the corner - the crop should be nudged, not shrunk
        cropped = SmartCrop([0, 0, 0.2, 0.2], aspect=1, padding=0.5).process(image)
        self.assertEqual(cropped.size, (400, 400))

        # a box bigger than the image can be cropped to
        cropped = SmartCrop([0, 0, 1, 1], aspect=1, padding=0.5).process(image)
        self.assertEqual(cropped.size, (500, 500))


class GetSubjectTest(TestCase):
    def test_prefers_the_biggest_bus(self):
        subject = get_subject(
            [
                (5, 0.9, [0.1, 0.1, 0.3, 0.3]),  # a small bus
                (7, 0.6, [0.4, 0.1, 0.9, 0.8]),  # a bigger truck
                (2, 0.99, [0, 0, 1, 1]),  # a huge, confident car
            ]
        )
        self.assertEqual(subject, [0.4, 0.1, 0.9, 0.8])

    def test_falls_back_to_a_big_car(self):
        subject = get_subject(
            [
                (0, 0.9, [0, 0, 1, 1]),  # a person - not a vehicle
                (2, 0.7, [0.2, 0.2, 0.8, 0.8]),
            ]
        )
        self.assertEqual(subject, [0.2, 0.2, 0.8, 0.8])

    def test_ignores_small_cars(self):
        # a parked car in the background isn't what the photo is of
        self.assertIsNone(get_subject([(2, 0.9, [0.1, 0.1, 0.2, 0.2])]))

    def test_no_detections(self):
        self.assertIsNone(get_subject([]))

    def test_clamps_to_the_image(self):
        subject = get_subject([(5, 0.9, [-0.02, 0.1, 1.03, 0.9])])
        self.assertEqual(subject, [0, 0.1, 1, 0.9])


@override_settings(
    STORAGES={
        "default": {"BACKEND": "django.core.files.storage.InMemoryStorage"},
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        },
    }
)
class PhotoTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        region = Region.objects.create(id="EA", name="East Anglia")
        operator = Operator.objects.create(
            region=region, name="Lynx", noc="LYNX", slug="lynx"
        )
        cls.vehicle = Vehicle.objects.create(
            code="2", fleet_number=2, operator=operator
        )

        photo = Photo(credit="Josh", caption="a bus")
        photo.image.save("bus.jpg", ContentFile(make_jpeg(1600, 900)))
        photo.vehicles.add(cls.vehicle)

    def test_vehicle_detail_photo(self):
        """the img tag should have the right dimensions, and getting them
        shouldn't open the image from storage more than once
        """
        opens = []
        real_open = InMemoryStorage.open

        def counting_open(self, name, mode="rb"):
            opens.append(name)
            return real_open(self, name, mode)

        InMemoryStorage.open = counting_open
        try:
            response = self.client.get(self.vehicle.get_absolute_url())
        finally:
            InMemoryStorage.open = real_open

        self.assertContains(response, 'width="320" height="180"')
        self.assertEqual(len(opens), 1)

    def test_no_bounding_box(self):
        """with no detected vehicle, the whole photo is used, as before"""
        photo = Photo.objects.get()
        self.assertIsNone(photo.bbox)
        self.assertLess(blueness(Image.open(photo.image_320)), 0.01)
        self.assertEqual(Image.open(photo.image_1200_630).size, (1200, 630))

    def test_smart_crop(self):
        """the crops should close in on the detected vehicle"""
        bus = [0.5, 0.55, 0.95, 0.95]
        photo = Photo(caption="a bus", bbox=bus)
        photo.image.save("bus.jpg", ContentFile(make_jpeg(1600, 900, bus=bus)))

        thumbnail = Image.open(photo.image_320)
        # same shape as before, but now mostly bus
        self.assertEqual(thumbnail.size, (320, 180))
        self.assertGreater(blueness(thumbnail), 0.5)

        open_graph = Image.open(photo.image_1200_630)
        self.assertEqual(open_graph.size, (1200, 630))
        self.assertGreater(blueness(open_graph), 0.5)

    def test_moving_the_box_regenerates_the_crops(self):
        """so correcting a bad bounding box in the admin takes effect"""
        photo = Photo.objects.get()
        before = photo.image_320.name

        photo.bbox = [0.5, 0.55, 0.95, 0.95]
        self.assertNotEqual(photo.image_320.name, before)
