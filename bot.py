"""Код для запуска бота."""

import logging
import os
from typing import Dict, List, Literal, Tuple

import matplotlib
import matplotlib.pyplot as plt
import pandas as pd
import requests
from dotenv import load_dotenv
from telebot import TeleBot, types

from db_functions import (add_user, db_connect, get_category_name,
                          sql_all_category, sql_delete_expense,
                          sql_delete_income, sql_for_chart, sql_for_graph,
                          sql_for_graph_incomes, sql_for_table,
                          sql_insert_category, sql_insert_expense,
                          sql_insert_incomes, sql_records_10_expense,
                          sql_records_10_incomes, sql_select_all_expenses_user,
                          sql_select_all_incomes_user, sql_select_category,
                          sql_select_id_category, sql_update_expense,
                          sql_update_income)
from strings import (DELETE_RECORDS_ID, EDIT_RECORDS_ID, ERROR_NUMBER,
                     ERROR_NUMBER_ID, ERROR_RECORD_EMPTY, ERROR_RECORDS_ID,
                     HELP_MSG, RETURN_MENU, send_instruction)

matplotlib.use('Agg')
load_dotenv()

secret_token = os.getenv('TOKEN')
bot = TeleBot(token=secret_token)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w'
)

BUTTONS = ['Доход', 'Расход', 'Статистика доходов', 'Статистика расходов']
PERIODS = {
    'День': 'start of day',
    'Неделя': '-7 day',
    'Месяц': 'start of month',
    'Квартал': '-3 month',
    'Год': 'start of year'
}
ALL_CONTENT_TYPES = ['text', 'photo', 'sticker', 'document', 'video',
                     'audio', 'voice', 'location', 'contact', 'poll',
                     'venue', 'animation']


con = db_connect()


@bot.message_handler(commands=['start'])
def start(message: types.Message) -> None:
    """Стартовое сообщение."""
    name = message.from_user.first_name
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    keyboard.add(*BUTTONS[:2])
    keyboard.add(*BUTTONS[2:])

    bot.send_message(
        chat_id=message.chat.id,
        text=(f'Привет, {name}!\n Я бюджет-трекер для подробной '
              'информации используй команду /help. Выберите опцию:'),
        reply_markup=keyboard,
    )
    add_user(message.chat.id)


@bot.message_handler(commands=['help'])
def help_commands(message: types.Message) -> None:
    """Помощь."""
    bot.reply_to(message, HELP_MSG)


@bot.message_handler(func=lambda message: message.text in BUTTONS)
def handle_option(message: types.Message) -> None:
    """Меню бота."""
    if message.text == 'Доход':
        send_action_keyboard(message, 'income')
    elif message.text == 'Расход':
        send_action_keyboard(message, 'expense')
    elif message.text == 'Статистика расходов':
        ask_period(message)
    elif message.text == 'Статистика доходов':
        show_table_statistics_incomes(message)


def send_action_keyboard(message: types.Message,
                         action_type: Literal['income', 'expense']) -> None:
    """Кнопки у Дохода/Расхода."""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if action_type == 'income':
        keyboard.add('Добавить', 'Редактировать', 'Удалить', 'Назад')
        text = (send_instruction(message.text))
    elif action_type == 'expense':
        keyboard.add('Добавить', 'Редактировать', 'Удалить',
                     'Добавить категорию', 'Назад')
        text = (send_instruction(message.text))
    else:
        return start(message)

    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=keyboard,
    )
    bot.register_next_step_handler(message, process_action, action_type)


