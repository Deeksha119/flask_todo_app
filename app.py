from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, UserMixin, current_user
from flask_bcrypt import Bcrypt
import os
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "yoursecretkey"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# -------------------- MODELS --------------------

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)
    tasks = db.relationship("Task", backref="user", lazy=True)


class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.String(300), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    category = db.Column(db.String(50), default="General")
    position = db.Column(db.Integer, default=0)
    due_date = db.Column(db.DateTime, nullable=True)  # new due date column
    reminder_sent = db.Column(db.Boolean, default=False)  # tracks reminders
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# -------------------- ROUTES --------------------

@app.route("/")
@login_required
def index():
    tasks = Task.query.filter_by(user_id=current_user.id).all()
    return render_template("index.html", tasks=tasks)

@app.route("/add", methods=["POST"])
@login_required
def add():
    text = request.form.get("task")
    category = request.form.get("category", "General")
    due_date_str = request.form.get("due_date")

    if due_date_str:
        due_date = datetime.strptime(due_date_str, "%Y-%m-%d")
    else:
        due_date = None

    new_task = Task(text=text, user_id=current_user.id,
                    category=category, due_date=due_date)
    db.session.add(new_task)
    db.session.commit()
    flash("Task added!")
    return redirect("/")


@app.route("/edit/<int:id>", methods=["POST"])
@login_required
def edit(id):
    task = Task.query.get_or_404(id)
    new_text = request.form.get("new_text")
    if task.user_id == current_user.id:
        task.text = new_text
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/toggle/<int:id>")
@login_required
def toggle(id):
    task = Task.query.get_or_404(id)
    if task.user_id == current_user.id:
        task.completed = not task.completed
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/delete/<int:id>")
@login_required
def delete(id):
    task = Task.query.get_or_404(id)
    if task.user_id == current_user.id:
        db.session.delete(task)
        db.session.commit()
    return redirect(url_for("index"))

@app.route("/reorder", methods=["POST"])
@login_required
def reorder():
    data = request.get_json()
    old = data["old_index"]
    new = data["new_index"]

    tasks = Task.query.filter_by(user_id=current_user.id).order_by(Task.position).all()

    moved_task = tasks.pop(old)
    tasks.insert(new, moved_task)

    for index, task in enumerate(tasks):
        task.position = index
    db.session.commit()

    return {"success": True}


# -------------------- AUTH --------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        
        if user and bcrypt.check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))
        else:
            flash("Invalid username or password.")
    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")

        if User.query.filter_by(username=username).first():
            flash("Username already exists!")
            return redirect(url_for("register"))

        new_user = User(username=username, password=password)
        db.session.add(new_user)
        db.session.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# -------------------- INIT --------------------

if __name__ == "__main__":
    if not os.path.exists("database.db"):
        with app.app_context():
            db.create_all()

    app.run(debug=True)
