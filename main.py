import requests
import os
from bs4 import BeautifulSoup
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, urljoin
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry

def grab_code(url, timeout=5, max_retries=3, backoff_factor=0.3):
    session = requests.Session()
    retries = Retry(total=max_retries, backoff_factor=backoff_factor, status_forcelist=[500, 502, 503, 504])
    session.mount('http://', HTTPAdapter(max_retries=retries))
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    try:
        response = session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    except requests.exceptions.RequestException as e:
        print(f"Error fetching {url}: {e}")
        return None

def is_internal_link(link, base_domain):
    link_parsed = urlparse(link)
    return base_domain in link_parsed.netloc

def code_crawler(start_url, website_dir, base_domain, visited=None):
    if visited is None:
        visited = set()
    
    if start_url in visited:
        return
    visited.add(start_url)

    page_content = grab_code(start_url)
    if page_content is None:
        return

    soup = BeautifulSoup(page_content, 'html.parser')
    
    for link in soup.find_all('a', href=True):
        href = link['href']
        href = urljoin(start_url, href)
        if not is_internal_link(href, base_domain):
            continue
        if href not in visited:
            code_crawler(href, website_dir, base_domain, visited)
        
        # Update the href attribute to point to the HTML file
        relative_path = save_page(href, website_dir, base_domain, visited)
        if relative_path:
            link['href'] = f"/{relative_path}"
    
    save_page(start_url, website_dir, base_domain, visited, soup)

def save_page(url, website_dir, base_domain, visited, soup=None):
    parsed_url = urlparse(url)
    path = parsed_url.path if parsed_url.path else '/'
    
    # Ensure all links are saved as .html files
    if not path.endswith('.html'):
        if path.endswith('/'):
            path = os.path.join(path, 'index.html')
        else:
            path += '.html'
    
    save_path = os.path.join(website_dir, path.lstrip('/'))
    save_dir = os.path.dirname(save_path)
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    if soup is None:
        page_content = grab_code(url)
        if page_content is None:
            return
        soup = BeautifulSoup(page_content, 'html.parser')
    
    with open(save_path, 'w', encoding='utf-8') as file:
        file.write(str(soup))
    
    # Return the relative path to be used for the href attribute
    relative_path = f"websites/{base_domain}/{os.path.relpath(save_path, website_dir)}"
    return relative_path


class MyHTTPRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, directory=None, **kwargs):
        super().__init__(*args, directory=directory, **kwargs)

def run_server(directory, port=5001):
    handler = MyHTTPRequestHandler
    httpd = HTTPServer(('', port), handler)
    print(f"Serving website on http://localhost:{port}/")
    httpd.serve_forever()

def main():
    website = input("Enter the website URL (include http:// or https://): ")
    parsed_website = urlparse(website)
    base_domain = ".".join(parsed_website.netloc.split(".")[-2:])
    website_dir = f"websites/{parsed_website.netloc}"

    if not os.path.exists(website_dir):
        os.makedirs(website_dir)

    code_crawler(website, website_dir, base_domain)

    # Serve the website on localhost port 5001
    run_server(website_dir)

if __name__ == "__main__":
    main()
