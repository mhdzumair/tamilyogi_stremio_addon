import re
from concurrent.futures import ThreadPoolExecutor
from sys import argv
from uuid import uuid4

import requests
from bs4 import BeautifulSoup
from imdb import Cinemagoer
from sqlalchemy.exc import IntegrityError

import utils
from database import SessionLocal

ia = Cinemagoer()

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

    return {
        "name": movie.a.get('title'),
        "imdb_id": imdb_id,
        "tamilyogi_id": tamilyogi_id,
        "link": movie.a.get('href'),
        "poster": f"https://external-content.duckduckgo.com/iu/?u=http%3A%2F%2Ftamilyogi.best/"
                  f"{movie.a.img.get('src').lstrip('http://tamilyogi.best')}&f=1&nofb=1"
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
            "url": link.get("href"),
        })
    return stream_data


def scrap_movies(catalog, url=None):
    if url is None:
        url = tamil_yogi_urls.get(catalog)
    movie_table = utils.get_movie_table(catalog)
    db = SessionLocal()

    if url is None:
        return {"message": "No movie catalog found"}

    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")
    movies_list = soup.find('ul', id='loop').find_all('li')
    with ThreadPoolExecutor() as executor:
        result = executor.map(parse_movie, movies_list)

    for movie_data in reversed(list(result)):
        if movie_data is None:
            continue
        try:
            db.add(movie_table(**movie_data))
            db.commit()
        except IntegrityError:
            db.rollback()


def get_movie_rating(movie_id):
    movie = ia.get_movie(movie_id)
    return movie.get("rating")


def pull_all_movies_data():
    movie_catalogs_data = [["tamil_hd", 50], ["tamil_new", 40], ["tamil_dubbed", 65]]
    for catalog, max_page in movie_catalogs_data:
        for page in range(max_page, 0, -1):
            print(f"scraping {catalog} page: {page}")
            link = f"{tamil_yogi_urls[catalog]}/page/{page}/"
            scrap_movies(catalog, link)


if __name__ == '__main__':
    catalog_data = argv[1]
    scrap_movies(catalog_data)
