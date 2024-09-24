from datetime import datetime
import os
from pathlib import Path
import polars as pl
import psycopg2
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import sys

# User credentials for Seamless.AI  'mark.h@brightpathassociates.com' 'Smh9141@$%'

# Initialize database connection
def initialize_db():
    print("Initializing database connection...")
    try:
        conn = psycopg2.connect(
            host="job-scounting-database-do-user-7586043-0.k.db.ondigitalocean.com",
            database="Blocks_lists",
            user="doadmin",
            password="AVNS_4B519UooZOlPzWnCaid",
            port = '25060'
        )
        print("Database connection established.")
        return conn
    except Exception as e:
        print(f"Error connecting to PostgreSQL: {e}")
        raise

# Validate function to check block list
def check_block_list(value, table_name, cur):
    print(f"Checking block list for {value} in {table_name}...")
    try:
        cur.execute(f"SELECT EXISTS(SELECT 1 FROM {table_name} WHERE keyword = %s)", (value,))
        exists = cur.fetchone()[0]
        return exists
    except Exception as e:
        print(f"Error checking block list: {e}")
        raise

# Function to validate rows
def validate_rows(df, conn):
    print("Validating rows...")
    cur = conn.cursor()
    valid_rows = []
    invalid_rows = []

    for row in df.iter_rows(named=True):
        try:
            print(f"Validating row: {row}")
            # Validation checks
            job_name_check = not check_block_list(row['Job_Name'], 'Block_List_Job', cur)
            company_name_check = not check_block_list(row['Company_Name'], 'Block_List_Cname', cur)
            company_size_check = not check_block_list(row['Company_Size'], 'Block_List_Size', cur)
            company_website_check = not check_block_list(row['Company_Website'], 'Block_List_Url', cur)
            company_indsutry_check = not check_block_list(row['Industry'], 'Block_List_Industry', cur)
            
            if job_name_check and company_name_check and company_size_check and company_website_check and company_indsutry_check:
                valid_rows.append(row)
            else:
                invalid_rows.append(row)
        except Exception as e:
            print(f"Error validating row {row}: {e}")

    cur.close()
    print(f"Validation complete. Valid rows: {len(valid_rows)}, Invalid rows: {len(invalid_rows)}")
    return valid_rows, invalid_rows

def initialize_driver():
    print("Initializing Selenium WebDriver...")
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')  # Uncomment to run in headless mode (no UI)

    # Set up the ChromeDriver using WebDriver Manager
    driver = webdriver.Chrome(
        service=webdriver.chrome.service.Service(ChromeDriverManager().install()),
        options=options
    )
    print("WebDriver initialized.")
    return driver

def extract_contact_info(row):
    print("Extracting contact information...")
    try:
        name_element = row.find('button', class_='Button__StyledButton-QGODF jakdAs Anchor-iRIgff ggxGOG EntityDataPoint__DataValue-iaySYK EntityDataPoint__DataValueButton-fDidaQ cOtrUz bNYhez rs-btn rs-btn-link')
        name = name_element.get_text().strip() if name_element else "No name found"
        
        position_element = row.find('div', class_='ContactColumn__TitleContainer-kNrLUz jRGtNZ')
        position = position_element.get_text(strip=True) if position_element else "No position found"
        
        email_links = row.find_all('a', class_='Button__StyledButton-QGODF jakdAs Anchor-iRIgff ggxGOG EntityDataPoint__DataValue-iaySYK EntityDataPoint__DataValueButton-fDidaQ iZbREi bNYhez rs-btn rs-btn-link')
        email = "No email found"
        if email_links:
            for link in email_links:
                href = link.get('href', '')
                if 'mailto:' in href:
                    email = href.replace('mailto:', '').strip()
                    break
        
        print(f"Extracted info - Name: {name}, Position: {position}, Email: {email}")
        return name, position, email
    except Exception as e:
        print(f"Error while processing contact information: {e}")
        return "Error", "Error", "Error"

