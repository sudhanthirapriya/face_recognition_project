import os
from flask import Flask, request, jsonify, render_template, redirect, url_for
import sqlite3
from deepface import DeepFace
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from PIL import Image

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'supersecretkey')

# Flask-Login setup
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, phone, name, email):
        self.id = id
        self.phone = phone
        self.name = name
        self.email = email

# Flask-Login: Load user from the database
@login_manager.user_loader
def load_user(user_id):
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        user = User(row[0], row[1], row[3], row[4])
        return user
    return None

# Ensure the uploads directory exists
UPLOAD_FOLDER = os.path.join(app.root_path, 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5 MB limit for uploads

# Handle file size errors
@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({'status': 'danger', 'message': 'File is too large. Maximum size is 5MB.'}), 413

# Initialize the database with schema checking
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()

    # Create the users table if it doesn't exist
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  phone TEXT NOT NULL UNIQUE,
                  password TEXT NOT NULL,
                  name TEXT NOT NULL,
                  dob TEXT NOT NULL,
                  email TEXT NOT NULL,
                  blood_group TEXT NOT NULL,
                  image_path TEXT NOT NULL)''')

    conn.commit()
    conn.close()

init_db()

# Load DeepFace model once at startup
try:
    face_model = DeepFace.build_model('Facenet')  # Load a lighter model (Facenet)
except Exception as e:
    print(f"Error loading DeepFace model: {e}")
    face_model = None

# Utility function to resize images before processing
def resize_image(image_path, max_size=(500, 500)):
    with Image.open(image_path) as img:
        img.thumbnail(max_size)
        img.save(image_path)

# Registration Route with DeepFace check
@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    dob = request.form.get('dob')
    email = request.form.get('email')
    blood_group = request.form.get('blood_group')
    phone = request.form.get('phone')
    password = request.form.get('password')
    photo = request.files.get('photo')

    # Validate all required fields
    if not all([name, dob, email, blood_group, phone, password, photo]):
        return jsonify({'status': 'danger', 'message': 'Please provide all required fields.'}), 400

    # Save the uploaded image
    filename = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{photo.filename}"
    photo_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    photo.save(photo_path)

    # Resize the image to reduce memory usage
    resize_image(photo_path)

    # Check if the face already exists in the database using DeepFace
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT id, image_path, phone FROM users")
    rows = c.fetchall()

    for row in rows:
        existing_user_id, existing_image_path, existing_phone = row
        try:
            if face_model:
                result = DeepFace.verify(img1_path=photo_path, img2_path=existing_image_path, model_name='Facenet', enforce_detection=False, model=face_model)
                if result['verified']:
                    os.remove(photo_path)  # Remove the new image after detection
                    conn.close()
                    return jsonify({'status': 'info', 'message': f"Image found in the database. The phone number is {existing_phone}."}), 200
        except Exception as e:
            continue  # Skip any errors during verification

    # If no matching face is found, proceed with registration
    hashed_password = generate_password_hash(password)

    try:
        # Insert new user into the database
        c.execute('INSERT INTO users (phone, password, name, dob, email, blood_group, image_path) VALUES (?, ?, ?, ?, ?, ?, ?)',
                  (phone, hashed_password, name, dob, email, blood_group, photo_path))
        conn.commit()
    except sqlite3.IntegrityError:
        # Handle duplicate phone numbers
        os.remove(photo_path)
        conn.close()
        return jsonify({'status': 'danger', 'message': 'Phone number already registered.'}), 400

    conn.close()

    return jsonify({'status': 'success', 'message': 'Registration successful. You can now log in with your phone number and password.'}), 200

# Login Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        phone = request.form.get('phone')
        password = request.form.get('password')

        if not phone or not password:
            return jsonify({'status': 'danger', 'message': 'Please provide phone number and password.'}), 400

        # Connect to the database and fetch user details
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE phone=?", (phone,))
        row = c.fetchone()
        conn.close()

        if row and check_password_hash(row[2], password):  # Check the hashed password
            user = User(row[0], row[1], row[3], row[4])
            login_user(user)
            return jsonify({'status': 'success', 'message': 'Login successful.'}), 200
        else:
            return jsonify({'status': 'danger', 'message': 'Invalid phone number or password.'}), 400
    else:
        return render_template('login.html')

# Dashboard Route
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', name=current_user.name)

# Logout Route
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return render_template('logout.html')

# Main route for index page
@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))  # Get the PORT from the environment or default to 5000
    app.run(host='0.0.0.0', port=port, debug=False)