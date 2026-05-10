from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key_here'

# Database initialization
def init_db():
    if not os.path.exists('orphanage.db'):
        conn = sqlite3.connect('orphanage.db')
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                is_admin BOOLEAN DEFAULT 0
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS donations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                donor_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT,
                amount REAL NOT NULL,
                purpose TEXT NOT NULL,
                payment_method TEXT NOT NULL,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS volunteers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fullname TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                role TEXT NOT NULL,
                message TEXT,
                date TEXT DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'pending'
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                description TEXT,
                count INTEGER DEFAULT 0,
                image_path TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS blog_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                publish_date TEXT DEFAULT CURRENT_TIMESTAMP,
                image_path TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                date TEXT NOT NULL,
                time TEXT NOT NULL,
                location TEXT NOT NULL,
                image_path TEXT
            )
        ''')

        # In the init_db() function, add this table creation:
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS residents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                age INTEGER NOT NULL,
                gender TEXT NOT NULL,
                admission_date TEXT NOT NULL,
                background TEXT,
                image_path TEXT,
                status TEXT DEFAULT 'active'
            )
        ''')
        
        # Insert admin user if not exists
        admin_password = generate_password_hash('admin123')
        cursor.execute('INSERT OR IGNORE INTO users (username, password, is_admin) VALUES (?, ?, ?)', 
                      ('admin', admin_password, 1))
        
        # Insert sample resources if not exists
        resources = [
            ('Quality Education', 'Learning resources including digital classrooms and tutoring', 120, 'images/IMG_1735.JPG'),
            ('Healthcare', 'Medical facilities with regular checkups and vaccinations', 80, 'images/IMG_1738.JPG'),
            ('Nutrition', 'Balanced meals served daily by nutritionists', 150, 'images/IMG_1736.JPG'),
            ('Safe Shelter', 'Fully furnished, child-friendly living spaces', 60, 'images/IMG_1743.JPG'),
            ('Clothing', 'New clothing items provided monthly', 200, 'images/IMG_1737.JPG'),
            ('Recreation', 'Toys, games, and sports equipment', 50, 'images/recreation.jpg')
        ]
        
        cursor.executemany('INSERT OR IGNORE INTO resources (name, description, count, image_path) VALUES (?, ?, ?, ?)', resources)
        
        conn.commit()
        conn.close()

# Initialize the database
init_db()

# Helper function to get database connection
def get_db_connection():
    conn = sqlite3.connect('orphanage.db')
    conn.row_factory = sqlite3.Row
    return conn

# Home page
@app.route('/')
def index():
    conn = get_db_connection()
    resources = conn.execute('SELECT * FROM resources').fetchall()
    blog_posts = conn.execute('SELECT * FROM blog_posts ORDER BY publish_date DESC LIMIT 3').fetchall()
    events = conn.execute('SELECT * FROM events WHERE date >= date("now") ORDER BY date ASC LIMIT 3').fetchall()
    conn.close()
    return render_template('index.html', resources=resources, blog_posts=blog_posts, events=events)

