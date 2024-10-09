import sqlite3


def db_connect():
    return sqlite3.connect('finance_bot.db')


def create_tables():
    con = db_connect()
    cur = con.cursor()
    cur.execute('''
                CREATE TABLE IF NOT EXITS incomes(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL,
                    description TEXT,
                    category TEXT,
                    date TEXT
                )
                ''')
    cur.execute('''
                CREATE TABLE IF NOT EXITS expenses(
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL,
                    description TEXT,
                    category TEXT,
                    date TEXT
                )
                ''')
    con.commit()
    con.close()


create_tables()
