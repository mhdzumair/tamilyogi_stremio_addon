from typing import List, Any, Optional

from pydantic import BaseModel, Field


class Catalog(BaseModel):
    id: str
    name: str
    type: str


class Meta(BaseModel):
    id: Any
    name: str
    type: str = Field(default="movie")
    poster: str


class Movie(BaseModel):
    metas: Optional[List[Meta]] = []


class Stream(BaseModel):
    title: str
    url: str


class Streams(BaseModel):
    streams: Optional[List[Stream]] = []
