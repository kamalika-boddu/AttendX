import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import execute_query, execute_non_query
from config import Config

def migrate():
    print("Running Marks Management database migration...")

    # 1. Create subjects table
    execute_non_query("""
    CREATE TABLE IF NOT EXISTS subjects (
        id INT AUTO_INCREMENT PRIMARY KEY,
        code VARCHAR(20) NOT NULL UNIQUE,
        name VARCHAR(100) NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_subjects_code (code)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """)

    # 2. Create assessments table
    execute_non_query("""
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
    """)

    # 3. Create student_marks table
    execute_non_query("""
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
    """)

    print("Tables subjects, assessments, student_marks created successfully!")

    # 4. Seed standard subjects
    initial_subjects = [
        ('MATH101', 'Mathematics'),
        ('PHY101', 'Physics'),
        ('CHEM101', 'Chemistry'),
        ('BIO101', 'Biology'),
        ('ENG101', 'English'),
        ('CS101', 'Computer Science'),
        ('SOC101', 'Social Science')
    ]

    for code, name in initial_subjects:
        execute_non_query("""
        INSERT INTO subjects (code, name) VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE name = VALUES(name);
        """, (code, name))
    print(f"Seeded {len(initial_subjects)} subjects.")

    # 5. Seed sample assessments and marks
    # Sample 1: Class 10-A, Mathematics - Mid Exam (PUBLISHED)
    asm1_id = "ASM-20260925-10A-MATH-MID1"
    execute_non_query("""
    INSERT INTO assessments (id, name, type, subject_name, class_name, section, assessment_date, max_marks, passing_marks, status, created_by_user_id, published_at)
    VALUES (%s, 'Mid Term Exam 1', 'Mid Exam', 'Mathematics', 'Class 10', 'A', '2026-09-25', 100.00, 35.00, 'published', 1, '2026-09-26 10:00:00')
    ON DUPLICATE KEY UPDATE status = VALUES(status), max_marks = VALUES(max_marks);
    """, (asm1_id,))

    # Marks for Class 10-A students in Mid Term Exam 1
    # Alexander Wright: 92/100, Sophia Chen: 88/100, Marcus Johnson: 32/100 (failed), Emma Watson: 74/100
    sample_marks_1 = [
        ('STD-101', 92.00),
        ('STD-102', 88.00),
        ('STD-103', 32.00),
        ('STD-104', 74.00),
        ('STD-105', 81.00),
        ('STD-106', 65.00),
        ('STD-107', 78.00),
        ('STD-108', 95.00),
        ('STD-109', 54.00),
        ('STD-110', 89.00),
        ('STD-111', 100.00),
        ('STD-112', 91.00),
        ('STD-113', 70.00),
        ('STD-114', 85.00),
        ('STD-115', 96.00),
    ]
    for stu_id, mks in sample_marks_1:
        execute_non_query("""
        INSERT INTO student_marks (assessment_id, student_id, draft_marks, published_marks, is_published)
        VALUES (%s, %s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE draft_marks = VALUES(draft_marks), published_marks = VALUES(published_marks), is_published = TRUE;
        """, (asm1_id, stu_id, mks, mks))

    # Sample 2: Class 10-A, Physics - Internal Assessment 1 (PUBLISHED)
    asm2_id = "ASM-20261002-10A-PHY-IA1"
    execute_non_query("""
    INSERT INTO assessments (id, name, type, subject_name, class_name, section, assessment_date, max_marks, passing_marks, status, created_by_user_id, published_at)
    VALUES (%s, 'Unit Test 1', 'Internal Exam', 'Physics', 'Class 10', 'A', '2026-10-02', 25.00, 10.00, 'published', 1, '2026-10-03 14:30:00')
    ON DUPLICATE KEY UPDATE status = VALUES(status);
    """, (asm2_id,))

    sample_marks_2 = [
        ('STD-101', 23.50),
        ('STD-102', 21.00),
        ('STD-103', 14.00),
        ('STD-104', 19.50),
    ]
    for stu_id, mks in sample_marks_2:
        execute_non_query("""
        INSERT INTO student_marks (assessment_id, student_id, draft_marks, published_marks, is_published)
        VALUES (%s, %s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE draft_marks = VALUES(draft_marks), published_marks = VALUES(published_marks), is_published = TRUE;
        """, (asm2_id, stu_id, mks, mks))

    # Sample 3: Class 10-A, Computer Science - Assignment 1 (DRAFT - must NOT be visible to students!)
    asm3_id = "ASM-20261008-10A-CS-ASG1"
    execute_non_query("""
    INSERT INTO assessments (id, name, type, subject_name, class_name, section, assessment_date, max_marks, passing_marks, status, created_by_user_id, published_at)
    VALUES (%s, 'Python Algorithms Assignment', 'Assignment', 'Computer Science', 'Class 10', 'A', '2026-10-08', 50.00, 20.00, 'draft', 1, NULL)
    ON DUPLICATE KEY UPDATE status = VALUES(status);
    """, (asm3_id,))

    sample_marks_3 = [
        ('STD-101', 48.00),
        ('STD-102', 45.00),
        ('STD-103', 38.00),
    ]
    for stu_id, mks in sample_marks_3:
        execute_non_query("""
        INSERT INTO student_marks (assessment_id, student_id, draft_marks, published_marks, is_published)
        VALUES (%s, %s, %s, NULL, FALSE)
        ON DUPLICATE KEY UPDATE draft_marks = VALUES(draft_marks), published_marks = NULL, is_published = FALSE;
        """, (asm3_id, stu_id, mks))

    # Sample 4: Class 10-B, Mathematics - Mid Term (PUBLISHED)
    asm4_id = "ASM-20260925-10B-MATH-MID1"
    execute_non_query("""
    INSERT INTO assessments (id, name, type, subject_name, class_name, section, assessment_date, max_marks, passing_marks, status, created_by_user_id, published_at)
    VALUES (%s, 'Mid Term Exam 1', 'Mid Exam', 'Mathematics', 'Class 10', 'B', '2026-09-25', 100.00, 35.00, 'published', 1, '2026-09-26 11:00:00')
    ON DUPLICATE KEY UPDATE status = VALUES(status);
    """, (asm4_id,))

    sample_marks_4 = [
        ('STD-201', 86.00),
        ('STD-202', 79.00),
        ('STD-203', 91.00),
    ]
    for stu_id, mks in sample_marks_4:
        execute_non_query("""
        INSERT INTO student_marks (assessment_id, student_id, draft_marks, published_marks, is_published)
        VALUES (%s, %s, %s, %s, TRUE)
        ON DUPLICATE KEY UPDATE draft_marks = VALUES(draft_marks), published_marks = VALUES(published_marks), is_published = TRUE;
        """, (asm4_id, stu_id, mks, mks))

    print("Sample assessments (published and draft) seeded successfully!")

if __name__ == '__main__':
    migrate()
