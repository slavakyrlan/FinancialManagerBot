import logging
import os
import requests
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from dotenv import load_dotenv
from telebot import TeleBot, types
from database import db_connect

load_dotenv()

secret_token = os.getenv('TOKEN')
bot = TeleBot(token=secret_token)

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename='main.log',
    filemode='w'
)

BUTTONS = ["Доход", "Расход", "Статистика"]
periods = {
    'День': '-1 day',
    'Неделя': '-7 day',
    'Месяц': '-1 month',
    'Квартал': '-3 month',
    'Год': '-1 year'
}

con = db_connect()
cur = con.cursor()


@bot.message_handler(commands=['start'])
def start(message):
    """Стартовое сообщение"""
    name = message.from_user.first_name
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(*BUTTONS)

    bot.send_message(
        chat_id=message.chat.id,
        text=f'Привет, {name}. Выберите опцию:',
        reply_markup=keyboard,
    )
    add_user(message.chat.id)


def add_user(telegram_id):
    cur.execute("SELECT * FROM clients WHERE telegram_id = ?",
                (str(telegram_id),))
    user = cur.fetchone()

    if user is None:
        cur.execute("INSERT INTO clients (telegram_id) VALUES (?)",
                    (str(telegram_id),))
        con.commit()


@bot.message_handler(func=lambda message: message.text in BUTTONS)
def handle_option(message):
    """Меню бота"""
    if message.text == "Доход":
        send_action_keyboard(message, "income")
    elif message.text == "Расход":
        send_action_keyboard(message, "expense")
    elif message.text == "Статистика":
        ask_period(message)


def send_action_keyboard(message, action_type):
    """Кнопки у Дохода/Расхода"""
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)

    if action_type == "income":
        keyboard.add("Добавить", "Редактировать", "Удалить", "Назад")
        text = "Выберите действие с доходом:"
    elif action_type == "expense":
        keyboard.add("Добавить", "Редактировать", "Удалить",
                     "Добавить категорию", "Назад")
        text = "Выберите действие с расходом:"

    bot.send_message(
        chat_id=message.chat.id,
        text=text,
        reply_markup=keyboard,
    )
    bot.register_next_step_handler(message, process_action, action_type)


def process_action(message, action_type):
    """Функции для Дохода/Расхода"""
    if message.text == "Добавить":
        hide_keyboard = types.ReplyKeyboardRemove()
        text = "Введите сумму расходов:" if \
            action_type == "expense" else "Введите сумму дохода:"
        bot.send_message(message.chat.id, text, reply_markup=hide_keyboard)
        bot.register_next_step_handler(message, adding_records, action_type)
    elif message.text == "Редактировать":
        edit_function = edit_expense if \
            action_type == "expense" else edit_income
        edit_function(message)
    elif message.text == "Удалить":
        delete_function = delete_expense if \
            action_type == "expense" else delete_income
        delete_function(message)
    elif message.text == "Добавить категорию":
        add_category(message)
    elif message.text == "Назад":
        start(message)


def adding_records(message, action_type):
    """Добавление записей для Дохода/Расхода"""
    try:
        amount = float(message.text.strip())
        if action_type == "income":
            bot.send_message(message.chat.id, "Введите описание дохода:")
            bot.register_next_step_handler(
                message, add_description_income, amount)
        elif action_type == "expense":
            hide_keyboard = types.ReplyKeyboardRemove()
            bot.send_message(message.chat.id, "Введите описание расхода:",
                             reply_markup=hide_keyboard)
            bot.register_next_step_handler(
                message, process_expense_description, amount)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Ошибка, вы отправили некорректную сумму.")
        start(message)


def add_category(message):
    """Добавление новой категории"""
    hide_keyboard = types.ReplyKeyboardRemove()
    bot.send_message(
        message.chat.id, "Введите новую категорию:",
        reply_markup=hide_keyboard)

    def handle_new_category(msg):
        new_category = str(msg.text)

        cur.execute('SELECT * FROM categories WHERE name = ?', (new_category,))
        if cur.fetchone() is not None:
            bot.send_message(
                msg.chat.id,
                f"Категория '{new_category}' уже существует. "
                f"Пожалуйста, введите другое название.")
            return add_category(msg)

        cur.execute("INSERT INTO categories (name) VALUES (?)",
                    (new_category,))
        con.commit()
        bot.send_message(
            msg.chat.id, f"Категория '{new_category}' успешно добавлена!")
        start(msg)

    bot.register_next_step_handler(message, handle_new_category)


