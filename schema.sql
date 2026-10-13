-- AttendX Database Schema (MySQL 8.0+)
-- Cloud-Based Attendance Management System

CREATE DATABASE IF NOT EXISTS attendx_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE attendx_db;

-- 1. Users Table (Authentication and Role-Based Access)
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('teacher', 'admin') NOT NULL DEFAULT 'teacher',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_users_email UNIQUE (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- 2. Students Table
CREATE TABLE IF NOT EXISTS students (
    id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    class_name VARCHAR(50) NOT NULL,
    section VARCHAR(20) NOT NULL,
    enrolled_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_students_class_sec (class_name, section),
    INDEX idx_students_name (name)
) ENGINE=InnoDB;

-- 3. Attendance Sessions Table (One session per class-section per date)
CREATE TABLE IF NOT EXISTS attendance_sessions (
    id VARCHAR(100) PRIMARY KEY,
    session_date DATE NOT NULL,
    class_name VARCHAR(50) NOT NULL,
    section VARCHAR(20) NOT NULL,
    recorded_by_user_id INT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_session_date_class_sec UNIQUE (session_date, class_name, section),
    CONSTRAINT fk_session_recorded_by FOREIGN KEY (recorded_by_user_id) 
        REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_session_date (session_date),
    INDEX idx_session_class_sec (class_name, section)
) ENGINE=InnoDB;

-- 4. Attendance Records Table (Individual student status per session)
CREATE TABLE IF NOT EXISTS attendance_records (
    id INT AUTO_INCREMENT PRIMARY KEY,
    session_id VARCHAR(100) NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    status ENUM('present', 'absent') NOT NULL,
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_session_student UNIQUE (session_id, student_id),
    CONSTRAINT fk_attendance_session FOREIGN KEY (session_id) 
        REFERENCES attendance_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_attendance_student FOREIGN KEY (student_id) 
        REFERENCES students(id) ON DELETE CASCADE,
    INDEX idx_attendance_student (student_id),
) ENGINE=InnoDB;

-- 5. Subjects Table
CREATE TABLE IF NOT EXISTS subjects (
    id INT AUTO_INCREMENT PRIMARY KEY,
    code VARCHAR(20) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_subjects_code (code)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 6. Assessments Table (Teacher/Admin managed)
CREATE TABLE IF NOT EXISTS assessments (
    id VARCHAR(100) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    type ENUM('Internal Exam', 'Mid Exam', 'Assignment', 'Lab Exam', 'Semester Exam') NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    class_name VARCHAR(50) NOT NULL,
    section VARCHAR(20) NOT NULL,
    assessment_date DATE NOT NULL,
    max_marks DECIMAL(5,2) NOT NULL,
    passing_marks DECIMAL(5,2) NOT NULL,
    status ENUM('draft', 'published', 'updated') NOT NULL DEFAULT 'draft',
    created_by_user_id INT NULL,
    published_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_assessment_created_by FOREIGN KEY (created_by_user_id) 
        REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_assessments_class_sec (class_name, section),
    INDEX idx_assessments_status (status),
    INDEX idx_assessments_subject (subject_name),
    INDEX idx_assessments_date (assessment_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- 7. Student Marks Table (Draft vs Published separation)
CREATE TABLE IF NOT EXISTS student_marks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    assessment_id VARCHAR(100) NOT NULL,
    student_id VARCHAR(50) NOT NULL,
    draft_marks DECIMAL(5,2) NULL,
    published_marks DECIMAL(5,2) NULL,
    is_published BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT uq_assessment_student UNIQUE (assessment_id, student_id),
    CONSTRAINT fk_marks_assessment FOREIGN KEY (assessment_id) 
        REFERENCES assessments(id) ON DELETE CASCADE,
    CONSTRAINT fk_marks_student FOREIGN KEY (student_id) 
        REFERENCES students(id) ON DELETE CASCADE,
    INDEX idx_student_marks_student (student_id),
    INDEX idx_student_marks_assessment (assessment_id),
    INDEX idx_student_marks_is_published (is_published)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
