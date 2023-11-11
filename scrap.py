#!/usr/bin/env python3

import argparse
import asyncio
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import urlparse
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from imdb import Cinemagoer
from pymongo.errors import DuplicateKeyError

import database
import models

ia = Cinemagoer()

tamil_yogi_urls = {
    "tamil_hd": "https://tamilyogi.plus/category/tamilyogi-bluray-movies/" and "https://tamilyogi.run/tamil-hd-movies/",
    "tamil_new": "https://tamilyogi.plus/category/tamilyogi-full-movie-online/" and "https://tamilyogi.run/tamilyogi-tamil-new-movies/",
    "tamil_dubbed": "https://tamilyogi.run/tamilyogi-tamil-web-series-one/",
}

request_headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
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

    imdb_id = search_imdb(movie.a.get("title"))
    tamilyogi_id = None
    if imdb_id is None:
        tamilyogi_id = f"ty{uuid4().fields[-1]}"
    else:
        imdb_id = f"tt{imdb_id}"

    data = re.search(r"^(.+\(\d{4}\))", movie.a.get("title"))
    try:
        name = data[1].strip()
    except TypeError:
        name = movie.a.get("title")

    print(f"parsed movie data: {name}")

    return {
        "name": name,
        "imdb_id": imdb_id,
        "tamilyogi_id": tamilyogi_id,
        "link": movie.a.get("href"),
        "poster": movie.a.img.get("src"),
    }


def scrap_stream_v2(movie_url):
    stream_data = []
    response = requests.get(
        movie_url,
        headers=request_headers,
    )
    soup = BeautifulSoup(response.content, "html.parser")
    iframe = soup.find("iframe")
    if not (search_param := re.search(r"([a-z0-9]+)\.html", iframe.get("src"))):
        return stream_data

    param = search_param[1]
    url_parser = urlparse(iframe.get("src"))

    embedded_url = f"{url_parser.scheme}://{url_parser.netloc}/embed-{param}.html"

    result = requests.get(
        embedded_url,
        headers=request_headers,
    )
    if result.status_code != 200:
        return stream_data

    soup = BeautifulSoup(result.content, "html.parser")

    download_links = soup.find_all("a", class_="download_links")
    if not download_links:
        return stream_data

    for link in download_links:
        stream_data.append(
            {
                "title": link.text,
                "url": link.get("href"),
                "behaviorHints": {
                    "notWebReady": True,
                    "proxyHeaders": {"request": request_headers},
                },
            }
        )
    return stream_data


def scrap_stream(movie_url):
    stream_data = []
    response = requests.get(
        movie_url,
        headers=request_headers,
    )
    soup = BeautifulSoup(response.content, "html.parser")
    iframe = soup.find("iframe")
    if not iframe:
        return stream_data

    result = requests.get(
        iframe.get("src"),
        headers=request_headers,
    )
    soup = BeautifulSoup(result.content, "html.parser")
    embedded_link_a = soup.find("a", class_="download_links")
    if not embedded_link_a:
        return stream_data
    embedded_link = embedded_link_a.get("onclick").split("'")[1]

    result = requests.get(
        embedded_link,
        headers=request_headers,
    )
    soup = BeautifulSoup(result.content, "html.parser")

    iframe = soup.find("iframe")
    if not iframe:
        return stream_data

    result = requests.get(
        iframe.get("src") + embedded_link.split("?")[1] + ".html",
        headers=request_headers,
    )
    soup = BeautifulSoup(result.content, "html.parser")

    download_links = soup.find_all("a", class_="download_links")
    if not download_links:
        return stream_data

    for link in download_links:
        stream_data.append(
            {
                "title": link.text,
                "url": link.get("href"),
                "behaviorHints": {
                    "notWebReady": True,
                    "proxyHeaders": {"request": request_headers},
                },
            }
        )
    return stream_data


async def scrap_movies(catalog, url=None):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    movies_list = soup.find("ul", id="loop").find_all("li")
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


async def run_scrape(catalog, pages):
    await database.init()
    for page in range(pages, 0, -1):
        print(f"scraping {catalog} page: {page}")
        link = f"{tamil_yogi_urls[catalog]}/page/{page}/"
        await scrap_movies(catalog, link)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scrap Movie metadata from TamilYogi")
    parser.add_argument("-c", "--movie-catalog", help="scrap movie catalog", default="tamil_hd")
    parser.add_argument("-p", "--pages", type=int, default=1, help="number of scrap pages")
    args = parser.parse_args()

    asyncio.run(run_scrape(args.movie_catalog, args.pages))
