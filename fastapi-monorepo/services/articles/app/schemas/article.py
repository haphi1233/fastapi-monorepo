from pydantic import BaseModel

class ArticleBase(BaseModel):
    article_title: str
    article_content: str
    is_evaluation: bool
    evaluation_score: float

