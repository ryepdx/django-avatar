from django.contrib import admin
from avatar.models import Avatar

class AvatarAdmin(admin.ModelAdmin):
    raw_id_fields = ('user',)


admin.site.register(Avatar, AvatarAdmin)
