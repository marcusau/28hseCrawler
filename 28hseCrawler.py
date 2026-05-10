import time
import argparse
import re
import yaml
from openpyxl import Workbook
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def parse_pages_arg(pages_arg):
    """
    Parse the --pages argument to extract start and end page numbers.

    Examples:
        "1" -> (1, 1)
        "1-2" -> (1, 2)
        "4-5" -> (4, 5)
    """
    if '-' in pages_arg:
        # Range format: "1-2" or "4-5"
        start, end = pages_arg.split('-')
        return int(start), int(end)
    else:
        # Single page: "1"
        page_num = int(pages_arg)
        return page_num, page_num

def load_config():
    """
    Load configuration from config.yml file.

    Returns:
        dict: Configuration parameters including base_url, transaction_type, district, category
    """
    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        return config
    except FileNotFoundError:
        print("Error: config.yml not found. Please create config.yml with your settings.")
        raise
    except yaml.YAMLError as e:
        print(f"Error parsing config.yml: {e}")
        raise

def get_data(start_page, end_page, config):
    result_list = []
    temp_list = []

    # Construct base URL from config
    base_url_domain = config.get('base_url', 'https://www.28hse.com')
    transaction_type = config.get('transaction_type', 'buy')
    base_url = f'{base_url_domain}/{transaction_type}'

    # Get filter settings from config
    district = config.get('district', '新界')
    category = config.get('category', '住宅')

    browser = webdriver.Chrome()
    browser.get(base_url)
    try:
        temp_list = ['District','Cat','Reported Size','Actual Size','$','Bedrooms','Bathrooms','LandLord','Listing URL']
        result_list.append(temp_list.copy())
        temp_list.clear()

        # Wait for page to load and main menu to be present
        WebDriverWait(browser, 5).until(
            EC.presence_of_element_located((By.ID,"mainMenuDiv"))
            )
        # Click district filter from config
        browser.find_element(By.LINK_TEXT, district).click()
        time.sleep(1)
        # Click "不限" (Any) to show all listings in selected district
        try:
            browser.find_element(By.LINK_TEXT, "不限").click()
        except:
            pass  # If "不限" is not clickable, continue
        time.sleep(1)
        # Click category filter from config
        browser.find_element(By.LINK_TEXT, category).click()
        time.sleep(1)
        # Click "不限" for category if available
        try:
            browser.find_elements(By.LINK_TEXT, "不限")[1].click()
        except:
            pass
        time.sleep(1)
        for page_num in range(start_page, end_page + 1):

            # Construct URL for current page
            if page_num == 1:
                current_url = base_url
            else:
                current_url = f"{base_url}/page-{page_num}"

            # Navigate to the page
            browser.get(current_url)

            # Wait for listings to load - look for description divs which contain property info
            WebDriverWait(browser, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME,"description"))
                )
            time.sleep(2)

            # Find all property listings by looking for property_item containers
            # Each listing is in a property_item div that contains description, price, and other info
            listings = browser.find_elements(By.CSS_SELECTOR, 'div.item.property_item')

            # If no listings found, we've reached the end
            if len(listings) == 0:
                break

            for item in listings:
                # Get the description div within this property_item
                description_div = item.find_elements(By.CSS_SELECTOR, 'div.description')

                if len(description_div) == 0:
                    # Skip this item if no description found
                    continue

                desc = description_div[0]

                # Extract district (first link in district_area)
                if len(desc.find_elements(By.CSS_SELECTOR, '.district_area.wHoverBlue a')) > 0:
                    try:
                        district_links = desc.find_elements(By.CSS_SELECTOR, '.district_area.wHoverBlue a')
                        district = district_links[0].text
                        temp_list.insert(len(temp_list), district)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                # Extract building/category (second link in district_area)
                if len(desc.find_elements(By.CSS_SELECTOR, '.district_area.wHoverBlue a')) > 1:
                    try:
                        district_links = desc.find_elements(By.CSS_SELECTOR, '.district_area.wHoverBlue a')
                        cat = district_links[1].text
                        temp_list.insert(len(temp_list), cat)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                # Extract reported size (建築面積)
                if len(desc.find_elements(By.XPATH, ".//*[contains(text(), '建築面積')]")) > 0:
                    try:
                        report_size = desc.find_element(By.XPATH, ".//*[contains(text(), '建築面積')]").text
                        temp_list.insert(len(temp_list), report_size)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                # Extract actual size (實用面積)
                if len(desc.find_elements(By.XPATH, ".//*[contains(text(), '實用面積')]")) > 0:
                    try:
                        actual_size = desc.find_element(By.XPATH, ".//*[contains(text(), '實用面積')]").text
                        temp_list.insert(len(temp_list), actual_size)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                # Extract price from .extra .ui.right.floated.red.large.label element (within property_item but outside description)
                if len(item.find_elements(By.CSS_SELECTOR, '.extra .ui.right.floated.red.large.label')) > 0:
                    try:
                        sold = item.find_element(By.CSS_SELECTOR, '.extra .ui.right.floated.red.large.label').text
                        temp_list.insert(len(temp_list), sold)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                # Extract bedrooms and bathrooms from .tagLabels .ui.label
                # Format: "3 房 , 1 浴室" (3 bedrooms, 1 bathroom)
                bedrooms = "NA"
                bathrooms = "NA"
                if len(item.find_elements(By.CSS_SELECTOR, '.tagLabels .ui.label')) > 0:
                    try:
                        tag_text = item.find_element(By.CSS_SELECTOR, '.tagLabels .ui.label').text
                        # Parse the text to extract bedroom and bathroom counts
                        # Match patterns like "3 房" or "3房"
                        bedroom_match = re.search(r'(\d+)\s*房', tag_text)
                        if bedroom_match:
                            bedrooms = bedroom_match.group(1)
                        # Match patterns like "1 浴室" or "1浴室"
                        bathroom_match = re.search(r'(\d+)\s*浴室', tag_text)
                        if bathroom_match:
                            bathrooms = bathroom_match.group(1)
                    except:
                        pass  # Keep default "NA" values
                temp_list.insert(len(temp_list), bedrooms)
                temp_list.insert(len(temp_list), bathrooms)

                # Extract landlord/agent info from .companyName (within description div)
                if len(desc.find_elements(By.CSS_SELECTOR, '.companyName')) > 0:
                    try:
                        land_lord = desc.find_element(By.CSS_SELECTOR, '.companyName').text
                        temp_list.insert(len(temp_list), land_lord)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                # Extract listing URL from a.detail_page link
                if len(item.find_elements(By.CSS_SELECTOR, 'a.detail_page')) > 0:
                    try:
                        listing_url = item.find_element(By.CSS_SELECTOR, 'a.detail_page').get_attribute('href')
                        temp_list.insert(len(temp_list), listing_url)
                    except:
                        temp_list.insert(len(temp_list), "NA")
                else:
                    temp_list.insert(len(temp_list), "NA")

                result_list.append(temp_list.copy())
                temp_list.clear()

            # Check if we should continue to next page
            if len(listings) == 0:
                break

    finally:
        browser.quit()
        
    return result_list

