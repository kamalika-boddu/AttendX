-- AttendX Seed Data (MySQL 8.0+)
USE attendx_db;

-- Seed Default Demo Users (Password: teacher123 and admin123)
INSERT INTO users (name, email, password_hash, role)
VALUES 
('Professor Teacher', 'teacher@attendx.edu', 'scrypt:32768:8:1$ZBfU2wiP1cZt9TgW$0b853de15de0471e2f10fa2f4a23a852c820d53e6ba604dbf4332cf0c2ef7dcccd91278614b61cd692933fbb5b2545259b05cdfd33113ed6238354731f2ebd3a', 'teacher'),
('System Administrator', 'admin@attendx.edu', 'scrypt:32768:8:1$ZhvY7xbGR24PBj4k$015166e23e8e51893543424cab3bf6fc282cae1422b6760c2bb55a9f4a22465897788810771ef781f98559e87cc05a4cb4a97872701ecf5370361d65214f9cbc', 'admin')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Seed Initial Students
INSERT INTO students (id, name, class_name, section, enrolled_date)
VALUES
('STD-101', 'Alexander Wright', 'Class 10', 'A', '2026-01-10'),
('STD-102', 'Sophia Chen', 'Class 10', 'A', '2026-01-12'),
('STD-103', 'Marcus Johnson', 'Class 10', 'A', '2026-01-15'),
('STD-104', 'Emma Watson', 'Class 10', 'A', '2026-01-18'),
('STD-105', 'Liam Patel', 'Class 10', 'B', '2026-02-01'),
('STD-106', 'Olivia Gomez', 'Class 10', 'B', '2026-02-04'),
('STD-107', 'Ethan Hunt', 'Class 9', 'A', '2026-02-10'),
('STD-108', 'Ava Vance', 'Class 9', 'A', '2026-02-12')
ON DUPLICATE KEY UPDATE name = VALUES(name);

-- Seed Attendance Sessions
INSERT INTO attendance_sessions (id, session_date, class_name, section, recorded_by_user_id)
VALUES
('ATT-20260918-10A', '2026-09-18', 'Class 10', 'A', 1),
('ATT-20260919-10A', '2026-09-19', 'Class 10', 'A', 1),
('ATT-20260920-10A', '2026-09-20', 'Class 10', 'A', 1),
('ATT-20260920-10B', '2026-09-20', 'Class 10', 'B', 1)
ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP;

-- Seed Attendance Records
INSERT INTO attendance_records (session_id, student_id, status)
VALUES
-- Session ATT-20260918-10A
('ATT-20260918-10A', 'STD-101', 'present'),
('ATT-20260918-10A', 'STD-102', 'present'),
('ATT-20260918-10A', 'STD-103', 'absent'),
('ATT-20260918-10A', 'STD-104', 'present'),
-- Session ATT-20260919-10A
('ATT-20260919-10A', 'STD-101', 'present'),
('ATT-20260919-10A', 'STD-102', 'present'),
('ATT-20260919-10A', 'STD-103', 'present'),
('ATT-20260919-10A', 'STD-104', 'absent'),
-- Session ATT-20260920-10A
('ATT-20260920-10A', 'STD-101', 'present'),
('ATT-20260920-10A', 'STD-102', 'present'),
('ATT-20260920-10A', 'STD-103', 'present'),
('ATT-20260920-10A', 'STD-104', 'present'),
-- Session ATT-20260920-10B
('ATT-20260920-10B', 'STD-105', 'present'),
('ATT-20260920-10B', 'STD-106', 'absent')
ON DUPLICATE KEY UPDATE status = VALUES(status);
