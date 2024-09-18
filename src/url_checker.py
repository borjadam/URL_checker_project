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

# paths relative to the script directory
script_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.abspath(os.path.join(script_dir, '..'))
data_dir = os.path.join(root_dir, 'data')
logs_dir = os.path.join(root_dir, 'logs')

def parse_arguments():
    """
    Helps the script understand and process options that you provide when running the script from the command line. 
    It allows the user to customize how the script runs without changing the code.
    """
    parser = argparse.ArgumentParser(description='Count <script> tags in webpages.')
    parser.add_argument('url_file', help='Name of the text file containing URLs (located in the data directory).')
    parser.add_argument('--workers', type=int, default=10, help='Number of concurrent threads.')
    parser.add_argument('--timeout', type=int, default=10, help='Request timeout in seconds.')
    parser.add_argument('--csv_output', default='results.csv', help='CSV output file name (saved in the data directory).')
    return parser.parse_args()

def setup_logging():
    """
    Set up the logging system for the script.
    Creates the logs directory if it doesn't exist and sets up the logging format and level.
    """
    
    if not os.path.exists(logs_dir):
        os.makedirs(logs_dir)
    log_file = os.path.join(logs_dir, 'url_checker.log')
    logging.basicConfig(
        filename=log_file,
        level=logging.INFO,
        format='%(asctime)s:%(levelname)s:%(message)s'
    )

def setup_database(db_name='results.db'):
    """
    Set up the SQLite database for storing results: the URLs, number of <script> tags, and status)
    Creates the data directory if it doesn't exist and initializes the database schema.
    Args:
        db_name (str): Name of the database file.
    """
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    db_path = os.path.join(data_dir, db_name)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS results (
            url TEXT PRIMARY KEY,
            script_count INTEGER,
            status TEXT
        )
    ''')
    # saves any changes made to the database
    conn.commit()
    return conn, c

def load_urls(url_file):
    """
    Load URLs from the specified file.
    Removes duplicates and returns a list of URLs.
    Args:
        url_file (str): Name of the URL file.
    Returns:
        urls (list): List of unique URLs.
    """
    url_file_path = os.path.join(data_dir, url_file)
    with open(url_file_path, 'r') as file:
        content = file.read()
        # splits the content by any whitespace or newlines
        urls = content.strip().split()
    # removes duplicates
    return list(set(urls))

def get_processed_urls(cursor):
    """
    Retrieves the URLs that have already been processed and stored in the database. 
    By keeping track of these URLs, the script avoids processing the same URLs again.
    Args:
        cursor: SQLite cursor object used to execute SQL queries.
    Returns:
        set: set of URLs that have already been processed.
    """
    cursor.execute('SELECT url FROM results')
    return set([row[0] for row in cursor.fetchall()])

def process_url(url, timeout):
    """
    Fetches a webpage and counts the number of <script> tags.
    Args:
        url (str): the URL to process.
        timeout (int): the maximum time to wait for a response.
    Returns:
        tuple: (url, script_count, status)
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (compatible; URLChecker/1.0)'
        }
        # sends HTTP GET request to the URL
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        # parses the HTML content using BeautifulSoup
        soup = BeautifulSoup(response.text, 'html.parser')
        # finds all <script> tags
        script_tags = soup.find_all('script')
        script_count = len(script_tags)
        status = 'Success'
        logging.info(f'Processed {url}: {script_count} <script> tags.')
        return url, script_count, status
    except RequestException as e:
        # handles exceptions related to the HTTP request
        script_count = None
        status = 'Failed'
        logging.error(f'Error processing {url}: {e}')
        return url, script_count, status

def save_result(cursor, url, script_count, status):
    """
    Saves the result of a processed URL to the database:
    - If the URL has already been processed, this will update the existing entry.
    - If the URL is new, this will insert a new record.
    Args:
        cursor: SQLite cursor object to execute SQL commands.
        url (str): URL that was processed.
        script_count (int or None): number of <script> tags found.
        status (str): 'Success' or 'Failed'.
    """
    cursor.execute('REPLACE INTO results (url, script_count, status) VALUES (?, ?, ?)',
                (url, script_count, status))

def export_to_csv(db_name='results.db', csv_file='results.csv'):
    """
    Exports the results from the database to a CSV for analysis.
    Args:
        db_name (str): name of the database file.
        csv_file (str): name of the CSV output file.
    """
    db_path = os.path.join(data_dir, db_name)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # retrieves all records from the results table
    cursor.execute('SELECT url, script_count, status FROM results')
    rows = cursor.fetchall()
    conn.close()
    csv_file_path = os.path.join(data_dir, csv_file)
    # writes the results to a CSV
    with open(csv_file_path, 'w', newline='', encoding='utf-8') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['URL', 'Script Count', 'Status'])
        csv_writer.writerows(rows)
    print(f'Results exported to {csv_file_path}')
    logging.info(f'Results exported to {csv_file_path}')

def main():
    """
    Main function to orchestrate the entire workflow of the script, 
    from reading URLs to processing them at the same time and saving/exporting the results.
    """
    args = parse_arguments()
    setup_logging()
    conn, cursor = setup_database()
    urls = load_urls(args.url_file)
    processed_urls = get_processed_urls(cursor)
    # filters out URLs that have already been processed, keeping only those that need processing
    urls_to_process = [url for url in urls if url not in processed_urls]

    # if all URLs have been processed, print a message and skip further processing
    if not urls_to_process:
        print('All URLs have been processed.')
    else:
        # if there are unprocessed URLs, start processing them
        print(f'Starting processing of {len(urls_to_process)} URLs...')

        # creates a thread pool to process multiple URLs at the same time
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
    # exports results to CSV
    export_to_csv(db_name='results.db', csv_file=args.csv_output)
    print('Processing completed.')

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('Script interrupted by user.')
        logging.info('Script interrupted by user.')

