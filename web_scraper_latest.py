#!/usr/bin/env python3
import argparse
import requests
import sqlite3
import logging
import os
import csv
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from requests.exceptions import RequestException

def parse_arguments():
    parser = argparse.ArgumentParser(description='Count <script> tags in webpages.')
    parser.add_argument('url_file', help='Path to the text file containing URLs.')
    parser.add_argument('--workers', type=int, default=10, help='Number of concurrent threads.')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds.')
    parser.add_argument('--csv_output', default='results.csv', help='CSV output file name.')
    return parser.parse_args()

def setup_logging():
    logging.basicConfig(
        filename='web_scraper.log',
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

def setup_database(db_name='results.db'):
    conn = sqlite3.connect(db_name)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            url TEXT PRIMARY KEY,
            script_count INTEGER,
            status TEXT
        )
    ''')
    conn.commit()
    return conn, c

def load_urls(url_file):
    with open(url_file, 'r') as file:
        content = file.read()
        # Split the content by any whitespace or newlines
        urls = content.strip().split()
    # Remove duplicates
    return list(set(urls))

def get_processed_urls(cursor):
    cursor.execute('SELECT url FROM results')
    return set([row[0] for row in cursor.fetchall()])

def process_url(url, timeout):
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; WebScraper/1.0)'
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tags = soup.find_all('script')
        script_count = len(script_tags)
        status = 'Success'
        logging.info(f'Processed {url}: {script_count} <script> tags.')
        return url, script_count, status
    except RequestException as e:
        script_count = None
        status = 'Failed'
        logging.error(f'Error processing {url}: {e}')
        return url, script_count, status

def save_result(cursor, url, script_count, status):
    cursor.execute('REPLACE INTO results (url, script_count, status) VALUES (?, ?, ?)',
                   (url, script_count, status))

def export_to_csv(db_name='results.db', csv_file='results.csv'):
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()
    cursor.execute('SELECT url, script_count, status FROM results')
    rows = cursor.fetchall()
    conn.close()
    with open(csv_file, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['URL', 'Script Count', 'Status'])
        csv_writer.writerows(rows)
    print(f'Results exported to {csv_file}')
    logging.info(f'Results exported to {csv_file}')

def main():
    args = parse_arguments()
    setup_logging()
    conn, cursor = setup_database()
    urls = load_urls(args.url_file)
    processed_urls = get_processed_urls(cursor)
    urls_to_process = [url for url in urls if url not in processed_urls]

    if not urls_to_process:
        print('All URLs have been processed.')
    else:
        print(f'Starting processing of {len(urls_to_process)} URLs...')

        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            future_to_url = {executor.submit(process_url, url, args.timeout): url for url in urls_to_process}
            for future in as_completed(future_to_url):
                url = future_to_url[future]
                try:
                    url, script_count, status = future.result()
                    save_result(cursor, url, script_count, status)
                    conn.commit()
                except Exception as e:
                    logging.error(f'Unexpected error processing {url}: {e}')

    conn.close()
    # Export results to CSV
    export_to_csv(db_name='results.db', csv_file=args.csv_output)
    print('Processing completed.')

if __name__ == '__main__':
    main()
