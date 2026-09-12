from database import get_db_connection

conn = get_db_connection()

rows = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name
""").fetchall()

for row in rows:
    print(row[0])

conn.close()