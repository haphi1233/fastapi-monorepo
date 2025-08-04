from pydantic import BaseModel

class ArticleRequest(BaseModel):
    article_title: str
    article_content: str
    is_evaluation: bool
    evaluation_score: float


class ArticleResponse(BaseModel):
    article_title: str
    article_content: str
    is_evaluation: bool
    evaluation_score: float
    class Config:
        orm_mode = True
