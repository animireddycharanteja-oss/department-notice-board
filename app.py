
import sqlite3
import uuid
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session,send_from_directory
from werkzeug.utils import secure_filename
import os
from datetime import timedelta,datetime
from werkzeug.security import check_password_hash, generate_password_hash
app = Flask(__name__)
# Image upload settings
UPLOAD_FOLDER = "uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

def allowed_file(filename):
    return (
        "." in filename and
        filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS
    )
load_dotenv()
app.secret_key = os.environ.get("SECRET_KEY")
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(minutes=10)

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

def get_db_connection():
    connection = sqlite3.connect("notice_board.db")
    connection.row_factory = sqlite3.Row
    return connection




@app.route("/")
def home():

    connection = get_db_connection()

    notices = connection.execute(
        """
        SELECT Notices.*, Faculty.name AS faculty_name
        FROM Notices
        LEFT JOIN Faculty
        ON Notices.faculty_id = Faculty.faculty_id
        ORDER BY Notices.created_at DESC
        """
    ).fetchall()

    current_faculty_id = None

    if "faculty" in session:

        faculty = connection.execute(
            "SELECT faculty_id FROM Faculty WHERE username = ?",
            (session["faculty"],)
        ).fetchone()

        if faculty:
            current_faculty_id = faculty["faculty_id"]

    connection.close()

    return render_template(
        "index.html",
        notices=notices,
        current_faculty_id=current_faculty_id
    )




@app.route("/admin/dashboard")
def admin_dashboard():

    if "admin" not in session:
        return redirect(url_for("login"))

    return render_template("admin_dashboard.html")

@app.route("/admin/change-credentials", methods=["GET", "POST"])
def change_admin_credentials():

    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        current_password = request.form.get("current_password")
        new_username = request.form.get("new_username", "").strip()
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        connection = get_db_connection()

        admin = connection.execute(
            "SELECT * FROM Admins WHERE username = ?",
            (session["admin"],)
        ).fetchone()

        if not admin or not check_password_hash(
            admin["password_hash"], current_password
        ):
            connection.close()
            return "Incorrect current password!"

        if not new_username or not new_password:
            connection.close()
            return "Username and password cannot be empty!"

        if new_password != confirm_password:
            connection.close()
            return "New passwords do not match!"

        if len(new_password) < 8:
            connection.close()
            return "Password must contain at least 8 characters!"

        existing_admin = connection.execute(
            "SELECT * FROM Admins WHERE username = ? AND admin_id != ?",
            (new_username, admin["admin_id"])
        ).fetchone()

        if existing_admin:
            connection.close()
            return "This username is already taken!"

        new_password_hash = generate_password_hash(new_password)

        connection.execute(
            """UPDATE Admins
               SET username = ?, password_hash = ?
               WHERE admin_id = ?""",
            (new_username, new_password_hash, admin["admin_id"])
        )

        connection.commit()
        connection.close()

        session["admin"] = new_username

        return redirect(url_for("admin_dashboard"))

    return render_template("change_admin_credentials.html")


@app.route("/admin/manage-notices")
def admin_manage_notices():

    if "admin" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    notices = connection.execute(
    """SELECT Notices.*,
              Faculty.name AS faculty_name
       FROM Notices
       LEFT JOIN Faculty
       ON Notices.faculty_id = Faculty.faculty_id
       ORDER BY Notices.created_at DESC"""
    ).fetchall()

    connection.close()

    return render_template(
        "admin_manage_notices.html",
        notices=notices
    )


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()

        admin = connection.execute(
            "SELECT * FROM Admins WHERE username = ?",
            (username,)
        ).fetchone()

        connection.close()

        if admin and check_password_hash(admin["password_hash"], password):
            session.permanent = True
            session["admin"] = admin["username"]
            return redirect(url_for("admin_dashboard"))

        return "Invalid username or password"

    return render_template("login.html")




@app.route("/admin/add", methods=["GET", "POST"])
def add_notice():

    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()

        image_file = next(
            (f for f in request.files.getlist("image")
             if f and f.filename),
            None
        )

        # Check posting details
        if bool(title) != bool(description):
            return "Please enter both title and description."

        if not title and not image_file:
            return "Please enter a notice or select an image."

        image_name = None

        if image_file:

            if not allowed_file(image_file.filename):
                return "Invalid image format!"

            image_name = str(uuid.uuid4()) + "_" + secure_filename(
                image_file.filename
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_name
            )

            image_file.save(image_path)

        connection = get_db_connection()

        connection.execute(
            """INSERT INTO Notices
               (title, description, category, image)
               VALUES (?, ?, ?, ?)""",
            (title, description, category, image_name)
        )

        connection.commit()
        connection.close()

        return redirect(url_for("home"))

    return render_template("add_notice.html")




