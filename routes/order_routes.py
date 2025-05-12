from flask import Blueprint, request, jsonify
from utils.db import orders_collection, products_collection
from bson.objectid import ObjectId

order_routes = Blueprint("order_routes", __name__)

# Get all orders
@order_routes.route("/orders", methods=["GET"])
def get_orders():
    orders = list(orders_collection.find({}, {"_id": 1, "customer_name": 1, "items": 1, "total_amount": 1}))
    for order in orders:
        order["_id"] = str(order["_id"])
    return jsonify(orders)

# Place an order
@order_routes.route("/orders", methods=["POST"])
def place_order():
    data = request.json
    items = data["items"]
    
    # Check stock availability
    for item in items:
        product = products_collection.find_one({"_id": ObjectId(item["product"])})
        if not product or product["stock"] < item["quantity"]:
            return jsonify({"error": f"{product['name']} is out of stock"}), 400

    # Reduce stock
    for item in items:
        products_collection.update_one(
            {"_id": ObjectId(item["product"])},
            {"$inc": {"stock": -item["quantity"]}}
        )

    new_order = {
        "customer_name": data["customer_name"],
        "items": data["items"],
        "total_amount": data["total_amount"]
    }
    result = orders_collection.insert_one(new_order)
    
    return jsonify({"message": "Order placed successfully", "order_id": str(result.inserted_id)})
