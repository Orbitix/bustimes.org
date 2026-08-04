import logging

from huey.contrib.djhuey import db_task

from .detect import update_photo
from .models import Photo

logger = logging.getLogger(__name__)


@db_task()
def detect_photo_subject(photo_id: int):
    """Runs in a huey worker, so the web workers don't each have to keep the
    object detection model in memory
    """
    photo = Photo.objects.get(id=photo_id)
    try:
        update_photo(photo)
    except Exception:
        # a photo with no bounding box just gets cropped the old way
        logger.exception("detecting subject of photo %d", photo_id)