def process_action(message: types.Message,
                   action_type: Literal['income', 'expense']) -> None:
    """Функции для Дохода/Расхода."""
    if message.text == 'Добавить':
        hide_keyboard = types.ReplyKeyboardRemove()
        text = 'Введите сумму расходов, указав число в рублях:' if \
            action_type == 'expense' else 'Введите сумму дохода, ' \
                                          'указав число в рублях:'
        bot.send_message(message.chat.id, text, reply_markup=hide_keyboard)
        bot.register_next_step_handler(message, adding_records, action_type)
    elif message.text == 'Редактировать':
        edit_function = edit_expense if \
            action_type == 'expense' else edit_income
        edit_function(message)
    elif message.text == 'Удалить':
        delete_function = delete_expense if \
            action_type == 'expense' else delete_income
        delete_function(message)
    elif message.text == 'Добавить категорию':
        add_category(message)
    elif message.text == 'Назад':
        start(message)
    else:
        bot.send_message(message.chat.id, 'Таких функций нет')
        start(message)


def adding_records(message: types.Message,
                   action_type: Literal['income', 'expense']) -> None:
    """Добавление записей для Дохода/Расхода."""
    try:
        amount = float(message.text.strip())
        if action_type == 'income':
            bot.send_message(message.chat.id, 'Введите описание дохода:')
            bot.register_next_step_handler(
                message, add_description_income, amount)
        elif action_type == 'expense':
            hide_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, 'Введите описание расхода:',
                             reply_markup=hide_keyboard)
            bot.register_next_step_handler(
                message, process_expense_description, amount)
    except ValueError:
        bot.send_message(
            message.chat.id,
            'Ошибка, вы отправили некорректную сумму.')
        start(message)


def add_category(message: types.Message) -> None:
    """Добавление новой категории."""
    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id, 'Введите новую категорию:',
        reply_markup=hide_keyboard)

    def handle_new_category(msg):
        new_category = str(msg.text)

        if sql_select_category(new_category) is not None:
            bot.send_message(
                msg.chat.id,
                f'Категория "{new_category}" уже существует. '
                f'Пожалуйста, введите другое название.')
            return add_category(msg)

        sql_insert_category(new_category)
        bot.send_message(
            msg.chat.id, f'Категория "{new_category}" успешно добавлена!')
        start(msg)

    bot.register_next_step_handler(message, handle_new_category)


def add_description_income(message: types.Message, amount: float) -> None:
    """Добавление новой записи дохода в БД."""
    sql_insert_incomes(amount, message.text, message.chat.id)
    bot.send_message(message.chat.id, 'Доход успешно добавлен!')
    start(message)


def edit_income(message: types.Message) -> None:
    """Лист последних 10 записей дохода -> изменение записи."""
    list_income = sql_records_10_incomes(message.chat.id)
    if not list_income:
        bot.send_message(message.chat.id,
                         'Нет записей для редактирования.')
        return start(message)
    response = 'Последние 10 записей:\n'
    for record in list_income:
        response += f'ID: {record[0]}, ' \
                    f'Сумма: {record[1]}, ' \
                    f'Описание: {record[2]}, ' \
                    f'Дата: {record[3]}\n'
    bot.send_message(message.chat.id, response)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(RETURN_MENU)
    bot.send_message(message.chat.id,
                     EDIT_RECORDS_ID,
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, edit_income_by_id)


def edit_income_by_id(message: types.Message) -> None:
    """Изменение записи Дохода по id."""
    if message.text == RETURN_MENU:
        return start(message)
    try:
        income_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            ERROR_NUMBER_ID)
        return edit_income(message)
    choice_income = sql_select_all_incomes_user(income_id, message.chat.id)
    if not choice_income:
        bot.send_message(message.chat.id, ERROR_RECORDS_ID)
        return edit_income(message)
    bot.send_message(message.chat.id, 'Введите новую сумму:')
    bot.register_next_step_handler(message, process_new_amount, income_id)


def process_new_amount(message: types.Message, income_id: int) -> None:
    """Редактирование суммы у записи дохода."""
    try:
        new_amount = float(message.text)
        if new_amount < 1:
            raise ValueError(ERROR_NUMBER)
    except ValueError:
        bot.send_message(message.chat.id, ERROR_NUMBER)
        return edit_income(message)
    bot.send_message(message.chat.id, 'Введите новое описание:')
    bot.register_next_step_handler(message, finalize_edit, income_id,
                                   new_amount)


