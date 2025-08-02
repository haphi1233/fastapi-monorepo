from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os
import dotenv

dotenv.load_dotenv()

DATABASE_URL = f"postgresql+psycopg2://{os.getenv('DATABASE_USER')}:{os.getenv('DATABASE_PASSWORD')}@{os.getenv('DATABASE_HOST')}:{os.getenv('DATABASE_PORT')}/{os.getenv('DATABASE_NAME')}"

engine = create_engine(DATABASE_URL, echo=True)
Sessionlocal = sessionmaker(bind=engine,autocommit=False,autoflush=False)
Base = declarative_base()

def get_db():
    db = Sessionlocal()
    try:
        yield db
    finally:
        db.close()