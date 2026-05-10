from selenium import webdriver

try:
    browser = webdriver.Chrome()
    print("✓ ChromeDriver works!")
    print(f"Browser title: {browser.title}")
    browser.quit()
except Exception as e:
    print(f"✗ Error: {e}")
