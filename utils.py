from typing import Optional

import schemas
import scrap
from models import TamilYogiMovie


async def get_movies_meta(catalog: str, skip: int = 0, limit: int = 25):
    movies_meta = []

    movies = await TamilYogiMovie.find(TamilYogiMovie.catalog == catalog).sort("-created_at").skip(skip).limit(
            limit).to_list()

    for movie in movies:
        meta_data = schemas.Meta.parse_obj(movie)
        meta_data.id = movie.imdb_id if movie.imdb_id else movie.tamilyogi_id
        movies_meta.append(meta_data)
    return movies_meta


async def get_movie_data(video_id: str) -> Optional[TamilYogiMovie]:
    if video_id.startswith("tt"):
        movie_data = await TamilYogiMovie.find_one(TamilYogiMovie.imdb_id == video_id)
    else:
        movie_data = await TamilYogiMovie.find_one(TamilYogiMovie.tamilyogi_id == video_id)

    if movie_data:
        return movie_data


async def get_movie_streams(video_id: str):
    movie_data = await get_movie_data(video_id)
    if not movie_data:
        return []

    return scrap.scrap_stream(movie_data.link)


async def get_movie_meta(meta_id: str):
    movie_data = await get_movie_data(meta_id)
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
