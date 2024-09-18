import os
import sys
import time
import polars as pl
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import psycopg2
from datetime import datetime, timedelta

# SMTP Server details
smtp_server = os.getenv("SMTP_SERVER", "mail.brightpathassociates.com")
smtp_port = int(os.getenv("SMTP_PORT", 465))
smtp_user = os.getenv("SMTP_USER", "vpn@brightpathassociates.com")
smtp_password = os.getenv("SMTP_PASSWORD", "Bp135@$%")

def send_email(first_name, job_title, location, recipient_email, username, office_position, email, phone_number):
    from_address = email
    to_address = recipient_email

    # Create a message
    message = MIMEMultipart()
    message["From"] = from_address
    message["To"] = to_address
    message["Subject"] = f"Candidate for {job_title} at {location}"

    # Email body
    html_body = f"""
    <html>
    <body>
        <p>Hi {first_name},</p>
        <p>I have found a promising candidate for the <strong>{job_title}</strong> opening at the <strong>{location}</strong> location posted at your career page, available for interview. Would you like to review their resume?</p>
        <p>Our contingent fee model allows you to Screen, Interview and meet our candidates without any fee unless you want to onboard.</p>
        <p>Looking forward to hearing from you.</p>
        <p>Warm regards,<br>
        {username}<br>
        {office_position}<br>
        <a href="mailto:{email}">{email}</a> | {phone_number}<br>
        100 Mesa Dr Bethany CT 06524<br>
        <a href="http://www.brightpathassociates.com">www.brightpathassociates.com</a></p>
        <p><strong>IMPORTANT:</strong> The contents of this email and any attachments are confidential. They are intended for the named recipient(s) only. If you have received this email by mistake, please notify the sender immediately or unsubscribe and do not disclose the contents to anyone or make copies thereof.</p>
    </body>
    </html>
    """
    
    message.attach(MIMEText(html_body, "html"))

    # Send email using SMTP
    try:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(from_address, to_address, message.as_string())
        print(f"Email sent to {recipient_email}")
    except Exception as e:
        print(f"Failed to send email to {recipient_email}. Error: {str(e)}")

# Database connection setup
def get_db_connection():
    try:
        conn = psycopg2.connect(
            host="job-scounting-database-do-user-7586043-0.k.db.ondigitalocean.com",
            database="Blocks_lists",
            user="doadmin",
            password="AVNS_4B519UooZOlPzWnCaid",
            port='25060'
        )
        return conn
    except Exception as e:
        print(f"Error connecting to the database: {e}")
        return None

# Validation function against unsubscribed_emails table
def check_unsubscribed_email(email, conn):
    cur = conn.cursor()
    try:
        cur.execute("SELECT EXISTS(SELECT 1 FROM unsubscribed_emails WHERE keyword = %s)", (email,))
        result = cur.fetchone()[0]
        return result
    except Exception as e:
        print(f"Error checking unsubscribed_emails for {email}: {e}")
        return False
    finally:
        cur.close()

# Validation function against sent_emails table
def check_sent_email(email, conn):
    cur = conn.cursor()
    try:
        # Check if the email exists and if the last sent date is older than 10 days
        cur.execute("SELECT sent_date FROM sent_emails WHERE email = %s", (email,))
        row = cur.fetchone()
        
        if row:
            last_sent_date = row[0]
            if last_sent_date and (datetime.now().date() - last_sent_date).days < 10:
                return False  # Email sent within the last 10 days
            else:
                return True  # Email can be sent again
        else:
            return True  # No previous email found, email can be sent
    except Exception as e:
        print(f"Error checking sent_emails for {email}: {e}")
        return False
    finally:
        cur.close()

# Update sent_emails table after sending email
def update_sent_email(email, conn):
    cur = conn.cursor()
    try:
        # Insert a new record or update the sent_date if the email already exists
        cur.execute("""
            INSERT INTO sent_emails (email, sent_date)
            VALUES (%s, %s)
            ON CONFLICT (email) 
            DO UPDATE SET sent_date = EXCLUDED.sent_date
        """, (email, datetime.now().date()))
        conn.commit()
    except Exception as e:
        print(f"Error updating sent_emails for {email}: {e}")
    finally:
        cur.close()

# Main process
def main(file_path, username, email, phone_number, office_position):
    #
    # Check if file exists
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    # Read input file using Polars
    df = pl.read_csv(file_path)
    
    # Database connection
    conn = get_db_connection()
    if not conn:
        print("Failed to connect to the database. Exiting.")
        return

    # Validate and send emails
    for row in df.iter_rows(named=True):
        recipient_email = row["email"]

        # Check if email is unsubscribed
        if check_unsubscribed_email(recipient_email, conn):
            print(f"Skipping email {recipient_email}: found in unsubscribed_emails")
            continue
        
        # Check if the email was sent within the last 10 days
        if not check_sent_email(recipient_email, conn):
            print(f"Skipping email {recipient_email}: already sent within the last 10 days")
            continue

        # Extract other necessary details from the row
        first_name = row["name"]
        job_title = row["job_name"]
        location = row["location"]
        
        # Update the sent_emails table before sending the email
        update_sent_email(recipient_email, conn)
        
        # Send email
        send_email(first_name, job_title, location, recipient_email, username, office_position, email, phone_number)

        # Delay between each email (1 minute)
        time.sleep(30)

    # Close the database connection
    conn.close()

if __name__ == "__main__":
    file_path = sys.argv[1]  # Path to the CSV file
    username = sys.argv[2]  # Sender's name
    email = sys.argv[3]  # Sender's email
    phone_number = sys.argv[4]  # Sender's phone number
    office_position = sys.argv[5]  # Sender's office position
    main(file_path, username, email, phone_number, office_position)