# Shop page
@app.route('/shop')
def shop():
    return render_template('shop.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['is_admin'] = bool(user['is_admin'])  # Ensure this is a boolean
            
            if remember:
                session.permanent = True
            
            if user['is_admin']:
                return redirect(url_for('dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            return jsonify({'error': 'Invalid username or password'}), 401
    
    return render_template('login.html')

# Logout
@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return redirect(url_for('index'))

# Signup page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = generate_password_hash(request.form['password'])
        
        conn = get_db_connection()
        try:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', 
                        (username, password))
            conn.commit()
            conn.close()
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('signup.html', error='Username already exists')
    
    return render_template('signup.html')

# Dashboard
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session or not session['is_admin']:
        return redirect(url_for('login'))
    
    conn = get_db_connection()
    
    # Get stats for dashboard
    total_donations = conn.execute('SELECT SUM(amount) FROM donations WHERE status = "completed"').fetchone()[0] or 0
    active_volunteers = conn.execute('SELECT COUNT(*) FROM volunteers WHERE status = "approved"').fetchone()[0]
    children_supported = 512  # This could be from another table in a real application
    upcoming_events = conn.execute('SELECT COUNT(*) FROM events WHERE date >= date("now")').fetchone()[0]
    
    # Recent donations
    recent_donations = conn.execute('''
        SELECT id, donor_name, amount, purpose, date, status 
        FROM donations 
        ORDER BY date DESC 
        LIMIT 5
    ''').fetchall()
    
    # Recent volunteers
    recent_volunteers = conn.execute('''
        SELECT id, fullname, email, role, date, status 
        FROM volunteers 
        ORDER BY date DESC 
        LIMIT 5
    ''').fetchall()
    
    # Resources
    resources = conn.execute('SELECT * FROM resources').fetchall()
    
    # All donations for donations tab
    all_donations = conn.execute('''
        SELECT id, donor_name, email, amount, purpose, date, payment_method, status 
        FROM donations 
        ORDER BY date DESC
    ''').fetchall()
    
    # All volunteers for volunteers tab
    all_volunteers = conn.execute('''
        SELECT id, fullname, email, phone, role, date, status 
        FROM volunteers 
        ORDER BY date DESC
    ''').fetchall()
    
    # Blog posts
    blog_posts = conn.execute('''
        SELECT id, title, author, publish_date 
        FROM blog_posts 
        ORDER BY publish_date DESC
    ''').fetchall()
    
    # Events
    events = conn.execute('''
        SELECT id, title, date, location, 
               CASE WHEN date >= date('now') THEN 'upcoming' ELSE 'past' END as status
        FROM events
        ORDER BY date
    ''').fetchall()

    residents = conn.execute('''
        SELECT id, name, age, gender, admission_date, status 
        FROM residents 
        ORDER BY name
    ''').fetchall()
    
    conn.close()
    
    return render_template('dashboard.html', 
                         total_donations=total_donations,
                         active_volunteers=active_volunteers,
                         children_supported=children_supported,
                         upcoming_events=upcoming_events,
                         recent_donations=recent_donations,
                         recent_volunteers=recent_volunteers,
                         resources=resources,
                         all_donations=all_donations,
                         all_volunteers=all_volunteers,
                         blog_posts=blog_posts,
                         events=events,
                         residents=residents)
    

# Handle volunteer form submission from index.html
@app.route('/submit_volunteer', methods=['POST'])
def submit_volunteer():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        phone = request.form['phone']
        role = request.form['volunteer_type']
        message = request.form['message']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO volunteers (fullname, email, phone, role, message)
            VALUES (?, ?, ?, ?, ?)
        ''', (fullname, email, phone, role, message))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Volunteer application submitted successfully'})
    
    return jsonify({'success': False, 'message': 'Invalid request'})

# Handle donation form submission from index.html
@app.route('/submit_donation', methods=['POST'])
def submit_donation():
    if request.method == 'POST':
        donor_name = request.form['fullname']
        email = request.form['email']
        phone = request.form.get('phone', '')
        amount = float(request.form['amount'])
        purpose = request.form['purpose']
        payment_method = request.form['payment_method']
        
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO donations (donor_name, email, phone, amount, purpose, payment_method, status)
            VALUES (?, ?, ?, ?, ?, ?, 'completed')
        ''', (donor_name, email, phone, amount, purpose, payment_method))
        conn.commit()
        conn.close()
        
        return jsonify({
            'success': True,
            'message': 'Donation processed successfully',
            'donor_name': donor_name,
            'amount': amount,
            'purpose': purpose
        })
    
    return jsonify({'success': False, 'message': 'Invalid request'})

# API endpoint to get stats for dashboard
@app.route('/api/stats')
def get_stats():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    conn = get_db_connection()
    
    total_donations = conn.execute('SELECT SUM(amount) FROM donations WHERE status = "completed"').fetchone()[0] or 0
    active_volunteers = conn.execute('SELECT COUNT(*) FROM volunteers WHERE status = "approved"').fetchone()[0]
    children_supported = 512  # Static for demo
    upcoming_events = conn.execute('SELECT COUNT(*) FROM events WHERE date >= date("now")').fetchone()[0]
    
    conn.close()
    
    return jsonify({
        'total_donations': total_donations,
        'active_volunteers': active_volunteers,
        'children_supported': children_supported,
        'upcoming_events': upcoming_events
    })

# API endpoint to add new resource
@app.route('/api/resources/add', methods=['POST'])
def add_resource():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    name = request.form.get('name')
    description = request.form.get('description')
    count = request.form.get('count', 0)
    image_path = request.form.get('image_path', '')
    
    if not name or not description:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO resources (name, description, count, image_path)
        VALUES (?, ?, ?, ?)
    ''', (name, description, count, image_path))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to update resource
@app.route('/api/resources/update', methods=['POST'])
def update_resource():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    resource_id = request.form.get('id')
    new_count = request.form.get('count')
    name = request.form.get('name')
    description = request.form.get('description')
    image_path = request.form.get('image_path')
    
    if not resource_id:
        return jsonify({'error': 'Missing resource ID'}), 400
    
    conn = get_db_connection()
    
    if new_count:
        conn.execute('UPDATE resources SET count = ? WHERE id = ?', (new_count, resource_id))
    if name:
        conn.execute('UPDATE resources SET name = ? WHERE id = ?', (name, resource_id))
    if description:
        conn.execute('UPDATE resources SET description = ? WHERE id = ?', (description, resource_id))
    if image_path:
        conn.execute('UPDATE resources SET image_path = ? WHERE id = ?', (image_path, resource_id))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to delete resource
@app.route('/api/resources/delete', methods=['POST'])
def delete_resource():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    resource_id = request.form.get('id')
    
    if not resource_id:
        return jsonify({'error': 'Missing resource ID'}), 400
    
    conn = get_db_connection()
    conn.execute('DELETE FROM resources WHERE id = ?', (resource_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to add/edit blog post
@app.route('/api/blog', methods=['POST'])
def manage_blog():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    post_id = request.form.get('id')
    title = request.form.get('title')
    content = request.form.get('content')
    
    if not title or not content:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    if post_id:  # Update existing post
        conn.execute('''
            UPDATE blog_posts 
            SET title = ?, content = ?
            WHERE id = ?
        ''', (title, content, post_id))
    else:  # Create new post
        conn.execute('''
            INSERT INTO blog_posts (title, author, content)
            VALUES (?, ?, ?)
        ''', (title, session['username'], content))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to delete blog post
@app.route('/api/blog/delete', methods=['POST'])
def delete_blog():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    post_id = request.form.get('id')
    
    if not post_id:
        return jsonify({'error': 'Missing post ID'}), 400
    
    conn = get_db_connection()
    conn.execute('DELETE FROM blog_posts WHERE id = ?', (post_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to add/edit event
@app.route('/api/events', methods=['POST'])
def manage_event():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    event_id = request.form.get('id')
    title = request.form.get('title')
    description = request.form.get('description')
    date = request.form.get('date')
    time = request.form.get('time')
    location = request.form.get('location')
    
    if not title or not description or not date or not time or not location:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    if event_id:  # Update existing event
        conn.execute('''
            UPDATE events 
            SET title = ?, description = ?, date = ?, time = ?, location = ?
            WHERE id = ?
        ''', (title, description, date, time, location, event_id))
    else:  # Create new event
        conn.execute('''
            INSERT INTO events (title, description, date, time, location)
            VALUES (?, ?, ?, ?, ?)
        ''', (title, description, date, time, location))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to delete event
@app.route('/api/events/delete', methods=['POST'])
def delete_event():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    event_id = request.form.get('id')
    
    if not event_id:
        return jsonify({'error': 'Missing event ID'}), 400
    
    conn = get_db_connection()
    conn.execute('DELETE FROM events WHERE id = ?', (event_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to update volunteer status
@app.route('/api/volunteers/update', methods=['POST'])
def update_volunteer():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    volunteer_id = request.form.get('id')
    new_status = request.form.get('status')
    
    if not volunteer_id or not new_status:
        return jsonify({'error': 'Missing parameters'}), 400
    
    conn = get_db_connection()
    conn.execute('UPDATE volunteers SET status = ? WHERE id = ?', (new_status, volunteer_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to delete volunteer
@app.route('/api/volunteers/delete', methods=['POST'])
def delete_volunteer():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    volunteer_id = request.form.get('id')
    
    if not volunteer_id:
        return jsonify({'error': 'Missing volunteer ID'}), 400
    
    conn = get_db_connection()
    conn.execute('DELETE FROM volunteers WHERE id = ?', (volunteer_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to update donation status
@app.route('/api/donations/update', methods=['POST'])
def update_donation():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    donation_id = request.form.get('id')
    new_status = request.form.get('status')
    
    if not donation_id or not new_status:
        return jsonify({'error': 'Missing parameters'}), 400
    
    conn = get_db_connection()
    conn.execute('UPDATE donations SET status = ? WHERE id = ?', (new_status, donation_id))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to delete donation
@app.route('/api/donations/delete', methods=['POST'])
def delete_donation():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    donation_id = request.form.get('id')
    
    if not donation_id:
        return jsonify({'error': 'Missing donation ID'}), 400
    
    conn = get_db_connection()
    conn.execute('DELETE FROM donations WHERE id = ?', (donation_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# Add these to your app.py

@app.route('/api/blog/get')
def get_blog_post():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    post_id = request.args.get('id')
    if not post_id:
        return jsonify({'error': 'Missing post ID'}), 400
    
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
    conn.close()
    
    if post:
        return jsonify(dict(post))
    else:
        return jsonify({'error': 'Post not found'}), 404

@app.route('/api/events/get')
def get_event():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    event_id = request.args.get('id')
    if not event_id:
        return jsonify({'error': 'Missing event ID'}), 400
    
    conn = get_db_connection()
    event = conn.execute('SELECT * FROM events WHERE id = ?', (event_id,)).fetchone()
    conn.close()
    
    if event:
        return jsonify(dict(event))
    else:
        return jsonify({'error': 'Event not found'}), 404
    

    # API endpoint to add/edit resident
@app.route('/api/residents', methods=['POST'])
def manage_resident():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    resident_id = request.form.get('id')
    name = request.form.get('name')
    age = request.form.get('age')
    gender = request.form.get('gender')
    admission_date = request.form.get('admission_date')
    background = request.form.get('background', '')
    image_path = request.form.get('image_path', '')
    status = request.form.get('status', 'active')
    
    if not name or not age or not gender or not admission_date:
        return jsonify({'error': 'Missing required fields'}), 400
    
    conn = get_db_connection()
    
    if resident_id:  # Update existing resident
        conn.execute('''
            UPDATE residents 
            SET name = ?, age = ?, gender = ?, admission_date = ?, 
                background = ?, image_path = ?, status = ?
            WHERE id = ?
        ''', (name, age, gender, admission_date, background, image_path, status, resident_id))
    else:  # Create new resident
        conn.execute('''
            INSERT INTO residents (name, age, gender, admission_date, background, image_path, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (name, age, gender, admission_date, background, image_path, status))
    
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

# API endpoint to get resident
@app.route('/api/residents/get')
def get_resident():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    resident_id = request.args.get('id')
    if not resident_id:
        return jsonify({'error': 'Missing resident ID'}), 400
    
    conn = get_db_connection()
    resident = conn.execute('SELECT * FROM residents WHERE id = ?', (resident_id,)).fetchone()
    conn.close()
    
    if resident:
        return jsonify(dict(resident))
    else:
        return jsonify({'error': 'Resident not found'}), 404

# API endpoint to delete resident
@app.route('/api/residents/delete', methods=['POST'])
def delete_resident():
    if 'user_id' not in session or not session['is_admin']:
        return jsonify({'error': 'Unauthorized'}), 401
    
    resident_id = request.form.get('id')
    
    if not resident_id:
        return jsonify({'error': 'Missing resident ID'}), 400
    
    conn = get_db_connection()
    conn.execute('DELETE FROM residents WHERE id = ?', (resident_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True)