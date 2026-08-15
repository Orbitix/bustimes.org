from django.conf import settings
from django.contrib.gis.db import models
from imagekit.models import ImageSpecField
from imagekit.processors import ResizeToFill, ResizeToFit


class Photo(models.Model):
    image = models.ImageField()
    image_1200_630 = ImageSpecField(
        source="image",
        processors=[ResizeToFill(1200, 630)],
        format="JPEG",
        options={"quality": 60},
    )
    image_1200 = ImageSpecField(
        source="image",
        processors=[ResizeToFit(1200, upscale=False)],
        format="JPEG",
        options={"quality": 60},
    )
    image_320 = ImageSpecField(
        source="image",
        processors=[ResizeToFit(320, upscale=False)],
        format="JPEG",
        options={"quality": 60},
    )
    credit = models.CharField(max_length=255, blank=True)
    caption = models.CharField(max_length=255, blank=True)
    url = models.URLField(blank=True, verbose_name="URL")
    created_at = models.DateTimeField(null=True, blank=True)
    license = models.CharField(null=True, blank=True)

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, null=True, blank=True
    )

    vehicles = models.ManyToManyField("vehicles.Vehicle", blank=True)

    livery = models.ForeignKey(
        "vehicles.Livery", models.SET_NULL, null=True, blank=True
    )
    vehicle_type = models.ForeignKey(
        "vehicles.VehicleType", models.SET_NULL, null=True, blank=True
    )
    service = models.ForeignKey(
        "busstops.Service", models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return self.caption

    def get_absolute_url(self):
        if vehicle := self.vehicles.first():
            return vehicle.get_absolute_url()
        return ""