def finalize_edit(message: types.Message,
                  income_id: int, amount: float) -> None:
    """Редактирование описания у записи дохода."""
    sql_update_income(amount, message.text, income_id)
    bot.send_message(message.chat.id, 'Доход успешно обновлен!')
    start(message)


def delete_income(message: types.Message) -> None:
    """Вывод всех записей дохода для удаления."""
    list_income = sql_records_10_incomes(message.chat.id)
    if not list_income:
        bot.send_message(message.chat.id, 'Нет записей для удаления.')
        return start(message)
    response = 'Последние 10 записей:\n'
    for record in list_income:
        response += f'ID: {record[0]}, ' \
                    f'Сумма: {record[1]}, ' \
                    f'Описание: {record[2]}, ' \
                    f'Дата: {record[3]}\n'
    bot.send_message(message.chat.id, response)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(RETURN_MENU)
    bot.send_message(message.chat.id,
                     DELETE_RECORDS_ID,
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, process_delete_id)


def process_delete_id(message: types.Message) -> None:
    """Удаление записи Дохода."""
    if message.text == RETURN_MENU:
        return start(message)
    try:
        income_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            ERROR_NUMBER_ID)
        return delete_income(message)
    choice_income = sql_select_all_incomes_user(income_id, message.chat.id)
    if not choice_income:
        bot.send_message(message.chat.id, ERROR_RECORDS_ID)
        return start(message)
    sql_delete_income(income_id, message.chat.id)
    bot.send_message(message.chat.id, 'Доход успешно удален!')
    start(message)


def process_expense_description(message: types.Message,
                                amount: float) -> None:
    """Добавление описания у новой записи расхода."""
    description = message.text.strip()
    categories = sql_all_category()

    if categories:
        category_buttons = [cat[1] for cat in categories]
        category_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in category_buttons:
            category_keyboard.add(category)
        bot.send_message(message.chat.id, 'Выберите категорию:',
                         reply_markup=category_keyboard)
        bot.register_next_step_handler(
            message, process_expense_category,
            amount, description, categories)
    else:
        bot.send_message(
            message.chat.id,
            'Нет категорий. '
            'Укажи новую категорию и попробуй заново создать запись о расходе')

        return add_category(message)


def process_expense_category(message: types.Message, amount: float,
                             description: str,
                             categories: List[Tuple[int, str]]) -> None:
    """Выбор категории у новой записи расхода."""
    selected_category = message.text.strip()

    category_id = None
    for cat in categories:
        if cat[1] == selected_category:
            category_id = cat[0]
            break

    if category_id is None:
        if selected_category == 'Назад':
            return process_action(message, 'expense')
        bot.send_message(message.chat.id,
                         'Категория не найдена. Пожалуйста, выберите снова.')
        return process_expense_description(message,
                                           amount)
    sql_insert_expense(amount, description, category_id, message.chat.id)
    bot.send_message(message.chat.id,
                     f'Расход в размере {amount} с описанием "{description}" '
                     f'успешно добавлен в категорию "{selected_category}".')
    start(message)


def edit_expense(message: types.Message) -> None:
    """Вывод 10 записей расхода -> для редактирования."""
    list_expense = sql_records_10_expense(message.chat.id)
    if not list_expense:
        bot.send_message(message.chat.id,
                         'Нет записей расходов для редактирования.')
        return start(message)
    response = 'Последние 10 записей:\n'
    for record in list_expense:
        response += f'ID: {record[0]}, ' \
                    f'Сумма: {record[1]}, ' \
                    f'Категория: {record[2]}, ' \
                    f'Описание: {record[3]}, ' \
                    f'Дата: {record[4]}\n'
    bot.send_message(message.chat.id, response)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(RETURN_MENU)
    bot.send_message(message.chat.id,
                     EDIT_RECORDS_ID,
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, process_edit_id_expense)


