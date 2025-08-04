from libs.db.base import Base
from sqlalchemy import Column, Integer, Text, DateTime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(Text, nullable=False)
    dob = Column(DateTime, nullable=True)