def add_description_income(message, amount):
    """Добавление новой записи дохода в БД"""
    description = message.text
    cur.execute(
        '''
        INSERT INTO incomes 
            (amount, description, client_id) VALUES (?, ?, ?)''',
        (amount, description, message.chat.id))
    con.commit()

    bot.send_message(message.chat.id, "Доход успешно добавлен!")
    start(message)


def edit_income(message):
    """Лист последних 10 записей дохода -> изменение записи"""
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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Вернутся в меню')

    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите редактировать:",
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, edit_income_by_id)


def edit_income_by_id(message):
    """Изменение записи Дохода по id"""
    if message.text == "Вернутся в меню":
        start(message)
        return
    try:
        income_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите действительный ID (целое число)")
        return edit_income(message)
    cur.execute('SELECT * FROM incomes WHERE id = ? AND client_id = ?',
                (income_id, message.chat.id,))
    choice_income = cur.fetchone()
    if not choice_income:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return edit_income(message)
    bot.send_message(message.chat.id, "Введите новую сумму:")
    bot.register_next_step_handler(message, process_new_amount, income_id)


def process_new_amount(message, income_id):
    """Редактирование суммы у записи дохода"""
    new_amount = float(message.text)
    bot.send_message(message.chat.id, "Введите новое описание:")
    bot.register_next_step_handler(message, finalize_edit, income_id,
                                   new_amount)


def finalize_edit(message, income_id, new_amount):
    """Редактирование описания у записи дохода"""
    new_description = message.text
    cur.execute(
        '''
        UPDATE incomes
        SET amount = ?, description = ?
        WHERE id = ?
        ''',
        (new_amount, new_description, income_id))
    con.commit()
    bot.send_message(message.chat.id, "Доход успешно обновлен!")
    start(message)


def delete_income(message):
    """Вывод всех записей дохода для удаления"""
    cur.execute(
        '''
        SELECT id, amount, description, date_added FROM incomes
        WHERE client_id = ?
        ORDER BY id DESC 
        LIMIT 10
        ''', (message.chat.id,))
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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Вернутся в меню')
    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите удалить:",
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, process_delete_id)


def process_delete_id(message):
    """Удаление записи Дохода"""
    if message.text == "Вернутся в меню":
        start(message)
        return
    try:
        income_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите действительный ID (целое число)")
        return delete_income(message)
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


def process_expense_description(message, amount):
    """Добавление описания у новой записи расхода"""
    description = message.text.strip()
    cur.execute("SELECT id, name FROM categories")
    categories = cur.fetchall()

    if categories:
        category_buttons = [cat[1] for cat in
                            categories]
        category_keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for category in category_buttons:
            category_keyboard.add(category)
        bot.send_message(message.chat.id, "Выберите категорию:",
                         reply_markup=category_keyboard)
        bot.register_next_step_handler(
            message, lambda msg: process_expense_category(
                msg, amount, description, categories))
    else:
        bot.send_message(
            message.chat.id,
            "Нет категорий. Пожалуйста, добавьте категорию сначала.")
        return process_action(message, 'expense')


def process_expense_category(message, amount, description, categories):
    """Выбор категории у новой записи расхода"""
    selected_category = message.text.strip()

    category_id = None
    for cat in categories:
        if cat[1] == selected_category:
            category_id = cat[0]
            break

    if category_id is None:
        if selected_category == "Назад":
            return process_action(message, 'expense')
        bot.send_message(message.chat.id,
                         "Категория не найдена. Пожалуйста, выберите снова.")
        return process_expense_description(message,
                                           amount)
    add_expense(amount, description, category_id, message.chat.id)
    bot.send_message(message.chat.id,
                     f"Расход в размере {amount} с описанием '{description}' успешно добавлен в категорию '{selected_category}'.")
    start(message)


def add_expense(amount, description, category_id, client_id):
    """Добавление новой записи расхода в БД"""
    cur.execute(
        '''
        INSERT INTO expenses
            (amount, description, category_id, client_id) VALUES (?, ?, ?, ?)
        ''',
        (amount, description, category_id, client_id))
    con.commit()


