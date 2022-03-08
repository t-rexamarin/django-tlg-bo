# ./manage.py shell < bot_app/management/commands/_debug.py
import os
from django.core.wsgi import get_wsgi_application
os.environ['DJANGO_SETTINGS_MODULE'] = 'bots.settings'
application = get_wsgi_application()


from django.db.models import F
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler, JobQueue
import telegram
from bot_app.models import User, Image, ImageRating
from bots.settings import MEDIA_ROOT
from bot_app.management.commands._bot_settings import TOKEN, PORT
import logging
import pytz
import datetime


class Bot:
    def __init__(self):
        self.time = {'hour': 23,
                     'minute': 00,
                     'second': 00}
        self.launch_time = datetime.time(**self.time, tzinfo=pytz.timezone('Europe/Moscow'))

        self.image_rate = "🦐"

        self.keyboard_callbacks_data = {
            'callback_data_1': '1',
            'callback_data_2': '5',
            'callback_data_3': '10',
        }

    def start(self, update, context):
        chat_id = update.effective_chat.id
        user_id = User.objects.filter(telegram_id=chat_id).exists()
        if not user_id:
            User.objects.create(
                telegram_id=update.effective_chat.id,
                username=update.effective_chat.username,
                first_name=update.effective_chat.first_name,
                last_name=update.effective_chat.last_name,
                description=update.effective_chat.description,
                link=update.effective_chat.link
            )

            def send_first_start_msg(context_f):
                context = context_f.job.context['context']
                chat_id = context_f.job.context['chat_id']
                text = 'Я - T1000-Mo, автоматизированная система поддержки хорошего настроения.\n'\
                       'Я послан из будушего, чтобы <s>убить Сару Конор</s> помочь тебе.\n'\
                       f'Я буду присылать тебе ежедневно одну картинку ' \
                       f'в {self.time["hour"]}:{"{:<02d}".format(self.time["minute"])},' \
                       ' а первую ты получишь через несколько секунд.'
                context_f.bot.send_message(chat_id, text, parse_mode=telegram.ParseMode.HTML)

            def send_second_start_msg(context_f):
                context = context_f.job.context['context']
                chat_id = context_f.job.context['chat_id']
                text = f'Для оценки картинок используется креветочный {self.image_rate} рейтинг - ' \
                          f'{self.keyboard_callbacks_data["callback_data_1"]}, ' \
                          f'{self.keyboard_callbacks_data["callback_data_2"]} ' \
                          f'и {self.keyboard_callbacks_data["callback_data_3"]}.\n' \
                          f'Оценка работ поможет понять, хорошо ли они получись.'
                context_f.bot.send_message(chat_id, text)

            context_for_msg_funcs = {
                'context': context,
                'chat_id': chat_id
            }

            context.job_queue.run_once(callback=send_first_start_msg,
                                       when=1,
                                       context=context_for_msg_funcs)

            context.job_queue.run_once(callback=send_second_start_msg,
                                       when=15,
                                       context=context_for_msg_funcs)

            # единожды запускаю, чтобы отправить первую картинку
            context.job_queue.run_once(callback=self.send_first_image,
                                       when=30,
                                       context={'updater': context,
                                                'chat_id': chat_id})

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

    def send_first_image(self, context):
        updater = context.job.context['updater']
        chat_id = context.job.context['chat_id']
        user_and_image = self.get_last_viewed_image(chat_id)
        user, last_image = user_and_image['user'], user_and_image['image']

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
            updater.bot.send_message(chat_id, 'По какой то причине картинки нет')

    def send_image(self, context):
        updater = context.job.context['updater']
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

    def test(self, update, context):
        chat_id = update.effective_chat.id
        context.bot.send_message(chat_id, 'я жив')

    def image_rating(self, context, update):
        """
        Ставим рейтинг изображению по коллбеку с клавиатуры
        @param context:
        @type context:
        @param update:
        @type update:
        """
        user = User.objects.get(telegram_id=context.effective_chat.id)
        last_image = Image.objects.get(id=user.last_viewed_image)
        # если есть связка пользователь-картинка
        image_exists = ImageRating.objects.filter(image=last_image, user=user).exists()

        if not image_exists:
            ImageRating.objects.create(
                image=last_image,
                user=user
            )

        image = ImageRating.objects.filter(image=last_image, user=user).get()
        # Entry.objects.get(Q(blog=blog) & Q(entry_number=1))
        query = context.callback_query
        choice = query.data

        # ставим рейтинг
        if self.keyboard_callbacks_data.get(choice):
            image.rating = int(self.keyboard_callbacks_data[choice])
        # повышаю счетчик голосов
        image.votes = F('votes') + 1
        image.user = user
        image.save()
        query.edit_message_reply_markup(None)

    def bot_init(self):
        updater = Updater(TOKEN, use_context=True)
        return updater

    def handle(self, *args, **options):
        updater = self.bot_init()
        dispatcher = updater.dispatcher
        j = updater.job_queue

        dispatcher.add_handler(CommandHandler("start", self.start))
        dispatcher.add_handler(CommandHandler("test", self.test))
        dispatcher.add_handler(CallbackQueryHandler(self.image_rating))
        job_daily = j.run_daily(self.send_image,
                                days=(0, 1, 2, 3, 4, 5, 6),
                                time=self.launch_time,
                                context={'updater': updater})

        logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

        updater.start_polling()
        # updater.start_webhook(listen='0.0.0.0',
        #                       port=PORT,
        #                       url_path=TOKEN,
        #                       webhook_url='' + TOKEN)
        updater.idle()


# if __name__ == '__main__':
bot = Bot()
bot.handle()
