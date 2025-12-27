# Amazon Products Scraper & API Dashboard

## Project Overview

This project consists of two main components:
1. **Amazon Scraper** - Extracts top 5 products from any Amazon category
2. **Flask API + Dashboard** - Provides HTTP API and web interface to view the scraped data

## Features

### Scraper Features:
- Extracts top 5 best-selling products from Amazon categories
- Collects comprehensive product data including:
  - ASIN, title, rank
  - Price (current and list price with discount percentage)
  - Rating and review count
  - Prime availability
  - Best Sellers Rank (BSR)
  - Bullet points
  - Product image URL
- Robust price extraction using multiple methods
- Anti-detection measures with random user agents
- Automatic data persistence to SQLite database
- Detailed logging and error handling

### API & Dashboard Features:
- RESTful API endpoints for data access
- Web dashboard with responsive design
- Real-time statistics display
- Interactive sorting and filtering
- Automatic public tunnel creation via ngrok
- CORS support for cross-origin requests

## Project Structure

```

|__ scraper.py              # Main scraping script
|__ api_server.py           # Flask API server with ngrok
|__ index.html             # Web dashboard interface
|__ styles.css             # Dashboard styling
|__ script.js              # Dashboard JavaScript
|__ amazon_products.db     # SQLite database (generated)
|__ requirements.txt       # Python dependencies
|__ .env                  # Configuration file (create from .env.example)
|__ .env.example          # Example configuration
|__ public_url.txt        # Generated public URL (after ngrok starts)
```

## Installation

### Prerequisites
- Python 3.8+
- Google Chrome browser
- ChromeDriver (compatible with your Chrome version)

### Step 1: Install Python Dependencies
```bash
pip install -r requirements.txt
```

### Step 2: Set Up Configuration
```bash
cp .env.example .env
# Edit .env file with your settings
```

### Step 3: Install ChromeDriver
Download ChromeDriver from https://chromedriver.chromium.org/ and ensure it's in your system PATH.

