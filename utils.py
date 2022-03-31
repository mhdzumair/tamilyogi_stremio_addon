from sqlalchemy.orm import Session

import models
import schemas
import scrap


def get_movie_table(catalog) -> models.TamilYogiMovie | None:
    movie_table = None
    if catalog == "tamil_hd":
        movie_table = models.TamilHDMovie
    elif catalog == "tamil_new":
        movie_table = models.TamilNewMovie
    elif catalog == "tamil_dubbed":
        movie_table = models.TamilDubbedMovie

    return movie_table


def get_movies_meta(db: Session, catalog: str, skip: int = 0, limit: int = 25):
    movies_meta = []
    movie_table = get_movie_table(catalog)
    if movie_table is None:
        return movies_meta

    for movie in db.query(movie_table).order_by(movie_table.id.desc()).offset(skip).limit(limit).all():
        meta_data = schemas.Meta.from_orm(movie)
        meta_data.id = movie.imdb_id if movie.imdb_id else movie.tamilyogi_id
        movies_meta.append(meta_data)
    return movies_meta


def get_movie_data(db: Session, video_id: str) -> models.TamilYogiMovie | None:
    priority_table = [models.TamilHDMovie, models.TamilNewMovie, models.TamilDubbedMovie]
    for movie_table in priority_table:
        if video_id.startswith("tt"):
            movie_data = db.query(movie_table).filter(movie_table.imdb_id == video_id).order_by(
                movie_table.created_at.desc()
            ).first()
        else:
            movie_data = db.query(movie_table).filter(movie_table.tamilyogi_id == video_id).order_by(
                movie_table.created_at.desc()
            ).first()

        if movie_data:
            return movie_data


def get_movie_streams(db: Session, video_id: str):
    movie_data = get_movie_data(db, video_id)
    if not movie_data:
        return []

    return scrap.scrap_stream(movie_data.link)


def get_movie_meta(db: Session, meta_id: str):
    movie_data = get_movie_data(db, meta_id)
    if not movie_data:
        return

    return {
        "meta": {
            "id": meta_id,
            "type": "movie",
            "name": movie_data.name,
            "poster": movie_data.poster,
            "background": movie_data.poster
        }
    }