def process_company_urls_in_batch(urls, email, password, job_names, locations, company_names):
    print(f"Processing company URLs in batch: {len(urls)} companies.")
    driver = initialize_driver()
    try:
        driver.maximize_window()

        # Navigate to Seamless.AI login page
        driver.get("https://login.seamless.ai/")
        WebDriverWait(driver, 40).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        print("Navigated to Seamless.AI login page.")

        # Zoom out
        zoom_out_script = "document.body.style.zoom='75%'"
        driver.execute_script(zoom_out_script)
        time.sleep(20)

        # Input email and password
        email_input = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[2]/div/div[2]/form/div/div[1]/input"))
        )
        email_input.send_keys(email)
        print("Entered email.")

        password_input = driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[2]/div/div[2]/form/div/div[2]/div[2]/input")
        password_input.send_keys(password)
        print("Entered password.")

        login_button = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div/div/div/div/div[1]/div[2]/div/div[2]/form/button"))
        )
        login_button.click()
        print("Clicked login button.")

        # Wait for login to succeed
        WebDriverWait(driver, 50).until(EC.url_changes("https://login.seamless.ai/"))
        print("Login successful.")

        cookies = driver.get_cookies()
        print(f"Stored cookies: {cookies}")

        # Process each URL in the batch
        all_results = []
        for url, job_name, location, company_name in zip(urls, job_names, locations, company_names):
            try:
                print(f"Processing URL: {url} for {company_name}")
                search_url = f"https://login.seamless.ai/search/contacts?page=1&companies={url}&industries=-Insurance|-Banking|-Government%25%20Administration|-Airlines%25%20Aviation&locations=United%20States%20of%20America&titles=Human%25%20Resource|HR|Talent|Recruiter|President|Founder|Owner|CEO"
                driver.get(search_url)
                print(f"Navigated to search URL: {search_url}")

                # Add cookies to the session and refresh
                for cookie in cookies:
                    driver.add_cookie(cookie)
                driver.refresh()
                print("Cookies added, page refreshed.")

                WebDriverWait(driver, 50).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'table.Table__StyledTable-bEWGVx.iWWlUt'))
                )
                print("Page loaded with search results.")

                # Extract contact information
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                table = soup.find('table', class_='Table__StyledTable-bEWGVx iWWlUt')
                if table:
                    tbody = table.find('tbody', role='rowgroup')
                    if tbody:
                        rows = tbody.find_all('tr', role='row')
                        for row in rows[:5]:
                            name, position, email = extract_contact_info(row)
                            all_results.append([url, name, position, email, job_name, location, company_name])
                            print(f"Extracted info - Name: {name}, Position: {position}, Email: {email}")
            except Exception as e:
                print(f"Error processing {url}: {e}")
        
        return all_results
    finally:
        driver.quit()
        print("Browser closed after batch processing.")


def main(input_file, username):
    # Generate a timestamp for file names
    timestamp = datetime.now().strftime("%Y%m%d")
    
    print(f"Reading input file: {input_file}")
    df = pl.read_csv(input_file, raise_if_empty=False)
    if df.shape[0] == 0:
        print("Error: The input file is empty.")
        raise ValueError("The input file is empty.")
    
    print(f"File read successfully with {df.shape[0]} rows.")

    conn = initialize_db()
    print("Database connection initialized.")

    valid_rows, invalid_rows = validate_rows(df, conn)
    print(f"Validation completed. Valid rows: {len(valid_rows)}, Invalid rows: {len(invalid_rows)}")

    conn.close()
    print("Database connection closed.")

    if valid_rows:
        print("Processing valid rows in batches...")
        valid_df = pl.DataFrame(valid_rows)
        company_websites = valid_df['Company_Website'].to_list()
        job_names = valid_df['Job_Name'].to_list()
        locations = valid_df['Job_Location'].to_list()
        company_names = valid_df['Company_Name'].to_list()

        all_results = []
        batch_size = 30  # Process 30 rows at a time
        for i in range(0, len(company_websites), batch_size):
            batch_urls = company_websites[i:i+batch_size]
            batch_job_names = job_names[i:i+batch_size]
            batch_locations = locations[i:i+batch_size]
            batch_company_names = company_names[i:i+batch_size]
            
            # Process the current batch of URLs
            print(f"Processing batch {i//batch_size + 1}...")
            batch_results = process_company_urls_in_batch(batch_urls, email, password, batch_job_names, batch_locations, batch_company_names)
            all_results.extend(batch_results)

        if all_results:
            uploads_folder = Path(os.path.abspath(f"C:/Projectscrappersfolders/{username}_output_folder"))
            uploads_folder.mkdir(parents=True, exist_ok=True)  # Create if it doesn't exist

            # Create a timestamp for the filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = uploads_folder / f"{username}_output_{timestamp}.xlsx"

            print(f"Saving {len(all_results)} results to {output_filename}...")
            output_df = pl.DataFrame(all_results, schema=["url", "name", "position", "email", "job_name", "location", "company Name"])

            # Write to Excel
            output_df.write_excel(output_filename)
            print(f"Scraped data saved to {output_filename}")
            return str(output_filename)  # Return the file path
        else:
            print("No results were found.")
            return None


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: script.py <input_file> <email> <password>")
        sys.exit(1)

    input_file = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
    username = sys.argv[4]
 
    print(f"Starting script with input file: {input_file}")
    main(input_file , username)
