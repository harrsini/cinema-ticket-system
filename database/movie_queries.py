from database.mongodb import movies


def search_movie(movie_name):
    """
    Search for a movie by name.
    """

    movie = movies.find_one(
        {
            "movie_name": {
                "$regex": f"^{movie_name}$",
                "$options": "i"
            }
        }
    )

    return movie