# FinancialManagerBot
Финансовый менеджер 
Это Telegram-бот для учета расходов. Пользователь может вводить свои расходы по категориям и получать графики своих затрат.

## Требования

- Python 3.6 и выше
- Библиотеки:
  - `python-telegram-bot`
  - `matplotlib`
  - `pandas`
    
## Установка

1. Склонируйте репозиторий:
   ```bash
   git clone <url_репозитория>
   ```
3. Перейдите в директорию проекта, пример:
   ```bash
   cd FinancialManagerBot
   ```
5. Создайте виртуальное окружение:
   ```bash
   python -m venv venv
   ```
7. Активируйте виртуальное окружение
8. Установите необходимые библиотеки:
   ```bash
   pip install -r requirements.txt
   ```
10. Создай файл `.env` командой:
    ```bash
    touch .env
    ``` 
12. Открой `.env` и добавь следующее: ```TOKEN=<твой токен>```
13. Замените значение `<твой токен>` в файле `.env` на токен вашего бота, полученный от [BotFather](https://core.telegram.org/bots#botfather).

## Использование

1. Активируйте виртуальное окружение 
2. Запустите создание базы данных:
   ```bash
   python database.py run
   ```
2. Запустите бота:
   ```bash
   python bot.py run
   ```
4. Откройте Telegram и найдите вашего бота.
5. Начните взаимодействие с помощью команды `/start`.

## Функционал
- **/start**: Регистрация пользователя в системе.
- **/help**: Вызов помощи

