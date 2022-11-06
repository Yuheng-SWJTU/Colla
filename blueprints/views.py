from flask import Blueprint, render_template, request, flash, redirect, url_for, session, g, jsonify
from models import EmailCaptchaModel, UserModel, CategoryModel, TodoModel
from .forms import RegisterForm, LoginForm, AddCategoryForm, AddTodoForm
from werkzeug.security import generate_password_hash, check_password_hash
from extensions import mail, db
from flask_mail import Message
import string
import random
from datetime import datetime
from decoration import login_required, check_category
from controller import todos_list, progress_bar, get_all_todos

bp = Blueprint("views", __name__, url_prefix="/")


@bp.route("/", methods=['GET', 'POST'])
@login_required
@check_category
def index():
    user_id = session.get("user_id")
    # Get the user information
    user = UserModel.query.get(user_id)
    # Get all categories in a user
    categories = CategoryModel.query.filter_by(user_id=user_id).all()

    filters_name = session.get("filter")
    sort = session.get("sort")

    todos = get_all_todos(TodoModel, user_id, filters_name, sort)

    # Using user id and category id to get the category name
    for todo in todos:
        category = CategoryModel.query.get(todo.category_id)
        todo.category_name = category.name
        todo.category_color = category.color

    # function: get the todos list
    todos_total_list = todos_list(todos)
    print(todos_total_list)

    # function: fully fulfill the progress bar
    todo_sum, todo_completed, todo_rate = progress_bar(todos)

    return render_template("index.html", user=user, categories=categories, todos=todos, todos_list=todos_total_list,
                           todo_sum=todo_sum, completed_sum=todo_completed, todo_rate=todo_rate)


@bp.route("/filter", methods=["POST"])
@login_required
def filters():
    if request.method == "POST":
        filters_name = request.form.get("filters")
        # print("filters_name:", filters_name)
        session["filter"] = filters_name
        return redirect(url_for("views.index"))


@bp.route("/sort", methods=["POST"])
@login_required
def sort():
    if request.method == "POST":
        sort_name = request.form.get("sort")
        # print("filters_name:", filters_name)
        session["sort"] = sort_name
        return redirect(url_for("views.index"))


@bp.route("/add_category", methods=['POST'])
@login_required
def add_category():
    # Add a new category
    if request.method == 'POST':
        user_id = session.get("user_id")
        # Using the form to validate the data
        form1 = AddCategoryForm(request.form)
        if form1.validate():
            name = form1.module_name.data
            color = form1.module_color.data
            category = CategoryModel(name=name, user_id=user_id, color=color, create_time=datetime.now())
            db.session.add(category)
            db.session.commit()
            flash("Success: Add a new category successfully!")
            return redirect(url_for('views.index'))
        else:
            error = form1.errors
            flash("Failed: " + error['module_name'][0])
            return redirect(url_for('views.index'))


@bp.route("/delete_category", methods=['POST'])
@login_required
def delete_category():
    category_id = request.form.get("category_id")
    category = CategoryModel.query.get(category_id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'code': 200, 'message': 'Success'})


@bp.route("/edit_category", methods=['POST'])
@login_required
def edit_category():
    form = AddCategoryForm(request.form)
    if form.validate():
        name = form.module_name.data
        color = form.module_color.data
        category_id = request.form.get("category_id")
        category = CategoryModel.query.get(category_id)
        category.name = name
        category.color = color
        db.session.commit()
        flash("Success: Edit successfully!")
        return redirect(url_for('views.index'))
    else:
        error = form.errors
        flash("Failed: " + error['module_name'][0])
        return redirect(url_for('views.index'))


@bp.route("/add_todo", methods=['POST'])
@login_required
def add_todo():
    form = AddTodoForm(request.form)
    if form.validate():
        user_id = session.get("user_id")
        module_code = form.module_code.data
        module_name = form.module_name_input.data
        assessment_title = form.assessment_title.data
        description = form.description.data
        category_id = request.form.get("category")
        due_date = request.form.get("due_date")
        important = request.form.get("important")
        mail_notifier = request.form.get("mail_notifier")
        if mail_notifier == 'mail_notifier':
            mail_notifier = 1
        else:
            mail_notifier = 0
        if important == 'important':
            important = 1
        else:
            important = 0
        # convert the date format from '2022-11-03T00:00' to '2022-11-03 00:00:00'
        due_date = datetime.strptime(due_date, '%Y-%m-%dT%H:%M')
        todo = TodoModel(module_code=module_code, module_name=module_name, assessment_name=assessment_title,
                         description=description, category_id=category_id, due_date=due_date, important=important,
                         email_inform=mail_notifier, user_id=user_id, create_time=datetime.now(), status=0, trash=0,
                         status_email=0, status_notification=0)
        db.session.add(todo)
        db.session.commit()
        flash("Success: Add a new todo successfully!")
        return redirect(url_for('views.index'))
    else:
        # flash("Failed: " + error['module_code'][0])
        flash("Failed: " + "You have to fill in the blanks except 'description' !")
        return redirect(url_for('views.index'))