def process_edit_id_expense(message: types.Message) -> None:
    """Выбор записи расхода по id для редактирования."""
    if message.text == RETURN_MENU:
        return start(message)
    try:
        expense_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            'Пожалуйста, введите действительный ID (целое число)')
        return edit_expense(message)
    choice_expense = sql_select_all_expenses_user(expense_id, message.chat.id)
    if not choice_expense:
        bot.send_message(message.chat.id, 'Запись с таким ID не найдена.')
        return edit_expense(message)
    bot.send_message(message.chat.id, 'Введите новую сумму:')
    bot.register_next_step_handler(
        message, process_new_amount_expense, expense_id)


def process_new_amount_expense(message: types.Message,
                               expense_id: int) -> None:
    """Редактирование суммы у редактируемой записи."""
    try:
        new_amount = float(message.text)
        if new_amount < 1:
            raise ValueError(ERROR_NUMBER)
    except ValueError:
        bot.send_message(
            message.chat.id,
            ERROR_NUMBER)
        return process_edit_id_expense(message)
    bot.send_message(message.chat.id, 'Введите новое описание:')
    bot.register_next_step_handler(message, process_new_category_expense,
                                   expense_id, new_amount)


def process_new_category_expense(message: types.Message,
                                 expense_id: int,
                                 new_amount: float) -> None:
    """Редактирование описания у редактируемой записи."""
    new_description = message.text.strip()
    categories = sql_all_category()
    if categories:
        category_buttons = [cat[1] for cat in
                            categories]
        category_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in category_buttons:
            category_keyboard.add(category)
        category_keyboard.add('Назад')
        bot.send_message(message.chat.id, 'Выберите категорию:',
                         reply_markup=category_keyboard)
        bot.register_next_step_handler(
            message,
            finalize_edit_expense, expense_id, new_amount, new_description)
    else:
        bot.send_message(
            message.chat.id,
            'Нет категорий. Пожалуйста, добавьте категорию сначала.')
        return process_new_amount_expense(message, expense_id)


def finalize_edit_expense(message: types.Message, expense_id: int,
                          new_amount: float, new_description: str) -> None:
    """Выбор категории для записи Расхода."""
    category_result = sql_select_id_category(message.text)
    if category_result:
        sql_update_expense(new_amount, new_description,
                           category_result[0], expense_id)
        bot.send_message(message.chat.id, 'Расход успешно обновлен!')
        start(message)
    else:
        bot.send_message(
            message.chat.id,
            'Категория не найдена! Пожалуйста, введите корректную категорию.')
        bot.register_next_step_handler(
            message,
            finalize_edit_expense, expense_id, new_amount, new_description)


def delete_expense(message: types.Message) -> None:
    """Вывод 10 записей расхода перед удалением."""
    list_income = sql_records_10_expense(message.chat.id)
    if not list_income:
        bot.send_message(message.chat.id, 'Нет записей для удаления.')
        return start(message)
    response = 'Последние 10 записей:\n'
    for record in list_income:
        response += (f'ID: {record[0]}, '
                     f'Сумма: {record[1]}, '
                     f'Описание: {record[2]}, '
                     f'Категория: {record[3]}'
                     f'Дата: {record[4]}\n')
    bot.send_message(message.chat.id, response)
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(RETURN_MENU)
    bot.send_message(message.chat.id,
                     DELETE_RECORDS_ID,
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, process_delete_id_expense)


def process_delete_id_expense(message: types.Message) -> None:
    """Удаление записи Расхода."""
    if message.text == RETURN_MENU:
        return start(message)
    try:
        income_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            'Пожалуйста, введите действительный ID (целое число)')
        return edit_expense(message)
    choice_income = sql_select_all_expenses_user(income_id, message.chat.id)
    if not choice_income:
        bot.send_message(message.chat.id, 'Запись с таким ID не найдена.')
        return start(message)
    sql_delete_expense(income_id, message.chat.id)
    bot.send_message(message.chat.id, 'Расход успешно удален!')
    start(message)