@app.route("/admin/faculty/add", methods=["GET", "POST"])
def add_faculty():

    if "admin" not in session:
        return redirect(url_for("login"))

    if request.method == "POST":

        name = request.form["name"]
        username = request.form["username"]
        password = request.form["password"]

        password_hash = generate_password_hash(password)

        connection = get_db_connection()

        try:
            connection.execute(
                "INSERT INTO Faculty (name, username, password_hash) VALUES (?, ?, ?)",
                (name, username, password_hash)
            )

            connection.commit()

            message = "Faculty account created successfully!"

        except sqlite3.IntegrityError:
            message = "This username already exists!"

        finally:
            connection.close()

        return render_template("add_faculty.html", message=message)

    return render_template("add_faculty.html")


@app.route("/faculty/login", methods=["GET", "POST"])
def faculty_login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        connection = get_db_connection()

        faculty = connection.execute(
            "SELECT * FROM Faculty WHERE username = ?",
            (username,)
        ).fetchone()

        connection.close()

        if faculty and check_password_hash(faculty["password_hash"], password):

            session.permanent = True
            session["faculty"] = faculty["username"]
            

            return redirect(url_for("faculty_dashboard"))

        return "Invalid username or password"

    return render_template("faculty_login.html")


@app.route("/faculty/dashboard")
def faculty_dashboard():

    if "faculty" not in session:
        return redirect(url_for("faculty_login"))

    return render_template("faculty_dashboard.html")

@app.route("/faculty/my-notices")
def faculty_my_notices():

    if "faculty" not in session:
        return redirect(url_for("faculty_login"))

    connection = get_db_connection()

    faculty = connection.execute(
        "SELECT faculty_id FROM Faculty WHERE username = ?",
        (session["faculty"],)
    ).fetchone()

    notices = connection.execute(
        "SELECT * FROM Notices WHERE faculty_id = ? ORDER BY created_at DESC",
        (faculty["faculty_id"],)
    ).fetchall()

    connection.close()

    return render_template(
        "faculty_my_notices.html",
        notices=notices
    )




@app.route("/faculty/add", methods=["GET", "POST"])
def faculty_add_notice():

    if "faculty" not in session:
        return redirect(url_for("faculty_login"))

    if request.method == "POST":

        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        category = request.form.get("category", "").strip()

        image_file = next(
            (f for f in request.files.getlist("image")
             if f and f.filename),
            None
        )

        # Check posting details
        if bool(title) != bool(description):
            return "Please enter both title and description."

        if not title and not image_file:
            return "Please enter a notice or select an image."

        image_name = None

        if image_file:

            if not allowed_file(image_file.filename):
                return "Invalid image format!"

            image_name = str(uuid.uuid4()) + "_" + secure_filename(
                image_file.filename
            )

            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                image_name
            )

            image_file.save(image_path)

        connection = get_db_connection()

        faculty = connection.execute(
            "SELECT faculty_id FROM Faculty WHERE username = ?",
            (session["faculty"],)
        ).fetchone()

        if not faculty:
            connection.close()
            session.pop("faculty", None)
            return redirect(url_for("faculty_login"))

        connection.execute(
            """INSERT INTO Notices
               (title, description, category, faculty_id, image)
               VALUES (?, ?, ?, ?, ?)""",
            (
                title,
                description,
                category,
                faculty["faculty_id"],
                image_name
            )
        )

        connection.commit()
        connection.close()

        return redirect(url_for("home"))

    return render_template("faculty_add_notice.html")





@app.route("/admin/delete/<int:notice_id>", methods=["POST"])
def delete_notice(notice_id):

    if "admin" not in session:
        return redirect(url_for("login"))

    connection = get_db_connection()

    notice = connection.execute(
        "SELECT image FROM Notices WHERE notice_id = ?",
        (notice_id,)
    ).fetchone()

    if notice:
        connection.execute(
            "DELETE FROM Notices WHERE notice_id = ?",
            (notice_id,)
        )

        connection.commit()

        if notice["image"]:
            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                notice["image"]
            )

            if os.path.isfile(image_path):
                os.remove(image_path)

    connection.close()

    return redirect(url_for("home"))


@app.route("/faculty/delete/<int:notice_id>", methods=["POST"])
def faculty_delete_notice(notice_id):

    if "faculty" not in session:
        return redirect(url_for("faculty_login"))

    connection = get_db_connection()

    notice = connection.execute(
        """SELECT image FROM Notices
           WHERE notice_id = ?
           AND faculty_id = (
               SELECT faculty_id FROM Faculty
               WHERE username = ?
           )""",
        (notice_id, session["faculty"])
    ).fetchone()

    if notice:
        connection.execute(
            """DELETE FROM Notices
               WHERE notice_id = ?
               AND faculty_id = (
                   SELECT faculty_id FROM Faculty
                   WHERE username = ?
               )""",
            (notice_id, session["faculty"])
        )

        connection.commit()

        if notice["image"]:
            image_path = os.path.join(
                app.config["UPLOAD_FOLDER"],
                notice["image"]
            )

            if os.path.isfile(image_path):
                os.remove(image_path)

    connection.close()

    return redirect(url_for("home"))



@app.route("/logout")
def logout():
    session.pop("admin", None)
    session.pop("faculty", None)

    return redirect(url_for("home"))


if __name__ == "__main__":
    app.run(debug=True)