def write_to_excel(plist):
    wb = Workbook()

    # grab the active worksheet
    ws = wb.active
    
    for i in plist:
        ws.append(i)

    # Save the file
    wb.save('28hse_data.xlsx')


if __name__ == '__main__':
    # Set up argument parsing
    parser = argparse.ArgumentParser(
        description='Scrape property listings from 28hse.com',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python 28hseCrawler.py --pages 1       # Scrape only page 1
  python 28hseCrawler.py --pages 1-2     # Scrape pages 1-2
  python 28hseCrawler.py --pages 4-5     # Scrape pages 4-5

Configuration:
  Edit config.yml to change transaction type, district, and category filters.
        """
    )
    parser.add_argument(
        '--pages',
        type=str,
        default='1-20',
        help='Page range to scrape (e.g., "1" for single page, "1-2" for range, "4-5" for specific pages). Default: "1-20"'
    )

    args = parser.parse_args()

    # Load configuration from config.yml
    try:
        config = load_config()
        print(f"Loaded config: {config['base_url']} | {config['transaction_type'].upper()} | District: {config['district']} | Category: {config['category']}")
    except Exception as e:
        print(f"Failed to load config: {e}")
        exit(1)

    # Parse the pages argument
    start_page, end_page = parse_pages_arg(args.pages)

    print(f"Scraping pages {start_page} to {end_page}...")

    result_list = get_data(start_page, end_page, config)
    write_to_excel(result_list)

    print(f"Successfully scraped {len(result_list) - 1} listings to 28hse_data.xlsx")
