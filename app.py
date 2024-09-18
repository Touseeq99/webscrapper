import sys
from flask import Flask, render_template, request, redirect, url_for, session, flash
import os
from werkzeug.utils import secure_filename
import subprocess
import psycopg2  # PostgreSQL library

app = Flask(__name__)
app.secret_key = 'supersecretkey99'  # Replace with a real secret key

# Configure file upload
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.before_request
def check_login():
    session.permanent = False
    if 'logged_in' not in session and request.endpoint not in ['login', 'signup', 'static']:
        return redirect(url_for('login'))

@app.route('/')
def index():
    if 'logged_in' in session:
        if session.get('user_type') == 'admin':
            return redirect(url_for('admin_panel'))
        return render_template('index.html')
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'logged_in' in session:
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        # Check user credentials and set session variables
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        
        if user:
            session['logged_in'] = True
            session['username'] = user[1]  # Assuming the username is at index 1
            session['email'] = user[2]     # Assuming the email is at index 2
            session['phone_number'] = user[4]  # Assuming the phone number is at index 4
            session['office_position'] = user[8]  # Assuming the office position is at index 8
            session['user_type'] = user[5]  # Assuming 'status' column is at index 5
            session['seamless_email'] = user[6]  
            session['seamless_password'] = user[7]  # Assuming 'seamless_password' column is at index 7
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('user_type', None)
    flash('You have been logged out.')
    return redirect(url_for('login'))

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        # Fetch seamless credentials from session
        seamless_email = session.get('seamless_email')
        seamless_password = session.get('seamless_password')

        try:
            # Use sys.executable to ensure the correct Python version is used
            result = subprocess.run([sys.executable, 'scripts.py', file_path, seamless_email, seamless_password], text=True, check=True)
            output = result.stdout
            flash('File processed successfully')
            print(output)
        except subprocess.CalledProcessError as e:
            error = e.stderr
            flash(f'Error: {error}')
        except Exception as e:
            flash(f'Unexpected error: {str(e)}')

        return redirect(url_for('index'))
    else:
        flash('Invalid file format')
        return redirect(request.url)


@app.route('/upload_email_file', methods=['POST'])
def upload_email_file():
    if 'file' not in request.files:
        flash('No file part')
        return redirect(request.url)

    file = request.files['file']
    if file.filename == '':
        flash('No selected file')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
 
        office_position = session.get('office_position')
        username = session.get('username')
        email = session.get('email')
        phone_number = session.get('phone_number')

        try:
            # Use sys.executable to ensure the correct Python version is used
            result = subprocess.run([
                sys.executable, 'emails.py', file_path,
                office_position, username, email, phone_number
            ], text=True, capture_output=True, check=True)

            # Capture stdout and display it
            output = result.stdout
            flash(f'Email file processed successfully: {output}')
            print(output)

        except subprocess.CalledProcessError as e:
            # Capture stderr and display it in case of an error
            error = e.stderr
            flash(f'Error: {error}')
            print(error)

        except Exception as e:
            # Catch unexpected exceptions
            flash(f'Unexpected error: {str(e)}')
            print(e)

        return redirect(url_for('email_page'))
    else:
        flash('Invalid file format')
        return redirect(request.url)

@app.route('/email', methods=['GET', 'POST'])
def email_page():
    if 'logged_in' in session and session.get('user_type') in ['admin', 'user']:
        if request.method == 'POST':
            return redirect(url_for('upload_email_file'))
        return render_template('email_page.html')
    return redirect(url_for('login'))

@app.route('/admin')
def admin_panel():
    if 'logged_in' in session and session.get('user_type') == 'admin':
        return render_template('admin.html')
    return redirect(url_for('login'))

# Routes for managing database tables
def get_db_connection():
    conn = psycopg2.connect(
        dbname='Blocks_lists',
        user='doadmin',
        password='AVNS_4B519UooZOlPzWnCaid',
        host='job-scounting-database-do-user-7586043-0.k.db.ondigitalocean.com',
        port = '25060'
    )
    return conn

