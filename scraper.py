"""
Amazon Products Scraper - Clean Version
Scrapes top 5 products from Amazon and saves to SQLite database
Usage: python scraper.py <category_url>
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import sqlite3
import time
import re
import logging
from typing import List, Optional, Tuple
from dataclasses import dataclass
import random
import sys

# ===== Logging Configuration =====
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# ===== Data Model =====
@dataclass
class ProductModel:
    asin: str
    title: str
    rank: int
    price: float
    currency: str = "$"
    list_price: Optional[float] = None
    discount_percent: Optional[float] = None
    rating: Optional[float] = None
    reviews_count: Optional[int] = None
    is_prime: bool = False
    best_sellers_rank: Optional[str] = None
    bullet_points: str = ""
    main_image_url: Optional[str] = None


# ===== Database Manager =====
class DatabaseManager:
    def __init__(self, db_path="amazon_products.db"):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                asin TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                rank INTEGER,
                price REAL,
                currency TEXT,
                list_price REAL,
                discount_percent REAL,
                rating REAL,
                reviews_count INTEGER,
                is_prime BOOLEAN,
                best_sellers_rank TEXT,
                bullet_points TEXT,
                main_image_url TEXT,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """
        )
        conn.commit()
        conn.close()
        logger.info("Database initialized")

    def save_product(self, product: ProductModel):
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO products 
                (asin, title, rank, price, currency, list_price, discount_percent,
                 rating, reviews_count, is_prime, best_sellers_rank, bullet_points,
                 main_image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    product.asin,
                    product.title,
                    product.rank,
                    product.price,
                    product.currency,
                    product.list_price,
                    product.discount_percent,
                    product.rating,
                    product.reviews_count,
                    product.is_prime,
                    product.best_sellers_rank,
                    product.bullet_points,
                    product.main_image_url,
                ),
            )
            conn.commit()
            conn.close()
            logger.info(f"Saved: {product.asin}")
        except Exception as e:
            logger.error(f"Error saving product: {e}")


# ===== Selenium Configuration =====
class SeleniumConfig:
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]

    @staticmethod
    def get_chrome_options():
        options = Options()
        options.add_argument(f"user-agent={random.choice(SeleniumConfig.USER_AGENTS)}")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)
        return options


