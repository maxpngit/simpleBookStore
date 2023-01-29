import sqlalchemy
from sqlalchemy import orm
from flask_login import LoginManager, UserMixin, login_required
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Book(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'books'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    title = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    author = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    genre = sqlalchemy.Column(sqlalchemy.Integer, sqlalchemy.ForeignKey('genres.id'), nullable=False)
    descript = sqlalchemy.Column(sqlalchemy.Text, nullable=False)
    cover = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    pdf = sqlalchemy.Column(sqlalchemy.String, nullable=False)
    is_private = is_private = sqlalchemy.Column(sqlalchemy.Boolean, default=True)

    genres = orm.relation("Genre", secondary="association", backref="genres")

    def __repr__(self):
        return '<Book %r>' % (self.title)