@app.route('/admin/manage_users', methods=['GET', 'POST'])
def manage_users():
    if 'logged_in' in session and session.get('user_type') == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()

        if request.method == 'POST':
            if 'add_user' in request.form:
                # Handle add user
                username = request.form.get('username').strip()
                email = request.form.get('email').strip()
                password = request.form.get('password').strip()
                phone_number = request.form.get('phone_number').strip()
                status = request.form.get('status').strip()
                
                # Validate status
                if status not in ['admin', 'user']:
                    flash('Invalid status selected.')
                else:
                    try:
                        cursor.execute(
                            "INSERT INTO users (username, email, password, phone_number, status) VALUES (%s, %s, %s, %s, %s)",
                            (username, email, password, phone_number, status)
                        )
                        conn.commit()
                        flash('User added successfully.')
                    except psycopg2.IntegrityError:
                        flash('Username or email already exists.')
                        conn.rollback()
                    except Exception as e:
                        flash(f'Error: {str(e)}')
            
            elif 'delete_user' in request.form:
                # Handle delete user
                user_id = request.form.get('user_id').strip()
                if user_id:
                    cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
                    if cursor.rowcount == 0:
                        flash('No user found with the provided ID.')
                    else:
                        conn.commit()
                        flash('User deleted successfully.')
                else:
                    flash('Invalid user ID provided.')

        # Fetch user data
        cursor.execute("SELECT id, username, email, phone_number, status FROM users")
        users = cursor.fetchall()
        conn.close()

        return render_template('manage_users.html', users=users)
    return redirect(url_for('login'))

@app.route('/admin/table/<table_name>', methods=['GET', 'POST'])
def manage_table(table_name):
    if 'logged_in' in session and session.get('user_type') == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if request.method == 'POST':
            if 'add' in request.form:
                # Handle add record
                value = request.form.get('value').strip()
                if value:
                    # Check if record already exists
                    cursor.execute(f"SELECT 1 FROM {table_name} WHERE keyword = %s", (value,))
                    if cursor.fetchone():
                        flash('Record already exists in the database')
                    else:
                        query = f"INSERT INTO {table_name} (keyword) VALUES (%s)"
                        cursor.execute(query, (value,))
                        conn.commit()
                        flash('Record added successfully')
                else:
                    flash('Invalid value provided')

            elif 'delete' in request.form:
                # Handle delete record
                value = request.form.get('value').strip()
                if value:
                    query = f"DELETE FROM {table_name} WHERE keyword = %s"
                    cursor.execute(query, (value,))
                    if cursor.rowcount == 0:
                        flash('No record found with the provided value')
                    else:
                        conn.commit()
                        flash('Record deleted successfully')
                else:
                    flash('Invalid value provided')

        # Fetch table data
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        conn.close()

        return render_template('manage_table.html', table_name=table_name, rows=rows)
    return redirect(url_for('login'))


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        phone_number = request.form['phone_number']
        status = request.form['status']
        seamless_email = request.form['seamless_email']
        seamless_password = request.form['seamless_password']
        office_position = request.form['office_position']
        
        # Validate status
        if status not in ['admin', 'user']:
            flash('Invalid status selected.')
            return redirect(request.url)

        # Insert user data into the database
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO users (username, email, password, phone_number, status, seamless_email, seamless_password, office_position) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                (username, email, password, phone_number, status, seamless_email, seamless_password, office_position)
            )
            conn.commit()
            cursor.close()
            conn.close()
            flash('Signup successful. Please log in.')
            return redirect(url_for('login'))
        except psycopg2.IntegrityError:
            flash('Username or email already exists.')
            conn.rollback()
        except Exception as e:
            flash(f'Error: {str(e)}')
        
    return render_template('signup.html')

if __name__ == '__main__':
    if not os.path.exists(UPLOAD_FOLDER):
        os.makedirs(UPLOAD_FOLDER)
    app.run(debug=True)