# ===== Price Extractor =====
class PriceExtractor:
    """Class for extracting prices using different methods"""

    def __init__(self, driver, wait):
        self.driver = driver
        self.wait = wait

    def extract_price_value(self, price_text: str) -> Tuple[Optional[float], str]:
        """Extract price and currency from text"""
        if not price_text:
            return None, "$"

        price_text = price_text.strip()
        price_text = re.sub(
            r"^(Price|From|Save|Limited time deal|List Price|List:)[\s:]*",
            "",
            price_text,
            flags=re.IGNORECASE,
        )
        price_text = price_text.strip()

        # Extract currency
        currency_match = re.search(r"([\$£€¥])", price_text)
        currency = currency_match.group(1) if currency_match else "$"

        # Extract numeric value
        price_patterns = [
            r"[\$£€¥]\s*([\d,]+\.?\d*)",
            r"([\d,]+\.?\d*)\s*[\$£€¥]",
            r"([\d,]+\.?\d*)",
        ]

        for pattern in price_patterns:
            price_match = re.search(pattern, price_text)
            if price_match:
                price_str = price_match.group(1).replace(",", "")
                try:
                    price_val = float(price_str)
                    if price_val > 0:
                        return price_val, currency
                except ValueError:
                    continue

        return None, currency

    def try_options_text(self) -> Optional[Tuple[float, str]]:
        """Method 1: Extract from 'X options from $XX.XX' text"""
        try:
            text_elements = self.driver.find_elements(
                By.CSS_SELECTOR,
                "span.a-size-small, span.olpWrapper, #twister_swatch_price",
            )

            for elem in text_elements:
                text = elem.text.strip()
                match = re.search(
                    r"\d+\s+options?\s+from\s+\$\s*([\d,]+\.?\d*)", text, re.IGNORECASE
                )
                if match:
                    price_str = match.group(1).replace(",", "")
                    price_val = float(price_str)
                    if price_val > 0:
                        logger.info(f"Price (from options text): ${price_val}")
                        return price_val, "$"
        except Exception as e:
            logger.debug(f"Options text method failed: {e}")
        return None

    def try_select_variant(self) -> Optional[Tuple[float, str]]:
        """Method 2: Select first variant and extract price"""
        try:
            variants = self.driver.find_elements(
                By.CSS_SELECTOR,
                "#variation_color_name li.swatchSelect, #variation_size_name li.swatchSelect, "
                "ul.swatches li.swatchAvailable",
            )

            if variants:
                self.driver.execute_script("arguments[0].click();", variants[0])
                logger.info("Selected first variant")
                time.sleep(2)

                offscreen = self.driver.find_elements(
                    By.CSS_SELECTOR, "span.a-price span.a-offscreen"
                )
                for elem in offscreen[:3]:
                    price_text = elem.get_attribute("textContent") or elem.text
                    if price_text and "$" in price_text:
                        price, currency = self.extract_price_value(price_text)
                        if price and price > 0:
                            logger.info(
                                f"Price (after variant selection): {currency}{price}"
                            )
                            return price, currency
        except Exception as e:
            logger.debug(f"Variant selection failed: {e}")
        return None

    def try_offscreen_elements(self) -> Optional[Tuple[float, str]]:
        """Method 3: All offscreen elements"""
        try:
            elements = self.driver.find_elements(
                By.CSS_SELECTOR, "span.a-price span.a-offscreen"
            )
            for elem in elements[:5]:
                price_text = elem.get_attribute("textContent") or elem.text
                if price_text and "$" in price_text:
                    price, currency = self.extract_price_value(price_text)
                    if price and price > 0:
                        logger.info(f"Price (offscreen): {currency}{price}")
                        return price, currency
        except Exception as e:
            logger.debug(f"Offscreen method failed: {e}")
        return None

    def try_visible_price(self) -> Optional[Tuple[float, str]]:
        """Method 4: Visible price (whole + fraction)"""
        try:
            selectors = [
                ".a-price-whole",
                "span.a-price .a-price-whole",
                ".a-priceToPay .a-price-whole",
            ]

            for selector in selectors:
                try:
                    whole = self.driver.find_element(By.CSS_SELECTOR, selector)
                    whole_text = whole.text.strip().replace(",", "")

                    fraction = "00"
                    try:
                        parent = whole.find_element(By.XPATH, "..")
                        frac_elem = parent.find_element(
                            By.CSS_SELECTOR, ".a-price-fraction"
                        )
                        fraction = frac_elem.text.strip()
                    except:
                        pass

                    if whole_text and whole_text.replace(".", "").isdigit():
                        price, currency = self.extract_price_value(
                            f"${whole_text}.{fraction}"
                        )
                        if price and price > 0:
                            logger.info(f"Price (visible): {currency}{price}")
                            return price, currency
                except:
                    continue
        except Exception as e:
            logger.debug(f"Visible price failed: {e}")
        return None

    def try_javascript_search(self) -> Optional[Tuple[float, str]]:
        """Method 5: JavaScript search throughout the page"""
        try:
            js_result = self.driver.execute_script(
                """
                let prices = [];
                document.querySelectorAll('span.a-offscreen').forEach(elem => {
                    let text = elem.textContent.trim();
                    if(text && text.includes('$')) {
                        let match = text.match(/\\$\\s*([\\d,]+\\.?\\d*)/);
                        if(match) {
                            let val = parseFloat(match[1].replace(',', ''));
                            if(val > 0) prices.push({text: text, value: val});
                        }
                    }
                });
                return prices.length > 0 ? prices[0].text : null;
            """
            )

            if js_result:
                price, currency = self.extract_price_value(js_result)
                if price and price > 0:
                    logger.info(f"Price (JS search): {currency}{price}")
                    return price, currency
        except Exception as e:
            logger.debug(f"JS search failed: {e}")
        return None

    def try_data_attributes(self) -> Optional[Tuple[float, str]]:
        """Method 6: Data attributes"""
        try:
            data = self.driver.execute_script(
                """
                let elems = document.querySelectorAll('[data-a-price]');
                for(let elem of elems) {
                    try {
                        let data = JSON.parse(elem.getAttribute('data-a-price'));
                        if(data && data.amount) return data.symbol + data.amount;
                    } catch(e) {}
                }
                return null;
            """
            )

            if data:
                price, currency = self.extract_price_value(data)
                if price and price > 0:
                    logger.info(f"Price (data attr): {currency}{price}")
                    return price, currency
        except Exception as e:
            logger.debug(f"Data attribute method failed: {e}")
        return None

    def get_price(self) -> Tuple[float, str]:
        """Main method - tries all approaches sequentially"""
        # Wait for page to load
        try:
            self.wait.until(EC.presence_of_element_located((By.ID, "productTitle")))
            time.sleep(2)
        except:
            pass

        # Scroll to activate lazy load
        self.driver.execute_script("window.scrollBy(0, 300);")
        time.sleep(1)

        # Check for unavailable status
        try:
            unavailable = self.driver.find_elements(
                By.CSS_SELECTOR,
                "#availability span.a-color-price, #availability span.a-color-state",
            )
            for elem in unavailable:
                if "unavailable" in elem.text.lower():
                    logger.warning("Product unavailable")
                    return 0.0, "$"
        except:
            pass

        # Try all methods
        methods = [
            self.try_options_text,
            self.try_select_variant,
            self.try_offscreen_elements,
            self.try_visible_price,
            self.try_javascript_search,
            self.try_data_attributes,
        ]

        for method in methods:
            result = method()
            if result:
                return result

        logger.warning("Price NOT FOUND")
        return 0.0, "$"