def ask_period(message: types.Message) -> None:
    """Кнопки для выбора периода."""
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True)
    markup.add(*list(PERIODS.keys()))
    bot.send_message(message.chat.id, 'Выберите период:', reply_markup=markup)


@bot.message_handler(
    func=lambda message: message.text in list(PERIODS.keys()))
def handle_period_selection(message: types.Message) -> None:
    """Кнопки для выбора периода для получения статистики по Расходам."""
    user_periods = PERIODS.get(message.text)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add('Таблица', 'Диаграмма', 'График', 'Меню')
    bot.send_message(message.chat.id,
                     'Выберите формат отображения:',
                     reply_markup=markup)
    bot.register_next_step_handler(message, handle_format_selection,
                                   user_periods)


def handle_format_selection(message: types.Message,
                            user_periods: Dict[str, str]) -> None:
    """Выбор формата вывода статистики."""
    try:
        selected_format = message.text
        if selected_format == 'Таблица':
            show_table_statistics(message, user_periods)
        elif selected_format == 'Диаграмма':
            show_chart_statistics(message, user_periods)
        elif selected_format == 'График':
            show_graph_statistics(message, user_periods)
        elif message.text == 'Меню':
            start(message)
        else:
            raise ValueError()
    except ValueError:
        bot.send_message(message.chat.id, 'Неверный выбор формата')
        start(message)


def show_table_statistics(message: types.Message,
                          user_periods: Dict[str, str]) -> None:
    """Статистика в виде таблице (топ 5 больших затрат)."""
    client_id = message.chat.id
    top_expenses = pd.read_sql_query(
        sql_for_table(user_periods, client_id), con)
    total_expenses = top_expenses['amount'].sum()
    if not total_expenses:
        bot.send_message(message.chat.id, ERROR_RECORD_EMPTY)
        return start(message)
    file_name = f'top_expenses_{client_id}.xlsx'
    top_expenses.to_excel(file_name, index=True)

    with open(file_name, 'rb') as file:
        bot.send_document(message.chat.id, file)
        bot.send_message(
            message.chat.id,
            'Таблица - Топ 5 крупных затрат за указанный период отправлен')
    os.remove(file_name)
    start(message)


def show_graph_statistics(message: types.Message,
                          user_periods: Dict[str, str]) -> None:
    """Статистика в виде графика."""
    client_id = message.chat.id
    choice_expenses = pd.read_sql_query(
        sql_for_graph(user_periods, client_id), con)

    # преобразование столбца date_added и amount к нужному формату
    choice_expenses['date_added'] = pd.to_datetime(
        choice_expenses['date_added'])
    total_expenses = choice_expenses['amount'].sum()
    if not total_expenses:
        bot.send_message(message.chat.id, ERROR_RECORD_EMPTY)
        return start(message)
    choice_expenses['amount'] = pd.to_numeric(choice_expenses['amount'],
                                              errors='coerce')
    choice_expenses = choice_expenses.sort_values(by='date_added')
    file_name = f'expenses_{client_id}.xlsx'
    choice_expenses.to_excel(file_name, index=True)

    plt.figure(figsize=(10, 6))
    plt.plot(choice_expenses['date_added'], choice_expenses['amount'],
             marker='o', linewidth=2,
             color='skyblue', label='Расходы по датам')
    plt.xlabel('Дата')
    plt.ylabel('Сумма, руб')
    plt.title('Расход за выбранный период')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()
    graph_file_name = f'choice_expenses_graph_{client_id}.png'
    plt.tight_layout()
    plt.savefig(graph_file_name)
    plt.close()
    with open(graph_file_name, 'rb') as graph_file:
        bot.send_photo(message.chat.id, graph_file)

    bot.send_message(message.chat.id,
                     f'Всего расходов за выбранный период: {total_expenses}')
    os.remove(file_name)
    os.remove(graph_file_name)
    start(message)


