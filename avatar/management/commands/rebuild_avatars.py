from datetime import datetime, timedelta
from optparse import make_option

from django.core.management.base import BaseCommand

from avatar.models import Avatar
from avatar.settings import AUTO_GENERATE_AVATAR_SIZES

class Command(BaseCommand):
    """ Regenerates avatar thumbnails for the sizes specified in
        settings.AUTO_GENERATE_AVATAR_SIZES."""
    help = __doc__

    option_list = BaseCommand.option_list + (
        make_option('--dry-run',
            action='store_true',
            dest='dryrun',
            default=False,
            help='Print what would be rebuilt without actually doing it'),

        make_option('--last-login',
            action='store',
            dest='lastlogin',
            default=None,
            help='Only rebuild avatars for users that logged in in the last <interval> days'),
    )


    def handle(self, **options):
        filters = {}
        if options['lastlogin']:
                filters['user__last_login__gt'] = datetime.now() - timedelta(days=int(options['lastlogin']))
        qs = Avatar.objects.filter(**filters)
        if options['dryrun']:
            print "Would rebuild %d avatars, each in %d different sizes %s" % (qs.count(), len(AUTO_GENERATE_AVATAR_SIZES), str(AUTO_GENERATE_AVATAR_SIZES))
        else:
            count = qs.count()
            for i, avatar in enumerate(qs.iterator()):
                for size in AUTO_GENERATE_AVATAR_SIZES:
                    print "Rebuilding Avatar %d / %d id=%s at size %s." % (i + 1, count, avatar.id, size)
                    avatar.create_thumbnail(size)