# CLAUDE.md

## Project Overview

28hseCrawler is a Python web scraper that extracts residential property listings from 28hse.com (a Hong Kong real estate website) and exports the data to Excel format.

## Dependencies

### Python Dependencies
Required Python packages (install via `pip install`):
- `selenium` - Browser automation for web scraping
- `openpyxl` - Excel file creation and manipulation
- `argparse` - Command-line argument parsing (built into Python standard library)

Note: This project does not currently have a requirements.txt file. You may need to install dependencies manually.

### External Tools
- **agent-browser** - Fast browser automation CLI for testing HTML structure and investigating website changes
  - Install: `npm install -g agent-browser` or `brew install agent-browser`
  - Used for: HTML structure investigation, selector testing, and website debugging
  - Advantages over Selenium: Faster, more reliable, better for exploration and testing

## Running the Crawler

```bash
# Basic usage (scrapes pages 1-20 by default)
python 28hseCrawler.py

# Scrape only page 1
python 28hseCrawler.py --pages 1

# Scrape pages 1-2
python 28hseCrawler.py --pages 1-2

# Scrape pages 4-5
python 28hseCrawler.py --pages 4-5

# See help
python 28hseCrawler.py --help
```

**Note:** The crawler requires Chrome and ChromeDriver to be installed. On macOS, install ChromeDriver via `brew install chromedriver`. The script uses the default ChromeDriver path.

## Architecture

### Main Components

**`28hseCrawler.py`** - Single-file application with three main functions:

1. **`parse_pages_arg(pages_arg)`** - Parses command-line page argument:
   - Accepts single page: `"1"` → `(1, 1)`
   - Accepts range: `"1-2"` → `(1, 2)`, `"4-5"` → `(4, 5)`
   - Returns tuple of (start_page, end_page)

2. **`get_data(start_page, end_page)`** - Handles web scraping logic:
   - Initializes Chrome WebDriver and navigates to 28hse.com/buy
   - Clicks filters: "新界" (New Territories), "住宅" (Residential)
   - Iterates through specified page range using direct URL navigation (`/page-1`, `/page-2`, etc.)
   - Extracts property data from each listing element with class `property_item`
   - Returns a 2D list with extracted data

3. **`write_to_excel(plist)`** - Exports data to Excel:
   - Creates workbook and appends data rows
   - Saves the output to `28hse_data.xlsx` in the script directory

### Data Extraction Schema

Each row contains: `['District', 'Cat', 'Reported Size', 'Actual Size', '$', 'LandLord']`

The scraper uses defensive programming patterns - if any XPath element is not found, it inserts "NA" instead of failing.


**Remaining Issues**:
1. **Hardcoded filters**: District, category, and price range filters are hardcoded to specific values ("新界", "住宅")
2. **Selector stability**: New selectors may change if website structure is updated again (mitigated by using URL navigation for pagination)


### Investigation Checklist

When the scraper fails:
1. ✅ **Check website accessibility**: `agent-browser open https://www.28hse.com/buy`
2. ✅ **Verify page structure**: `agent-browser screenshot /tmp/debug.png`
3. ✅ **Test selectors**: `agent-browser get html "<selector>"`
4. ✅ **Check element visibility**: `agent-browser is visible "<selector>"`
5. ✅ **Try direct navigation**: `agent-browser goto "https://www.28hse.com/buy/page-2"`
6. ✅ **Review HTML changes**: Compare current HTML with documented selectors
7. ✅ **Update selectors**: Modify Selenium code with new selectors
8. ✅ **Test incrementally**: Run script and monitor output

### Agent-Browser Usage

Agent-browser is the preferred tool for investigating HTML structure changes and testing selectors:

```bash
# Open the website
agent-browser open https://www.28hse.com/buy --headed

# Take an accessibility tree snapshot (shows all interactive elements)
agent-browser snapshot -i

# Take a screenshot
agent-browser screenshot /tmp/28hse_screenshot.png

# Get text content of an element
agent-browser get text <selector>

# Check if element exists
agent-browser is visible <selector>

# Close browser
agent-browser close
```

**Example workflow**:
1. Navigate to the target page
2. Take snapshot to see interactive elements
3. Test selectors from the old code
4. Identify new selectors that match current HTML structure
5. Update Selenium code with new selectors

**Debugging Process Example (Pagination Fix 2026-05-10)**:
```bash
# 1. Open the website
agent-browser open https://www.28hse.com/buy

# 2. Take screenshot to see current state
agent-browser screenshot /tmp/28hse_current.png

# 3. Check pagination structure
agent-browser get html ".pagination"

# 4. Test visibility of pagination links
agent-browser is visible "a[rel='next']"  # Returned: false
agent-browser is visible ".pagination a.item"  # Returned: true

# 5. Test direct URL navigation
agent-browser goto "https://www.28hse.com/buy/page-2"
agent-browser get text ".pagination a.item.active"  # Returned: 2

# 6. Close browser
agent-browser close
```



### HTML Structure Targeted (Updated 2026-05-10)

**Filter Navigation**:
- **Menu container**: `#mainMenuDiv`
- **District filter**: Click "新界" link, then "不限" for all sub-regions
- **Category filter**: Click "住宅" link, then "不限" for all sub-categories

**Property Listings** (Final structure - 2026-05-10):
```
div.item.property_item (parent container)
├── div.description
│   ├── .district_area.wHoverBlue a[0] → District
│   ├── .district_area.wHoverBlue a[1] → Building/Category
│   ├── .areaUnitPrice div:contains('建築面積') → Reported Size
│   ├── .areaUnitPrice div:contains('實用面積') → Actual Size
│   └── .companyName → Landlord/Agency ✅
└── div.extra
    └── .ui.right.floated.red.large.label → Price ✅
```

**Selectors**:
- **Listing container**: `div.item.property_item` (updated from `.description` to access price)
- **Description container**: `div.description` (nested within property_item)
- **District**: First link in `.district_area.wHoverBlue a`
- **Building/Category**: Second link in `.district_area.wHoverBlue a`
- **Reported Size**: Element containing text "建築面積"
- **Actual Size**: Element containing text "實用面積"
- **Price**: `.extra .ui.right.floated.red.large.label` ✅ **FIXED** (was `.priceDesc`, didn't exist in description)
- **Landlord**: `.companyName` ✅ **FIXED** (was `.landlord_2`, didn't exist)

**Pagination** (Updated 2026-05-10):
- **Method**: Direct URL navigation instead of clicking links
- **URL Pattern**: `https://www.28hse.com/buy/page-{n}` (where n = 1, 2, 3, ...)
- **Page 1**: `https://www.28hse.com/buy` (no page suffix)
- **Subsequent pages**: Append `/page-2`, `/page-3`, etc.
- **Why this approach**: Pagination links ("下一頁") exist in HTML but are not visible/clickable via Selenium
- **Pagination structure found**:
  - HTML contains: `<a href="https://www.28hse.com/buy/page-2" rel="next">下一頁</a>`
  - Links are in `.pagination_hi` div but not visible to automation
  - Numbered page links exist: `.pagination a.item[attr1='2']` but also not functional via clicking

