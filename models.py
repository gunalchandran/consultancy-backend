import random
from pymongo import MongoClient

# Connect to your MongoDB
client = MongoClient("mongodb+srv://ashilinbs22cse:Ashmi@cluster0.ttjdr.mongodb.net/supermarket_db")
db = client["supermarket_db"]
products_collection = db["Products"]

def get_price_from_name(name):
    name = name.lower()
    if any(keyword in name for keyword in ["milk", "cheese", "dairy", "butter"]):
        return random.randint(40, 100)
    elif any(keyword in name for keyword in ["chocolate", "candy", "sweet", "sugar"]):
        return random.randint(20, 80)
    elif any(keyword in name for keyword in ["chips", "lays", "kurkure", "snack"]):
        return random.randint(10, 50)
    elif any(keyword in name for keyword in ["rice", "atta", "wheat", "flour"]):
        return random.randint(60, 150)
    elif any(keyword in name for keyword in ["oil", "refined", "mustard", "sunflower"]):
        return random.randint(100, 250)
    elif any(keyword in name for keyword in ["soap", "shampoo", "toothpaste", "detergent"]):
        return random.randint(30, 200)
    elif any(keyword in name for keyword in ["juice", "drink", "beverage"]):
        return random.randint(25, 100)
    elif any(keyword in name for keyword in ["biscuit", "cookies", "parle"]):
        return random.randint(10, 50)
    else:
        return random.randint(20, 120)

# Update each product
for product in products_collection.find():
    name = product.get("product_name", "").lower()
    price = get_price_from_name(name)
    products_collection.update_one(
        {"_id": product["_id"]},
        {"$set": {"price": price}}
    )

print("✅ Prices updated based on product name.")
