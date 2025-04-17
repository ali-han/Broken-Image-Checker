# Broken Image Checker

Broken Image Checker is a Python-based tool designed to identify and report broken images on websites. This tool is perfect for web developers, SEO specialists, and content managers who want to ensure their websites are free of broken image links, improving user experience and search engine rankings.

## Features

- Scans web pages starting from a given URL.
- Detects broken images and image redirects.
- Generates a detailed CSV report with broken image information.
- Handles rate-limiting (HTTP 429) and respects website policies.

## Requirements

- Python 3.7 or higher

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/your-repo/BrokenImageChecker.git
   cd BrokenImageChecker
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Run the script:
   ```bash
   python run.py
   ```

2. Enter the starting URL when prompted (e.g., `https://example.com`).

3. The script will crawl the website, check for broken images, and generate a CSV report in the current directory.

## Output

- A CSV file named `broken_images_<timestamp>.csv` will be created in the current directory.
- The CSV file contains the following columns:
  - Page URL
  - Broken Image URL
  - Details

## Notes

- This script is for educational purposes only. Use responsibly and respect website policies.
- The developer is not responsible for any misuse of this tool.

## License

This project is licensed under the MIT License.