from flask import Flask, render_template, request, redirect,jsonify, session, url_for, abort
import cv2
import numpy as np
import datetime
import base64
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from google.cloud.firestore_v1.base_query import FieldFilter
from flask_session import Session

app = Flask(__name__)
cred = credentials.Certificate("moodbook.json")
firebase_admin.initialize_app(cred)
db = firestore.client()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Load pre-trained face and smile cascade classifiers
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')

# Open log file in append mode
log_file = open('emotion_log.txt', 'a')

@app.route('/')
def intro():
    return render_template('intro.html')

@app.route('/signup')
def signup():
    return render_template('registration final.html')

@app.route('/register', methods=['POST'])
def register():
    name = request.form.get('name')
    surname = request.form.get('surname')
    age = request.form.get('age')
    gender = request.form.get('gender')
    email = request.form.get('email')
    password = request.form.get('password')
    confirm_password = request.form.get('confirm_password')

    if password and confirm_password and password == confirm_password:
        user_data = {
            'name': name,
            'surname': surname,
            'age': age,
            'gender': gender,
            'email': email,
            'password': password,
        }
        # Add a new document with auto-generated ID to a 'users' collection
        db.collection("users").document(request.form["email"]).set(user_data)
        # Passwords match, redirect to home page
        return redirect('/login')
    else:
        # Passwords don't match or one of them is missing
        return render_template('registration final.html', error="Passwords do not match")

@app.route('/login')
def login():
    return render_template('login final.html')

@app.route('/login', methods=['POST'])
def authenticate():
    print(locals())
    data = request.json
    email = data.get('email')
    password = data.get('password')
    image = data.get('image')
    print(image)
   
    # Query Firestore for user with provided username
    users_ref = db.collection('users')
    query = users_ref.where('email', '==', email).where('password', '==', password).limit(1).stream()
    user = next(query, None)
    print(f"Function invoked {email}")
    if user:
        session['email'] = email  # Store email in session
        session['image'] = image  # Store image in session
        # Successful login, redirect to home page with email as URL parameter
        return redirect(url_for('home'))
    else:
        # Incorrect email or password
        return render_template('login final.html', error="Passwords do not match or user doesn't exist")
    
    # This part of the code will never be reached, so you can remove it

@app.route('/home')
def home():
    email = session.get('email')  # Retrieve email from session
    image = session.get('image') 
    if email:
        return render_template('home.html', image_data=image, email=email)
    else:
        return redirect(url_for('login'))
    # Use the email to customize the user's experience, retrieve data, etc.

@app.route('/add_entry', methods=['POST'])
def handle_ajax_request():
    email = session.get('email')  # Retrieve email from session
    # Process the data as needed
    data = request.get_json()
    # Process data and post it to Firebase
    date = data.get('date')
    category = data.get('category')
    feedback = data.get('feedback')
    #email=session['email']
    #email = data.get('email')
    user_ref = db.collection('users').where('email', '==', email).limit(1)
    user = user_ref.get()
    #for user in user_data:
    # Insert the data into Firestore
    if not user:
        return jsonify({'error': 'Email not found'})
    
    user_doc_id = None
    for doc in user:
        user_doc_id = doc.id

    entry_ref = db.collection("users").document(user_doc_id).collection('entries').document()
    entry = {  
        "date": date,  
        "category": category,  
        "feedback": feedback,
        "email": email
    }
    entry_ref.set(entry)
    # Return a response which includes the ID of the newly created document
    return jsonify({'id': category, 'error': None}) 
#write a code to get the data back

