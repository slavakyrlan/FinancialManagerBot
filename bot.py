import logging
import os
import requests

from dotenv import load_dotenv
from telebot import TeleBot, types


load_dotenv()

secret_token = os.getenv('TOKEN')
bot = TeleBot(token=secret_token)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)

BUTTONS = ["Доход", "Расход", "Статистика"]
BUTTONS_EDIT = ["Добавить", "Редактировать", "Удалить", "Назад"]


@bot.message_handler(commands=['start'])
def start(message):
    name = message.from_user.first_name
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*BUTTONS)

    bot.send_message(
        chat_id=message.chat.id,
        text=f'Привет, {name}. Выберите опцию:',
        reply_markup=keyboard,
    )


@bot.message_handler(func=lambda message: message.text in BUTTONS)
def handle_option(message):
    if message.text == "Доход":
        print('Доход')
        handle_income_option(message)
    elif message.text == "Расход":
        print('Расход')
    elif message.text == "Статистика":
        bot.send_message(
            chat_id=message.chat.id,
            text="Введите промежуток дат в формате: "
                 "'YYYY-MM-DD to YYYY-MM-DD'")


def handle_income_option(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*BUTTONS_EDIT)
    bot.send_message(
        chat_id=message.chat.id,
        text="Выберите действие с доходом:",
        reply_markup=keyboard,
    )


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
