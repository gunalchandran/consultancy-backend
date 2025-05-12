from flask import Flask, request, jsonify, send_from_directory,send_file
from flask_pymongo import PyMongo
from werkzeug.utils import secure_filename
from flask_cors import CORS
import os
from bson.objectid import ObjectId
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
import logging
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from werkzeug.security import generate_password_hash
import random
from dotenv import load_dotenv
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io


load_dotenv()
app = Flask(__name__)

CORS(app, resources={r"/*": {"origins": "*"}})

app.config["MONGO_URI"] = os.getenv("MONGO_URI")
mongo = PyMongo(app)
UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "uploads")
PROFILE_FOLDER = os.getenv("PROFILE_FOLDER", os.path.join("static", "profiles"))


os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(PROFILE_FOLDER, exist_ok=True)


app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["PROFILE_FOLDER"] = PROFILE_FOLDER

db = mongo.db  
products_collection = db["Products"]
users_collection = db["Users"]
cart_collection = db["Cart"]
orders_collection = db["Orders"]

bcrypt = Bcrypt(app)

app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY")
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))


jwt = JWTManager(app)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def send_email(to_email, subject, body):
    try:
     
        msg = MIMEMultipart()
        msg["From"] = EMAIL_ADDRESS
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

       
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        server.quit()

        print(f"Email sent to {to_email}")
    except Exception as e:
        print(f"Error sending email: {e}")


@app.route("/products", methods=["POST"])
def add_product():
    if "image" not in request.files:
        return jsonify({"error": "No image uploaded"}), 400

    image = request.files["image"]
    if image.filename == "":
        return jsonify({"error": "No selected file"}), 400

    if image and allowed_file(image.filename):
        filename = secure_filename(image.filename)
        image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        image.save(image_path)
        image_url = f"http://localhost:5000/uploads/{filename}"

        product_data = {
            "brands": request.form.get("brands", ""),
            "code": request.form.get("code", ""),
            "image_url": image_url,
            "ingredients_text": request.form.get("ingredients_text", ""),
            "product_name": request.form.get("product_name", ""),
            "schema_version": int(request.form.get("schema_version", 1)),
            "stock": int(request.form.get("stock", 0)),
            "price": float(request.form.get("price", 0))
        }

        result = products_collection.insert_one(product_data)
        return jsonify({"message": "Product added", "product_id": str(result.inserted_id)}), 201

    return jsonify({"error": "Invalid file type"}), 400


@app.route("/products", methods=["GET"])
def get_products():
    products = list(products_collection.find({}, {
        "_id": 1,
        "brands": 1,
        "code": 1,
        "image_url": 1,
        "ingredients_text": 1,
        "product_name": 1,
        "schema_version": 1,
        "stock": 1,
        "price": 1
    }))
    for product in products:
        product["_id"] = str(product["_id"])
    return jsonify(products)

