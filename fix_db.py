import aiosqlite, asyncio, json

async def fix_db():
    db = await aiosqlite.connect("tickets.db")
    cursor = await db.cursor()

    all_tickets = await cursor.execute("SELECT * FROM Tickets")
    all_tickets = await all_tickets.fetchall()

    for ticket in all_tickets:
        msgs = []
        for message in json.loads(ticket[5]):
            if not message[0]:
                msgs.append(message)
                continue
            if message[0].startswith("file_"):
                
                message[0] = message[0].replace("file_", "file:")
                message[0] = message[0].replace("_JPEG", ":JPEG")

            msgs.append(message)
        
        await cursor.execute("UPDATE Tickets SET chat_history = ? WHERE id = ?", (json.dumps(msgs), ticket[0]))

    await db.commit()

asyncio.run(fix_db())   