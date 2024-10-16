"""Код для запросов к БД."""

from database import db_connect

con = db_connect()
cur = con.cursor()


def sql_select_user_id(user_id):
    """Поиск пользователя в БД."""
    cur.execute(
        '''
        SELECT * FROM clients WHERE telegram_id = ?
        ''', (str(user_id),))
    return cur.fetchone()


def sql_insert_user_id(user_id):
    """Добавление пользователя в БД."""
    cur.execute(
        '''
        INSERT INTO clients (telegram_id) VALUES (?)
        ''', (str(user_id),))
    con.commit()


def sql_select_category(name):
    """Список всех категорий."""
    cur.execute(
        '''
        SELECT * FROM categories WHERE name = ?
        ''', (name,))
    return cur.fetchone()


def sql_select_id_category(name):
    """Поиск категории по имени."""
    cur.execute(
        '''
        SELECT id FROM categories WHERE name = ?
        ''', (name,))
    return cur.fetchone()


def sql_select_name_category(category_id):
    """Поиск имени категории по id."""
    cur.execute(
        '''
        SELECT name FROM categories WHERE id = ?
        ''', (category_id,))
    return cur.fetchone()


def sql_insert_category(name):
    """Добавлени имени категории."""
    cur.execute(
        '''
        INSERT INTO categories (name) VALUES (?)
        ''', (name,))
    con.commit()


def sql_all_category():
    """Поиск id и имени всех категорий."""
    cur.execute(
        '''
        SELECT id, name FROM categories
        '''
    )
    return cur.fetchall()


def sql_insert_incomes(amount, description, user_id):
    """Добавление записи дозода."""
    cur.execute(
        '''
        INSERT INTO incomes
            (amount, description, client_id) VALUES (?, ?, ?)
        ''', (amount, description, user_id,)
    )
    con.commit()


def sql_records_10_incomes(user_id):
    """Вывод 10 записей дохода."""
    cur.execute(
        '''
        SELECT id, amount, description, date_added FROM incomes
        WHERE client_id = ?
        ORDER BY id DESC
        LIMIT 10
        ''', (user_id,))

    return cur.fetchall()


def sql_select_all_incomes_user(income_id, user_id):
    """Запрос для проверки авторства записи."""
    cur.execute(
        '''
        SELECT * FROM incomes WHERE id = ? AND client_id = ?
        ''', (income_id, user_id,))
    return cur.fetchone()


def sql_update_income(amount, description, income_id):
    """Обновление записи о доходе."""
    cur.execute(
        '''
        UPDATE incomes
        SET amount = ?, description = ?
        WHERE id = ?
        ''',
        (amount, description, income_id,))
    con.commit()


def sql_delete_income(income_id, user_id):
    """Удаление записи дохода."""
    cur.execute(
        '''
        DELETE FROM incomes
        WHERE id = ? AND client_id = ?
        ''', (income_id, user_id))
    con.commit()


def sql_insert_expense(amount, description, category_id, user_id):
    """Добавление записи расхода."""
    cur.execute(
        '''
        INSERT INTO expenses
            (amount, description, category_id, client_id) VALUES (?, ?, ?, ?)
        ''',
        (amount, description, category_id, user_id,))
    con.commit()


def sql_records_10_expense(user_id):
    """Вывод 10 записей расхода."""
    cur.execute(
        '''
        SELECT e.id, e.amount, c.name
            AS category_name, e.description, e.date_added
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.client_id = ?
        ORDER BY e.id DESC
        LIMIT 10
        ''', (user_id,))
    return cur.fetchall()


def sql_select_all_expenses_user(expense_id, user_id):
    """Запрос для проверки авторства."""
    cur.execute(
        '''
        SELECT * FROM expenses WHERE id = ? AND client_id = ?
        ''', (expense_id, user_id,))
    return cur.fetchone()


def sql_update_expense(amount, description, category_id, expense_id):
    """Обновление записи расхода."""
    cur.execute(
        '''
        UPDATE expenses
        SET amount = ?, description = ?, category_id = ?
        WHERE id = ?''',
        (amount, description, category_id, expense_id,))
    con.commit()


def sql_delete_expense(expense_id, user_id):
    """Удаление записи расхода."""
    cur.execute(
        '''
        DELETE FROM expenses
        WHERE id = ? AND client_id = ?
        ''', (expense_id, user_id,))
    con.commit()


def sql_for_table(periods, user_id):
    """Вывод записей расходов на выбранный период."""
    return (
        f'''
        SELECT e.amount, e.description, e.date_added, c.name AS category_name
        FROM expenses e
        JOIN categories c ON e.category_id = c.id
        WHERE e.date_added >= datetime("now", "{periods}")
            AND e.client_id = {user_id}
        ORDER BY e.amount DESC
        LIMIT 5
        '''
    )


def sql_for_graph(periods, user_id):
    """Вывод записей расходов для графика."""
    return (
        f'''
        SELECT amount, description, date_added
        FROM expenses
        WHERE date_added >= datetime("now", "{periods}")
        AND client_id = {user_id}
        '''
    )


def sql_for_chart(periods, user_id):
    """Вывод записей расходов для диаграммы."""
    return (
        f'''
        SELECT SUM(amount) as total_amount, category_id
        FROM expenses
        WHERE date_added >= datetime("now", "{periods}")
            AND client_id = {user_id}
        GROUP BY category_id
        '''
    )


def sql_for_graph_incomes(user_id):
    """Вывод записей доходов для графика."""
    return (
        f'''
        SELECT amount, description, date_added
        FROM incomes
        WHERE date_added >= datetime("now", "start of month")
        AND client_id = {user_id}
        '''
    )


def add_user(telegram_id):
    """Проверка нового пользователя."""
    user = sql_select_user_id(telegram_id)
    if user is None:
        sql_insert_user_id(telegram_id)


def get_category_name(category_id):
    """Функция для получения названий категорий по ID для диаграммы."""
    result = sql_select_name_category(category_id)
    return result[0] if result else 'Неизвестная категория'
