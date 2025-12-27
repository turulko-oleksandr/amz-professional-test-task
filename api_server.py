from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os

app = Flask(__name__)
CORS(app)

# Render.com automatically provides PORT environment variable
PORT = int(os.environ.get("PORT", 10000))
DB_PATH = os.environ.get("DB_PATH", "amazon_products.db")

def get_db_connection():
    """Database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# API endpoints
@app.route("/")
def index():
    """Home page"""
    return send_from_directory(".", "index.html")

@app.route("/api/products", methods=["GET"])
def get_products():
    """Get all products"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT 
                id, asin, title, rank, price, currency,
                list_price, discount_percent, rating, reviews_count,
                is_prime, best_sellers_rank, bullet_points, 
                main_image_url, scraped_at
            FROM products
            ORDER BY rank ASC
        """
        )
        rows = cursor.fetchall()
        conn.close()

        products = []
        for row in rows:
            products.append(
                {
                    "id": row["id"],
                    "asin": row["asin"],
                    "title": row["title"],
                    "rank": row["rank"],
                    "price": row["price"],
                    "currency": row["currency"],
                    "list_price": row["list_price"],
                    "discount_percent": row["discount_percent"],
                    "rating": row["rating"],
                    "reviews_count": row["reviews_count"],
                    "is_prime": bool(row["is_prime"]),
                    "best_sellers_rank": row["best_sellers_rank"],
                    "bullet_points": row["bullet_points"],
                    "main_image_url": row["main_image_url"],
                    "scraped_at": row["scraped_at"],
                }
            )

        return jsonify({"success": True, "count": len(products), "products": products})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/products/<asin>", methods=["GET"])
def get_product(asin):
    """Get single product by ASIN"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM products WHERE asin = ?", (asin,))
        row = cursor.fetchone()
        conn.close()

        if row:
            product = dict(row)
            product["is_prime"] = bool(product["is_prime"])
            return jsonify({"success": True, "product": product})
        else:
            return jsonify({"success": False, "error": "Product not found"}), 404
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Database statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) as total FROM products")
        total = cursor.fetchone()["total"]

        cursor.execute("SELECT AVG(price) as avg_price FROM products WHERE price > 0")
        avg_price = cursor.fetchone()["avg_price"]

        cursor.execute(
            "SELECT AVG(rating) as avg_rating FROM products WHERE rating IS NOT NULL"
        )
        avg_rating = cursor.fetchone()["avg_rating"]

        cursor.execute(
            "SELECT COUNT(*) as prime_count FROM products WHERE is_prime = 1"
        )
        prime_count = cursor.fetchone()["prime_count"]

        conn.close()

        return jsonify(
            {
                "success": True,
                "stats": {
                    "total_products": total,
                    "average_price": round(avg_price, 2) if avg_price else 0,
                    "average_rating": round(avg_rating, 2) if avg_rating else 0,
                    "prime_products": prime_count,
                },
            }
        )
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint for Render"""
    return jsonify({"status": "healthy", "service": "Amazon Products API"}), 200

@app.route("/<path:path>")
def static_files(path):
    """Serve static files"""
    return send_from_directory(".", path)

if __name__ == "__main__":
    print("=" * 60)
    print("Amazon Products API Server (Render.com)")
    print("=" * 60)
    print(f"Port: {PORT}")
    print(f"Database: {DB_PATH}")
    print("=" * 60)
    
    # Run Flask app - Render expects 0.0.0.0 binding
    app.run(host="0.0.0.0", port=PORT, debug=False)