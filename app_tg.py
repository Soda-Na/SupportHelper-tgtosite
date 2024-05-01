import json
import aiosqlite
import imghdr

from time                   import time

from aiogram                import Bot, Dispatcher, types
from aiogram.filters        import Command, CommandStart
from aiogram.fsm.context    import FSMContext
from aiogram.filters.state  import State, StatesGroup
from aiogram.enums          import ParseMode
from aiogram.utils.keyboard import InlineKeyboardButton, InlineKeyboardBuilder
from PIL                    import Image

async def get_db():
    db = await aiosqlite.connect('tickets.db')
    return db

TOKEN = json.loads(open('token.json', encoding='utf-8').read())['token']

bot = Bot(token=TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer('Привет! Я бот поддержки. Создайте тикет, чтобы получить помощь /ticket')
    await bot.set_my_commands([types.BotCommand(command='ticket', description='Создать новый тикет'), types.BotCommand(command='close_ticket', description='Закрыть тикет')])

class Ticket(StatesGroup):
    theme = State()

@dp.message(Command(types.BotCommand(command='ticket', description='Создать новый тикет')))
async def ticket(message: types.Message, state: FSMContext):
    await state.clear()

    db = await get_db()
    cursor = await db.cursor()
    tickets = await cursor.execute('SELECT * FROM Tickets WHERE user_id = ? AND status = "open"', (message.from_user.id,))
    tickets = await tickets.fetchall()
    if tickets:
        await message.answer('У вас уже есть открытый тикет. Пожалуйста, дождитесь ответа или закройте его командой /close_ticket')
        return

    topics = json.loads(open('topics.json', encoding='utf-8').read())
    topics_keyboard = InlineKeyboardBuilder()
    for topic in topics.get('topics'):
        topics_keyboard.add(InlineKeyboardButton(text=topic, callback_data=f'topic_{topic}'))
    
    topics_keyboard.adjust(1)

    await message.answer('Выберите тему обращения', reply_markup=topics_keyboard.as_markup())

@dp.callback_query(lambda query: query.data.startswith('topic_'))
async def topic(query: types.CallbackQuery, state: FSMContext):
    await state.clear()

    topic = query.data.split('_')[1]
    await state.update_data(topic=topic)

    await query.message.answer(f'Тема обращения: {topic}\nУкажите описание обращения')
    await state.set_state(Ticket.theme)

@dp.message(Command(types.BotCommand(command='close_ticket', description='Закрыть тикет')))
async def close_ticket(message: types.Message):
    db = await get_db()
    cursor = await db.cursor()

    await cursor.execute('SELECT * FROM Tickets WHERE user_id = ? AND status = "open"', (message.from_user.id,))
    ticket = await cursor.fetchone()
    if not ticket:
        await message.answer('У вас нет открытых тикетов')
        return

    await cursor.execute('UPDATE Tickets SET status = "closed" WHERE id = ?', (ticket[0],))
    await db.commit()

    await message.answer('Тикет закрыт')

@dp.message(Ticket.theme)
async def theme(message: types.Message, state: FSMContext):
    data = await state.get_data()
    theme = data['topic']
    description = message.text
    
    check_button = InlineKeyboardBuilder()

    check_button.add(InlineKeyboardButton(text='Подтвердить', callback_data=f'confirm_ticket'))
    check_button.add(InlineKeyboardButton(text='Отменить', callback_data='cancel_ticket'))
    check_button.adjust(1)
    
    await state.clear()
    await state.update_data(theme=theme, description=description)

    await message.answer(f'Тема обращения: {theme}\nОписание: {description}', reply_markup=check_button.as_markup())


@dp.callback_query(lambda query: query.data == "confirm_ticket")
async def confirm_ticket(query: types.CallbackQuery, state: FSMContext):
    db = await get_db()
    cursor = await db.cursor()

    data = await state.get_data()
    theme = data['theme']
    description = data['description']

    description = json.dumps([[description, int(time()), query.from_user.full_name]])

    await state.clear()

    await cursor.execute(
        '''
        INSERT INTO Tickets (user_id, user_nickname, user_name, status, chat_history, theme)
        VALUES (?, ?, ?, ?, ?, ?)
        ''',
        (query.from_user.id, query.from_user.username, query.from_user.full_name, 'open', description, theme)
    )
    await db.commit()

    await query.message.answer('Тикет создан, ожидайте ответа. Вы можете закрыть тикет командой /close_ticket')

@dp.callback_query(lambda query: query.data == 'cancel_ticket')
async def cancel_ticket(query: types.CallbackQuery, state: FSMContext):
    await state.clear()

    await query.message.answer('Создание тикета отменено')
    await query.message.delete()

async def check_if_user_created_ticket(message: types.Message):
    db = await get_db()
    cursor = await db.cursor()

    await cursor.execute('SELECT * FROM Tickets WHERE user_id = ? AND status = "open"', (message.from_user.id,))
    ticket = await cursor.fetchone()
    if ticket:
        return True
    return False

@dp.message(check_if_user_created_ticket)
async def check_if_user_created_ticket(message: types.Message): 
    if message.sticker or message.video or message.voice :
        await message.react([types.ReactionTypeEmoji(emoji='👎')])
        return
    
    db = await get_db()
    cursor = await db.cursor()

    await cursor.execute('SELECT * FROM Tickets WHERE user_id = ? AND status = "open"', (message.from_user.id,))
    ticket = await cursor.fetchone()

    chat_history = json.loads(ticket[5])
    if message.photo:
        photo_blob = await bot.download(message.photo[-1].file_id)
        await cursor.execute('INSERT INTO Photos (data, fileid) VALUES (?, ?)', (photo_blob.read(), message.photo[-1].file_id))
        await db.commit()

        chat_history.append([f'file:{message.photo[-1].file_id}:{Image.open(photo_blob).format}', int(time()), message.from_user.full_name])
    else:
        chat_history.append([message.text, int(time()), message.from_user.full_name])

    print(chat_history)
    
    await cursor.execute('UPDATE Tickets SET chat_history = ? WHERE id = ?', (json.dumps(chat_history), ticket[0]))
    await db.commit()

    await message.react([types.ReactionTypeEmoji(emoji='👍')])