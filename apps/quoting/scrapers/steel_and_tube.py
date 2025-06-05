# quoting/scrapers/steel_and_tube.py
import time
import re
import requests
from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from .base import BaseScraper


class SteelAndTubeScraper(BaseScraper):
    """Steel & Tube specific scraper implementation"""

    def login(self):
        """Login to Steel & Tube portal"""
        username, password = self.get_credentials()

        if not username or not password:
            self.logger.error("Credentials not found")
            return False

        try:
            login_url = self.supplier.login_url or self.supplier.base_url
            self.driver.get(login_url)

            username_field = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable((By.ID, "UserName"))
            )
            username_field.clear()
            username_field.send_keys(username)

            password_field = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.ID, "Password"))
            )
            password_field.clear()
            password_field.send_keys(password)

            login_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, "button.btn-medium.btn-login")
                )
            )
            login_button.click()

            time.sleep(2)
            WebDriverWait(self.driver, 15).until(
                EC.invisibility_of_element_located((By.ID, "UserName"))
            )

            self.logger.info("Login successful")
            return True

        except Exception as e:
            self.logger.error(f"Login failed: {e}")
            return False

    def get_product_urls(self):
        """Get product URLs from sitemap"""
        if not self.supplier.sitemap_url:
            return []

        try:
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(
                self.supplier.sitemap_url, headers=headers, timeout=15
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "xml")
            url_entries = soup.find_all("url")

            product_urls = []

            # Use URL patterns from supplier config, fallback to defaults
            url_patterns = self.supplier.url_patterns or [
                f"{self.supplier.base_url}stainless/",
                f"{self.supplier.base_url}steel/",
            ]

            for url_entry in url_entries:
                loc_tag = url_entry.find("loc")
                if not loc_tag:
                    continue

                url = loc_tag.get_text(strip=True)

                # Check if it matches our patterns and is a product URL
                if any(url.startswith(pattern) for pattern in url_patterns):
                    if self.is_product_url(url):
                        product_urls.append(url)

            self.logger.info(f"Found {len(product_urls)} product URLs")
            return product_urls

        except Exception as e:
            self.logger.error(f"Error fetching product URLs: {e}")
            return []

    def is_product_url(self, url):
        """Check if URL is a product page"""
        return bool(re.search(r"p\d{7}", url) or re.search(r"-p\d+", url))

    def scrape_product(self, url):
        """Scrape a single product page"""
        self.driver.get(url)
        time.sleep(3)

        # Check if login required
        if "login" in self.driver.current_url.lower():
            if not self.login():
                return []
            self.driver.get(url)
            time.sleep(2)

        try:
            # Check for page not found
            if "The requested page cannot be found" in self.driver.page_source:
                return [self.create_page_not_found_record(url)]

            # Extract basic product info
            product_name = self.extract_text_by_selector(
                'h1[itemprop="name"]', default="N/A"
            )
            item_no = self.extract_text_by_selector(
                'span[itemprop="productID sku"]', default="N/A"
            )
            description = self.extract_description()
            specifications = self.extract_specifications()
            price_unit = self.extract_price_unit()

            # Extract variants
            variants_data = self.extract_variants(
                url, product_name, item_no, description, specifications, price_unit
            )
            return variants_data

        except Exception as e:
            self.logger.error(f"Error scraping product {url}: {e}")
            return []

    def extract_text_by_selector(self, selector, default="N/A"):
        """Helper to extract text by CSS selector"""
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            return element.text.strip() if element else default
        except:
            return default

    def extract_description(self):
        """Extract product description"""
        try:
            description_div = self.driver.find_element(
                By.CSS_SELECTOR, 'div[itemprop="description"]'
            )
            if description_div:
                try:
                    inner_div = description_div.find_element(By.CLASS_NAME, "fr-view")
                    return inner_div.text.strip()
                except:
                    return description_div.text.strip()
        except:
            pass
        return "N/A"

    def extract_specifications(self):
        """Extract product specifications"""
        try:
            spec_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "#specifications table.gvi-name-value tr"
            )
            spec_parts = []
            for row in spec_elements:
                try:
                    name_cell = row.find_element(By.CLASS_NAME, "name")
                    value_cell = row.find_element(By.CLASS_NAME, "value")
                    spec_parts.append(
                        f"{name_cell.text.strip()}: {value_cell.text.strip()}"
                    )
                except:
                    continue
            return "; ".join(spec_parts) if spec_parts else "N/A"
        except:
            return "N/A"

    def extract_price_unit(self):
        """Extract price unit"""
        try:
            price_unit_element = self.driver.find_element(
                By.CSS_SELECTOR, ".after-prices .lbl-price-per"
            )
            return price_unit_element.text.strip()
        except:
            try:
                after_prices = self.driver.find_element(By.CLASS_NAME, "after-prices")
                return after_prices.text.strip()
            except:
                return "N/A"

    def extract_variants(
        self, url, product_name, item_no, description, specifications, price_unit
    ):
        """Extract product variants"""
        variants_data = []

        try:
            variant_select_element = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "variantId"))
            )

            options_data = self.driver.execute_script(
                """
                var select = document.getElementById('variantId');
                var options = [];
                for (var i = 0; i < select.options.length; i++) {
                    var option = select.options[i];
                    if (option.value && option.value.toUpperCase() !== 'N/A') {
                        options.push({
                            value: option.value,
                            text: option.text.trim(),
                            price: option.getAttribute('data-price'),
                            inventory: option.getAttribute('data-inventory')
                        });
                    }
                }
                return options;
            """
            )

            for option_data in options_data:
                variant_id = option_data["value"]
                price_text = option_data["price"]
                inventory_text = option_data["inventory"]
                raw_text = option_data["text"]

                price = None
                if price_text:
                    try:
                        price = float(
                            price_text.replace("$", "").replace(",", "").strip()
                        )
                    except:
                        pass

                stock = 0
                if inventory_text and inventory_text.isdigit():
                    stock = int(inventory_text)

                # Parse length from option text
                variant_length = None
                if raw_text:
                    cleaned_text = re.sub(r"\s+", " ", raw_text).strip()
                    length_match = re.search(r"(\d+(?:\.\d+)?)", cleaned_text)
                    if length_match:
                        variant_length = length_match.group(1)
                    else:
                        variant_length = cleaned_text

                variants_data.append(
                    {
                        "product_name": product_name,
                        "item_no": item_no,
                        "description": description,
                        "specifications": specifications,
                        "variant_id": variant_id,
                        "variant_width": None,
                        "variant_length": variant_length,
                        "variant_price": price,
                        "price_unit": price_unit,
                        "variant_available_stock": stock,
                        "url": url,
                    }
                )

            return variants_data

        except Exception as e:
            self.logger.error(f"Could not extract variants: {e}")
            return []

    def create_page_not_found_record(self, url):
        """Create a record for page not found"""
        return {
            "product_name": "Page Not Found",
            "item_no": "N/A",
            "description": "N/A",
            "specifications": "N/A",
            "variant_id": "N/A",
            "variant_width": None,
            "variant_length": None,
            "variant_price": None,
            "price_unit": "N/A",
            "variant_available_stock": None,
            "url": url,
        }
