from flask import Blueprint, request, jsonify
from utils.db import products_collection
from utils.image_handler import save_image
from bson.objectid import ObjectId

product_routes = Blueprint("product_routes", __name__)

# Get all products
@product_routes.route("/products", methods=["GET"])
def get_products():
    products = list(products_collection.find({}, {"_id": 1, "name": 1, "price": 1, "stock": 1, "image_url": 1}))
    for product in products:
        product["_id"] = str(product["_id"])
    return jsonify(products)

# Add new product
@product_routes.route("/products", methods=["POST"])
def add_product():
    data = request.json
    new_product = {
        "name": data["name"],
        "price": data["price"],
        "stock": data["stock"],
        "image_url": save_image(data["image"])
    }
    result = products_collection.insert_one(new_product)
    return jsonify({"message": "Product added", "product_id": str(result.inserted_id)})

# Delete product
@product_routes.route("/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    result = products_collection.delete_one({"_id": ObjectId(product_id)})
    if result.deleted_count:
        return jsonify({"message": "Product deleted"})
    return jsonify({"error": "Product not found"}), 404
