from sqlalchemy import Table, Column, Integer, String
from sqlalchemy import orm
from flask_login import LoginManager, UserMixin, login_required
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Genre(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'genres'
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=True)

    # genres = orm.relation("Genre", secondary="association", backref="books")

    def __repr__(self):
        return '<Genre %r>' % (self.name)
