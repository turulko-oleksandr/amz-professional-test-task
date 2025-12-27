from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
import sqlite3
import os
import subprocess
import time
import requests
import sys
import shutil

app = Flask(__name__)
CORS(app)


def load_env():
    """Load environment variables from .env file"""
    if os.path.exists(".env"):
        with open(".env", "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    if "=" in line:
                        key, value = line.split("=", 1)
                        os.environ[key.strip()] = value.strip()


load_env()

DB_PATH = os.environ.get("DB_PATH", "amazon_products.db")
USE_NGROK = os.environ.get("USE_NGROK", "True").lower() in ("true", "1", "t")
NGROK_AUTH_TOKEN = os.environ.get("NGROK_AUTH_TOKEN", "")


def get_db_connection():
    """Database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def start_ngrok():
    """Start ngrok tunnel in background thread"""
    if not USE_NGROK:
        return None

    try:
        # Find ngrok path
        ngrok_path = shutil.which("ngrok")
        if not ngrok_path:
            # Try to find via where (Windows)
            try:
                result = subprocess.run(
                    ["where", "ngrok"], capture_output=True, text=True
                )
                if result.returncode == 0:
                    ngrok_path = result.stdout.strip().split("\n")[0]
            except:
                pass

        if not ngrok_path:
            print("Error: Ngrok not found in PATH")
            print("Please make sure ngrok is installed and in your PATH")
            return None

        print(f"Found ngrok at: {ngrok_path}")

        # Kill any existing ngrok processes (for Windows)
        try:
            if sys.platform == "win32":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "ngrok.exe"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            else:
                subprocess.run(
                    ["pkill", "ngrok"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except:
            pass

        # Prepare ngrok command
        cmd = [ngrok_path, "http", "5000"]

        if NGROK_AUTH_TOKEN:
            cmd = [ngrok_path, "http", "5000", "--authtoken", NGROK_AUTH_TOKEN]

        print("=" * 60)
        print("Starting ngrok tunnel...")
        print("=" * 60)

        # Start ngrok with shell=True for Windows
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )

        # Give ngrok time to start
        time.sleep(5)

        # Get public URL
        public_url = None
        max_attempts = 15

        for i in range(max_attempts):
            try:
                response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
                if response.status_code == 200:
                    data = response.json()
                    tunnels = data.get("tunnels", [])
                    if tunnels:
                        for tunnel in tunnels:
                            if tunnel.get("proto") == "https":
                                public_url = tunnel.get("public_url")
                                break
                    if public_url:
                        break
            except requests.exceptions.RequestException:
                pass

            print(f"  Waiting for ngrok... ({i+1}/{max_attempts})")
            time.sleep(2)

        if public_url:
            print(f"\nPublic URL: {public_url}")
            print("=" * 60)

            # Write URL to file
            with open("public_url.txt", "w") as f:
                f.write(f"Public URL: {public_url}\n")
                f.write(f"Dashboard: {public_url}\n")
                f.write(f"API Products: {public_url}/api/products\n")
                f.write(f"API Stats: {public_url}/api/stats\n")

            return public_url
        else:
            print("Failed to get ngrok URL")
            print("\nYou can manually create tunnel:")
            print("1. Open NEW terminal window")
            print("2. Run: ngrok http 5000")
            print("3. Copy the 'Forwarding' URL")
            return None

    except Exception as e:
        print(f"Ngrok error: {str(e)[:100]}...")
        print("\nTroubleshooting:")
        print("1. Try running manually in separate terminal: ngrok http 5000")
        print("2. Or use: npx ngrok http 5000")
        return None


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


@app.route("/<path:path>")
def static_files(path):
    """Serve static files"""
    return send_from_directory(".", path)


if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"Error: Database '{DB_PATH}' not found!")
        print("Please run scraper.py first to create the database.")
        exit(1)

    # Start ngrok tunnel
    public_url = None
    if USE_NGROK:
        public_url = start_ngrok()

    print("=" * 60)
    print("Amazon Products API Server")
    print("=" * 60)
    print("API Endpoints:")
    print("  GET /api/products       - All products")
    print("  GET /api/products/<asin> - Single product")
    print("  GET /api/stats          - Statistics")
    print("  GET /                   - Dashboard")

    if public_url:
        print(f"\nPublic Access URL: {public_url}")
        print(f"Mobile Access: {public_url}")
        print(f"\nDashboard: {public_url}")
        print(f"Stats: {public_url}/api/stats")
        print(f"Products: {public_url}/api/products")
        print("\nShare this link with anyone!")
    else:
        print("\nLocal Access: http://localhost:5000")
        print("\nTo create public tunnel:")
        print("1. Open NEW terminal window")
        print("2. Run: ngrok http 5000")
        print("3. Or: npx ngrok http 5000")
        print("4. Copy the 'Forwarding' URL")

    print("=" * 60)
    print("Press Ctrl+C to stop")
    print("=" * 60)

    # Run Flask app
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
