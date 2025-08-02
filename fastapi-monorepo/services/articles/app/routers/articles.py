from db.session import get_db
from schemas.article import ArticleBase
from models.articles import Article
from fastapi import APIRouter, Depends

router = APIRouter()

@router.post("/articles", response_model=Article)
def create_articles(db= Depends(get_db), data = ArticleBase):
    new_article = Article(
        article_title=data.article_title,
        article_content=data.article_content,
        is_evaluation=data.is_evaluation,
    )
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    return new_article
    