import json

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import database
import schemas
import utils

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory="resources"), name="static")

with open("manifest.json") as file:
    manifest = json.load(file)


async def init_db():
    await database.init()


@app.get("/")
async def get_info():
    return {
        "description": manifest.get("description"),
        "github": "https://github.com/mhdzumair/tamilyogi_stremio_addon",
        "created_by": "Mohamed Zumair",
        "version": manifest.get("version")
    }


@app.get("/manifest.json")
async def get_manifest():
    return manifest


@app.get("/catalog/movie/{catalog_id}.json", response_model=schemas.Movie)
@app.get("/catalog/movie/{catalog_id}/skip={skip}.json", response_model=schemas.Movie)
async def get_catalog(catalog_id: str, skip: int = 0, _=Depends(init_db)):
    movies = schemas.Movie()
    movies.metas.extend(await utils.get_movies_meta(catalog_id, skip))
    return movies


@app.get("/meta/movie/{meta_id}.json")
async def get_meta(meta_id: str, _=Depends(init_db)):
    return await utils.get_movie_meta(meta_id)


@app.get("/stream/movie/{video_id}.json", response_model=schemas.Streams)
async def get_stream(video_id: str, _=Depends(init_db)):
    streams = schemas.Streams()
    streams.streams.extend(await utils.get_movie_streams(video_id))
    return streams
