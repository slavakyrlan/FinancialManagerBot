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
        expense_action(message)
        #print('Расход')
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


def add_category(message):
    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id, "Введите новую категорию:",
                     reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, process_new_category)


def process_new_category(message):
    new_category = str(message.text)

    if not new_category.strip():
        bot.send_message(message.chat.id,
                         "Название категории не может быть пустым. Пожалуйста, попробуйте снова.")
        return add_category(message)

    cur.execute('SELECT * FROM categories WHERE name = ?', (new_category,))
    if cur.fetchone() is not None:
        bot.send_message(message.chat.id,
                         f"Категория '{new_category}' уже существует. Пожалуйста, введите другое название.")
        return add_category(message)

    cur.execute("INSERT INTO categories (name) VALUES (?)",
                (new_category,))
    con.commit()
    bot.send_message(message.chat.id,
                     f"Категория '{new_category}' успешно добавлена!")
    start(message)


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
        WHERE client_id = ?
        ORDER BY id DESC 
        LIMIT 10
        ''', (message.chat.id,))

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
    bot.register_next_step_handler(message, process_edit_id_income)


def process_edit_id_income(message):
    income_id = int(message.text)
    cur.execute('SELECT * FROM incomes WHERE id = ? AND client_id = ?',
                (income_id, message.chat.id,))
    choice_income = cur.fetchone()
    if not choice_income:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return edit_income(message)
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


def expense_action(message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*["Добавить", "Редактировать",
                   "Удалить", "Добавить категорию", "Назад"])
    bot.send_message(
        chat_id=message.chat.id,
        text="Выберите действие с расходом:",
        reply_markup=keyboard,
    )
    bot.register_next_step_handler(message, process_expense_action)


def process_expense_action(message):
    if message.text == "Добавить":
        hide_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id, "Введите сумму расходов:",
                         reply_markup=hide_keyboard)
        bot.register_next_step_handler(message, process_expense_amount)
    elif message.text == "Редактировать":
        edit_expense(message)
    elif message.text == "Удалить":
        delete_expense(message)
    elif message.text == "Добавить категорию":
        add_category(message)
    elif message.text == "Назад":
        start(message)


def process_expense_amount(message):
    try:
        amount = float(message.text.strip())
        hide_keyboard = types.ReplyKeyboardRemove()
        bot.send_message(message.chat.id,
                         "Введите описание расхода:",
                         reply_markup=hide_keyboard)
        bot.register_next_step_handler(
            message, lambda msg: process_expense_description(msg, amount))
    except ValueError:
        bot.send_message(message.chat.id, "Пожалуйста, введите корректную сумму расходов.")
        return process_expense_action(message)


def process_expense_description(message, amount):
    description = message.text.strip()
    cur.execute("SELECT id, name FROM categories")
    categories = cur.fetchall()

    if categories:
        category_buttons = [cat[1] for cat in
                            categories]
        category_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in category_buttons:
            category_keyboard.add(category)
        category_keyboard.add("Назад")
        bot.send_message(message.chat.id, "Выберите категорию:",
                         reply_markup=category_keyboard)
        bot.register_next_step_handler(
            message, lambda msg: process_expense_category(
                msg, amount, description, categories))
    else:
        bot.send_message(
            message.chat.id,
            "Нет категорий. Пожалуйста, добавьте категорию сначала.")
        return process_expense_action(message)


def process_expense_category(message, amount, description, categories):
    selected_category = message.text.strip()

    category_id = None
    for cat in categories:
        if cat[1] == selected_category:
            category_id = cat[0]
            break

    if category_id is None:
        if selected_category == "Назад":
            return process_expense_action(message)
        bot.send_message(message.chat.id,
                         "Категория не найдена. Пожалуйста, выберите снова.")
        return process_expense_description(message,
                                           amount)
    add_expense(amount, description, category_id, message.chat.id)
    bot.send_message(message.chat.id,
                     f"Расход в размере {amount} с описанием '{description}' успешно добавлен в категорию '{selected_category}'.")
    start(message)


def add_expense(amount, description, category_id, client_id):
    cur.execute(
        '''
        INSERT INTO expenses
            (amount, description, category_id, client_id) VALUES (?, ?, ?, ?)
        ''',
        (amount, description, category_id, client_id))
    con.commit()


def edit_expense(message):
    cur.execute(
        '''
        SELECT id, amount, category_id, description, date_added FROM expenses 
        WHERE client_id = ?
        ORDER BY id DESC 
        LIMIT 10
        ''', (message.chat.id,))

    list_expense = cur.fetchall()
    if not list_expense:
        bot.send_message(message.chat.id,
                         "Нет записей расходов для редактирования.")
        return
    response = "Последние 10 записей:\n"
    for record in list_expense:
        response += f"ID: {record[0]}, " \
                    f"Сумма: {record[1]}, " \
                    f"Категория: {record[2]}, " \
                    f"Описание: {record[3]}, " \
                    f"Дата: {record[4]}\n"
    bot.send_message(message.chat.id, response)
    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите редактировать:",
                     reply_markup=hide_keyboard)
    bot.register_next_step_handler(message, process_edit_id_expense)


def process_edit_id_expense(message):
    expense_id = int(message.text)
    cur.execute('SELECT * FROM expenses WHERE id = ? AND client_id = ?',
                (expense_id, message.chat.id,))
    choice_expense = cur.fetchone()
    if not choice_expense:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return edit_expense(message)
    bot.send_message(message.chat.id, "Введите новую сумму:")
    bot.register_next_step_handler(message, process_new_amount_expense, expense_id)


def process_new_amount_expense(message, expense_id):
    new_amount = float(message.text)
    bot.send_message(message.chat.id, "Введите новое описание:")
    bot.register_next_step_handler(message, process_new_category_expense,
                                   expense_id, new_amount)


def process_new_category_expense(message, expense_id, new_amount):
    new_description = message.text.strip()
    cur.execute("SELECT id, name FROM categories")
    categories = cur.fetchall()
    if categories:
        category_buttons = [cat[1] for cat in
                            categories]
        category_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in category_buttons:
            category_keyboard.add(category)
        category_keyboard.add("Назад")
        bot.send_message(message.chat.id, "Выберите категорию:",
                         reply_markup=category_keyboard)
        bot.register_next_step_handler(
            message,
            finalize_edit_expense, expense_id, new_amount, new_description)
    else:
        bot.send_message(
            message.chat.id,
            "Нет категорий. Пожалуйста, добавьте категорию сначала.")
        return process_new_amount_expense(message, expense_id)


def finalize_edit_expense(message, expense_id, new_amount, new_description):
    new_category = message.text
    cur.execute(
        '''
        UPDATE expenses
        SET amount = ?, description = ?, category_id = ?, date_added = datetime('now')
        WHERE id = ?
        ''',
        (new_amount, new_description, new_category, expense_id))
    con.commit()
    bot.send_message(message.chat.id, "Доход успешно обновлен!")
    start(message)


def main():
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