# ===== Amazon Scraper =====
class AmazonScraper:
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.driver = None
        self.wait = None
        self.price_extractor = None

    def init_driver(self):
        try:
            options = SeleniumConfig.get_chrome_options()
            self.driver = webdriver.Chrome(options=options)
            self.wait = WebDriverWait(self.driver, 15)
            self.price_extractor = PriceExtractor(self.driver, self.wait)
            logger.info("Chrome driver initialized")
        except Exception as e:
            logger.error(f"Failed to initialize driver: {e}")
            raise

    def close_driver(self):
        if self.driver:
            self.driver.quit()
            logger.info("Driver closed")

    def extract_rating(self) -> Optional[float]:
        """Extract rating"""
        try:
            elem = self.driver.find_element(
                By.CSS_SELECTOR, "i.a-icon-star span.a-icon-alt"
            )
            text = elem.get_attribute("textContent") or elem.text
            match = re.search(r"([\d.]+)", text)
            if match:
                return float(match.group(1))
        except:
            pass
        return None

    def extract_reviews_count(self) -> Optional[int]:
        """Extract number of reviews"""
        try:
            elem = self.driver.find_element(
                By.CSS_SELECTOR, "span#acrCustomerReviewText"
            )
            text = elem.text.strip()
            match = re.search(r"([\d,]+)", text)
            if match:
                return int(match.group(1).replace(",", ""))
        except:
            pass
        return None

    def extract_bullet_points(self) -> str:
        """Extract bullet points"""
        try:
            bullets = []
            elements = self.driver.find_elements(
                By.CSS_SELECTOR, "#feature-bullets ul li span.a-list-item"
            )
            for elem in elements[:5]:
                text = elem.text.strip()
                if text and len(text) > 10:
                    bullets.append(text)
            return " | ".join(bullets) if bullets else ""
        except:
            return ""

    def extract_best_sellers_rank(self) -> Optional[str]:
        """Extract Best Sellers Rank (first rank)"""
        try:
            # Look for BSR table
            bsr_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "th.prodDetSectionEntry"
            )

            for th_elem in bsr_elements:
                if "Best Sellers Rank" in th_elem.text:
                    # Found header, look for data in next td
                    parent_row = th_elem.find_element(By.XPATH, "..")
                    td_elem = parent_row.find_element(By.TAG_NAME, "td")

                    # Extract first rank (e.g., "#1 in Home & Kitchen")
                    first_item = td_elem.find_element(
                        By.CSS_SELECTOR, "ul li:first-child span"
                    )
                    rank_text = first_item.text.strip()

                    # Extract only "#1 in Home & Kitchen" without "See Top 100" link
                    rank_match = re.search(r"#(\d+)\s+in\s+([^(]+)", rank_text)
                    if rank_match:
                        rank_number = rank_match.group(1)
                        category = rank_match.group(2).strip()
                        result = f"#{rank_number} in {category}"
                        logger.info(f"BSR: {result}")
                        return result

                    # If regex didn't work, return as is
                    return rank_text.split("(")[0].strip()

            # Alternative method via ID
            try:
                bsr_elem = self.driver.find_element(
                    By.ID, "productDetails_detailBullets_sections1"
                )
                spans = bsr_elem.find_elements(By.CSS_SELECTOR, "span")
                for span in spans:
                    text = span.text.strip()
                    if text.startswith("#") and "in" in text:
                        return text.split("(")[0].strip()
            except:
                pass

        except Exception as e:
            logger.debug(f"BSR extraction failed: {e}")

        return None

    def get_product_details(self, asin: str) -> dict:
        """Get detailed product data"""
        url = f"https://www.amazon.com/dp/{asin}"
        details = {}

        try:
            logger.info(f"Fetching details for ASIN: {asin}")
            self.driver.get(url)

            # Title
            try:
                title_elem = self.driver.find_element(By.ID, "productTitle")
                details["title"] = title_elem.text.strip()
                logger.info(f"Title: {details['title'][:60]}...")
            except:
                details["title"] = f"Product {asin}"
                logger.warning("Title not found")

            # Price
            price, currency = self.price_extractor.get_price()
            details["price"] = price
            details["currency"] = currency

            # List price (discount)
            try:
                elem = self.driver.find_element(
                    By.CSS_SELECTOR, "span.a-price.a-text-price span.a-offscreen"
                )
                list_price, _ = self.price_extractor.extract_price_value(
                    elem.text.strip()
                )
                if list_price and list_price > 0 and price > 0:
                    details["list_price"] = list_price
                    discount = ((list_price - price) / list_price) * 100
                    details["discount_percent"] = round(discount, 2)
                    logger.info(f"Discount: {details['discount_percent']}%")
            except:
                pass

            # Rating
            rating = self.extract_rating()
            if rating:
                details["rating"] = rating
                logger.info(f"Rating: {rating}")

            # Reviews
            reviews = self.extract_reviews_count()
            if reviews:
                details["reviews_count"] = reviews
                logger.info(f"Reviews: {reviews}")

            # Bullet points
            bullets = self.extract_bullet_points()
            if bullets:
                details["bullet_points"] = bullets
                logger.info(f"Bullets: {len(bullets.split('|'))} items")

            # Best Sellers Rank
            bsr = self.extract_best_sellers_rank()
            if bsr:
                details["best_sellers_rank"] = bsr

            # Image
            try:
                img = self.driver.find_element(By.ID, "landingImage")
                details["main_image_url"] = img.get_attribute("src")
                logger.info("Image found")
            except:
                pass

            # Prime
            try:
                self.driver.find_element(By.CSS_SELECTOR, "i.a-icon-prime")
                details["is_prime"] = True
                logger.info("Prime: Yes")
            except:
                details["is_prime"] = False

            return details

        except Exception as e:
            logger.error(f"Error getting details for {asin}: {e}")
            return details

    def scrape_top_products(
        self, category_url: str, max_products: int = 5
    ) -> List[ProductModel]:
        """Main scraping function"""
        products = []

        try:
            logger.info(f"Loading category: {category_url}")
            self.driver.get(category_url)
            self.wait.until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[data-asin]"))
            )
            time.sleep(random.uniform(3, 5))

            # Scroll the page
            for i in range(3):
                self.driver.execute_script("window.scrollBy(0, 500);")
                time.sleep(random.uniform(1, 2))

            # Collect ASINs
            elements = self.driver.find_elements(
                By.CSS_SELECTOR, 'div[data-asin]:not([data-asin=""])'
            )
            logger.info(f"Found {len(elements)} products on page")

            asins = []
            for elem in elements[: max_products * 2]:
                try:
                    asin = elem.get_attribute("data-asin")
                    if asin and asin.strip() and asin not in asins:
                        asins.append(asin)
                        if len(asins) >= max_products:
                            break
                except:
                    continue

            logger.info(f"Collected {len(asins)} ASINs to process")

            # Process products
            for rank, asin in enumerate(asins, 1):
                try:
                    logger.info(f"\n{'='*60}")
                    logger.info(f"Processing product #{rank}/{len(asins)}")
                    logger.info(f"{'='*60}")

                    details = self.get_product_details(asin)

                    if not details or "title" not in details:
                        logger.warning(f"Skipping {asin}")
                        continue

                    product = ProductModel(
                        asin=asin,
                        title=details.get("title", "N/A"),
                        rank=rank,
                        price=details.get("price", 0.0),
                        currency=details.get("currency", "$"),
                        list_price=details.get("list_price"),
                        discount_percent=details.get("discount_percent"),
                        rating=details.get("rating"),
                        reviews_count=details.get("reviews_count"),
                        is_prime=details.get("is_prime", False),
                        best_sellers_rank=details.get("best_sellers_rank"),
                        bullet_points=details.get("bullet_points", ""),
                        main_image_url=details.get("main_image_url"),
                    )

                    self.db_manager.save_product(product)
                    products.append(product)

                    logger.info(
                        f"Product #{rank} completed: {product.currency}{product.price}"
                    )

                    # Delay
                    time.sleep(random.uniform(3, 5))

                except Exception as e:
                    logger.error(f"Error processing #{rank} (ASIN: {asin}): {e}")
                    continue

            logger.info(f"\n{'='*60}")
            logger.info(f"Successfully scraped {len(products)} products")
            logger.info(f"{'='*60}\n")

            return products

        except Exception as e:
            logger.error(f"Scraping failed: {e}")
            return products


