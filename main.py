
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

    await db.commit()

async def startup():
    loop = asyncio.get_event_loop()
    app_flask.loop = loop

    await create_db()
    threading.Thread(target=app_flask.run).start()
    await dp.start_polling(bot)

if __name__ == '__main__':

    asyncio.run(startup())
