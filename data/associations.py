from sqlalchemy import Table, Column, Integer, String, ForeignKey
from .db_session import SqlAlchemyBase

association_table = Table('association', SqlAlchemyBase.metadata,
                          Column('genres', Integer, ForeignKey('genres.id')),
                          Column('books', Integer, ForeignKey('books.id')),
                          Column('orders', Integer, ForeignKey('orders.id')),
                          Column('users', Integer, ForeignKey('users.id')))
