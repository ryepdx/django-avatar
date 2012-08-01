from celery.decorators import task

from avatar.settings import AUTO_GENERATE_AVATAR_SIZES


@task(ignore_result=True)
def create_default_thumbnails(instance=None, created=False, square=False, **kwargs):
    if created:
        for size in AUTO_GENERATE_AVATAR_SIZES:
            instance.create_thumbnail(size, square=square)
