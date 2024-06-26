
import threading, asyncio

import app_flask
from app_tg import dp, bot

async def create_db():
    db = await app_flask.get_db()
    cursor = await db.cursor()

    await cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS Tickets
        (
            id INTEGER PRIMARY KEY, 
            user_id INTEGER,
            user_nickname TEXT,
            user_name TEXT,
            status TEXT,
            chat_history TEXT,
            theme TEXT
        )
        '''
    )

    await cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS Photos
        (
            id INTEGER PRIMARY KEY,
            data BLOB,
            fileid TEXT
        )
        '''
    )

    await db.commit()

async def startup():
    await create_db()
    threading.Thread(target=app_flask.run).start()
    await dp.start_polling(bot)

if __name__ == '__main__':

    asyncio.run(startup())