**For Windows:**
- Download ChromeDriver
- Add location to PATH (e.g., `C:\Users\User\AppData\Local\Microsoft\WindowsApps\`)
- Or place in project directory

## Usage

### 1. Scrape Amazon Products
```bash
python scraper.py https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden
```

### 2. Start API Server & Dashboard
```bash
python api_server.py
```

The server will:
- Start on http://localhost:5000 and http://192.168.31.41:5000
- Automatically create a public ngrok tunnel
- Display public URL (e.g., https://unmuscled-mucic-kamden.ngrok-free.dev)
- Provide access to web dashboard and API endpoints

## API Endpoints

### GET `/api/products`
Returns all scraped products.

**Response:**
```json
{
  "success": true,
  "count": 5,
  "products": [
    {
      "asin": "B0ABCDEFGH",
      "title": "Product Name",
      "rank": 1,
      "price": 99.99,
      "currency": "$",
      "list_price": 129.99,
      "discount_percent": 23.1,
      "rating": 4.5,
      "reviews_count": 1247,
      "is_prime": true,
      "best_sellers_rank": "#1 in Home & Kitchen",
      "bullet_points": "Feature 1 | Feature 2 | Feature 3",
      "main_image_url": "https://example.com/image.jpg",
      "scraped_at": "2024-01-15 10:30:00"
    }
  ]
}
```

### GET `/api/products/<asin>`
Returns a single product by ASIN.

### GET `/api/stats`
Returns database statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_products": 5,
    "average_price": 89.99,
    "average_rating": 4.3,
    "prime_products": 3
  }
}
```

## Public Access via Ngrok

The system automatically creates a public tunnel using ngrok. After starting the server, you'll see:

```bash
============================================================
Starting ngrok tunnel...
============================================================
Public URL: https://unmuscled-mucic-kamden.ngrok-free.dev
============================================================
API Endpoints:
  GET /api/products       - All products
  GET /api/products/<asin> - Single product
  GET /api/stats          - Statistics
  GET /                   - Dashboard
Public Access URL: https://unmuscled-mucic-kamden.ngrok-free.dev
Dashboard: https://unmuscled-mucic-kamden.ngrok-free.dev
Stats: https://unmuscled-mucic-kamden.ngrok-free.dev/api/stats
Products: https://unmuscled-mucic-kamden.ngrok-free.dev/api/products
============================================================
```

**Access Options:**
1. **Local Access**: http://127.0.0.1:5000 or http://192.168.31.41:5000
2. **Public Access**: https://unmuscled-mucic-kamden.ngrok-free.dev (share with anyone!)
3. **Mobile Access**: Use the public URL on any device

### Manual Tunnel Creation:
If auto-start fails, create tunnel manually:
```bash
# In a separate terminal
ngrok http 5000
```

## Anti-Detection Measures

The scraper implements several techniques to avoid Amazon blocks:

1. **Random User Agents**: Rotates between different Chrome user agents
2. **Automation Hiding**: Disables Chrome automation flags
3. **Realistic Delays**: Random delays between requests (3-5 seconds)
4. **Scrolling Simulation**: Simulates human-like page interaction
5. **Request Throttling**: Limits concurrent requests
6. **Error Recovery**: Graceful handling of missing elements

### Additional Recommendations:
- Use residential proxies for large-scale scraping
- Implement IP rotation
- Add CAPTCHA solving services if needed
- Respect robots.txt and Amazon's terms of service

## Web Dashboard Features

The dashboard (`index.html`) provides:

1. **Product Cards**: Visual display of all products
2. **Statistics Panel**: Real-time metrics
3. **Sorting Controls**: Sort by price, rating, or rank
4. **Product Details**: Complete product information
5. **Responsive Design**: Works on desktop and mobile
6. **Interactive Elements**: Hover effects and transitions

## Configuration

### Environment Variables (`.env`):
```
DB_PATH=amazon_products.db
USE_NGROK=True
NGROK_AUTH_TOKEN=your_token_here
```

### Customization Options:
- **Database Path**: Change `DB_PATH` for custom database location
- **Ngrok Control**: Set `USE_NGROK=False` to disable auto-tunnel
- **Auth Token**: Add your ngrok auth token for custom domains

## How It Meets Project Requirements

### Task 1 Requirements:

| Requirement | Implementation |
|------------|----------------|
| Extract 5 top products | `scraper.py` extracts exactly 5 products |
| Collect all specified fields | All 12 fields extracted as per specification |
| Price and currency | Multiple extraction methods ensure price capture |
| Discount calculation | Automatically calculates discount percentage |
| Rating and reviews | Extracts from product pages |
| Prime detection | Checks for Prime badge |
| BSR extraction | Extracts first Best Sellers Rank |
| Bullet points | Extracts first 5 bullet points |
| Image URL | Captures main product image |
| Data storage | SQLite database with proper schema |
| HTTP interface | Flask API with JSON responses |
| Filtering capability | API supports client-side filtering |

### Task 2 Requirements:

| Requirement | Implementation |
|------------|----------------|
| Web interface | `index.html` with modern dashboard |
| Data display | Card-based layout with all product info |
| Sorting | JavaScript sorting by price, rating, rank |
| External access | Automatic ngrok tunnel integration |
| Public URL display | Console output with public link |
| Mobile compatibility | Responsive CSS design |

## Limitations & Considerations

1. **Rate Limiting**: Amazon may block aggressive scraping
2. **HTML Structure Changes**: Selectors may need updating if Amazon changes layout
3. **Legal Compliance**: Use responsibly and comply with Amazon's terms
4. **Free Ngrok Limitations**: 2-hour sessions, random URLs with free tier
5. **CAPTCHA Handling**: Basic scraping may trigger CAPTCHAs

## Troubleshooting

### Common Issues:

1. **"ChromeDriver not found"**
   - Download ChromeDriver and add to PATH
   - Ensure ChromeDriver version matches Chrome browser

2. **"Ngrok not found"**
   - Install ngrok: `npm install -g ngrok`
   - Or download from https://ngrok.com/download

3. **No products scraped**
   - Check internet connection
   - Verify URL format
   - Amazon may have blocked the request

4. **Database not created**
   - Run scraper first to create database
   - Check file permissions

