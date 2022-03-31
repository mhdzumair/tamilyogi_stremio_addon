from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime

from database import Base


class TamilYogiMovie(Base):
    __abstract__ = True

    id: int = Column(Integer, primary_key=True, autoincrement=True)
    name: str = Column(String, unique=True, nullable=False)
    link: str = Column(String, nullable=False)
    poster: str = Column(String, nullable=False)
    imdb_id: str = Column(String, nullable=True)
    tamilyogi_id: str = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now(), nullable=False)


class TamilNewMovie(TamilYogiMovie):
    __tablename__ = 'tamil_new_movie'


class TamilHDMovie(TamilYogiMovie):
    __tablename__ = 'tamil_hd_movie'


class TamilDubbedMovie(TamilYogiMovie):
    __tablename__ = 'tamil_dubbed_movie'
