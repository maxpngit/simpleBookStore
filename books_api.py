import os

import flask
from data import db_session
from data.books import Book
from data.genre import Genre
from data.users import User
from data.orders import Order
from flask import jsonify
from flask_paginate import Pagination
from flask import render_template, request, redirect
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

# разрешённые расширения
EXTS = ['png', 'jpg', 'jpeg', 'gif']
# директории для хранения
UPLOAD_COVER = 'static/covers/'  # для обложек
UPLOAD_PDF = 'static/pdf/'  # для PDF-файлов книг
PERPAGE = 10  # позиций на страницу при пагинации (pagination)


# проверка типа файла на допустимые ('png', 'jpg', 'jpeg', 'gif')
def allowed_cover_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in EXTS


# проверка на расширение PDF
def allowed_pdf_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'pdf'


# расширяющий эскиз для панели администрирования
blueprint = flask.Blueprint('books_api', __name__, template_folder='templates')


# главная страница администрирования
@blueprint.route('/api/admin', methods=['GET', 'POST'])
@login_required
def admin_page():
    if current_user.is_admin():
        g_json = jsonify({'status': 'index', 'action': ['genres', 'books', 'users']})
        return render_template('/admin/index.html', data='Выбор действия', g_json=g_json.json)
    else:
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', data='Недостаточный уровень прав доступа', g_json=g_json.json)


# пользователи (только просмотр и удаление)
@blueprint.route('/api/admin/users')
@login_required
def get_users():
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    users = db_sess.query(User.id, User.name, User.level, User.created_date).order_by(User.name).all()
    if not users:
        g_json = jsonify({'status': 'error', 'errormsg': 'Перечень пользователей пуст!'})
    else:
        rec = {}
        for item in users:
            rec[item.id] = [item.name, item.level, item.created_date.strftime('%d.%m.%Y в %H:%M')]
        g_json = jsonify({'status': 'users', 'record': rec})
    return render_template('/admin/index.html', data='Перечень пользователей', g_json=g_json.json)


# удаление пользователя
@blueprint.route('/api/admin/users/del/<int:user_id>', methods=['GET'])
@login_required
def delete_user(user_id):
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', crumb=['users', 'Пользователи'],
                               data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    role = db_sess.query(User).get(user_id)
    if not role:
        g_json = jsonify({'status': 'error', 'errormsg': f'Записи c номером {user_id} не существует!'})
    else:
        # если предпринята попытка удалить админа по прямой ссылке
        if role.level == 2:
            g_json = jsonify(
                {'status': 'error',
                 'errormsg': 'Удаление администратора невозможно!'}
            )
        else:
            db_sess.delete(role)
            records = db_sess.query(Order).filter(Order.user == user_id).all()
            if records:
                for rec in records:
                    db_sess.delete(rec)
            db_sess.commit()
            return redirect('/api/admin/users')
    return render_template('/admin/index.html', crumb=['users', 'Пользователи'],
                           data=f'Запись {user_id} не была удалена',
                           g_json=g_json.json)


# таблица жанров книг
@blueprint.route('/api/admin/genres')
@login_required
def get_genres():
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    genres = db_sess.query(Genre).all()
    if not genres:
        g_json = jsonify({'status': 'error', 'errormsg': 'Перечень жанров пуст!'})
    else:
        rec = {}
        for item in genres:
            rec[item.id] = item.name
        g_json = jsonify({'status': 'genres', 'record': rec})
    return render_template('/admin/index.html', data='Перечень жанров книг', g_json=g_json.json)


# таблица книг
@blueprint.route('/api/admin/books')
@blueprint.route('/api/admin/books/index')
@blueprint.route('/api/admin/books/index/<int:page>')
@login_required
def get_books(page=1):
    offset = PERPAGE * (page - 1)
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    books = db_sess.query(Book).all()
    if not books:
        total = 0
        g_json = jsonify({'status': 'error', 'errormsg': 'Перечень книг пуст!'})
    else:
        rec = {}
        total = len(books)
        for item in books[offset: offset + PERPAGE]:
            rec[item.id] = [item.author, item.title]
        g_json = jsonify({'status': 'books', 'record': rec})
    pagination = Pagination(page=page, per_page=PERPAGE, total=total, items=books[offset: offset + PERPAGE],
                            css_framework='bootstrap4')
    return render_template('/admin/index.html', data='Перечень книг', page=page,
                           per_page=PERPAGE, pagination=pagination, g_json=g_json.json)


