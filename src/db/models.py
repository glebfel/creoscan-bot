from sqlalchemy import (
    ARRAY,
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Integer,
    MetaData,
    String,
    Table,
    UniqueConstraint,
)

metadata = MetaData()

user_table = Table(
    'users',
    metadata,
    Column('id', Integer, autoincrement=True, primary_key=True),
    Column('firstname', String),
    Column('lastname', String),
    Column('username', String),
    Column('chat_id', BigInteger),
    Column('user_id', BigInteger),
    Column('role', Integer, nullable=True),
    Column('blocked', Boolean, default=False),
    Column('announce_allowed', Boolean, default=True),
    Column('last_announced', DateTime, nullable=True),
    Column('created_at', DateTime, nullable=True),
    Column('updated_at', DateTime, nullable=True),
    Column('utm_created_at', DateTime, nullable=True),
    Column('utm', ARRAY(String), nullable=True),
    Column('paid_requests_count', BigInteger, default=0),
    UniqueConstraint('user_id', 'username', name='unique_user_id'),
)


class User:
    pass
