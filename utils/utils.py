import re
import sqlite3

database = sqlite3.connect("db/radio.db")
db = database.cursor()

async def checkradio(interaction, radio):
    data = db.execute("SELECT * FROM radios WHERE radio = ?", (radio,)).fetchall()
    if radio not in [i[1] for i in data if i[0] == interaction.user.id or i[2] != 1]:
        return False
    else:
        return True