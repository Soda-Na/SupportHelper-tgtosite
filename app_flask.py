import asyncio
import aiosqlite
import json

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from time import time
from jinja2 import Environment, select_autoescape

app = Flask(__name__)

def timestamp_to_datetime(timestamp):
    timestamp = int(timestamp)
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%m/%d/%Y, %I:%M:%S %p')

app.jinja_env.filters['timestamp_to_datetime'] = timestamp_to_datetime

async def get_db():
    db = await aiosqlite.connect('tickets.db')
    return db

async def create_db():
    db = await get_db()
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
            chat_history TEXT
        )
        '''
    )

    await db.commit()

@app.route('/tickets', methods=['GET'])
async def tickets():
    # Получение списка тикетов
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM Tickets")
    tickets = await cursor.fetchall()
    return render_template('tickets.html', tickets=tickets)

@app.route('/tickets/<int:id>', methods=['GET', 'POST'])
async def ticket(id):
    db = await get_db()
    cursor = await db.cursor()

    await cursor.execute("SELECT * FROM Tickets")
    tickets = await cursor.fetchall()

    if request.method == 'POST':
        # Добавление нового сообщения в историю чата
        new_message = request.form['message']
        await cursor.execute("SELECT chat_history FROM Tickets WHERE id = ?", (id,))
        chat_history = json.loads((await cursor.fetchone())[0])
        chat_history.append((new_message, int(time()), 'Вы'))  # 'User' is a placeholder for the sender's nickname
        await cursor.execute("UPDATE Tickets SET chat_history = ? WHERE id = ?", (json.dumps(chat_history), id))
        await db.commit()
        return redirect(url_for('ticket', id=id))  # Redirect after POST

    # Получение информации о тикете и истории чата
    await cursor.execute("SELECT * FROM Tickets WHERE id = ?", (id,))
    ticket = await cursor.fetchone()
    chat_history = json.loads(ticket[5])
    return render_template('ticket.html', ticket=ticket, chat_history=chat_history, tickets=tickets)

@app.route('/tickets/send_message', methods=['POST'])
async def send_message():
    message = request.form['message']
    id = request.form['id']
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT chat_history FROM Tickets WHERE id = ?", (id,))
    chat_history = json.loads((await cursor.fetchone())[0])
    chat_history.append((message, int(time()), 'Вы'))  # 'User' is a placeholder for the sender's nickname
    await cursor.execute("UPDATE Tickets SET chat_history = ? WHERE id = ?", (json.dumps(chat_history), id))
    await db.commit()
    return jsonify({'status': 'success'})

@app.route('/tickets/<int:id>/chat', methods=['GET'])
async def get_chat(id):
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT chat_history FROM Tickets WHERE id = ?", (id,))
    chat_history = json.loads((await cursor.fetchone())[0])
    return jsonify(chat_history)


if __name__ == '__main__':
    asyncio.run(create_db())
    app.run(debug=True)