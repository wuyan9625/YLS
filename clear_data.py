import sqlite3

DB_PATH = "checkin.db"

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("DELETE FROM checkins;")
cursor.execute("DELETE FROM location_logs;")
cursor.execute("DELETE FROM users;")
cursor.execute("DELETE FROM user_states;")
conn.commit()
conn.close()

print("⚠️ 已清空所有資料（打卡、定位、綁定）")
