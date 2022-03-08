from django.contrib import admin
from bot_app.models import Image, User, ImageRating

# Register your models here.

admin.site.register(Image)
admin.site.register(User)
admin.site.register(ImageRating)
