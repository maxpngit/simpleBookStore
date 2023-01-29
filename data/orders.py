import sqlalchemy
from sqlalchemy import orm
from flask_login import LoginManager, UserMixin, login_required
from sqlalchemy_serializer import SerializerMixin
from .db_session import SqlAlchemyBase


class Order(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'orders'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    user = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    books = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)
    date = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    orders = orm.relation("Order", secondary="association", backref="users")

    def __repr__(self):
        return "{}:{}:{}".format(self.id, self.user, self.books)

    def get_user(self):
        return self.user
