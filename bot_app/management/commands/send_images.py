import os
from django.core.management import BaseCommand
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from bots.settings import MEDIA_ROOT
from bot_app.management.commands._debug import Bot
from bot_app.models import User, Image


class Command(BaseCommand):
    def handle(self, *args, **options):
        self.send_image()

    def build_keyboard(self):
        image_rate = "🦐"

        keyboard = [
            [InlineKeyboardButton(f"{image_rate}/10",
                                  callback_data='callback_data_1')],
            [InlineKeyboardButton(f"{image_rate * 5}/10",
                                  callback_data='callback_data_2')],
            [InlineKeyboardButton(f"{image_rate * 10}/10",
                                  callback_data='callback_data_3')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        return reply_markup

    def get_last_viewed_image(self, chat_id):
        user = User.objects.get(telegram_id=chat_id)
        last_viewed_image = user.last_viewed_image
        user_and_image = {
            'user': user,
            'image': last_viewed_image
        }
        return user_and_image

    def send_image(self):
        bot = Bot()
        updater = bot.bot_init()

        users = User.objects.all()
        for user in users:
            limit_reach = 'Картинки временно закончились'
            chat_id = user.telegram_id
            user_and_image = self.get_last_viewed_image(chat_id)
            user, last_image = user_and_image['user'], user_and_image['image']

            if last_image:
                image_to_send = Image.get_next_image(last_image)
            else:
                image_to_send = Image.objects.all().first()

            if image_to_send is not None:
                try:
                    updater.bot.send_photo(chat_id,
                                           photo=open(os.path.join(MEDIA_ROOT, image_to_send.image.name), 'rb'),
                                           reply_markup=self.build_keyboard())
                    user.last_viewed_image = image_to_send.id
                    user.save()
                # топор?
                except Exception as e:
                    raise e
            else:
                updater.bot.send_message(chat_id, limit_reach)
