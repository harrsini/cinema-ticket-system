import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("TMDB_API_KEY")
BASE_URL = "https://api.themoviedb.org/3"


# --------------------------------------------------
# Search Movie
# --------------------------------------------------

def search_movie(movie_name):
    """
    Search for a movie and return the best matching result.
    """

    url = f"{BASE_URL}/search/movie"

    params = {
        "api_key": API_KEY,
        "query": movie_name
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    results = response.json().get("results", [])

    if not results:
        return None

    return results[0]


# --------------------------------------------------
# Movie Details
# --------------------------------------------------

def get_movie_details(movie_id):
    """
    Returns movie details such as
    runtime, genres, overview etc.
    """

    url = f"{BASE_URL}/movie/{movie_id}"

    params = {
        "api_key": API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    return response.json()


# --------------------------------------------------
# Movie Credits
# --------------------------------------------------

def get_movie_credits(movie_id):
    """
    Returns cast and crew.
    """

    url = f"{BASE_URL}/movie/{movie_id}/credits"

    params = {
        "api_key": API_KEY
    }

    response = requests.get(url, params=params)

    if response.status_code != 200:
        return None

    return response.json()


# --------------------------------------------------
# Complete Movie Details
# --------------------------------------------------

def get_complete_movie_details(movie_name):
    """
    Returns all important movie information.
    """

    movie = search_movie(movie_name)

    if movie is None:
        return None

    movie_id = movie["id"]

    details = get_movie_details(movie_id)

    credits = get_movie_credits(movie_id)

    if details is None or credits is None:
        return None

    cast = []

    for actor in credits.get("cast", [])[:10]:
        cast.append(actor["name"])

    director = "Unknown"

    for crew in credits.get("crew", []):

        if crew["job"] == "Director":
            director = crew["name"]
            break

    genres = []

    for genre in details.get("genres", []):
        genres.append(genre["name"])

    return {

        "title": details.get("title"),

        "overview": details.get("overview"),

        "release_date": details.get("release_date"),

        "runtime": details.get("runtime"),

        "language": details.get("original_language"),

        "genres": genres,

        "cast": cast,

        "director": director,

        "rating": details.get("vote_average")

    }