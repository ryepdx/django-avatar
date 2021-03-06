from urlparse import urlparse
from django.core.files.base import ContentFile
from django.http import HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages

from avatar.forms import PrimaryAvatarForm, DeleteAvatarForm, UploadAvatarForm
from avatar.models import Avatar
from avatar.settings import AVATAR_MAX_AVATARS_PER_USER, AVATAR_DEFAULT_SIZE
from avatar.signals import avatar_updated
from avatar.util import get_primary_avatar, get_default_avatar_url

def _validate_next_parameter(request, next):
    parsed = urlparse(next)
    if parsed and parsed.path:
        return parsed.path
    return None

def _get_next(request):
    """
    The part that's the least straightforward about views in this module is how they 
    determine their redirects after they have finished computation.

    In short, they will try and determine the next place to go in the following order:

    1. If there is a variable named ``next`` in the *POST* parameters, the view will
    redirect to that variable's value.
    2. If there is a variable named ``next`` in the *GET* parameters, the view will
    redirect to that variable's value.
    3. If Django can determine the previous page from the HTTP headers, the view will
    redirect to that previous page.
    """
    next = request.POST.get('next', request.GET.get('next',
        request.META.get('HTTP_REFERER', None)))
    if next:
        next = _validate_next_parameter(request, next)
    if not next:
        next = request.path
    return next

def _get_avatars(user):
    # Default set. Needs to be sliced, but that's it. Keep the natural order.
    avatars = user.avatar_set.all()
    
    # Current avatar
    primary_avatar = avatars.order_by('-primary')[:1]
    if primary_avatar:
        avatar = primary_avatar[0]
    else:
        avatar = None
    
    if AVATAR_MAX_AVATARS_PER_USER == 1:
        avatars = primary_avatar
    else:
        # Slice the default set now that we used the queryset for the primary avatar
        avatars = avatars[:AVATAR_MAX_AVATARS_PER_USER]
    return (avatar, avatars)


@csrf_exempt
def webcam_upload(request, id):
    # TODO: add proper security by attaching session to flash request
    user = get_object_or_404(User, pk=id)
    if request.method == "POST":
        avatar = Avatar(user=user, primary=True)
        avatar.avatar.save("%s_webcam_%s.jpg" %
                          (user.pk, Avatar.objects.filter(user=user).count()),
                           ContentFile(request.raw_post_data))
        avatar.save()
        messages.success(request, _("Successfully uploaded a new avatar."))
        return HttpResponse(status=200, content="ok")
        
        
@login_required
def add(request, extra_context=None, next_override=None,
        upload_form=UploadAvatarForm, *args, **kwargs):
    if extra_context is None:
        extra_context = {}
    user = kwargs.pop('user',None) or request.user    
    avatar, avatars = _get_avatars(user)
    upload_avatar_form = upload_form(request.POST or None,
        request.FILES or None, user=user)
    if request.method == "POST" and 'avatar' in request.FILES:
        if upload_avatar_form.is_valid():
            avatar = Avatar(
                user = user,
                primary = True,
            )
            image_file = request.FILES['avatar']
            avatar.avatar.save(image_file.name, image_file)
            avatar.save()
            messages.success(request, _("Successfully uploaded a new avatar."))
            avatar_updated.send(sender=Avatar, user=user, avatar=avatar)
            return HttpResponseRedirect(next_override or _get_next(request))
    return render_to_response(
            'avatar/add.html',
            extra_context,
            context_instance = RequestContext(
                request,
                { 'avatar': avatar, 
                  'avatars': avatars, 
                  'upload_avatar_form': upload_avatar_form,
                  'next': next_override or _get_next(request), }
            )
        )

@login_required
def change(request, extra_context=None, next_override=None,
        upload_form=UploadAvatarForm, primary_form=PrimaryAvatarForm,
        *args, **kwargs):
    if extra_context is None:
        extra_context = {}
    avatar, avatars = _get_avatars(request.user)
    if avatar:
        kwargs = {'initial': {'choice': avatar.id}}
    else:
        kwargs = {}
    upload_avatar_form = upload_form(user=request.user, **kwargs)
    primary_avatar_form = primary_form(request.POST or None,
        user=request.user, avatars=avatars, **kwargs)
    if request.method == "POST":
        updated = False
        if 'choice' in request.POST and primary_avatar_form.is_valid():
            avatar = Avatar.objects.get(
                id=primary_avatar_form.cleaned_data['choice'])
            avatar.primary = True
            avatar.save()
            updated = True
            messages.success(request, _("Successfully updated your avatar."))
        if updated:
            avatar_updated.send(sender=Avatar, user=request.user, avatar=avatar)
        return HttpResponseRedirect(next_override or _get_next(request))
    return render_to_response(
        'avatar/change.html',
        extra_context,
        context_instance = RequestContext(
            request,
            { 'avatar': avatar, 
              'avatars': avatars,
              'show_avatars': (AVATAR_MAX_AVATARS_PER_USER > 1),
              'upload_avatar_form': upload_avatar_form,
              'primary_avatar_form': primary_avatar_form,
              'next': next_override or _get_next(request), }
        )
    )