@app.route('/entries')
def get_entries():
    # Assuming the user's email is stored in the session
    image = session.get('image')
    user_email = session.get('email')

    # Check if user email is available in session
    if user_email:
        # Query Firestore to get all entries for the specific user
        user_ref = db.collection('users').where('email', '==', user_email).limit(1)
        user = user_ref.get()

        # Check if user exists
        if user:
            user_doc = user[0]
            user_entries_ref = db.collection('users').document(user_doc.id).collection('entries')
            user_entries = user_entries_ref.stream()

            # Initialize a list to store the entries
            all_entries = []

            # Loop through each entry and append it to the list
            for entry in user_entries:
                entry_data = entry.to_dict()
                all_entries.append(entry_data)

            # Render a template to display the entries
            return render_template('home.html', entries=all_entries, image_data=image, email=user_email)
        else:
            # User not found, handle appropriately (redirect to login, show error message, etc.)
            return "User not found"
    else:
        # User email not available in session, handle appropriately (redirect to login, show error message, etc.)
        return "User email not available"

@app.route('/add_reminder', methods=['POST'])
def add_reminder():
    email = session.get('email')  # Retrieve email from session
    data = request.json
    rdate = data.get('date')
    reminder = data.get('reminder')

    # Check if user exists
    user_ref = db.collection('users').where('email', '==', email).limit(1)
    user = user_ref.get()
    if not user:
        return jsonify({'error': 'Email not found'})

    # Retrieve user ID
    user_doc_id = None
    for doc in user:
        user_doc_id = doc.id
    # Add the reminder to the reminders subcollection
    reminder_ref = db.collection("users").document(user_doc_id).collection('reminders').document()
    reminder_data = {
        "date": rdate,
        "reminder": reminder
    }
    reminder_ref.set(reminder_data)

    return jsonify({'status': 'success', 'error': None})

@app.route('/reminders')
def get_reminders():
    # Assuming the user's email is stored in the session
    image = session.get('image')
    user_email = session.get('email')

    # Check if user email is available in session
    if user_email:
        # Query Firestore to get all reminders for the specific user
        user_ref = db.collection('users').where('email', '==', user_email).limit(1)
        user = user_ref.get()

        # Check if user exists
        if user:
            user_doc = user[0]
            user_reminders_ref = db.collection('users').document(user_doc.id).collection('reminders')
            user_reminders = user_reminders_ref.get()

            user_entries_ref = db.collection('users').document(user_doc.id).collection('entries')
            user_entries = user_entries_ref.stream()

            # Initialize a list to store the reminders
            all_reminders = []
            all_entries = []

            # Loop through each reminder and append it to the list
            for reminder in user_reminders:
                reminder_data = reminder.to_dict()
                all_reminders.append(reminder_data)
            
            for entry in user_entries:
                entry_data = entry.to_dict()
                all_entries.append(entry_data)

            # Render a template to display the reminders
            return render_template('home.html', reminders=all_reminders,  entries= all_entries, image_data=image, email=user_email)
        else:
            # User not found, handle appropriately (redirect to login, show error message, etc.)
            return "User not found"
    else:
        # User email not available in session, handle appropriately (redirect to login, show error message, etc.)
        return "User email not available"

@app.route('/logout')
def logout():
    # Clear the session, effectively logging the user out
    session.clear()
    return redirect('/')
    #return render_template('intro.html')
           
@app.route('/detect_emotion', methods=['POST'])
def detect_emotion():
    try:
        # Decode base64 image from request
        image_data = request.json['image'].split(',')[1]
        nparr = np.frombuffer(base64.b64decode(image_data), np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        # Convert image to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # Detect faces in the image
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.3, minNeighbors=5)

        # Detect smiles or frowns in each face
        for (x, y, w, h) in faces:
            face_roi = gray[y:y+h, x:x+w]
            smile = smile_cascade.detectMultiScale(face_roi, scaleFactor=1.7, minNeighbors=20)

            # Check if smile or frown is detected
            if len(smile) > 0:
                detected_emotion = 'Smile'
            else:
                detected_emotion = 'Frown'
                
            print(f"Detected emotion: {detected_emotion}")  # Debugging statement

            # Log the detected emotion with timestamp
            log_entry = f"{detected_emotion} detected at {datetime.datetime.now()}\n"
            print(log_entry)  # Debugging statement
            log_file.write(log_entry)
            log_file.flush()  # Ensure data is written immediately
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True)