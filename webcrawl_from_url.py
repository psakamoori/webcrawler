import requests
from bs4 import BeautifulSoup
#import pdfkit
import os

def fetch_content(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure we notice bad responses
        return response.content

    except requests.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None


def save_as_pdf(content, filename):
    try:
        pdfkit.from_string(content, filename)

    except Exception as e:
        print(f"Error saving PDF {filename}: {e}")

def save_as_webpage(content, filename):

    try:
        with open(filename, 'w', encoding='utf-8') as file:
            file.write(content)
    except Exception as e:
        print(f"Error saving HTML {filename}: {e}")

def extract_links(content, base_url):
    soup = BeautifulSoup(content, 'html.parser')
    links = set()

    for a_tag in soup.find_all('a', href=True):
        href = a_tag['href']
        if href.startswith('/'):
            href = base_url + href
        elif not href.startswith('http'):
            continue
    #if 'paint-and-supplies' in href:
        links.add(href)
    return links
    
def crawl_and_save(url, visited=None):
    if visited is None:
        visited = set()
    if url in visited:
        return
    visited.add(url)
    content = fetch_content(url)
    if content is None:
        return
    content_str = BeautifulSoup(content, 'html.parser').prettify()
    dataset_dir = "./dataset/paint"
    dataset_dir_pdf = "./dataset/paint/pdf"
    # Save the main page content
    save_as_pdf(content_str, f"i{dataset_dir_pdf}/{url.replace('https://', '').replace('/', '_')}.pdf")
    save_as_webpage(content_str, f"{dataset_dir}/{url.replace('https://', '').replace('/', '_')}.html")

    links = extract_links(content, url)

    for link in links:
        if 'paint-and-supplies' in link:
            crawl_and_save(link, visited)

# Start crawling from the main URL
start_url = 'https://www.acehardware.com/departments/paint-and-supplies'

crawl_and_save(start_url)
