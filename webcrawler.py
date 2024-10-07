import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import time
from urllib.parse import urlparse, urljoin
import os
import pdfkit  # Import pdfkit for saving as PDF

# Set environment variable for XDG_RUNTIME_DIR
os.environ['XDG_RUNTIME_DIR'] = '/tmp'  # or any other valid path

# Create the dataset/dp directory if it doesn't exist
dataset_directory = './dataset/html'
os.makedirs(dataset_directory, exist_ok=True)

visited_urls = set()  # Track visited URLs to avoid duplication

def get_dynamic_content(url):
    """Fetch dynamic content from a webpage using Selenium."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run Chrome in headless mode
    chrome_options.add_argument("--no-sandbox")  # Bypass OS security model
    chrome_options.add_argument("--disable-dev-shm-usage")  # Overcome limited resource issues
    chrome_options.add_argument("--disable-gpu")  # Disable GPU hardware acceleration

    # Set the location of the ChromeDriver executable
    service = Service('/usr/local/bin/chromedriver')

    # Initialize the WebDriver with Chrome options
    driver = webdriver.Chrome(service=service, options=chrome_options)

    driver.get(url)
    time.sleep(10)  # Wait for dynamic content to load (increased time)

    # Get the page source after the dynamic content has loaded
    page_source = driver.page_source
    driver.quit()

    return page_source

def generate_filename(url, extension):
    """Generate a filename from the URL and save it in the dataset/dp directory."""
    parsed_url = urlparse(url)
    filename = f"{parsed_url.netloc.replace('.', '_')}_{parsed_url.path.replace('/', '_').strip('_')}.{extension}"
    return os.path.join(dataset_directory, filename)

def save_full_webpage(content, filename):
    """Save the full HTML content of a webpage."""
    with open(filename, 'w', encoding='utf-8') as file:
        file.write(content)

from multiprocessing import Process

def save_pdf_process(content, filename, options):
    """Sub-process for saving PDF to avoid hanging."""
    try:
        pdfkit.from_string(content, filename, options=options)
    except Exception as e:
        print(f"Error saving PDF {filename}: {e}")

def save_as_pdf(content, filename, timeout=30):
    """Convert HTML content to PDF with a timeout."""
    try:
        options = {
            'enable-local-file-access': True,
            'no-stop-slow-scripts': True,
            'load-error-handling': 'ignore',
            'javascript-delay': '5000',
            'debug-javascript': True,
        }

        p = Process(target=save_pdf_process, args=(content, filename, options))
        p.start()

        p.join(timeout)

        if p.is_alive():
            print(f"Terminating the process due to timeout ({timeout} seconds)")
            p.terminate()
            p.join()
            raise TimeoutError(f"PDF generation exceeded the time limit of {timeout} seconds")

        print(f"Saved PDF: {filename}")

    except TimeoutError as te:
        print(te)
    except Exception as e:
        print(f"Error saving PDF {filename}: {e}")

def download_resource(resource_url, base_url):
    """Download a CSS, JS, or image resource."""
    try:
        if "googletagmanager.com" in resource_url or "contentsquare.net" in resource_url:
            #print(f"Skipping resource: {resource_url}")
            return None
        
        resource_response = requests.get(resource_url)
        resource_response.raise_for_status()
        resource_path = urlparse(resource_url).path
        resource_filename = os.path.basename(resource_path)

        resource_directory = os.path.join(dataset_directory, 'resources')
        os.makedirs(resource_directory, exist_ok=True)

        resource_save_path = os.path.join(resource_directory, resource_filename)
        with open(resource_save_path, 'wb') as resource_file:
            resource_file.write(resource_response.content)

        return resource_save_path

    except Exception as e:
        #print(f"Error downloading resource {resource_url}: {e}")
        return None

def extract_links_and_resources(content, base_url):
    """Extract links and resources from HTML content."""
    soup = BeautifulSoup(content, 'html.parser')
    links = set()
    resources = []

    # Extract anchor links
    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/'):
            href = urljoin(base_url, href)
        elif not href.startswith('http'):
            continue
        links.add(href)

    # Extract CSS and JS links
    for link_tag in soup.find_all('link', href=True):
        resource_url = urljoin(base_url, link_tag['href'])
        if link_tag.get('rel') == ['stylesheet']:
            resources.append(download_resource(resource_url, base_url))

    for script_tag in soup.find_all('script', src=True):
        resource_url = urljoin(base_url, script_tag['src'])
        resources.append(download_resource(resource_url, base_url))

    # Extract images
    for img_tag in soup.find_all('img', src=True):
        resource_url = urljoin(base_url, img_tag['src'])
        resources.append(download_resource(resource_url, base_url))

    return links, resources

def save_complete_webpage(url):
    """Fetch and save the complete webpage as both HTML and PDF."""
    html_content = get_dynamic_content(url)

    html_filename = generate_filename(url, 'html')
    pdf_filename = generate_filename(url, 'pdf')

    save_full_webpage(html_content, html_filename)
    #save_as_pdf(html_content, pdf_filename)

    links, resources = extract_links_and_resources(html_content, url)
    
    with open(html_filename, 'r+', encoding='utf-8') as file:
        content = file.read()
        for resource in resources:
            if resource:
                local_resource_url = os.path.join('resources', os.path.basename(resource))
                content = content.replace(resource, local_resource_url)
        file.seek(0)
        file.write(content)
        file.truncate()

    print(f"Complete webpage saved as {html_filename} and {pdf_filename}")

def scrape_parent_and_subpages(parent_url, depth=0, max_depth=3):
    """Recursively scrape the parent URL and all its sub-pages, ensuring 'paint-and-supplies' is in the URL."""
    if parent_url in visited_urls:
        return
    if 'paint-and-supplies' not in parent_url:
        return
    if depth > max_depth:
        return

    visited_urls.add(parent_url)
    
    print(f"Processing page: {parent_url} (Depth: {depth})")
    save_complete_webpage(parent_url)

    parent_content = get_dynamic_content(parent_url)
    subpage_links, _ = extract_links_and_resources(parent_content, parent_url)

    for link in subpage_links:
        if link not in visited_urls and 'paint-and-supplies' in link:
            scrape_parent_and_subpages(link, depth + 1, max_depth)

# Example usage
parent_url = "https://www.acehardware.com/departments/paint-and-supplies"
scrape_parent_and_subpages(parent_url)