@bp.route("/completed", methods=['POST', 'GET'])
@login_required
def completed():
    todo_id = request.form.get("id")
    todo = TodoModel.query.get(todo_id)
    if todo.status == 0:
        todo.status = 1
    else:
        todo.status = 0
    db.session.commit()
    # code:200说明是一个成功的正常的请求
    return jsonify({"code": 200})


@bp.route("/trash_todo", methods=['POST'])
@login_required
def trash_todo():
    todo_id = request.form.get("id")
    todo = TodoModel.query.get(todo_id)
    if todo.trash == 0:
        todo.trash = 1
    else:
        todo.trash = 0
    db.session.commit()
    return jsonify({"code": 200})


@bp.route("/edit_todo", methods=['POST'])
@login_required
def edit_todo():
    form = AddTodoForm(request.form)
    if form.validate():
        todo_id = request.form.get("todo_id")
        todo = TodoModel.query.get(todo_id)
        todo.module_code = form.module_code.data
        todo.module_name = form.module_name_input.data
        todo.assessment_name = form.assessment_title.data
        todo.description = form.description.data
        todo.category_id = request.form.get("category")
        todo.due_date = request.form.get("due_date")
        todo.important = request.form.get("important")
        todo.email_inform = request.form.get("mail_notifier")
        if todo.email_inform == 'mail_notifier':
            todo.email_inform = 1
        else:
            todo.email_inform = 0
        if todo.important == 'important':
            todo.important = 1
        else:
            todo.important = 0
        # convert the date format from '2022-11-03T00:00' to '2022-11-03 00:00:00'
        todo.due_date = datetime.strptime(todo.due_date, '%Y-%m-%dT%H:%M')
        db.session.commit()
        flash("Success: Edit successfully!")
        return redirect(url_for('views.index'))
    else:
        flash("Failed: " + "You have to fill in the blanks except 'description' !")
        return redirect(url_for('views.index'))


@bp.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'GET':
        return render_template("register.html")
    else:
        form = RegisterForm(request.form)
        if form.validate():
            email = form.email.data
            username = form.username.data
            password = form.password.data

            # encrypt
            hash_password = generate_password_hash(password)
            user = UserModel(email=email, username=username, password=hash_password)
            db.session.add(user)
            db.session.commit()
            return redirect(url_for("views.login"))
        else:
            flash("Failed: The information you entered is not valid!")
            return redirect(url_for("views.register"))


@bp.route("/captcha", methods=['POST'])
def get_captcha():
    # GET请求
    email = request.form.get("email")
    name = request.form.get("username")
    if name == "":
        name = "user"
    # 生成一个验证码
    letters = string.digits
    captcha = "".join(random.sample(letters, 4))
    if email:
        message = Message(
            subject="[Colla] - your register code",
            recipients=[email],
            body=f"Hi, {name} ! \n\n"
                 f"You can enter this code to register into Colla: \n\n"
                 f"{captcha} \n\n"
                 f"If you weren't trying to register in, let me know."
        )
        mail.send(message)
        captcha_model = EmailCaptchaModel.query.filter_by(email=email).first()
        if captcha_model:
            captcha_model.captcha = captcha
            captcha_model.creat_time = datetime.now()
            db.session.commit()
        else:
            captcha_model = EmailCaptchaModel(email=email, captcha=captcha)
            db.session.add(captcha_model)
            db.session.commit()
        # code:200说明是一个成功的正常的请求
        return jsonify({"code": 200})
    else:
        # code:400 客户端错误
        return jsonify({"code": 400, "message": "Please deliver your e-mail first! "})


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    else:
        form = LoginForm(request.form)
        if form.validate():
            email = form.email.data
            password = form.password.data
            user = UserModel.query.filter_by(email=email).first()
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['filter'] = "all"
                session['sort'] = "due_date"
                rememverme = request.form.getlist("remember")
                if "rememberme" in rememverme:
                    session['remember'] = "true"
                else:
                    session['remember'] = "false"
                return redirect("/")
            else:
                flash("Password or email is wrong! ")
                return redirect(url_for("views.login"))
        else:
            flash("The format of email or password is wrong! ")
            return redirect(url_for("views.login"))


@bp.route("/logout", methods=['GET'])
def logout():
    # 清楚session当中所有的数据
    session.clear()
    return redirect(url_for('views.login'))
