from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import (
    Updater,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    RegexHandler,
    CallbackQueryHandler
)
from telegram.ext.filters import Filters
from dotenv import load_dotenv
from logger import get_logger

import logging
import os
import vk_api
import telegramcalendar
import datetime
import re

logger = get_logger('BOT')

BASE_PATH = os.path.abspath(os.path.dirname(__file__))

# DOTENV
load_dotenv(os.path.join(BASE_PATH, '.env'))


class Bot:
    """
    MAIN CLASS TO WORK WITH BOT
    """
    description = None
    photo = None
    date = None
    path = os.path.join(BASE_PATH, 'tmp.png')  # TODO: Better to not download image

    def __init__(self, token=None):
        logger.info("START BOT")
        # FETCH TOKEN
        if token is None:
            token = os.getenv('TOKEN')

        if token is None:
            raise Exception("Please, provide token")

        # GET UPDATER
        updater = Updater(token)

        dp = updater.dispatcher

        # CONVERSATION HANDLER
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
                CommandHandler('cancel', self.cancel),
            )
        )

        dp.add_handler(con_hand)

        # HANDLE ERRORS
        dp.add_error_handler(self.error)

        # START BOT
        updater.start_polling()
        updater.idle()

    def login_to_vk(self):
        vk_session = vk_api.VkApi(os.getenv('LOGIN'), os.getenv('PASSWORD'))
        try:
            vk_session.auth(token_only=True)
            self.vk_session = vk_session
            return True

        except vk_api.AuthError as error_msg:
            logger.exception(error_msg)
            return False

    def start(self, bot, update):
        """
        Get the image download it
        :param bot:
        :param update:
        :return:
        """
        image = update.message.document or update.message.photo[-1]
        image = image.get_file()
        image.download(self.path)

        logger.info("CONVERSATION STARTED, TRYING TO LOGIN")

        if not self.login_to_vk():
            logger.error("CAN'T LOGIN")
            update.message.reply_text(
                "Sorry, we can't login to vk"
            )
            return ConversationHandler.END

        update.message.reply_text(
            'Input description',
        )

        return 0

    def other_date(self, bot, update):
        """
        Pick a date for delayed posting
        :param bot:
        :param update:
        :return:
        """
        logger.info("PICK OTHER DATE")
        update.message.reply_text("Please select a date: ",
                                  reply_markup=telegramcalendar.create_calendar())

        return 2

    def post(self, bot, update):
        logger.info("TRYING TO POST")
        """
        Post image to vk
        :param bot:
        :param update:
        :return:
        """

        upload = vk_api.VkUpload(self.vk_session)

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

        post = self.vk_session.method('wall.post', post_data)

        logger.info("GENERATING URL")
        response = self.vk_session.method('groups.getById', {'group_id': os.getenv('GROUP_ID')})

        url = 'https://vk.com/{}?w=wall-{}_{}'.format(
            response[0]['screen_name'], os.getenv('GROUP_ID'), post['post_id']
        )

        update.message.reply_text(url)

        return ConversationHandler.END

    def input_description(self, bot, update):
        """
        Choose when publish the image
        :param bot:
        :param update:
        :return:
        """
        logger.info("WAITING FOR DESCRIPTION")

        self.description = update.message.text
        update.message.reply_text("Please select a date: ",
                                  reply_markup=ReplyKeyboardMarkup(
                                      (('Now', 'Other date'),),
                                      one_time_keyboard=True
                                  ))
        return 1

    def input_date(self, bot, update):
        """
        Time of publishing
        :param bot:
        :param update:
        :return:
        """
        logger.info("TIME OF PUB")
        if not re.search(r'^\d{2}:\d{2}$', update.message.text):
            return 2
        hours = update.message.text.split(':')
        delta = {
            'hours': int(hours[0]),
            'minutes': int(hours[1])
        }

        self.date += datetime.timedelta(**delta)
        self.post(bot, update)

    def inline_handler(self, bot, update):
        """
        Select date
        :param bot:
        :param update:
        :return:
        """
        logger.info("DATE OF PUB")
        selected, date = telegramcalendar.process_calendar_selection(bot, update)
        if selected:
            self.date = date
            bot.send_message(chat_id=update.callback_query.from_user.id,
                             text="Please enter the time in HH:MM format",
                             reply_markup=ReplyKeyboardRemove())
            return 3

    def error(self, update, context):
        """
        Log Errors caused by Updates.
        :param context:
        :return:
        """
        logger.warning('Update "%s" caused error "%s"', update, context.error)

    def cancel(self, bot, update):
        """
        Cancel
        :param update:
        :return:
        """
        user = update.message.from_user
        update.message.reply_text('Bye! I hope we can talk again some day.',
                                  reply_markup=ReplyKeyboardRemove())

        return ConversationHandler.END


if __name__ == '__main__':
    Bot()
