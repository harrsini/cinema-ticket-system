from pymongo import MongoClient
from dotenv import load_dotenv
import os

load_dotenv()

client = MongoClient(os.getenv("MONGO_URI"))

db = client["cinema_booking_system"]

movies = db["movies"]
theatres = db["theatres"]
shows = db["shows"]
seats = db["seats"]
bookings = db["bookings"]