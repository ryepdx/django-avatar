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
