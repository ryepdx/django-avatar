django-avatar
-------------

Django-avatar is a reusable application for handling user avatars.  It has the
ability to default to Gravatar if no avatar is found for a certain user.
Django-avatar automatically generates thumbnails and stores them to your default
file storage backend for retrieval later.

Documentation can be found under /docs/

Why another fork?
-----------------

I wanted users to have just one avatar on my website, so I decided to look at the commit graph on Github to see if anyone had already implemented that functionality. I noticed someone had, but I also noticed that this project hadn't been touched in over a year by the maintainer listed on PyPi and was being more vigorously kept up by tens of other developers, many of whom (judging by the commit comments) were fixing a number of the same problems over and over.

So I picked what seemed to me the most vigorously maintained fork and forked it with the intention of merging in as many as the other 90+ forks as possible.

What's New?
-----------
- The delete method on Avatar objects actually deletes the underlying file and thumbnails now.
- A number of template tags were added by various contributors.
- Django 1.4 compatibility.
- Celery is now required. Thumbnail generation is a Celery task in this fork. In the near future this will be optional, but a fork I merged in required it, so my fork does too now. I found this website helpful in getting things up and running with Celery: http://query7.com/tutorial-celery-with-django
- Support for aspect ratio preservation.
- Support for SSL with Gravatar, which should help all you folks plagued by "mixed content" warnings.
- Support for using hashes of usernames (settings.AVATAR_HASH_USERDIRNAMES) or user IDs (settings.AVATAR_USERDIRNAMES_AS_ID) for avatar directory names.
- Support for specifying which storage class you would like to use. (settings.AVATAR_STORAGE)

Fitness for use
---------------

Right now the code may or may not work. I have a copy running on my development box that uses the 'add' view just fine. But I haven't thoroughly tested the code just yet. There aren't tests for everything I've merged in yet. Those tests need to be written. Until they are, understand that there may be pretty obvious bugs lurking about that I just haven't caught yet. Especially since I just forked this and started playing with it today.

