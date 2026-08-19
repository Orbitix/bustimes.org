import hashlib
from pathlib import Path

import requests
from django.conf import settings
from django.core.files.base import ContentFile

from .models import Photo
from .tasks import detect_photo_subject


class WrongLicense(Exception):
    pass


def get_sha1(content):
    sha1 = hashlib.sha1(usedforsecurity=False)
    sha1.update(content)
    return sha1.hexdigest()


def add_uploaded_photo(image, vehicle, request):
    photo = Photo()
    content = image.read()
    suffix = Path(image.name).suffix.lower() or ".jpg"
    photo.image.save(get_sha1(content) + suffix, ContentFile(content))
    photo.user = request.user
    photo.save()
    photo.vehicles.add(vehicle)


def add_flickr_photo(url, vehicle, request):
    photo_id = url.split("/photos/", 1)[1].split("/")[1]
    photo = Photo()
    session = requests.Session()
    session.headers.update({"User-Agent": "bustimes.org"})
    session.params = {
        "format": "json",
        "api_key": settings.FLICKR_API_KEY,
        "photo_id": photo_id,
        "nojsoncallback": 1,
    }
    response = session.get(
        "https://www.flickr.com/services/rest",
        params={"method": "flickr.photos.getInfo"},
    )
    response.raise_for_status()
    info = response.json()
    photo.url = info["photo"]["urls"]["url"][0]["_content"]

    photo.license = info["photo"]["license"]
    if photo.license in ("0", "1", "2", "3", "14", "15", "16"):
        raise WrongLicense()

    if info["photo"]["owner"]["path_alias"] != "goodwinjoshua":
        photo.credit = (
            info["photo"]["owner"]["realname"] or info["photo"]["owner"]["username"]
        )
    photo.caption = info["photo"]["title"]["_content"]
    response = session.get(
        "https://www.flickr.com/services/rest",
        params={"method": "flickr.photos.getSizes"},
    )
    response.raise_for_status()
    sizes = response.json()
    url = sizes["sizes"]["size"][-1]["source"]
    original = session.get(url)
    photo.image.save(get_sha1(original.content) + ".jpg", ContentFile(original.content))
    photo.user = request.user
    photo.save()
    photo.vehicles.add(vehicle)
    detect_photo_subject(photo.id)
