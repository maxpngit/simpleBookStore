import datetime
import os

from data import db_session
from data.books import Book
from data.genre import Genre
from data.orders import Order
from data.users import User
from flask import Flask, render_template, request, redirect, send_from_directory
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from flask_paginate import Pagination
from forms.loginform import LoginForm
from forms.user import RegisterForm
from books_api import blueprint

UPLOAD_COVER = 'static/covers/'  # для обложек
UPLOAD_PDF = 'static/pdf/'  # для PDF-файлов книг
PERPAGE = 10  # позиций на страницу

DEBUGER = True  # пока откладка, потом False

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'still short secret key'
app.config['UPLOAD_COVER'] = UPLOAD_COVER
app.config['UPLOAD_PDF'] = UPLOAD_PDF
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False


# данные о пользователе
@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


# начнём с error 404 (провалились в колодец)
@app.errorhandler(404)
def http_404_handler(error):
    return redirect('/error404')  # well - колодец


# следующая error 404 (не авторизован, попытка входа по прямой ссылке)
@app.errorhandler(401)
def http_401_handler(error):
    message = ''
    return redirect('/login')  # надо авторизоваться


# декоратор для главной страницы
@app.route('/', methods=['GET', 'POST'])
@app.route('/index', methods=['GET', 'POST'])
@app.route('/index/<int:page>', methods=['GET', 'POST'])
def index(page=1):
    curgenre = ''
    offset = PERPAGE * (page - 1)
    total = 0
    db_sess = db_session.create_session()
    items = db_sess.query(Book).filter(Book.is_private == True)
    genres = db_sess.query(Genre).all()
    try:
        total = items.count()
    except:
        total = 0
    # в случае сортировки по жанрам
    if request.method == "POST":
        curgenre = request.form.get('genre')
        if curgenre == 'Всё':
            genres = db_sess.query(Genre).all()
        else:
            g_id = db_sess.query(Genre).filter(Genre.name == curgenre).one()
            items = db_sess.query(Book).filter(Book.genre == g_id.id)
        try:
            total = items.count()
        except:
            total = 0
        pagination = Pagination(page=page, per_page=PERPAGE, total=total, items=items[offset: offset + PERPAGE],
                                css_framework='bootstrap4')
        return render_template('index.html', data=items[offset: offset + PERPAGE], genres=genres, curgenre=curgenre,
                               page=page, per_page=PERPAGE, pagination=pagination)  # главный файл
    # вывод без сортировки, а также поиск методом GET
    context = request.args.get('context')
    if page > 1 and context:
        return redirect('/?context=' + context)
    if context and context != '':
        context = context.strip()
        items = db_sess.query(Book).filter(
            Book.author.ilike(f'%{context}%') | Book.title.ilike(f'%{context}%') | Book.author.ilike(
                f'%{context.title()}%') | Book.title.ilike(f'%{context.title()}%')).all()
        try:
            total = len(items)
        except:
            total = 0
    pagination = Pagination(page=page, per_page=PERPAGE, total=total, items=items[offset: offset + PERPAGE],
                            css_framework='bootstrap4')
    return render_template('index.html', data=items[offset: offset + PERPAGE], genres=genres, page=page,
                           per_page=PERPAGE, pagination=pagination)  # главный файл


# если провалились в колодец 404
@app.route('/error404')
def well():
    return render_template('well.html')


# декоратор страницы аутентификации пользователя
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect("/")
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.name == form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect('/')
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login.html', title='Авторизация', form=form)


# декоратор для страницы about
@app.route('/about')
def about():
    return render_template('about.html')


# декоратор для страницы скачивания
@app.route('/download/<int:id>')
@login_required
def item_download(id):
    cur_date = datetime.datetime.now().strftime('%d/%m/%Y в %H:%M:%S')
    db_sess = db_session.create_session()
    item = db_sess.query(Book).get(id)
    file_name = item.pdf
    full_path = os.path.join(app.root_path, app.config['UPLOAD_PDF'])
    order = Order(
        user=current_user.get_id(),
        books=item.id,
        date=cur_date
    )
    db_sess.add(order)
    db_sess.commit()
    return send_from_directory(full_path, file_name, as_attachment=True)


# история заказов залогиненного пользователя
@app.route('/history')
@login_required
def history():
    data = []
    db_sess = db_session.create_session()
    items = db_sess.query(Order).filter(Order.user == current_user.get_id()).all()
    try:
        for item in items:
            book = db_sess.query(Book).filter(Book.id == item.books).one()
            data.append((book.author, book.title, item.date))
    except:
        data = 0
    if current_user.is_admin():
        return render_template('history.html', title='История скачиваний', data=data, admin=1)
    else:
        return render_template('history.html', title='История скачиваний', data=data)


# завершение сессии залогиненного пользователя
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


# регистрация нового пользователя
@app.route('/register', methods=['GET', 'POST'])
def reqister():
    if current_user.is_authenticated:
        return redirect('/')
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form, message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


# если файл исполняемый, то:
if __name__ == "__main__":
    db_session.global_init("db/books.db")
    # подключаем API (blueprint) админки
    app.register_blueprint(blueprint)
    # запускаем наш app (клиентская часть)
    app.run(debug=DEBUGER)
