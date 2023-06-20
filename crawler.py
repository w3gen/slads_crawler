import os
import requests
import pandas as pd
import sqlite3
from bs4 import BeautifulSoup
import urllib.parse
import csv

# Base URL of the website to scan
base_url = "https://sl-ads.com"
ad_url_template = "https://sl-ads.com/viewAd.php?aid="

# Create the 'images' folder if it doesn't exist
if not os.path.exists('images'):
    os.makedirs('images')

# Create the SQLite database connection
conn = sqlite3.connect('lkadsdata.sqlite')
c = conn.cursor()

# Create the 'ads' table in the database
c.execute('''CREATE TABLE IF NOT EXISTS ads
             (AdTitle TEXT, Description TEXT, IsVerified TEXT, IsBoosted TEXT, URL TEXT, ImagePath TEXT, MobileNumber TEXT, PageURL TEXT)''')

# Function to save the image in a folder
def save_image(url, image_name):
    response = requests.get(url, stream=True)
    with open(f"images/{image_name}", 'wb') as out_file:
        out_file.write(response.content)

# Function to extract data from a page
def extract_data(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the ad title with the specified CSS id
    ad_title_element = soup.find(id='AddTitleTXt')
    ad_title = ad_title_element.text.strip() if ad_title_element else ''

    # Find the description with the specified CSS id
    description_element = soup.find(id='desctiptionTxt')
    description_text = description_element.text.strip() if description_element else ''

    # Find all image tags with the specified CSS classes and extract the source URLs
    image_tags = soup.find_all('img', {'class': ['img-fluid', 'singleadImage']})

    # Check if any image tag exists with class 'singleadImage' and a valid 'src' attribute
    if not any(image_tag.get('src') for image_tag in image_tags):
        return

    # Find the div with the specified class for verification and boosting
    verified_element = soup.find('div', {'class': 'verified-ad-banner'})
    is_verified = 'true' if verified_element and 'Verified 100% Cash Back Guaranteed' in verified_element.text else 'false'
    is_boosted = 'true' if verified_element and 'Top Ad' in verified_element.text else 'false'

    # List to store data: ad title, description, mobile number, original URL, image path, and page URL
    data = []

    for image_tag in image_tags:
        source_url = urllib.parse.urljoin(url, image_tag.get('src', ''))

        if not source_url:
            # Stop scanning the page if the 'src' URL is not present
            return

        # Check if the source URL starts with a forward slash
        if source_url.startswith('/'):
            source_url = urllib.parse.urljoin(base_url, source_url)

        ad_id = urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get('aid')
        if not ad_id:
            return
        
        print("Scanning:", url)
        
        ad_id = ad_id[0]
        image_name = f"{ad_id}.jpg"

        # Save the image in the 'images' folder
        save_image(source_url, image_name)

        # Get the path of the saved image
        image_path = f"https://sl-ads.info/wp-content/uploads/slads_crawler/images/{image_name}"

        # Find the mobile number element by id and extract the phone number
        mobile_number_element = soup.find('span', {'id': 'sellerPhoneNumberaa'})
        mobile_number = mobile_number_element.text.strip() if mobile_number_element else ''

        # Append the data to the list
        data.append([ad_title, description_text, is_verified, is_boosted, source_url, image_path, mobile_number, url])

        # Insert the data into the 'ads' table in the database
        c.execute("INSERT INTO ads VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                  (ad_title, description_text, is_verified, is_boosted, source_url, image_path, mobile_number, url))

    # Save the extracted data to a CSV file
    df = pd.DataFrame(data, columns=['AdTitle', 'Description', 'IsVerified', 'IsBoosted', 'URL', 'ImagePath', 'MobileNumber', 'PageURL'])
    df.to_csv('data.csv', index=False, mode='a', header=not os.path.exists('data.csv'))

# Main function to start scanning the website
def scan_website():
    # Iterate through IDs from 0 to 1000000
    for ad_id in range(249901, 1000001):
        page_url = ad_url_template + str(ad_id)
        response = requests.get(page_url)

        # Check if the page exists (response status code 200)
        if response.status_code == 200:
            extract_data(page_url)

# Run the website scanning
scan_website()

conn.commit()
# Commit the changes and close the database connection
conn.close()

print("Scanning completed and data saved to 'data.csv' and 'lkadsdata.sqlite'.")
