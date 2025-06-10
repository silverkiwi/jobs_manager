# quoting/scrapers/base.py
import os
import logging
from abc import ABC, abstractmethod
from django.utils import timezone
from selenium import webdriver
from selenium.webdriver.chrome.options import Options


class BaseScraper(ABC):
    """Base class for all supplier scrapers"""

    def __init__(self, supplier, limit=None, force=False):
        self.supplier = supplier
        self.limit = limit
        self.force = force
        self.driver = None
        self.logger = logging.getLogger(
            f'scraper.{supplier.name.lower().replace(" ", "_")}'
        )

    def setup_driver(self):
        """Setup Selenium WebDriver - common for all scrapers"""
        chrome_options = Options()
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-extensions")
        user_agent = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        )
        chrome_options.add_argument(f"user-agent={user_agent}")

        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver

    def get_credentials(self):
        """Get credentials from environment variables"""
        return self.supplier.get_credentials()

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            self.driver.quit()

    @abstractmethod
    def get_product_urls(self):
        """Get list of product URLs to scrape"""
        pass

    @abstractmethod
    def scrape_product(self, url):
        """Scrape a single product page"""
        pass

    @abstractmethod
    def login(self):
        """Handle login process"""
        pass

    def run(self):
        """Main scraper execution"""
        from apps.quoting.models import ScrapeJob, SupplierProduct

        # Create scrape job
        job = ScrapeJob.objects.create(
            supplier=self.supplier, status="running", started_at=timezone.now()
        )

        try:
            self.setup_driver()
            login_success = self.login()

            if not login_success:
                self.logger.warning("Login failed, continuing without login")

            # Get URLs to scrape
            product_urls = self.get_product_urls()

            if not product_urls:
                job.status = "failed"
                job.error_message = "No product URLs found"
                job.completed_at = timezone.now()
                job.save()
                return

            # Filter existing URLs if not forcing
            if not self.force:
                existing_urls = set(
                    SupplierProduct.objects.filter(supplier=self.supplier).values_list(
                        "url", flat=True
                    )
                )
                product_urls = [url for url in product_urls if url not in existing_urls]

            # Apply limit
            if self.limit:
                product_urls = product_urls[: self.limit]

            self.logger.info(
                f"Processing {len(product_urls)} URLs for {self.supplier.name}"
            )

            successful = 0
            failed = 0
            batch_data = []

            for i, url in enumerate(product_urls, 1):
                try:
                    self.logger.info(f"Processing {i}/{len(product_urls)}: {url}")
                    products_data = self.scrape_product(url)

                    if products_data:
                        batch_data.extend(products_data)
                        successful += 1
                    else:
                        failed += 1

                    # Save in batches
                    if len(batch_data) >= 50:
                        self.save_products(batch_data)
                        batch_data = []

                except Exception as e:
                    self.logger.error(f"Error processing {url}: {e}")
                    failed += 1

            # Save remaining data
            if batch_data:
                self.save_products(batch_data)

            # Update job status
            job.status = "completed"
            job.products_scraped = successful
            job.products_failed = failed
            job.completed_at = timezone.now()
            job.save()

            self.logger.info(f"Completed: {successful} successful, {failed} failed")

        except Exception as e:
            job.status = "failed"
            job.error_message = str(e)
            job.completed_at = timezone.now()
            job.save()
            self.logger.error(f"Scraper failed: {e}")
            raise
        finally:
            self.cleanup()

    def save_products(self, products_data):
        """Save products to database"""
        from apps.quoting.models import SupplierProduct, SupplierPriceList

        # Create or get a price list for these products
        price_list, created = SupplierPriceList.objects.get_or_create(
            supplier=self.supplier,
            file_name=f"Scraped Products - {len(products_data)} items",
            defaults={'file_name': f"Scraped Products - {len(products_data)} items"}
        )

        for product_data in products_data:
            try:
                product_data["supplier"] = self.supplier
                product_data["price_list"] = price_list
                
                product, created = SupplierProduct.objects.update_or_create(
                    supplier=self.supplier,
                    variant_id=product_data["variant_id"],
                    url=product_data["url"],
                    defaults=product_data,
                )

            except Exception as e:
                self.logger.error(f"Error saving product: {e}")