def show_chart_statistics(message: types.Message,
                          user_periods: Dict[str, str]) -> None:
    """Статистика в виде круговой диаграммы с распределением по категориям."""
    client_id = message.chat.id
    category_expenses = pd.read_sql_query(
        sql_for_chart(user_periods, client_id), con)
    # Получаем категории по id
    category_expenses['category'] = category_expenses['category_id'].apply(
        get_category_name)

    total_expenses = category_expenses['total_amount'].sum()
    if not total_expenses:
        bot.send_message(message.chat.id, ERROR_RECORD_EMPTY)
        return start(message)
    plt.figure(figsize=(10, 6))
    plt.pie(
        category_expenses['total_amount'],
        labels=category_expenses['category'],
        autopct='%.1f%%',
    )
    plt.title('Распределение расходов по категориям')
    plt.axis('equal')

    graph_file_name = f'category_expenses_graph_{client_id}.png'
    plt.savefig(graph_file_name)
    plt.close()

    with open(graph_file_name, 'rb') as graph_file:
        bot.send_photo(message.chat.id, graph_file)

    total_expenses = category_expenses['total_amount'].sum()
    bot.send_message(message.chat.id,
                     f'Всего расходов за выбранный период: {total_expenses}')
    os.remove(graph_file_name)
    start(message)


def show_table_statistics_incomes(message: types.Message) -> None:
    """Отображение статистики дохода за месяц."""
    client_id = message.chat.id
    choice_expenses = pd.read_sql_query(sql_for_graph_incomes(client_id), con)
    choice_expenses['date_added'] = pd.to_datetime(
        choice_expenses['date_added'])
    total_expenses = choice_expenses['amount'].sum()
    if not total_expenses:
        bot.send_message(message.chat.id, ERROR_RECORD_EMPTY)
        return start(message)
    choice_expenses['amount'] = pd.to_numeric(choice_expenses['amount'],
                                              errors='coerce')
    choice_expenses = choice_expenses.sort_values(by='date_added')
    file_name = f'incomes_{client_id}.xlsx'
    choice_expenses.to_excel(file_name, index=True)

    plt.figure(figsize=(10, 6))
    plt.plot(choice_expenses['date_added'], choice_expenses['amount'],
             marker='o', linewidth=2,
             color='skyblue', label='Доходы по датам')
    plt.xlabel('Дата')
    plt.ylabel('Сумма, руб')
    plt.title('Доходы за месяц')
    plt.xticks(rotation=45)
    plt.grid(axis='y')

    graph_file_name = f'choice_incomes_graph_{client_id}.png'
    plt.tight_layout()
    plt.savefig(graph_file_name)
    plt.close()

    with open(file_name, 'rb') as file:
        bot.send_document(message.chat.id, file)
        bot.send_message(message.chat.id, 'Таблица доходов за месяц')
    with open(graph_file_name, 'rb') as graph_file:
        bot.send_photo(message.chat.id, graph_file,
                       caption=f'Всего доходов за месяц: {total_expenses}')
    os.remove(file_name)
    os.remove(graph_file_name)
    start(message)


@bot.message_handler(content_types=ALL_CONTENT_TYPES)
def error_message(message: types.Message) -> None:
    """Отправка сообщения при некорректном запросе."""
    chat = message.chat
    chat_id = chat.id
    bot.send_photo(chat.id, get_new_image())
    bot.send_message(chat_id=chat_id,
                     text='Я вас не понял, используйте /start')


def get_new_image():
    """Получение фотографий."""
    try:
        response = requests.get('https://api.thecatapi.com/v1/images/search')
    except Exception as error:
        logging.error(f'Ошибка при запросе к основному API: {error}')
        new_url = 'https://api.thedogapi.com/v1/images/search'
        response = requests.get(new_url)
    response = response.json()
    random_cat = response[0].get('url')
    return random_cat


def main():
    """Запсук бота."""
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
