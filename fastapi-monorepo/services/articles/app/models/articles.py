from libs.db.base import Base
from sqlalchemy import Column, Integer, String, Boolean, Float

class Article(Base):
    __tablename__= "articles"
    id = Column(Integer, primary_key=True, index=True)
    article_title = Column(String, index=True)
    article_content = Column(String)
    is_evaluation = Column(Boolean, default=False)
    evaluation_score = Column(Float, default=None)