# создание нового жанра книг
@blueprint.route('/api/admin/genres/create', methods=['GET', 'POST'])
@login_required
def create_genre():
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', crumb=['genres', 'Жанры'],
                               data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    query = db_sess.query(Genre).filter(Genre.id > 0).all()
    if not query:
        new_id = 1
    else:
        id_list = [item.id for item in query]
        new_id = max(id_list) + 1
    g_json = jsonify({'status': 'create', 'genre': new_id})
    if request.method == "POST":
        id = request.form.get('id')
        name = request.form.get('name')
        if not name:
            g_json = jsonify({'status': 'error', 'errormsg': 'Пустое значение для нового жанра!'})
        else:
            item = Genre(id=id, name=name)
            try:
                db_sess.add(item)
                db_sess.commit()
                return redirect('/api/admin/genres')
            except:
                g_json = jsonify({'status': 'error', 'errormsg': 'Запись не добавлена!'})
    return render_template('/admin/index.html', crumb=['genres', 'Жанры'], data=f'Добавление нового жанра #{new_id}',
                           g_json=g_json.json)


# удаление жанра книг
@blueprint.route('/api/admin/genres/del/<int:genre_id>', methods=['GET'])
@login_required
def delete_genre(genre_id):
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', crumb=['genres', 'Жанры'],
                               data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    genre = db_sess.query(Genre).get(genre_id)
    book = db_sess.query(Book.title).filter(Book.genre == genre_id).all()
    if not genre:
        g_json = jsonify({'status': 'error', 'errormsg': f'Записи c номером {genre} не существует!'})
    else:
        if book:
            fbook = book[0].title
            g_json = jsonify(
                {'status': 'error',
                 'errormsg': f'Категория "{genre.name}" уже привязана к книгам: "{fbook}" и др. Удаление невозможно!'}
            )
        else:
            db_sess.delete(genre)
            db_sess.commit()
            return redirect('/api/admin/genres')
    return render_template('/admin/index.html', crumb=['genres', 'Жанры'], data=f'Запись {genre_id} не была удалена',
                           g_json=g_json.json)


# редактирование жанра книг
@blueprint.route('/api/admin/genres/edit/<int:genre_id>', methods=['GET', 'POST'])
@login_required
def edit_genre(genre_id):
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', crumb=['genres', 'Жанры'],
                               data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    genre = db_sess.query(Genre).get(genre_id)
    if not genre:
        g_json = jsonify({'status': 'error', 'errormsg': 'Запись не найдена!'})
    else:
        if request.method == "POST":
            id = request.form.get('id')
            name = request.form.get('name')
            db_sess.query(Genre).filter(Genre.id == id).update({Genre.name: name}, synchronize_session=False)
            db_sess.commit()
            return redirect('/api/admin/genres')
        g_json = jsonify({'status': 'edit', 'genre': {'id': [genre.id, 'hidden'], 'name': [genre.name, 'text']}})
        return render_template('/admin/index.html', crumb=['genres', 'Жанры'],
                               data=f'Запись #{genre.id} для редактирования',
                               g_json=g_json.json)


# удаление книги, а также сопутствующих файлов обложки и PDF
@blueprint.route('/api/admin/books/del/<int:book_id>', methods=['GET'])
@login_required
def del_book(book_id):
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', crumb=['books', 'Книги'],
                               data='Недостаточный уровень прав доступа', g_json=g_json.json)
    db_sess = db_session.create_session()
    book = db_sess.query(Book).get(book_id)
    if not book:
        g_json = jsonify({'status': 'error', 'errormsg': f'Записи c номером {book_id} не существует!'})
    else:
        # если файлы обложки (и PDF) существуют, удалить и их
        if os.path.exists(os.path.join(UPLOAD_COVER, book.cover)):
            os.remove(os.path.join(UPLOAD_COVER, book.cover))
        if os.path.exists(os.path.join(UPLOAD_PDF, book.pdf)):
            os.remove(os.path.join(UPLOAD_PDF, book.pdf))
        db_sess.delete(book)
        db_sess.commit()
        return redirect('/api/admin/books')
    return render_template('/admin/index.html', crumb=['books', 'Книги'], data=f'Запись {book_id} не была удалена',
                           g_json=g_json.json)


