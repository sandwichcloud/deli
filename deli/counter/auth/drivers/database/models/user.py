import arrow
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy_utils import PasswordType, ArrowType

from deli.counter.auth.drivers.database.database import Base


class UserRole(Base):
    __tablename__ = 'user_roles'

    id = Column(Integer, autoincrement=True, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    role = Column(String, nullable=False)

    created_at = Column(ArrowType(timezone=True), default=arrow.now, nullable=False, index=True)
    updated_at = Column(ArrowType(timezone=True), default=arrow.now, onupdate=arrow.now, nullable=False)


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, autoincrement=True, primary_key=True)
    username = Column(String, nullable=False, unique=True)
    password = Column(PasswordType(schemes=['bcrypt']), nullable=False)
    created_at = Column(ArrowType(timezone=True), default=arrow.now, nullable=False, index=True)
    updated_at = Column(ArrowType(timezone=True), default=arrow.now, onupdate=arrow.now, nullable=False)

    roles = relationship(UserRole)
