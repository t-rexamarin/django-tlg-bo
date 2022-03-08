import uuid
import os
from django.db import models


# Create your models here.
def image_directory_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = "%s.%s" % (uuid.uuid4(), ext)
    return os.path.join('images', filename)


class Image(models.Model):
    id = models.BigAutoField(primary_key=True)
    image = models.ImageField(upload_to=image_directory_path, blank=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    # class Meta:
    #     order_with_respect_to = 'id'

    @staticmethod
    def get_next_image(last_viewed_image):
        """
        Возвращает следующий за переданным объект Image
        @param last_viewed_image:
        @type last_viewed_image: int
        """
        image = Image.objects.filter(id__gt=last_viewed_image).order_by('created').first()
        return image


class User(models.Model):
    telegram_id = models.PositiveIntegerField()
    username = models.CharField(max_length=64, blank=True, null=True)
    first_name = models.CharField(max_length=64, blank=True, null=True)
    last_name = models.CharField(max_length=64, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    link = models.URLField(null=True)
    last_viewed_image = models.PositiveIntegerField(blank=True, null=True)
    images_requested = models.PositiveIntegerField(verbose_name='запрошено картинок', default=0)


class ImageRating(models.Model):
    image = models.ForeignKey(Image, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    rating = models.PositiveIntegerField(blank=True, null=True)
    votes = models.PositiveIntegerField(verbose_name='кол-во голосов', default=0)