@app.route("/products/<product_id>", methods=["PUT"])
def update_product(product_id):
    try:
        update_fields = {}

        if "image" in request.files:
            image = request.files["image"]
            if image and allowed_file(image.filename):
                filename = secure_filename(image.filename)
                image_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
                image.save(image_path)
                update_fields["image_url"] = f"http://localhost:5000/uploads/{filename}"
            else:
                return jsonify({"error": "Invalid file type"}), 400

        for field in ["brands", "code", "ingredients_text", "product_name", "schema_version", "stock", "price"]:
            if field in request.form:
                if field in ["stock", "schema_version"]:
                    update_fields[field] = int(request.form[field])
                elif field == "price":
                    update_fields[field] = float(request.form[field])
                else:
                    update_fields[field] = request.form[field]

        if not update_fields:
            return jsonify({"message": "No valid fields to update"}), 400

        result = products_collection.update_one({"_id": ObjectId(product_id)}, {"$set": update_fields})
        if result.modified_count > 0:
            return jsonify({"message": "Product updated successfully"}), 200
        return jsonify({"message": "No changes made"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/generate-bill", methods=["POST"])
def generate_bill():
    data = request.json
    items = data.get("items", [])

    if not items:
        return jsonify({"error": "No items provided"}), 400

    # Create PDF in memory
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    width, height = letter

    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(200, y, "Customer Bill")
    y -= 40

    pdf.setFont("Helvetica", 12)
    pdf.drawString(50, y, "Product Name")
    pdf.drawString(250, y, "Quantity")
    pdf.drawString(350, y, "Price")
    pdf.drawString(450, y, "Total")
    y -= 20

    grand_total = 0
    for item in items:
        name = item['product_name']
        quantity = item['quantity']
        price = item['price']
        total = quantity * price
        grand_total += total

        pdf.drawString(50, y, name)
        pdf.drawString(250, y, str(quantity))
        pdf.drawString(350, y, f"₹{price}")
        pdf.drawString(450, y, f"₹{total:.2f}")
        y -= 20

    y -= 10
    pdf.setFont("Helvetica-Bold", 12)
    pdf.drawString(350, y, "Grand Total:")
    pdf.drawString(450, y, f"₹{grand_total:.2f}")

    pdf.save()
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name="bill.pdf", mimetype="application/pdf")


@app.route("/products/<product_id>", methods=["DELETE"])
def delete_product(product_id):
    try:
        result = products_collection.delete_one({"_id": ObjectId(product_id)})
        if result.deleted_count > 0:
            return jsonify({"message": "Product deleted"}), 200
        return jsonify({"error": "Product not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 400
    


@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/register", methods=["POST"])
def register():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "customer") 

    if users_collection.find_one({"email": email}):
        return jsonify({"error": "Email already exists"}), 400

    hashed_password = bcrypt.generate_password_hash(password).decode("utf-8")

    users_collection.insert_one({
        "name": name,
        "email": email,
        "password": hashed_password,
        "role": role
    })

    return jsonify({"message": "User registered successfully"}), 201


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    user = users_collection.find_one({"email": email})
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    access_token = create_access_token(identity=email)
    return jsonify({
        "message": "Login successful",
        "token": access_token,
        "role": user.get("role", "customer"),
        "name": user.get("name", ""),
        "phone": user.get("phone", "")
    }), 200


@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user = get_jwt_identity()
    return jsonify({"message": "Access granted", "user": current_user}), 200


@app.route("/update-profile", methods=["POST"])
def update_profile():
    email = request.form.get("email")
    phone = request.form.get("phone")
    profile_pic = request.files.get("profile")

    if not email or not phone:
        return jsonify({"error": "Email and phone number are required!"}), 400

    user = users_collection.find_one({"email": email})

    if not user:
        return jsonify({"error": "User not found!"}), 404

    if profile_pic:
    
        filename = secure_filename(profile_pic.filename)
        profile_pic.save(os.path.join("static/profiles", filename))

     
        users_collection.update_one(
            {"email": email},
            {"$set": {"phone": phone, "profile_pic": filename}}
        )
        
 
        profile_url = f"http://localhost:5000/static/profiles/{filename}"
        return jsonify({"message": "Profile updated successfully!", "profile_url": profile_url}), 200

    
    users_collection.update_one(
        {"email": email},
        {"$set": {"phone": phone}}
    )

    return jsonify({"message": "Profile updated successfully!"}), 200

@app.route("/get-profile", methods=["GET"])
def get_profile():
    email = request.args.get("email")
    name=request.args.get("name")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = users_collection.find_one(
        {"email": email},
        {"_id": 0, "email": 1, "name": 1,"phone": 1, "profile_pic": 1} 
    )

    if user:
        profile_pic_filename = user.get("profile_pic") 

        if profile_pic_filename:
           
            user["profile_url"] = f"http://localhost:5000/static/profiles/{profile_pic_filename}"
        else:
            user["profile_url"] = None

        
        user.pop("profile_pic", None)

        return jsonify(user), 200

    return jsonify({"message": "User not found 🕵️‍♂️"}), 404





@app.route("/cart", methods=["POST"])
def add_to_cart():
    data = request.json
    email = data.get("email")
    product_id = data.get("product_id")
    quantity = data.get("quantity", 1)

    if not email or not product_id:
        return jsonify({"error": "Missing email or product_id"}), 400

    product = products_collection.find_one({"_id": ObjectId(product_id)})
    if not product:
        return jsonify({"error": "Product not found"}), 404

    existing = cart_collection.find_one({"user": email, "product_id": product_id})
    if existing:
        cart_collection.update_one({"_id": existing["_id"]}, {"$inc": {"quantity": quantity}})
    else:
        cart_collection.insert_one({
            "user": email,
            "product_id": product_id,
            "product_name": product["product_name"],
            "quantity": quantity,
            "price": product["price"],
            "image_url": product.get("image_url", "")
        })

    return jsonify({"message": "Item added to cart"}), 201


@app.route("/cart", methods=["GET"])
def get_cart():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    items = list(cart_collection.find({"user": email}))
    for item in items:
        item["_id"] = str(item["_id"])
        item["total_price"] = round(item["quantity"] * item["price"], 2)

      
        if "image_url" in item and item["image_url"]:
            
            pass
        elif "image" in item and item["image"]:
        
            if not item["image"].startswith("uploads/"):
                item["image"] = f"uploads/{item['image']}"
        else:
           
            item["image"] = "uploads/default.jpg"

    return jsonify(items), 200


@app.route("/cart/<item_id>", methods=["PUT"])
def update_cart_item(item_id):
    data = request.json
    quantity = data.get("quantity")
    if not quantity or quantity < 1:
        return jsonify({"error": "Quantity must be at least 1"}), 400

    result = cart_collection.update_one({"_id": ObjectId(item_id)}, {"$set": {"quantity": quantity}})
    return jsonify({"message": "Cart updated"} if result.modified_count else {"error": "Item not found"}), 200


@app.route("/cart/<item_id>", methods=["DELETE"])
def remove_cart_item(item_id):
    result = cart_collection.delete_one({"_id": ObjectId(item_id)})
    return jsonify({"message": "Item removed"} if result.deleted_count else {"error": "Item not found"}), 200

@app.route("/cart", methods=["DELETE"])
def clear_cart():
    email = request.args.get("email")
    if not email:
        return jsonify({"error": "Email is required"}), 400

    cart_collection.delete_many({"user": email})
    return jsonify({"message": "Cart cleared"}), 200

@app.route("/static/profiles/<filename>")
def serve_profile(filename):
    return send_from_directory(PROFILE_FOLDER, filename)
@app.route("/order", methods=["POST"])
def place_order():
    data = request.json
    required_fields = [
        "email", "name", "phone", "product_id", "product_name", "quantity",
        "order_date", "order_time", "delivery_time", "payment_method",
        "payment_status", "delivery_status", "address" 
    ]

    if not all(field in data for field in required_fields):
        return jsonify({"error": "Missing fields in order"}), 400

    try:
        
        try:
            data["quantity"] = int(data["quantity"])
        except ValueError:
            return jsonify({"error": "Quantity must be an integer"}), 400

        
        product = products_collection.find_one({"_id": ObjectId(data["product_id"])})

        if not product:
            return jsonify({"error": "Product not found"}), 404

       
        unit_price = product["price"]
        total_price = unit_price * data["quantity"]

        
        data["price"] = unit_price
        data["total_price"] = total_price

      
        if 'image_url' in product:
            data["image"] = product["image_url"]

        
        result = orders_collection.insert_one(data)

       
        products_collection.update_one(
            {"_id": ObjectId(data["product_id"])},
            {"$inc": {"stock": -data["quantity"]}}
        )

        return jsonify({"message": "Order placed successfully", "order_id": str(result.inserted_id)}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route("/order-history", methods=["GET"])
def order_history():
    password = request.args.get('password')  # You can also get it from the headers if preferred
    
    if password == "admin":
        
        orders = list(orders_collection.find())
    else:
        
        email = request.args.get('email')
        if not email:
            return jsonify({"error": "Email is required"}), 400
        
        
        orders = list(orders_collection.find({"email": email}))

    if not orders:
        return jsonify({"message": "No orders found"}), 404

    
    for order in orders:
        order["_id"] = str(order["_id"])  
        order["delivery_time"] = str(order["delivery_time"])  
        order["order_date"] = str(order["order_date"]) 
        order["order_time"] = str(order["order_time"])  
        order["total_price"] = str(order.get("total_price", 0)) 

    return jsonify(orders), 200


@app.route("/cancel-order/<order_id>", methods=["DELETE"])
def cancel_order(order_id):
    email = request.args.get('email') 
    if not email:
        return jsonify({"error": "Email is required"}), 400


    order = orders_collection.find_one({"_id": ObjectId(order_id), "email": email})

    if not order:
        return jsonify({"error": "Order not found or you don't have permission to cancel it"}), 404

    if order["delivery_status"] != "Pending":
        return jsonify({"error": "Order cannot be canceled, it's already processed or delivered"}), 400


    orders_collection.update_one(
        {"_id": ObjectId(order_id)},
        {"$set": {"delivery_status": "Canceled"}}
    )

  
    products_collection.update_one(
        {"_id": ObjectId(order["product_id"])},
        {"$inc": {"stock": order["quantity"]}}
    )

    return jsonify({"message": "Order canceled successfully"}), 200

@app.route("/orderss", methods=["GET"])
def get_orders():
  
    orders = list(orders_collection.find({}))
    for order in orders:
        order["_id"] = str(order["_id"])  
    return jsonify(orders)


@app.route("/orders/<order_id>", methods=["PUT"])
def update_order_status(order_id):
    try:
        data = request.get_json()
        payment_status = data.get("payment_status")
        delivery_status = data.get("delivery_status")

        if not payment_status or not delivery_status:
            return jsonify({"error": "Missing payment status or delivery status"}), 400

       
        order_object_id = ObjectId(order_id)

        
        order = orders_collection.find_one({"_id": order_object_id})
        if not order:
            return jsonify({"error": "Order not found"}), 404

        
        result = orders_collection.update_one(
            {"_id": order_object_id},
            {"$set": {"payment_status": payment_status, "delivery_status": delivery_status}}
        )

        if result.matched_count == 0:
            return jsonify({"error": "Order not found"}), 404

        if delivery_status == "Delivered":
            customer_email = order.get("email")
            customer_name = order.get("name", "Customer")
            subject = "Your Order Has Been Delivered"
            body = f"Dear {customer_name},\n\nYour order has been successfully delivered. Thank you for shopping with us!\n\nBest regards,\nGrocery Store Team"
            send_email(customer_email, subject, body)

        return jsonify({"message": "Order status updated successfully"}), 200

    except Exception as e:
        return jsonify({"error": str(e)}), 500
def extract_order_details(orders):
    result = []
    for order in orders:
        order_date = order.get("order_date")  
        if order_date:
            order_date = datetime.strptime(order_date, "%Y-%m-%d") 
            month = order_date.strftime("%B") 
            order_place = order.get("order_place", "Unknown") 
            result.append({
                "month": month,
                "order_place": order_place
            })
    return result


@app.route("/admin/orders", methods=["GET"])
def get_admin_orders():
    orders_cursor = orders_collection.find({})
    orders = []

    for order in orders_cursor:
        orders.append({
            "order_date": order.get("order_date", ""),
            "delivery_status": order.get("delivery_status", ""),
            "payment_method": order.get("payment_method", ""),
            "total_price": order.get("total_price", 0),
            "product_name": order.get("product_name", ""),
            "quantity": order.get("quantity", 0),
            "name": order.get("name", ""), 
            "email": order.get("email", ""),  
            "phone": order.get("phone", ""),  
            "address": order.get("address", ""),  
            "_id": str(order.get("_id")) 
        })

    return jsonify(orders), 200



@app.route("/orders/bulk", methods=["POST"])
def place_bulk_orders():
    data = request.json
    orders = data.get("orders", [])

    if not orders:
        return jsonify({"error": "No orders provided"}), 400

    inserted_orders = []
    for order in orders:
        required_fields = [
            "email", "name", "phone", "product_id", "product_name", "quantity",
            "order_date", "order_time", "delivery_time", "payment_method",
            "payment_status", "delivery_status"
        ]

        if not all(field in order for field in required_fields):
            return jsonify({"error": "Missing fields in one of the orders"}), 400

        try:
            order["quantity"] = int(order["quantity"])
        except ValueError:
            return jsonify({"error": "Quantity must be an integer"}), 400

        product = products_collection.find_one({"_id": ObjectId(order["product_id"])})
        if not product:
            return jsonify({"error": f"Product with ID {order['product_id']} not found"}), 404

        unit_price = product["price"]
        order["price"] = unit_price
        order["total_price"] = unit_price * order["quantity"]
        order["image"] = product.get("image_url", "")

        inserted_orders.append(order)

    orders_collection.insert_many(inserted_orders)
    return jsonify({"message": "Bulk order placed successfully"}), 201




if __name__ == "__main__":
    app.run(debug=True)
