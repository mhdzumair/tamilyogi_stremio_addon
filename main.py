import json
from pathlib import Path

from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import database
import schemas
import utils

app = FastAPI()
BASE_PATH = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_PATH / "resources"))

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


@app.on_event("startup")
async def init_db():
    await database.init()


@app.get("/")
async def get_home(request: Request):
    return TEMPLATES.TemplateResponse(
        "home.html",
        {
            "request": request, "name": manifest.get("name"), "version": manifest.get("version"),
            "description": manifest.get("description"), "gives": ["Tamil Movies", "Tamil Dubbed Movies"],
            "logo": "static/tamilyogi.png"
        },
    )


@app.get("/manifest.json")
async def get_manifest():
    return manifest


@app.get("/catalog/movie/{catalog_id}.json", response_model=schemas.Movie)
@app.get("/catalog/movie/{catalog_id}/skip={skip}.json", response_model=schemas.Movie)
async def get_catalog(catalog_id: str, skip: int = 0):
    try:
        movies = schemas.Movie()
        movies.metas.extend(await utils.get_movies_meta(catalog_id, skip))
        return movies
    except Exception as e:
        print(e)
        return {"error": str(e)}


@app.get("/meta/movie/{meta_id}.json")
async def get_meta(meta_id: str):
    return await utils.get_movie_meta(meta_id)


@app.get("/stream/movie/{video_id}.json", response_model=schemas.Streams)
async def get_stream(video_id: str):
    streams = schemas.Streams()
    streams.streams.extend(await utils.get_movie_streams(video_id))
    return streams
