import asyncio
import aiosqlite
import json
import requests

from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify
from time import time
from jinja2 import Environment, select_autoescape

from app_tg import bot

loop: asyncio.AbstractEventLoop = None

app = Flask(__name__)

TOKEN = json.loads(open('token.json', encoding='utf-8').read())['token']

def timestamp_to_datetime(timestamp):
    timestamp = int(timestamp)
    dt = datetime.fromtimestamp(timestamp)
    return dt.strftime('%m/%d/%Y, %I:%M:%S %p')

app.jinja_env.filters['timestamp_to_datetime'] = timestamp_to_datetime

async def get_db():
    db = await aiosqlite.connect('tickets.db')
    return db

def send_message(chat_id, text):
    token = TOKEN
    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = {'chat_id': chat_id, 'text': text}
    response = requests.post(url, data=payload)
    return response

@app.route('/tickets')
async def tickets():
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM Tickets ORDER BY status DESC")
    tickets = await cursor.fetchall()
    return render_template('tickets.html', tickets=tickets)

@app.route('/tickets_data', methods=['GET'])
async def tickets_data():
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM Tickets ORDER BY status DESC")
    tickets = await cursor.fetchall()
    return jsonify(tickets)

@app.route('/tickets/<int:id>', methods=['GET', 'POST'])
async def ticket(id):
    db = await get_db()
    cursor = await db.cursor()

    await cursor.execute("SELECT * FROM Tickets ORDER BY status DESC")
    tickets = await cursor.fetchall()

    await cursor.execute("SELECT * FROM Tickets WHERE id = ?", (id,))
    ticket = await cursor.fetchone()
    chat_history = json.loads(ticket[5])
    return render_template('ticket.html', ticket=ticket, chat_history=chat_history, tickets=tickets)

@app.route('/tickets/send_message', methods=['POST'])
async def send_message1():
    nickname = request.form['nickname']
    message = request.form['message']
    id = request.form['id']
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM Tickets WHERE id = ?", (id,))
    data = await cursor.fetchone()
    chat_history = json.loads(data[5])

    text = f'Ответ от: {nickname}\n\n{message}'

    send_message(data[1], text)

    chat_history.append((message, int(time()), nickname)) 
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

@app.route('/toggle_ticket', methods=['POST'])
async def toggle_ticket():
    id = request.form['id']
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM Tickets WHERE id = ?", (id,))
    data = await cursor.fetchone()
    status = data[4]
    new_status = 'open' if status == 'closed' else 'closed'
    if new_status == 'closed':
        send_message(data[1], f'Тикет с темой "{data[6]}" был закрыт администратором')
    elif new_status == 'open':
        send_message(data[1], f'Тикет с темой "{data[6]}" был открыт администратором')
    await cursor.execute("UPDATE Tickets SET status = ? WHERE id = ?", (new_status, id))
    await db.commit()
    return jsonify({'status': new_status})

@app.route('/images/<id>', methods=['GET'])
async def images(id):
    db = await get_db()
    cursor = await db.cursor()
    await cursor.execute("SELECT * FROM Photos WHERE fileid = ?", (id,))
    data = await cursor.fetchone()
    return data[1]

def run():
    app.run(host="0.0.0.0")