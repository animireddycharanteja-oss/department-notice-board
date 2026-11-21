
import sqlite3

connection = sqlite3.connect("notice_board.db")

try:
    columns = [
        row[1] for row in
        connection.execute("PRAGMA table_info(Notices)").fetchall()
    ]

    if "image" not in columns:
        connection.execute(
            "ALTER TABLE Notices ADD COLUMN image TEXT"
        )
        connection.commit()
        print("Image column added successfully!")
    else:
        print("Image column already exists!")

except sqlite3.Error as e:
    print("Database error:", e)

finally:
    connection.close()