def edit_expense(message):
    """Вывод 10 записей расхода -> для редактирования"""
    cur.execute(
        '''
        SELECT e.id, e.amount, c.name AS category_name, e.description, e.date_added 
        FROM expenses e 
        JOIN categories c ON e.category_id = c.id 
        WHERE e.client_id = ?
        ORDER BY e.id DESC 
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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Вернутся в меню')
    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите редактировать:",
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, process_edit_id_expense)


def process_edit_id_expense(message):
    """Выбор записи расхода по id для редактирования"""
    if message.text == "Вернутся в меню":
        start(message)
        return
    try:
        expense_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите действительный ID (целое число)")
        return edit_expense(message)
    cur.execute('SELECT * FROM expenses WHERE id = ? AND client_id = ?',
                (expense_id, message.chat.id,))
    choice_expense = cur.fetchone()
    if not choice_expense:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return edit_expense(message)
    bot.send_message(message.chat.id, "Введите новую сумму:")
    bot.register_next_step_handler(message, process_new_amount_expense, expense_id)


def process_new_amount_expense(message, expense_id):
    """Редактирование суммы у редактируемой записи"""
    try:
        new_amount = float(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Ошибка, вы отправили некорректную сумму.")
        return process_edit_id_expense(message)
    bot.send_message(message.chat.id, "Введите новое описание:")
    bot.register_next_step_handler(message, process_new_category_expense,
                                   expense_id, new_amount)


def process_new_category_expense(message, expense_id, new_amount):
    """Редактирование описания у редактируемой записи"""
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
    """Выбор категории для записи Расхода"""
    new_category_name = message.text
    cur.execute(
        '''
        SELECT id FROM categories WHERE name = ?
        ''', (new_category_name,))
    category_result = cur.fetchone()
    if category_result:
        new_category_id = category_result[0]
        cur.execute(
            '''UPDATE expenses
               SET amount = ?, description = ?, category_id = ?
               WHERE id = ?''',
            (new_amount, new_description, new_category_id, expense_id))

        con.commit()
        bot.send_message(message.chat.id, "Расход успешно обновлен!")
        start(message)
    else:
        bot.send_message(
            message.chat.id,
            "Категория не найдена! Пожалуйста, введите корректную категорию.")
        bot.register_next_step_handler(
            message,
            finalize_edit_expense, expense_id, new_amount, new_description)


def delete_expense(message):
    """Вывод 10 записей расхода перед удалением"""
    cur.execute(
        '''
        SELECT e.id, e.amount, c.name AS category_name, e.description, e.date_added 
        FROM expenses e 
        JOIN categories c ON e.category_id = c.id 
        WHERE e.client_id = ?
        ORDER BY e.id DESC 
        LIMIT 10
        ''', (message.chat.id,)
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
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add('Вернутся в меню')
    bot.send_message(message.chat.id,
                     "Введите ID записи, которую хотите удалить:",
                     reply_markup=keyboard)
    bot.register_next_step_handler(message, process_delete_id_expense)


def process_delete_id_expense(message):
    """Удаление записи Расхода"""
    if message.text == "Вернутся в меню":
        start(message)
        return
    try:
        income_id = int(message.text)
    except ValueError:
        bot.send_message(
            message.chat.id,
            "Пожалуйста, введите действительный ID (целое число)")
        return edit_expense(message)
    cur.execute('SELECT * FROM expenses WHERE id = ?', (income_id,))
    choice_income = cur.fetchone()
    if not choice_income:
        bot.send_message(message.chat.id, "Запись с таким ID не найдена.")
        return
    cur.execute(
        '''
            DELETE FROM expenses
            WHERE id = ?
        ''',
        (income_id,))
    con.commit()
    bot.send_message(message.chat.id, "Расход успешно удален!")
    start(message)


def ask_period(message):
    """Кнопки для выбора периода"""
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True)
    markup.add(*list(periods.keys()))
    bot.send_message(message.chat.id,
                     "Выберите период:",
                     reply_markup=markup)


@bot.message_handler(
    func=lambda message: message.text in list(periods.keys()))
def handle_period_selection(message):
    """Кнопки для выбора периода для получения статистики по Расходам"""
    user_periods = periods.get(message.text)
    markup = types.ReplyKeyboardMarkup(
        resize_keyboard=True,
        one_time_keyboard=True)

    markup.add("Таблица", "Диаграмма", "График")
    bot.send_message(message.chat.id,
                     "Выберите формат отображения:",
                     reply_markup=markup)
    bot.register_next_step_handler(message, handle_format_selection,
                                   user_periods)


def handle_format_selection(message, user_periods):
    """Выбор формата вывода статистики"""
    selected_format = message.text

    if selected_format == "Таблица":
        show_table_statistics(message, user_periods)
    elif selected_format == "Диаграмма":
        show_chart_statistics(message, user_periods)
    elif selected_format == "График":
        show_graph_statistics(message, user_periods)
    else:
        bot.send_message(message.chat.id, "Неверный выбор формата. Пожалуйста, выберите снова.")
        handle_period_selection(message, user_periods)


def show_table_statistics(message, user_periods):
    """Статистика в виде таблице (топ 5 больших затрат)"""
    client_id = message.chat.id
    top_expenses = pd.read_sql_query(
        f"""
        SELECT e.amount, e.description, e.date_added, c.name AS category_name
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.date_added >= datetime('now', '{user_periods}') 
            AND e.client_id = {client_id}
        ORDER BY e.amount DESC
        LIMIT 5
        """, con)
    file_name = 'top_expenses.xlsx'
    top_expenses.to_excel(file_name, index=True)

    with open(file_name, 'rb') as file:
        bot.send_document(message.chat.id, file)
        bot.send_message(message.chat.id,
                         "Топ 5 крупных затрат за указанный период отправлен.")
    os.remove(file_name)
    start(message)


def show_graph_statistics(message, user_periods):
    """Статистика в виде графика"""
    client_id = message.chat.id
    choice_expenses = pd.read_sql_query(
        f"""        
            SELECT amount, description, date_added        
            FROM expenses         
            WHERE date_added >= datetime('now', '{user_periods}')
            AND client_id = {client_id}         
            """, con)

    # преобразование столбца date_added и amount к нужному формату
    choice_expenses['date_added'] = pd.to_datetime(
        choice_expenses['date_added'])
    choice_expenses['amount'] = pd.to_numeric(choice_expenses['amount'],
                                              errors='coerce')

    choice_expenses = choice_expenses.sort_values(by='date_added')
    file_name = 'expenses.xlsx'
    choice_expenses.to_excel(file_name, index=True)

    plt.figure(figsize=(10, 6))
    plt.plot(choice_expenses['date_added'], choice_expenses['amount'],
             marker='o', linewidth=2, color='skyblue', label='Расходы по датам')
    plt.xlabel('Дата')
    plt.ylabel('Сумма, руб')
    plt.title('Расход за выбранный период')
    plt.xticks(rotation=45)
    plt.grid()
    plt.legend()

    graph_file_name = 'choice_expenses_graph.png'
    plt.tight_layout()
    plt.savefig(graph_file_name)
    plt.close()

    with open(graph_file_name, 'rb') as graph_file:
        bot.send_photo(message.chat.id, graph_file)

    total_expenses = choice_expenses['amount'].sum()
    bot.send_message(message.chat.id,
                     f"Всего расходов за выбранный период: {total_expenses}")

    os.remove(file_name)
    os.remove(graph_file_name)

    start(message)


def show_chart_statistics(message, user_periods):
    """Статистика в виде круговой диаграммы с распределением по категориям"""
    client_id = message.chat.id
    category_expenses = pd.read_sql_query(
        f"""
        SELECT SUM(amount) as total_amount, category_id 
        FROM expenses 
        WHERE date_added >= datetime('now', '{user_periods}') 
            AND client_id = {client_id} 
        GROUP BY category_id""", con)
    # Получаем категории по id
    category_expenses['category'] = category_expenses['category_id'].apply(
        get_category_name)
    plt.figure(figsize=(10, 6))
    plt.pie(
        category_expenses['total_amount'],
        labels=category_expenses['category'],
        autopct='%.1f%%',
    )
    plt.title('Распределение расходов по категориям')
    plt.axis('equal')

    graph_file_name = 'category_expenses_graph.png'
    plt.savefig(graph_file_name)
    plt.close()

    with open(graph_file_name, 'rb') as graph_file:
        bot.send_photo(message.chat.id, graph_file)

    total_expenses = category_expenses['total_amount'].sum()
    bot.send_message(message.chat.id,
                     f"Всего расходов за выбранный период: {total_expenses}")
    os.remove(graph_file_name)
    start(message)


def get_category_name(category_id):
    """Функция для получения названия категории по ID"""
    cur.execute('SELECT name FROM categories WHERE id = ?', (category_id,))
    result = cur.fetchone()
    return result[0] if result else 'Неизвестная категория'


@bot.message_handler(content_types=['text'])
def say_hi(message):
    chat = message.chat
    chat_id = chat.id
    bot.send_photo(chat.id, get_new_image())
    bot.send_message(chat_id=chat_id, text='Я вас не понял, используйте /start')


def get_new_image():
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
    bot.polling(none_stop=True)


if __name__ == '__main__':
    main()