@login_required
def delete(request, extra_context=None, next_override=None, *args, **kwargs):
    if extra_context is None:
        extra_context = {}
    avatar, avatars = _get_avatars(request.user)
    delete_avatar_form = DeleteAvatarForm(request.POST or None,
        user=request.user, avatars=avatars)
    if request.method == 'POST':
        if delete_avatar_form.is_valid():
            ids = delete_avatar_form.cleaned_data['choices']
            if unicode(avatar.id) in ids and avatars.count() > len(ids):
                # Find the next best avatar, and set it as the new primary
                for a in avatars:
                    if unicode(a.id) not in ids:
                        a.primary = True
                        a.save()
                        avatar_updated.send(sender=Avatar, user=request.user, avatar=avatar)
                        break
            Avatar.objects.filter(id__in=ids).delete()
            messages.success(request, _("Successfully deleted the requested avatars."))
            return HttpResponseRedirect(next_override or _get_next(request))
    return render_to_response(
        'avatar/confirm_delete.html',
        extra_context,
        context_instance = RequestContext(
            request,
            { 'avatar': avatar, 
              'avatars': avatars,
              'delete_avatar_form': delete_avatar_form,
              'next': next_override or _get_next(request), }
        )
    )
    
    
def avatar_gallery(request, username, template_name="avatar/gallery.html"):
    user = get_object_or_404(User, username=username)
    return render_to_response(template_name, {
        "other_user": user,
        "avatars": user.avatar_set.all(),
    }, context_instance=RequestContext(request))
    
    
def avatar(request, username, id, template_name="avatar/avatar.html"):
    user = get_object_or_404(User, username=username)
    avatars = user.avatar_set.order_by("-date_uploaded")
    index = None
    avatar = None
    if avatars:
        avatar = avatars.get(pk=id)
        if not avatar:
            return Http404
        
        index = avatars.filter(date_uploaded__gt=avatar.date_uploaded).count()
        count = avatars.count()
        
        if index==0:
            prev = avatars.reverse()[0]
            if count <= 1:
                next = avatars[0]
            else:
                next = avatars[1]
        else:
            prev = avatars[index-1]
        
        if (index+1)>=count:
            next = avatars[0]
            prev_index = index-1
            if prev_index < 0:
                prev_index = 0
            prev = avatars[prev_index]
        else:
            next = avatars[index+1]
        
        
    return render_to_response(template_name, {
        "other_user": user,
        "avatar": avatar,
        "index": index+1,
        "avatars": avatars,
        "next": next,
        "prev": prev,
        "count": count,
    }, context_instance=RequestContext(request))


def render_primary(request, extra_context={}, user=None, size=AVATAR_DEFAULT_SIZE, *args, **kwargs):
    size = int(size)
    avatar = get_primary_avatar(user, size=size)
    return _get_render_primary_response(avatar)

def render_primary_id(request, extra_context={}, user_id=None, size=AVATAR_DEFAULT_SIZE, *args, **kwargs):
    size = int(size)

    try:
        # Order by -primary first; this means if a primary=True avatar exists
        # it will be first, and then ordered by date uploaded, otherwise a
        # primary=False avatar will be first.  Exactly the fallback behavior we
        # want.
        avatar = Avatar.objects.filter(user__id=user_id).order_by("-primary", "-date_uploaded")[0]
    except IndexError:
        avatar = None
    if avatar:
        if not avatar.thumbnail_exists(size):
            avatar.create_thumbnail(size)

    return _get_render_primary_response(avatar)

def _get_render_primary_response(avatar=None):
    if avatar:
        # FIXME: later, add an option to render the resized avatar dynamically
        # instead of redirecting to an already created static file. This could
        # be useful in certain situations, particulary if there is a CDN and
        # we want to minimize the storage usage on our static server, letting
        # the CDN store those files instead
        return HttpResponseRedirect(avatar.avatar_url(size))
    else:
        url = get_default_avatar_url()
        return HttpResponseRedirect(url)
 
