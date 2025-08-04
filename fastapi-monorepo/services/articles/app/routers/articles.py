from libs.db.session import get_db
from ..schemas.article import ArticleRequest, ArticleResponse
from ..models.articles import Article
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

router = APIRouter()

@router.post("/articles", response_model=ArticleResponse)
def create_articles(article: ArticleRequest, db: Session = Depends(get_db)):
    new_article = Article(
        article_title=article.article_title,
        article_content=article.article_content,
        is_evaluation=article.is_evaluation,
    )
    db.add(new_article)
    db.commit()
    db.refresh(new_article)
    return new_article
    