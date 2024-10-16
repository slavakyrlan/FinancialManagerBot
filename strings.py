RETURN_MENU = 'Меню'
EDIT_RECORDS_ID = 'Введите ID записи, которую хотите редактировать:'
DELETE_RECORDS_ID = 'Введите ID записи, которую хотите удалить:'

ERROR_NUMBER = 'Необходимо вести положительное число'
ERROR_NUMBER_ID = 'Пожалуйста, введите действительный ID (целое число)'
ERROR_RECORDS_ID = 'Запись с таким ID не найдена'
ERROR_RECORD_EMPTY = 'Записей доходов/расходов нет'

HELP_MSG = '👋 Привет! Это Финансовый менеджер - ' \
           'ваш личный помощник для учета расходов.\n\n'\
           '📊 С помощью этого бота вы можете:\n'\
           '1. Вводить свои доходы, и расходы по категориям.\n'\
           '2. Получать графики ваших затрат, ' \
           'чтобы лучше контролировать свои финансы.\n\n'\
           '📝 Команды:\n'\
           '- /start - начать диалог с ботом.\n'\
           '- /help - получить помощь по использованию бота.\n\n'\
           '❗ Если у вас возникли проблемы или есть вопросы, ' \
           'не стесняйтесь писать @slavakyrlan. '\
           'Я всегда готов помочь вам!'


def send_instruction(type_budget):
    result = f'Вы нажали на кнопку "{type_budget}", доступные опции: '\
             f'три дополнительных кнопки:\n1. Добавить - используйте эту '\
             'кнопку, чтобы внести новый доход в систему.\n2. Редактировать '\
             '- с помощью этой кнопки вы сможете изменить уже существующую '\
             'запись о доходе.\n3. Удалить - если вам нужно удалить запись '\
             'о доходе, нажмите эту кнопку.\n'
    if type_budget == 'Расход':
        result += '4. Добавить категорию - если вы хотите добавить новую ' \
                  'категорию для своих расходов, это поможет вам лучше ' \
                  'организовать ваши финансы и отслеживать источники ' \
                  'ваших доходов.\n'
    result += 'Просто выберите нужную опцию для управления вашими ' \
              'записями о доходе!'
    return result