# создание записи новой книги (с учётом жанра и с загрузкой файлов)
# а также обновление записи существующей (с загрузкой файлов или без неё)
@blueprint.route('/api/admin/books/create', methods=['GET', 'POST'])
@blueprint.route('/api/admin/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
def create(book_id=-1):
    if not current_user.is_admin():
        g_json = jsonify({'status': 'error', 'errormsg': f'{current_user.name}, Вы не являетесь админом!'})
        return render_template('/admin/index.html', crumb=['books', 'Книги'], data='Недостаточный уровень прав доступа',
                               g_json=g_json.json)
    # если режим редактирования и метод GET
    if book_id != -1 and request.method == "GET":
        fields = {}
        db_sess = db_session.create_session()
        query = db_sess.query(Book).get(book_id)
        genres_list = db_sess.query(Genre.name).all()
        fields['title'] = query.title
        fields['author'] = query.author
        fields['genre'] = db_sess.query(Genre).get(query.genre).name
        fields['descript'] = query.descript
        fields['cover'] = query.cover
        fields['pdf'] = query.pdf
        genres = ['Всё'] + [item[0] for item in genres_list]
        g_json = jsonify({'status': 'createbook', 'book_id': query.id, 'message': {},
                          'fields': fields, 'genres': genres})
        return render_template('/admin/index.html', crumb=['books', 'Книги'], data='Редактирование книги',
                               edtit=f'Вы редактируете книгу "{query.title}"', g_json=g_json.json)
    # метод GET при добавлении новой книги
    mess = {}
    db_sess = db_session.create_session()
    query = db_sess.query(Book).all()
    genres_list = db_sess.query(Genre.name).all()
    if not query:
        new_id = 1
        g_json = jsonify({'status': 'error', 'errormsg': 'Перечень книг пуст!'})
    else:
        id_list = [item.id for item in query]
        new_id = max(id_list) + 1
        genres = ['Всё'] + [item[0] for item in genres_list]
    g_json = jsonify({'status': 'createbook', 'book_id': new_id, 'message': mess, 'fields': None, 'genres': genres})
    # результат отправки заполненной формы
    if request.method == "POST":
        nofiles = request.form.get('nofiles')
        title = request.form.get('title')
        author = request.form.get('author')
        genre = request.form.get('genre')
        descript = request.form.get('descript')
        cover = request.files.get('cover')
        if not title:
            mess['title'] = 1
        if not author:
            mess['author'] = 1
        if genre == 'Ваш выбор':
            mess['genre'] = 1
        if cover.filename != '' and allowed_cover_file(cover.filename):
            covername = secure_filename(cover.filename)
            cover.save(os.path.join(UPLOAD_COVER, covername))
        else:
            if not nofiles:  # был выставлен флажок (без обновления файлов)
                mess['cover'] = 1
        pdf = request.files.get('pdf')
        if pdf.filename != '' and allowed_pdf_file(pdf.filename):
            pdfname = secure_filename(pdf.filename)
            pdf.save(os.path.join(UPLOAD_PDF, pdfname))
        else:
            if not nofiles:  # был выставлен флажок (без обновления файлов)
                mess['pdf'] = 1
        if len(mess) == 0:  # ошибок в форме не было
            if book_id == -1:  # запись в БД новой книги
                genre_id = db_sess.query(Genre).filter(Genre.name == genre).one().id
                record = Book(id=new_id, title=title, author=author, genre=genre_id, descript=descript, cover=covername,
                              pdf=pdfname, is_private=True)
                try:
                    db_sess.add(record)
                    db_sess.commit()
                    return redirect('/api/admin/books')
                except:
                    g_json = jsonify({'status': 'error', 'errormsg': 'Книга не добавлена!'})
                    return render_template('/admin/index.html', crumb=['books', 'Книги'], data='Ошибка при добавлении',
                                           g_json=g_json.json)
            else:  # update существующей книги
                genre_id = db_sess.query(Genre).filter(Genre.name == genre).one().id
                if nofiles:  # если файлы обложки и PDF не обновляются
                    db_sess.query(Book).filter(Book.id == book_id).update({Book.title: title, Book.author: author,
                                                                           Book.genre: genre_id,
                                                                           Book.descript: descript},
                                                                          synchronize_session=False)
                else:
                    db_sess.query(Book).filter(Book.id == book_id).update({Book.title: title, Book.author: author,
                                                                           Book.genre: genre_id,
                                                                           Book.descript: descript,
                                                                           Book.cover: covername,
                                                                           Book.pdf: pdfname},
                                                                          synchronize_session=False)
                db_sess.commit()
                return redirect('/api/admin/books')
        else:
            if book_id == -1:  # ошибки в форме при добавлении новой книги
                g_json = jsonify(
                    {'status': 'createbook', 'book_id': new_id, 'message': mess, 'fields': request.form,
                     'genres': genres})
                return render_template('/admin/index.html', data='Перечень книг', g_json=g_json.json)
            else:  # ошибки в форме при при редактировани существующей
                g_json = jsonify({'status': 'createbook', 'book_id': book_id, 'message': mess,
                                  'fields': request.form, 'genres': genres})
                return render_template('/admin/index.html', crumb=['books', 'Книги'], data='Редактирование книги',
                                       edtit=f'Вы редактируете книгу "{title}"', g_json=g_json.json)
    else:
        return render_template('/admin/index.html', crumb=['books', 'Книги'], data='Новая книга', g_json=g_json.json)
