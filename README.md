# URL checker project

## Overview 

This project contains a Python script that processes a list of URLs, counts the number of <script> tags in each webpage, and stores the results with persistence and error logging. The script is designed to handle thousands of URLs efficiently using multithreading and ensures that the data is saved for easy analysis.

## Project structure

- src/: contains the source code of the project
    - `url_checker.py`: the main Python script.
- data/: stores all data files
    - `urls.txt`: input file containing the list of URLs to process.
    - `results.db`: SQLite database file where results are stored.
    - `results.csv`: CSV file exported from the database for easy analysis.
- logs/: contains log files generated during script execution.
    - `url_checker.log`: log file capturing processing details and errors.
- analysis/: 
    - I'm aware this wasn't a requirement, but I included a simple Jupyter notebook in this folder that illustrates how you'd quickly analyze the results with pandas
- `README.md`: documentation.

## Requirements

- Python 3.x
- Packages: 'requests', 'beautifulsoup4'

## How to run

1. Prepare the URL File:
   - Place your `urls.txt` file in the data/ directory.
   - Ensure that it contains the URLs you want to process, separated by newlines or whitespace.
   - Example content of `urls.txt`:
     ```arduino
     https://www.google.com
     https://www.youtube.com
     https://www.github.com
     ```
2. Navigate to the src/ directory:
   - Open a terminal and navigate to the src/ directory: `cd url_checker_assignment/src`

3. Run the script: `python3 -m url_checker urls.txt`
   - The script reads `urls.txt` from the data/ directory.
   - Outputs are saved in the data/ and logs/ directories.

4. Optional arguments:
   - --workers: number of concurrent threads (default is 10).
   - --timeout: request timeout in seconds (default is 10).
   - --csv_output: name of the CSV output file (saved in the data/ directory).
   
   Example: `python3 m- url_checker.py urls.txt --workers 20 --timeout 15 --csv_output my_results.csv`

## Features

- Concurrent processing: uses multithreading with ThreadPoolExecutor to process multiple URLs at the same time, improving performance.
- Data persistence: results are stored in a SQLite database (`results.db`) in the data/ directory, which allows the script to resume processing without duplicating efforts.
- CSV export: exports results to a CSV file (`results.csv`) in the data/ directory for easy analysis with Excel or data analysis tools like pandas.
- Error handling and logging: logs detailed processing information and errors to `url_checker.log` in the logs/ directory.
- Resumability: the script checks the database for already processed URLs and skips them, allowing you to stop and resume execution seamlessly.

### Data persistence and resumability

- SQLite database (`results.db`):
  - Stores the URL, the count of <script> tags, and the status (Success or Failed) for each URL.
  - Ensures that each URL is processed only once.
  - Facilitates resuming the script without reprocessing URLs.

- How resumability works:
  - On each run, the script fetches the list of already processed URLs from the database.
  - It compares this list with the URLs in `urls.txt` and processes only the URLs that have not been processed yet.

### Error handling and logging

- Logging:
  - All processing information and errors are logged to logs/url_checker.log.
  - Includes timestamps, log levels, and detailed messages.

- Error handling:
  - The script handles exceptions related to network requests and other issues.
  - If a URL cannot be processed, it logs the error and marks the status as Failed in the database and CSV file.
  - Detailed error messages are available in the log file for troubleshooting (at the same time,the csv file  shows 'Success' or 'Failed' so users can quickly identify which URLs failed).

## Performance considerations

- Multithreading:
  - The script uses ThreadPoolExecutor from the concurrent.futures module to process URLs at the same time.
  - The number of worker threads can be adjusted using the --workers argument.
  - Suitable for handling thousands of URLs efficiently.

- Scalability:
  - While this script is able to process thousands of URLs using multithreading, I am aware that for processing tens or hundreds of thousands of URLs, an asynchronous approach using libraries like asyncio and aiohttp could offer better performance and scalability.
  - Because of the time constraints and the scope of this assignment, I chose to implement multithreading, which provides a good balance between performance and code simplicity.

## Summary

- Persisting results on disk: results are stored in a SQLite database and exported to a CSV file for easy analysis.
- Allowing the script to be stopped and resumed: the script checks for already processed URLs and skips them, enabling resumability.
- Handling errors: errors are logged, and failed URLs are marked appropriately without stopping the entire process.
- Optimizing performance: thanks to multithreading it processes multiple URLs at the same time, improving speed.
- All the code is contained within a single Python file (`url_checker.py`)
