from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    balance = Column(Float, default=0.0)
    api_key = Column(String, unique=True, index=True)

class Record(Base):
    __tablename__ = 'records'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action = Column(String)  # 充值/识别等
    amount = Column(Float)
    user = relationship('User') 