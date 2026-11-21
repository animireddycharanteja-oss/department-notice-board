
import sqlite3
from werkzeug.security import generate_password_hash

username = input("Enter admin username: ")
password = input("Enter admin password: ")

password_hash = generate_password_hash(password)

connection = sqlite3.connect("notice_board.db")

try:
    connection.execute(
        "INSERT INTO Admins (username, password_hash) VALUES (?, ?)",
        (username, password_hash)
    )

    connection.commit()
    print("Admin account created successfully!")

except sqlite3.IntegrityError:
    print("This username already exists!")

finally:
    connection.close()
