-- Users table: stores all user information
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    student_reg_number TEXT NOT NULL UNIQUE,
    username TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    phone_number TEXT,
    password TEXT NOT NULL, 
    role TEXT NOT NULL DEFAULT 'member' CHECK (role IN ('member', 'executive'))
);

-- Clubs table: stores information about student clubs and societies
CREATE TABLE IF NOT EXISTS clubs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    category TEXT NOT NULL DEFAULT 'General' CHECK (category IN ('Academic', 'Sports', 'Arts', 'Cultural', 'Technology', 'Social', 'General'))
);

-- Memberships table: many-to-many relationship between users and clubs
CREATE TABLE IF NOT EXISTS memberships (
    user_id INTEGER NOT NULL,
    club_id INTEGER NOT NULL,
    joined_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, club_id),
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
    FOREIGN KEY (club_id) REFERENCES clubs (id) ON DELETE CASCADE
);

-- Bookings table: stores room booking information
CREATE TABLE IF NOT EXISTS bookings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    club_id INTEGER NOT NULL,
    booked_by_user_id INTEGER NOT NULL,
    room_name TEXT NOT NULL,
    event_title TEXT NOT NULL,
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status TEXT NOT NULL DEFAULT 'Confirmed' CHECK (status IN ('Confirmed', 'Cancelled')),
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (club_id) REFERENCES clubs (id) ON DELETE CASCADE,
    FOREIGN KEY (booked_by_user_id) REFERENCES users (id) ON DELETE CASCADE
);


-- Sample users (password is 'password123' for all - remember to hash in production!)
INSERT OR IGNORE INTO users (student_reg_number, username, email, phone_number, password, role) VALUES
('2123456', 'john_doe', 'john.doe@warwick.ac.uk', '07123456789', 'password123', 'executive'),
('2123457', 'jane_smith', 'jane.smith@warwick.ac.uk', '07123456790', 'password123', 'member'),
('2123458', 'alice_wilson', 'alice.wilson@warwick.ac.uk', '07123456791', 'password123', 'executive'),
('2123459', 'bob_brown', 'bob.brown@warwick.ac.uk', '07123456792', 'password123', 'member'),
('2123460', 'charlie_davis', 'charlie.davis@warwick.ac.uk', '07123456793', 'password123', 'member');

-- Sample clubs
INSERT OR IGNORE INTO clubs (name, description, category) VALUES
('Computer Science Society', 'For students passionate about computing, programming, and technology. We organize coding competitions, tech talks, and networking events.', 'Technology'),
('Drama Society', 'University''s premier dramatic society. We put on several productions each year and welcome actors, directors, and technical crew of all levels.', 'Arts'),
('Football Club', 'The official university football club. We have teams for all skill levels and compete in various leagues throughout the academic year.', 'Sports'),
('Photography Club', 'For photography enthusiasts of all levels. We organize photo walks, workshops, and exhibitions to help members improve their skills.', 'Arts'),
('Business Society', 'Connecting future business leaders. We host speaker events, case competitions, and networking opportunities with industry professionals.', 'Academic'),
('International Students Association', 'Supporting international students at Warwick. We organize cultural events, social gatherings, and provide help with settling into university life.', 'Cultural');

-- Sample memberships (connecting users to clubs)
INSERT OR IGNORE INTO memberships (user_id, club_id) VALUES
(1, 1),
(1, 5), 
(2, 2),
(2, 4),
(3, 2),
(3, 6),
(4, 1), 
(4, 3),
(5, 4), 
(5, 6); 

-- Sample bookings
INSERT OR IGNORE INTO bookings (club_id, booked_by_user_id, room_name, event_title, start_time, end_time, status) VALUES
(1, 1, 'CS Building Room 1.04', 'Weekly Committee Meeting', '2025-09-01 18:00:00', '2025-09-01 20:00:00', 'Confirmed'),
(1, 1, 'Library Seminar Room 3', 'Python Workshop', '2025-09-05 14:00:00', '2025-09-05 16:00:00', 'Confirmed'),
(2, 3, 'Arts Centre Studio 1', 'Romeo and Juliet Rehearsal', '2025-09-02 19:00:00', '2025-09-02 22:00:00', 'Confirmed'),
(3, 4, 'Sports Hall', 'Football Training Session', '2025-09-03 16:00:00', '2025-09-03 18:00:00', 'Confirmed'),
(6, 3, 'Student Union Meeting Room 2', 'Cultural Festival Planning', '2025-09-04 17:00:00', '2025-09-04 19:00:00', 'Confirmed');