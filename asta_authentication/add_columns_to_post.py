import sqlite3

conn = sqlite3.connect('C:/Users/dell/Desktop/astra_full/astra_monorepo/asta_authentication/instance/users.db')
cursor = conn.cursor()

try:
    cursor.execute("ALTER TABLE post ADD COLUMN image_url VARCHAR(200)")
except sqlite3.OperationalError as e:
    print(e)

try:
    cursor.execute("ALTER TABLE post ADD COLUMN link_url VARCHAR(200)")
except sqlite3.OperationalError as e:
    print(e)

conn.commit()
conn.close()