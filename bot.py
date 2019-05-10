from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import Updater, ConversationHandler, CommandHandler, MessageHandler, RegexHandler, \
    CallbackQueryHandler
from telegram.ext.filters import Filters
from dotenv import load_dotenv

import logging
import os
import vk_api
import telegramcalendar
import datetime
import dateutil
import re

# LOGGING
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# DOTENV
load_dotenv(os.path.join(BASE_PATH, '.env'))


class Bot:
    description = None
    photo = None
    date = None
    path = os.path.join(BASE_PATH, 'tmp.png')

    def __init__(self, token=None):
        print("START")

        # FETCH TOKEN
        if token is None:
            token = os.getenv('TOKEN')

        if token is None:
            raise Exception("Please, provide token")

        # GET UPDATER
        updater = Updater(token)

        dp = updater.dispatcher

        con_hand = ConversationHandler(
            entry_points=(
                MessageHandler(Filters.document | Filters.photo, self.start),
            ),
            states={
                0: [MessageHandler(Filters.text, self.input_description)],
                1: [RegexHandler(r'^Now', self.post), MessageHandler(Filters.text, self.other_date)],
                2: [CallbackQueryHandler(self.inline_handler)],
                3: [MessageHandler(Filters.text, self.input_date)]
            },
            fallbacks=(
                CommandHandler('cancel', cancel),
            )
        )

        dp.add_handler(con_hand)

        dp.add_error_handler(error)

        updater.start_polling()

        updater.idle()

    def start(self, bot, update):
        image = update.message.document or update.message.photo[-1]
        image = image.get_file()
        image.download(self.path)

        update.message.reply_text(
            'Input description',
        )

        return 0

    def other_date(self, bot, update):
        print(update.message.text)
        update.message.reply_text("Please select a date: ",
                                  reply_markup=telegramcalendar.create_calendar())

        return 2

    def post(self, bot, update):
        vk_session = vk_api.VkApi(os.getenv('LOGIN'), os.getenv('PASSWORD'))
        try:
            vk_session.auth(token_only=True)
        except vk_api.AuthError as error_msg:
            print(error_msg)
            return

        upload = vk_api.VkUpload(vk_session)

        logger.info("UPLOAD PHOTO")
        photo = upload.photo_wall(  # Подставьте свои данные
            self.path,
            group_id=os.getenv('GROUP_ID')
        )

        logger.info("PUBLIC PHOTO")

        post_data = {
            'owner_id': "-{}".format(os.getenv('GROUP_ID')),
            'message': self.description,
            'attachments': "photo{}_{}".format(photo[0]['owner_id'], photo[0]['id'])
        }

        if self.date:
            post_data.update({
                'publish_date': self.date.timestamp()
            })

        post = vk_session.method('wall.post', post_data)

        logger.info("GENERATING URL")
        response = vk_session.method('groups.getById', {'group_id': os.getenv('GROUP_ID')})

        url = 'https://vk.com/{}?w=wall-{}_{}'.format(
            response[0]['screen_name'], os.getenv('GROUP_ID'), post['post_id']
        )

        update.message.reply_text(url)

        return ConversationHandler.END

    def input_description(self, bot, update):
        self.description = update.message.text
        update.message.reply_text("Please select a date: ",
                                  reply_markup=ReplyKeyboardMarkup(
                                      (('Now', 'Other date'),),
                                      one_time_keyboard=True
                                  ))
        return 1

    def input_date(self, bot, update):

        if not re.search(r'^\d{2}:\d{2}$', update.message.text):
            return 2
        hours = update.message.text.split(':')
        delta = {
            'hours': int(hours[0]),
            'minutes': int(hours[1])
        }

        self.date += datetime.timedelta(**delta)
        print('delayed', self.date.timestamp())
        self.post(bot, update)

    def inline_handler(self, bot, update):
        selected, date = telegramcalendar.process_calendar_selection(bot, update)
        if selected:
            self.date = date
            bot.send_message(chat_id=update.callback_query.from_user.id,
                             text="Please enter the time in HH:MM format",
                             reply_markup=ReplyKeyboardRemove())
            return 3


# FUNCTIONS


def cancel(bot, update):
    user = update.message.from_user
    update.message.reply_text('Bye! I hope we can talk again some day.',
                              reply_markup=ReplyKeyboardRemove())

    return ConversationHandler.END


def set_today_date():
    pass


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    print("START")
    updater = Updater('767539981:AAFH3LaY_3Vdt3mmTfSUM57LEaC4iNvQX2Y')

    dp = updater.dispatcher

    # con_hand = ConversationHandler(
    #     entry_points=(
    #         MessageHandler(Filters.document | Filters.photo, start),
    #     ),
    #     states={
    #         0: [MessageHandler(Filters.text, input_description)],
    #         1: [CallbackQueryHandler(inline_handler)],
    #         2: [MessageHandler(Filters.text, input_date)]
    #     },
    #     fallbacks=(
    #         CommandHandler('cancel', cancel),
    #     )
    # )

    # dp.add_handler(con_hand)

    dp.add_error_handler(error)

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    # main()
    Bot()
