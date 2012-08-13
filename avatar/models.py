import datetime
import os

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.base import ContentFile
from django.core.files.storage import get_storage_class
from django.utils.translation import ugettext as _
from django.utils.hashcompat import md5_constructor
from django.utils.encoding import smart_str
from django.db.models import signals

from avatar.tasks import create_default_thumbnails

try:
    from cStringIO import StringIO
    dir(StringIO) # Placate PyFlakes
except ImportError:
    from StringIO import StringIO

try:
    from PIL import Image
    dir(Image) # Placate PyFlakes
except ImportError:
    import Image

from avatar.util import invalidate_cache
from avatar.settings import (AVATAR_STORAGE_DIR, AVATAR_RESIZE_METHOD,
                             AVATAR_MAX_AVATARS_PER_USER, AVATAR_THUMB_FORMAT,
                             AVATAR_HASH_USERDIRNAMES, AVATAR_HASH_FILENAMES,
                             AVATAR_THUMB_QUALITY, AUTO_GENERATE_AVATAR_SIZES, 
                             AVATAR_USERDIRNAMES_AS_ID, AVATAR_STORAGE,
                             AVATAR_DEFAULT_SIZE)

avatar_storage = get_storage_class(AVATAR_STORAGE)()

def avatar_file_path(instance=None, filename=None, size=None, ext=None):
    tmppath = [AVATAR_STORAGE_DIR]
    if AVATAR_HASH_USERDIRNAMES:
        tmp = md5_constructor(instance.user.username).hexdigest()
        tmppath.extend([tmp[0], tmp[1], instance.user.username])
    elif AVATAR_USERDIRNAMES_AS_ID:
        tmppath.append(str(instance.user.id))
    else:
        tmppath.append(instance.user.username)
    if not filename:
        # Filename already stored in database
        filename = instance.avatar.name
        if ext and AVATAR_HASH_FILENAMES:
            # An extension was provided, probably because the thumbnail
            # is in a different format than the file. Use it. Because it's
            # only enabled if AVATAR_HASH_FILENAMES is true, we can trust
            # it won't conflict with another filename
            (root, oldext) = os.path.splitext(filename)
            filename = root + "." + ext
    else:
        # File doesn't exist yet
        if AVATAR_HASH_FILENAMES:
            (root, ext) = os.path.splitext(filename)
            filename = md5_constructor(smart_str(filename)).hexdigest()
            filename = filename + ext
    if size:
        tmppath.extend(['resized', str(size)])
    tmppath.append(os.path.basename(filename))
    return os.path.join(*tmppath)

def find_extension(format):
    format = format.lower()

    if format == 'jpeg':
        format = 'jpg'

    return format

class Avatar(models.Model):
    user = models.ForeignKey(User)
    primary = models.BooleanField(default=False)
    avatar = models.ImageField(max_length=1024,
        upload_to=avatar_file_path, storage=avatar_storage, blank=True)
    date_uploaded = models.DateTimeField(auto_now=True)
    existing_thumbnail_sizes = models.CommaSeparatedIntegerField(max_length=1024, blank=True)
    
    def __unicode__(self):
        return _(u'Avatar for %s') % self.user
    
    def save(self, *args, **kwargs):
        square = kwargs.pop('square', False)
        avatars = Avatar.objects.filter(user=self.user)
        if self.pk:
            avatars = avatars.exclude(pk=self.pk)
        
        if AVATAR_MAX_AVATARS_PER_USER > 1:
            if self.primary:
                avatars = avatars.filter(primary=True)
                avatars.update(primary=False)
        else:
            avatars.delete()
            
        invalidate_cache(self.user)
        is_new = False
        if not self.id:
            is_new = True
        super(Avatar, self).save(*args, **kwargs)
        if is_new:
            create_default_thumbnails.delay(self, created=True, square=square)
    
    def delete(self, *args, **kwargs):
        invalidate_cache(self.user)
        super(Avatar, self).delete(*args, **kwargs)
    
    def thumbnail_exists(self, size):
		return (self.existing_thumbnail_sizes and
            str(size) in self.existing_thumbnail_sizes.split(','))
	
	# This is the older version of thumbnail_exists.
	# It requires a little more I/O than the version here,
	# but if database size for the avatars table becomes
	# an issue, you can always return to this version and
	# delete the existing_thumbnail_sizes column.
	# It's a tradeoff and I'm not sure which is better, so
	# I'm just leaving this here for future developers
	# in case they disagree with my decision.
	#def thumbnail_exists(self, size):
    #    return self.avatar.storage.exists(self.avatar_name(size))
    
    def create_thumbnail(self, size, quality=None, square=False):
        """ Creates a thumbnail for this avatar. 
        
            If Square is False, the image will retain it's original proportions.
            Also, when square is false, size then dictates the height of the new image
        """
        if self.primary:
            square = True

        # invalidate the cache of the thumbnail with the given size first
        invalidate_cache(self.user, size)
        try:
			# The line below relies on the "upload_to" field.
			# If you want to get rid of that column, one of the things you will
			# need to do is comment out the line below and uncomment the line
			# after it.
            orig = self.avatar.storage.open(self.avatar.name, 'rb').read()
            #orig = avatar_storage.open(self.avatar.name, 'rb').read()
            image = Image.open(StringIO(orig))
        except IOError:
            return # What should we do here?  Render a "sorry, didn't work" img?
        quality = quality or AVATAR_THUMB_QUALITY
        (w, h) = image.size
        if w != size or h != size:
            if square:
                if w > h:
                    diff = (w - h) / 2
                    image = image.crop((diff, 0, w - diff, h))
                else:
                    diff = (h - w) / 2
                    image = image.crop((0, diff, w, h - diff))
                w = size
                h = size
            else:
                scaling_ratio = 1.0*size/h
                h = int(size)
                w = int(scaling_ratio * w)
            if image.mode != "RGB":
                image = image.convert("RGB")
            image = image.resize((w, h), AVATAR_RESIZE_METHOD)
            thumb = StringIO()
            image.save(thumb, AVATAR_THUMB_FORMAT, quality=quality)
            thumb_file = ContentFile(thumb.getvalue())
        else:
            thumb_file = ContentFile(orig)

		# See above comment about the "upload_to" field.
		# Commenting out the line below and uncommenting
		# the line below it will allow you to remove it.
        thumb = self.avatar.storage.save(self.avatar_name(size), thumb_file)
		#thumb = avatar_storage.save(self.avatar_name(size), thumb_file)

        # Save this image size in the database so we know what thumbnails have already been created
        size_string = str(size)
        if self.existing_thumbnail_sizes:
            size_string = ',' + size_string
        self.existing_thumbnail_sizes += size_string
        self.save()

    def avatar_url(self, size=None):
        if size:
            return self.avatar.storage.url(self.avatar_name(size))
        else:
            return self.avatar.url

    def get_absolute_url(self, size=AVATAR_DEFAULT_SIZE):
        return self.avatar_url(size)
    
    def avatar_name(self, size):
        ext = find_extension(AVATAR_THUMB_FORMAT)
        return avatar_file_path(
            instance=self,
            size=size,
            ext=ext
        )

signals.post_save.connect(create_default_thumbnails, sender=Avatar)
