import sqlite3


def db_connect():
    return sqlite3.connect('finance_bot.db', check_same_thread=False)


def create_tables():
    con = db_connect()
    cur = con.cursor()
    cur.execute('''
                CREATE TABLE IF NOT EXISTS clients(
                    id INTEGER PRIMARY KEY,
                    telegram_id TEXT NOT NULL
                )
    ''')
    cur.execute('''
                CREATE TABLE IF NOT EXISTS categories(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE
                )
    ''')
    cur.execute('''
                CREATE TABLE IF NOT EXISTS incomes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    description TEXT,
                    date_added TEXT DEFAULT (datetime('now')),
                    client_id INTEGER,
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                )
                ''')
    cur.execute('''
                CREATE TABLE IF NOT EXISTS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    description TEXT,
                    date_added TEXT DEFAULT (datetime('now')),
                    category_id INTEGER,
                    client_id INTEGER,
                    FOREIGN KEY (category_id) REFERENCES categories(id),
                    FOREIGN KEY (client_id) REFERENCES clients(id)
                )
                ''')
    con.commit()
    con.close()


def main():
    create_tables()
    print('Таблицы успешно созданы')


if __name__ == '__main__':
    main()


