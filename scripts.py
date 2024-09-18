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

def process_company_url(url, email, password, job_name, location , company_name ):
    print(f"Processing company URL: {url}")
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

        # Wait for login to succeed (check for URL change or certain element presence)
        WebDriverWait(driver, 50).until(EC.url_changes("https://login.seamless.ai/"))
        print("Login successful.")

        # Store cookies after login
        cookies = driver.get_cookies()
        print(f"Stored cookies: {cookies}")

        # Navigate to the desired page using the company URL
        search_url = f"https://login.seamless.ai/search/contacts?page=1&companies={url}&industries=-Insurance|-Banking|-Government%25%20Administration|-Airlines%25%20Aviation&locations=United%20States%20of%20America&titles=Human%25%20Resource|HR|Talent|Recruiter|President|Founder|Owner|CEO"
        driver.get(search_url)
        print(f"Navigated to search URL: {search_url}")

        # Add cookies to the session
        for cookie in cookies:
            driver.add_cookie(cookie)
        driver.refresh()  # Refresh after adding cookies to ensure session is active
        print("Cookies added, page refreshed.")

        WebDriverWait(driver, 50).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'table.Table__StyledTable-bEWGVx.iWWlUt'))
        )
        print("Page loaded with search results.")

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        table = soup.find('table', class_='Table__StyledTable-bEWGVx iWWlUt')
        results = []
        if table:
            tbody = table.find('tbody', role='rowgroup')
            if tbody:
                rows = tbody.find_all('tr', role='row')

                for i, row in enumerate(rows[:5]):
                    print(f"Processing row {i+1}...")

                    # Find and click the 'Find contact information' button
                    find_button = row.find('button', class_='Button__StyledButton-QGODF iIMTsb FindLockedValueButton__StyledButton-dMKDVR gRuMwN rs-btn rs-btn-ghost')
                    if find_button:
                        find_button_element = WebDriverWait(driver, 60).until(
                            EC.element_to_be_clickable((By.XPATH, ".//button[contains(@class, 'FindLockedValueButton__StyledButton-dMKDVR')]"))
                        )
                        find_button_element.click()
                        print(f"Clicked 'Find contact' button in row {i+1}.")
                        time.sleep(20)

                driver.refresh()
                time.sleep(20)
                print("Page refreshed.")

                # Extract contact info after refresh
                page_source = driver.page_source
                soup = BeautifulSoup(page_source, 'html.parser')
                table = soup.find('table', class_='Table__StyledTable-bEWGVx iWWlUt')
                if table:
                    tbody = table.find('tbody', role='rowgroup')
                    if tbody:
                        rows = tbody.find_all('tr', role='row')
                        for i, row in enumerate(rows[:5]):
                            name, position, email = extract_contact_info(row)
                            # Add the job_name and location for each result
                            results.append([url, name, position, email, job_name, location , company_name ])
                            print(f"Extracted info from row {i+1} - Name: {name}, Position: {position}, Email: {email}, Job: {job_name}, Location: {location}")

        return results
    except Exception as e:
        print(f"Error: {e}")
        return []
    finally:
        driver.quit()
        print("Browser closed.")


def main(input_file):
    # Generate a timestamp for file names
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
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

    # Determine the path to the Downloads folder
    downloads_folder = Path(os.path.expanduser("~/Downloads"))

    if valid_rows:
        print("Processing valid rows...")
        valid_df = pl.DataFrame(valid_rows)
        company_websites = valid_df['Company_Website']
        job_names = valid_df['Job_Name']
        locations = valid_df['Job_Location']
        company_name = valid_df['Company_Name']
        print(company_name)
        all_results = []
        for company_url, job_name, location, company_name in zip(company_websites, job_names, locations, company_name):
            print(f"Processing URL: {company_url} with Job: {job_name} and Location: {location}")
            results = process_company_url(company_url, email, password, job_name, location, company_name)
            all_results.extend(results)

        # Save the scraped data to a CSV file with timestamp in the Downloads folder
        if all_results:
            output_filename = downloads_folder / f"output_{timestamp}.csv"
            print(f"Saving {len(all_results)} results to {output_filename}...")
            output_df = pl.DataFrame(all_results, schema=["url", "name", "position", "email", "job_name", "location", "company Name"])
            output_df.write_csv(output_filename)
            print(f"Scraped data saved to {output_filename}")
        else:
            print("No results were found.")

    if invalid_rows:
        # Save the invalid rows to an Excel file with a timestamp in the Downloads folder
        invalid_filename = downloads_folder / f"invalid_GD_Jobs_Octoparse_AM_{timestamp}.xlsx"
        print(f"Saving {len(invalid_rows)} invalid rows to {invalid_filename}...")
        invalid_df = pl.DataFrame(invalid_rows)
        invalid_df.write_excel(invalid_filename)
        print(f"Invalid data saved to {invalid_filename}")
# inputs = "company_testing.csv"

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: script.py <input_file> <email> <password>")
        sys.exit(1)

    input_file = sys.argv[1]
    email = sys.argv[2]
    password = sys.argv[3]
 
    print(f"Starting script with input file: {input_file}")
    main(input_file)



    
