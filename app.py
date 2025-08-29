from flask import Flask, render_template, request, redirect, url_for, session, flash, g
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'secret'

DATABASE = 'club_management.db'

def get_db():
    """Get database connection"""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row  # we use this to access columns by name
    return db

def init_db():
    """Initialize the database with the schema from schema.sql"""
    with app.app_context():
        db = get_db()
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()
        db.close()

def get_user_clubs(user_id):
    """Helper function to get all clubs a user belongs to"""
    db = get_db()
    clubs = db.execute('''
        SELECT c.* FROM clubs c
        JOIN memberships m ON c.id = m.club_id
        WHERE m.user_id = ?
    ''', (user_id,)).fetchall()
    db.close()
    return clubs

def get_user_role():
    """Helper function to get current user's role"""
    if 'user_id' not in session:
        return None
    
    db = get_db()
    user = db.execute('SELECT role FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    db.close()
    return user['role'] if user else None

def is_user_member_of_club(user_id, club_id):
    """Check if user is a member of a specific club"""
    db = get_db()
    membership = db.execute('''
        SELECT * FROM memberships 
        WHERE user_id = ? AND club_id = ?
    ''', (user_id, club_id)).fetchone()
    db.close()
    return membership is not None

@app.before_request
def load_logged_in_user():
    """Load user info before each request"""
    user_id = session.get('user_id')
    
    if user_id is None:
        g.user = None
    else:
        db = get_db()
        g.user = db.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
        db.close()

# Routes

@app.route('/')
def index():
    """Homepage - accessible to everyone"""
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    """User registration"""
    if request.method == 'POST':
        # Get the data from the form
        student_reg_number = request.form['student_reg_number']
        username = request.form['username']
        email = request.form['email']
        phone_number = request.form['phone_number']
        password = request.form['password']
        
        db = get_db()
        error = None
        
        # Basic validation
        if not student_reg_number or not username or not email or not password:
            error = 'All fields except phone number are required.'
        else:
            # Check if user already exists
            if db.execute('SELECT id FROM users WHERE username = ?', (username,)).fetchone():
                error = f'Username {username} is already taken.'
            elif db.execute('SELECT id FROM users WHERE email = ?', (email,)).fetchone():
                error = f'Email {email} is already registered.'
            elif db.execute('SELECT id FROM users WHERE student_reg_number = ?', (student_reg_number,)).fetchone():
                error = f'Student registration number {student_reg_number} is already registered.'
        
        if error is None:
            try:
                # Insert new user
                db.execute('''
                    INSERT INTO users (student_reg_number, username, email, phone_number, password, role)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (student_reg_number, username, email, phone_number, password, 'member'))
                db.commit()
                flash('Registration successful! Please log in.', 'success')
                return redirect(url_for('login'))
            except sqlite3.Error as e:
                error = f'Registration failed: {str(e)}'
        
        flash(error, 'danger')
        db.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        db = get_db()
        error = None

        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        
        if user is None:
            error = 'Incorrect username.'
        elif user['password'] != password:
            error = 'Incorrect password.'
        
        if error is None:
            # Login successful
            session.clear()
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            flash(f'Welcome back, {user["username"]}!', 'success')
            return redirect(url_for('dashboard'))
        
        flash(error, 'danger')
        db.close()
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    """User logout"""
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/clubs')
def clubs():
    """List all clubs - accessible to everyone"""
    db = get_db()
    all_clubs = db.execute('SELECT * FROM clubs ORDER BY name').fetchall()
    
    # If user is logged in, check membership status for each club
    club_memberships = {}
    if 'user_id' in session:
        for club in all_clubs:
            club_memberships[club['id']] = is_user_member_of_club(session['user_id'], club['id'])
    
    db.close()
    return render_template('clubs.html', clubs=all_clubs, club_memberships=club_memberships)

@app.route('/dashboard')
def dashboard():
    """User dashboard - requires login"""
    if 'user_id' not in session:
        flash('Please log in to access your dashboard.', 'warning')
        return redirect(url_for('login'))
    
    user_clubs = get_user_clubs(session['user_id'])
    upcoming_events = []
    if user_clubs:
        club_ids = [str(club['id']) for club in user_clubs]
        placeholders = ','.join('?' * len(club_ids))
        
        db = get_db()
        upcoming_events = db.execute(f'''
            SELECT b.*, c.name as club_name, u.username as booked_by_username
            FROM bookings b
            JOIN clubs c ON b.club_id = c.id
            JOIN users u ON b.booked_by_user_id = u.id
            WHERE b.club_id IN ({placeholders}) 
            AND b.status = 'Confirmed'
            AND datetime(b.start_time) >= datetime('now')
            ORDER BY b.start_time
            LIMIT 10
        ''', club_ids).fetchall()
        db.close()
    
    return render_template('dashboard.html', clubs=user_clubs, user_role=get_user_role(), upcoming_events=upcoming_events)

@app.route('/club/<int:club_id>')
def club_details(club_id):
    """Show club details and bookings - requires membership or executive role"""
    if 'user_id' not in session:
        flash('Please log in to view club details.', 'warning')
        return redirect(url_for('login'))
    
    db = get_db()
    membership = db.execute('''
        SELECT * FROM memberships 
        WHERE user_id = ? AND club_id = ?
    ''', (session['user_id'], club_id)).fetchone()
    
    if not membership:
        flash('You must be a member of this club to view its details.', 'danger')
        return redirect(url_for('dashboard'))
    
    club = db.execute('SELECT * FROM clubs WHERE id = ?', (club_id,)).fetchone()
    
    # Get club bookings (upcoming only)
    bookings = db.execute('''
        SELECT b.*, u.username as booked_by_username
        FROM bookings b
        JOIN users u ON b.booked_by_user_id = u.id
        WHERE b.club_id = ? AND b.status = 'Confirmed'
        AND datetime(b.start_time) >= datetime('now')
        ORDER BY b.start_time
    ''', (club_id,)).fetchall()
    
    db.close()
    
    return render_template('club_details.html', club=club, bookings=bookings, user_role=get_user_role())

@app.route('/join_club/<int:club_id>', methods=['POST'])
def join_club(club_id):
    """Join a club - requires login"""
    if 'user_id' not in session:
        flash('Please log in to join clubs.', 'warning')
        return redirect(url_for('login'))
    
    db = get_db()
    
    # Check if club exists
    club = db.execute('SELECT * FROM clubs WHERE id = ?', (club_id,)).fetchone()
    if not club:
        flash('Club not found.', 'danger')
        return redirect(url_for('clubs'))
    
    # Check if user is already a member
    existing_membership = db.execute('''
        SELECT * FROM memberships 
        WHERE user_id = ? AND club_id = ?
    ''', (session['user_id'], club_id)).fetchone()
    
    if existing_membership:
        flash(f'You are already a member of {club["name"]}.', 'info')
        return redirect(url_for('club_details', club_id=club_id))
    

    try:
        db.execute('''
            INSERT INTO memberships (user_id, club_id)
            VALUES (?, ?)
        ''', (session['user_id'], club_id))
        db.commit()
        flash(f'Successfully joined {club["name"]}! Welcome to the club.', 'success')
        return redirect(url_for('club_details', club_id=club_id))
    except sqlite3.Error as e:
        flash(f'Failed to join club: {str(e)}', 'danger')
        return redirect(url_for('clubs'))
    finally:
        db.close()

@app.route('/book/<int:club_id>', methods=['POST'])
def book_room(club_id):
    """Book a room - executives only"""
    if 'user_id' not in session or get_user_role() != 'executive':
        flash('Only club executives can book rooms.', 'danger')
        return redirect(url_for('club_details', club_id=club_id))
    
    # Get form data
    room_name = request.form['room_name']
    event_title = request.form['event_title']
    start_time = request.form['start_time']
    end_time = request.form['end_time']
    
    # Basic validation
    if not all([room_name, event_title, start_time, end_time]):
        flash('All fields are required for booking.', 'danger')
        return redirect(url_for('club_details', club_id=club_id))
    
    # Validate time format and logic
    try:
        start_dt = datetime.fromisoformat(start_time)
        end_dt = datetime.fromisoformat(end_time)
        
        if start_dt >= end_dt:
            flash('End time must be after start time.', 'danger')
            return redirect(url_for('club_details', club_id=club_id))
        
        if start_dt < datetime.now():
            flash('Cannot book rooms for past dates.', 'danger')
            return redirect(url_for('club_details', club_id=club_id))
            
    except ValueError:
        flash('Invalid date/time format.', 'danger')
        return redirect(url_for('club_details', club_id=club_id))
    
    # we need to check for overlapping bookings in the same room
    # This is important because in the future when we will have a rooms table, we need to make sure only
    # one booking exists for a room at a given time
    db = get_db()
    overlap = db.execute('''
        SELECT * FROM bookings
        WHERE room_name = ?
        AND status = 'Confirmed'
        AND (
            (? < end_time) AND (? > start_time)
        )
    ''', (room_name, start_time, end_time)).fetchone()
    if overlap:
        flash('This room is already booked for the selected time slot.', 'danger')
        db.close()
        return redirect(url_for('club_details', club_id=club_id))
    
    # Create booking
    try:
        db.execute('''
            INSERT INTO bookings (club_id, booked_by_user_id, room_name, event_title, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (club_id, session['user_id'], room_name, event_title, start_time, end_time, 'Confirmed'))
        db.commit()
        flash('Room booked successfully!', 'success')
    except sqlite3.Error as e:
        flash(f'Booking failed: {str(e)}', 'danger')
    finally:
        db.close()
    
    return redirect(url_for('club_details', club_id=club_id))

@app.route('/cancel_booking/<int:booking_id>')
def cancel_booking(booking_id):
    """Cancel a booking - executives only"""
    if 'user_id' not in session or get_user_role() != 'executive':
        flash('Only club executives can cancel bookings.', 'danger')
        return redirect(url_for('dashboard'))
    
    db = get_db()
    
    # Get the booking to check club ownership
    booking = db.execute('SELECT * FROM bookings WHERE id = ?', (booking_id,)).fetchone()
    
    if not booking:
        flash('Booking not found.', 'danger')
        return redirect(url_for('dashboard'))
    
    # Check if user is a member of the club that made this booking
    membership = db.execute('''
        SELECT * FROM memberships 
        WHERE user_id = ? AND club_id = ?
    ''', (session['user_id'], booking['club_id'])).fetchone()
    
    if not membership:
        flash('You can only cancel bookings for clubs you belong to.', 'danger')
        return redirect(url_for('dashboard'))
    
    try:
        db.execute('UPDATE bookings SET status = ? WHERE id = ?', ('Cancelled', booking_id))
        db.commit()
        flash('Booking cancelled successfully.', 'success')
    except sqlite3.Error as e:
        flash(f'Failed to cancel booking: {str(e)}', 'danger')
    finally:
        db.close()
    
    return redirect(url_for('club_details', club_id=booking['club_id']))

if __name__ == '__main__':
    # Initialize database if it doesn't exist
    if not os.path.exists(DATABASE):
        init_db()
        print("Database initialized!")
    app.run(debug=True)