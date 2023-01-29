import datetime
import sqlalchemy
from sqlalchemy import orm
from flask_login import LoginManager, UserMixin, login_required
from .db_session import SqlAlchemyBase
from sqlalchemy_serializer import SerializerMixin
from werkzeug.security import generate_password_hash, check_password_hash

# роль пользователей
ACCESS = {
    'user': 1,
    'admin': 2
}


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    about = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    email = sqlalchemy.Column(sqlalchemy.String, index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    level = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    created_date = sqlalchemy.Column(sqlalchemy.DateTime, default=datetime.datetime.now)

    users = orm.relation("User", secondary="association", backref="orders")

    def __repr__(self):
        return "<{}:{}>".format(self.id, self.name)

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    # является ли текущий пользователь админом
    def is_admin(self):
        return self.level == ACCESS['admin']

    # разрешён ли доступ пользователю с текущим уровнем
    def allowed(self, access_level):
        return self.level >= access_level

    def get_id(self):
        return self.id

    def __unicode__(self):
        return self.name