# ===== Main Execution =====
def main():
    if len(sys.argv) < 2:
        print("Usage: python scraper.py <amazon_category_url>")
        print("\nExample:")
        print(
            "python scraper.py https://www.amazon.com/Best-Sellers-Home-Kitchen/zgbs/home-garden"
        )
        sys.exit(1)

    category_url = sys.argv[1]

    logger.info("=" * 60)
    logger.info("Amazon Products Scraper")
    logger.info("=" * 60)

    db_manager = DatabaseManager()
    scraper = AmazonScraper(db_manager)

    try:
        scraper.init_driver()
        products = scraper.scrape_top_products(category_url, max_products=5)

        if products:
            print("\n" + "=" * 60)
            print("RESULTS SUMMARY")
            print("=" * 60)
            for p in products:
                print(f"\n{p.rank}. {p.title[:60]}...")
                print(f"   ASIN: {p.asin}")
                print(f"   Price: {p.currency}{p.price}")
                if p.list_price:
                    print(
                        f"   List Price: {p.currency}{p.list_price} (Save {p.discount_percent}%)"
                    )
                if p.rating:
                    print(f"   Rating: {p.rating}/5.0 ({p.reviews_count} reviews)")
                print(f"   Prime: {'Yes' if p.is_prime else 'No'}")
        else:
            print("\nNo products were scraped")

    except KeyboardInterrupt:
        logger.info("\nScraping interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
    finally:
        scraper.close_driver()
        logger.info("\nScraper finished")


if __name__ == "__main__":
    main()
