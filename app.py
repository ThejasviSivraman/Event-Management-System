import json
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, render_template, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Initialize the Flask application
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "your_default_secret_key")  # Use environment variable for better security

# Path to the JSON database
USER_DB = "users.json"
DATA_FILE = 'data.json'

# SMTP credentials loaded from environment variables
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER")  # Load SMTP_USER from .env
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")  # Load SMTP_PASSWORD from .env

# Load users from the JSON file
def load_users():
    try:
        with open(USER_DB, "r") as file:
            users = json.load(file)
    except FileNotFoundError:
        users = []

    # Check if the admin user exists; if not, create the admin user with password '1234'
    if not any(u["username"] == "admin" for u in users):
        # Hash password '1234' for admin user
        admin_password = generate_password_hash("1234")
        users.append({"username": "admin", "password": admin_password, "email": "admin@example.com", "role": "admin"})
        save_users(users)

    return users

# Save users to the JSON file
def save_users(users):
    with open(USER_DB, "w") as file:
        json.dump(users, file, indent=4)

# Function to send the email
def send_email_immediately(to_email, subject, description, date, time_input):
    """Function to send an email with the given details."""
    try:
        # Create email content
        email_body = f"""
        Subject: {subject}
        
        Description: {description}
        
        Date: {date}
        
        Time: {time_input}
        """
        
        msg = MIMEText(email_body)
        msg['Subject'] = "Scheduled Email"
        msg['From'] = SMTP_USER
        msg['To'] = to_email

        # Send email via SMTP server
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())

        return f"Email sent successfully to {to_email}!"

    except Exception as e:
        return f"Failed to send email: {str(e)}"

# Route for the home page (index). This will be the first page users see.
@app.route('/')
def home():
    """Render the home page."""
    return render_template('home.html')

# Route for login page
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Load users from JSON
        users = load_users()

        # Login logic
        user = next((u for u in users if u["username"] == username), None)
        if user and check_password_hash(user["password"], password):
            session['user'] = username
            session['role'] = user.get('role', 'user')  # Default role is 'user'
            flash("Login successful!", "success")
            if session['role'] == 'admin':
                return redirect(url_for('admin'))
            return redirect(url_for('index'))
        else:
            flash("Invalid username or password.", "danger")

    return render_template('login.html')

# Route for admin login page
@app.route('/admin-login', methods=['GET', 'POST'])
def admin_login():
    """Handle admin login."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        # Load users from JSON
        users = load_users()

        # Admin login logic
        user = next((u for u in users if u["username"] == username), None)
        if user and check_password_hash(user["password"], password) and user.get('role') == 'admin':
            session['user'] = username
            session['role'] = 'admin'
            flash("Admin login successful!", "success")
            return redirect(url_for('admin'))
        else:
            flash("Invalid admin credentials or you are not an admin.", "danger")

    return render_template('admin.html')

# Route for register page
@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle registration."""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        # Load users from JSON
        users = load_users()

        # Registration logic
        if any(u["username"] == username for u in users):
            flash("Username already exists. Please choose a different one.", "danger")
        else:
            hashed_password = generate_password_hash(password)
            users.append({"username": username, "password": hashed_password, "email": email, "role": "user"})
            save_users(users)
            flash("Registration successful! You can now log in.", "success")
            return redirect(url_for('login'))

    return render_template('register.html')

# Route for the home page (index) when logged in (only accessible when logged in)
@app.route('/index')
def index():
    """Render the home page (index). Only accessible when logged in."""
    if 'user' not in session:
        return redirect(url_for('login'))
    
    return render_template('index.html', user=session['user'])

# Route for sending email
@app.route('/send-email', methods=['GET', 'POST'])
def send_email():
    """Handle sending an email immediately with time and description."""
    message = None

    if request.method == 'POST':
        # Capture the form data
        to_email = request.form.get('to_email')
        subject = request.form.get('subject')
        description = request.form.get('description')
        date = request.form.get('date')
        time_input = request.form.get('time')

        # Simply send the email immediately
        try:
            send_email_immediately(to_email, subject, description, date, time_input)
            message = f"Email sent successfully to {to_email}!"
        except Exception as e:
            message = f"Failed to send email: {str(e)}"

    return render_template('send_email.html', message=message)

# Route for logout
@app.route('/logout')
def logout():
    """Logout the user and clear the session."""
    session.pop('user', None)
    session.pop('role', None)
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# Route for admin dashboard
@app.route('/admin', methods=['GET', 'POST'])
def admin_dashboard():
    """Admin dashboard, accessible only by admins."""
    if 'user' not in session or session.get('role') != 'admin':
        flash("Access denied. Admins only.", "danger")
        return redirect(url_for('login'))
    
    users = load_users()

    if request.method == 'POST':  
        # Admin actions: delete, promote, or add user
        action = request.form.get('action')
        username = request.form.get('username')

        if action == "delete":
            # Remove user from the database
            users = [user for user in users if user["username"] != username]
            save_users(users)
            flash(f"User '{username}' has been deleted.", "success")

        elif action == "promote":
            # Promote user to admin
            for user in users:
                if user["username"] == username:
                    user["role"] = "admin"
            save_users(users)
            flash(f"User '{username}' has been promoted to admin.", "success")

        elif action == "add":
            # Add a new user (admin only)
            new_username = request.form.get('new_username')
            new_password = request.form.get('new_password')
            new_email = request.form.get('new_email')

            # Check if the username already exists
            if any(u["username"] == new_username for u in users):
                flash("Username already exists. Please choose a different one.", "danger")
            else:
                hashed_password = generate_password_hash(new_password)
                users.append({"username": new_username, "password": hashed_password, "email": new_email, "role": "user"})
                save_users(users)
                flash(f"User '{new_username}' has been added.", "success")
    
    return render_template('admin.html', users=users)
@app.route('/about')
def about():
    """Render the booking page."""
    return render_template('about.html')

@app.route('/event')
def event():
    """Render the booking page."""
    return render_template('event.html')

@app.route('/contact')
def contact():
    """Render the booking page."""
    return render_template('contact.html')

@app.route('/booking')
def booking():
    """Render the booking page."""
    return render_template('booking.html')
@app.route('/viewbook')
def viewbooking():
    """Render the viewbooking page."""
    return render_template('viewbooking.html')
@app.route('/payment')
def payment():
    """Render the payment page."""
    return render_template('payment.html')
@app.route('/mess')
def message():
    """Render the payment page."""
    return render_template('send-message.html')
@app.route('/note')
def notification():
    """Render the payment page."""
    return render_template('notification.html')
@app.route('/log')
def log():
    """Render the payment page."""
    return render_template('log.html')
@app.route('/page')
def page():
    """Render the payment page."""
    return render_template('book.html')
if __name__ == '__main__':
    app.run(debug=True,port=5001)
