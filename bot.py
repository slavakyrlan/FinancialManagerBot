import logging
import os
import sqlite3

import requests

from dotenv import load_dotenv
from telebot import TeleBot, types
from database import db_connect

load_dotenv()

secret_token = os.getenv('TOKEN')
bot = TeleBot(token=secret_token)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
)

BUTTONS = ["Доход", "Расход", "Статистика"]
BUTTONS_EDIT = ["Добавить", "Редактировать", "Удалить", "Назад"]


con = db_connect()
cur = con.cursor()


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
    add_user(message.chat.id)


@bot.message_handler(func=lambda message: message.text in BUTTONS)
def handle_option(message):
    if message.text == "Доход":
        income_action(message)
    elif message.text == "Расход":
        print('Расход')
    elif message.text == "Статистика":
        bot.send_message(
            chat_id=message.chat.id,
            text="Введите промежуток дат в формате: "
                 "'YYYY-MM-DD to YYYY-MM-DD'")


def income_action(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*BUTTONS_EDIT)
    bot.send_message(
        chat_id=message.chat.id,
        text="Выберите действие с доходом:",
        reply_markup=keyboard,
    )
    bot.register_next_step_handler(message, process_income_action)


def process_income_action(message):
    if message.text == "Добавить":
        hide_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Введите сумму дохода:",
                         reply_markup=hide_keyboard)
        bot.register_next_step_handler(message, process_income_amount)
    elif message.text == "Редактировать":
        edit_income(message)
    elif message.text == "Удалить":
        delete_income(message)
    elif message.text == "Назад":
        start(message)


def add_user(telegram_id):
    cur.execute("SELECT * FROM clients WHERE telegram_id = ?",
                (str(telegram_id),))
    user = cur.fetchone()

    if user is None:
        cur.execute("INSERT INTO clients (telegram_id) VALUES (?)",
                    (str(telegram_id),))
        con.commit()


def add_category(name):
    cur.execute("INSERT INTO categories (name) VALUES (?)",
                name)
    con.commit()


def add_income(amount, description, client_id):
    cur.execute('''INSERT INTO incomes 
                (amount, description, client_id) VALUES (?, ?, ?)''',
                (amount, description, client_id))
    con.commit()


def process_income_amount(message):
    amount = float(message.text)
    bot.send_message(message.chat.id, "Введите описание дохода:")
    bot.register_next_step_handler(message, process_income_description, amount)


def process_income_description(message, amount):
    description = message.text
    add_income(amount, description, message.chat.id)
    bot.send_message(message.chat.id, "Доход успешно добавлен!")
    start(message)


def edit_income(message):
    cur.execute(
        '''
        SELECT id, amount, description, date_added FROM incomes 
        ORDER BY id DESC 
        LIMIT 10
        '''
    )
    list_income = cur.fetchall()
    if not list_income:
        bot.send_message(message.chat.id, "Нет записей для редактирования.")
        return
    response = "Последние 10 записей:\n"
    for record in list_income:
        response += f"ID: {record[0]}, " \
                    f"Сумма: {record[1]}, " \
                    f"Описание: {record[2]}, " \
                    f"Дата: {record[3]}\n"
    bot.send_message(message.chat.id, response)
    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите редактировать:",
                     reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, process_edit_id)


def process_edit_id(message):
    income_id = int(message.text)
    cur.execute('SELECT * FROM incomes WHERE id = ?', (income_id,))
    choice_income = cur.fetchone()
    if not choice_income:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return
    bot.send_message(message.chat.id, "Введите новую сумму:")
    bot.register_next_step_handler(message, process_new_amount, income_id)


def process_new_amount(message, income_id):
    new_amount = float(message.text)
    bot.send_message(message.chat.id, "Введите новое описание:")
    bot.register_next_step_handler(message, finalize_edit, income_id,
                                   new_amount)


def finalize_edit(message, income_id, new_amount):
    new_description = message.text
    cur.execute(
        '''
        UPDATE incomes
        SET amount = ?, description = ?, date_added = datetime('now')
        WHERE id = ?
        ''',
        (new_amount, new_description, income_id))
    con.commit()
    bot.send_message(message.chat.id, "Доход успешно обновлен!")
    start(message)


def delete_income(message):
    cur.execute(
        '''
        SELECT id, amount, description, date_added FROM incomes 
        ORDER BY id DESC 
        LIMIT 10
        '''
    )
    list_income = cur.fetchall()
    if not list_income:
        bot.send_message(message.chat.id, "Нет записей для удаления.")
        return
    response = "Последние 10 записей:\n"
    for record in list_income:
        response += f"ID: {record[0]}, " \
                    f"Сумма: {record[1]}, " \
                    f"Описание: {record[2]}, " \
                    f"Дата: {record[3]}\n"
    bot.send_message(message.chat.id, response)
    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите удалить:",
                     reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, process_delete_id)


def process_delete_id(message):
    income_id = int(message.text)
    cur.execute('SELECT * FROM incomes WHERE id = ?', (income_id,))
    choice_income = cur.fetchone()
    if not choice_income:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return
    cur.execute(
        '''
            DELETE FROM incomes
            WHERE id = ?
        ''',
        (income_id,))
    con.commit()
    bot.send_message(message.chat.id, "Доход успешно удален!")
    start(message)


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
