#!/usr/bin/env python3

import argparse
import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from urllib import parse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from imdb import Cinemagoer
from pymongo.errors import DuplicateKeyError

import database
import models

ia = Cinemagoer(loggingLevel=logging.INFO)

tamil_yogi_urls = {
    "tamil_hd": "http://tamilyogi.best/category/tamilyogi-bluray-movies/",
    "tamil_new": "http://tamilyogi.best/category/tamilyogi-full-movie-online/",
    "tamil_dubbed": "http://tamilyogi.best/category/tamilyogi-dubbed-movies-online/"
}


def search_imdb(title: str):
    filter_titles = []
    result = re.search(r"^.+\(\d*\)", title)
    if result:
        filter_titles.append(result[0])

    result = re.search(r"([\w\s.]+).+(\(\d+\))", title)
    if result:
        filter_titles.append(f"{result[1].strip()} {result[2]}")

    result = re.search(r"^[\w\s.]+", title)
    if result:
        filter_titles.append(f"{result[0].strip()}")

    for filter_title in filter_titles:
        result = ia.search_movie(filter_title)
        if result:
            for movie in result:
                if movie.get("title").lower() in title.lower():
                    return movie.movieID


def parse_movie(movie):
    if movie.a is None:
        return

    imdb_id = search_imdb(movie.a.get('title'))
    tamilyogi_id = None
    if imdb_id is None:
        tamilyogi_id = f"ty{uuid4().fields[-1]}"
    else:
        imdb_id = f"tt{imdb_id}"

    data = re.search(r"^(.+\(\d{4}\))", movie.a.get('title'))
    try:
        name = data[1].strip()
    except TypeError:
        name = movie.a.get('title')

    logging.info(f"parsed movie data: {name}")

    return {
        "name": name,
        "imdb_id": imdb_id,
        "tamilyogi_id": tamilyogi_id,
        "link": movie.a.get('href'),
        "poster": f"https://external-content.duckduckgo.com/iu/?u={parse.quote_plus(movie.a.img.get('src'))}&f=1&nofb=1"
    }


def scrap_stream(movie_url):
    stream_data = []
    r = requests.get(movie_url)
    soup = BeautifulSoup(r.content, "html.parser")
    iframe = soup.find("iframe")
    if not iframe:
        return stream_data

    result = requests.get(iframe.get("src"), headers={
        'User-Agent': 'Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/90.0.4430.91 Mobile Safari/537.36'
    })
    soup = BeautifulSoup(result.content, "html.parser")
    download_links = soup.find_all("a", class_="download_links")
    if not download_links:
        return stream_data

    for link in download_links:
        stream_data.append({
            "title": link.text,
            "externalUrl": link.get("href"),
            "behaviorHints": {"notWebReady": True}
        })
    return stream_data


async def scrap_movies(catalog, url=None):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    movies_list = soup.find('ul', id='loop').find_all('li')
    with ThreadPoolExecutor() as executor:
        result = executor.map(parse_movie, movies_list)

    for movie_data in reversed(list(result)):
        if movie_data is None:
            continue
        movie_data.update({"catalog": catalog})
        new_data = models.TamilYogiMovie.parse_obj(movie_data)
        try:
            await new_data.insert()
        except DuplicateKeyError:
            pass


def get_movie_rating(movie_id):
    movie = ia.get_movie(movie_id)
    return movie.get("rating")


async def run_scrape(catalog, pages):
    await database.init()
    for page in range(pages, 0, -1):
        logging.info(f"scraping {catalog} page: {page}")
        link = f"{tamil_yogi_urls[catalog]}/page/{page}/"
        await scrap_movies(catalog, link)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Scrap Movie metadata from TamilYogi")
    parser.add_argument("-c", "--movie-catalog", help="scrap movie catalog", default="tamil_hd")
    parser.add_argument("-p", "--pages", type=int, default=1, help="number of scrap pages")
    args = parser.parse_args()

    logging.basicConfig(format='%(levelname)s::%(asctime)s - %(message)s', datefmt='%d-%b-%y %H:%M:%S',
                        level=logging.INFO)

    asyncio.run(run_scrape(args.movie_catalog, args.pages))
