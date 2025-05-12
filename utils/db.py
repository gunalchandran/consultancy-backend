from pymongo import MongoClient
from config import MONGO_URI, DATABASE_NAME

client = MongoClient(MONGO_URI)
db = client[DATABASE_NAME]

products_collection = db["products"]
orders_collection = db["orders"]
