import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db import execute_query, execute_non_query
from auth_utils import hash_password

STUDENTS_DATA = [
    # Class 10 - C
    {"id": "STD-221", "name": "Lucas Vance", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-15"},
    {"id": "STD-222", "name": "Chloe Bennett", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-16"},
    {"id": "STD-223", "name": "Henry Ford", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-18"},
    {"id": "STD-224", "name": "Maya Lin", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-20"},
    {"id": "STD-225", "name": "Leo Tolstoy", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-22"},
    {"id": "STD-226", "name": "Zoe Saldana", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-25"},
    {"id": "STD-227", "name": "Oscar Wilde", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-01-28"},
    {"id": "STD-228", "name": "Lily Potter", "class_name": "Class 10", "section": "C", "enrolled_date": "2026-02-01"},

    # Class 10 - D
    {"id": "STD-241", "name": "Felix Mendelssohn", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-15"},
    {"id": "STD-242", "name": "Nora Jones", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-17"},
    {"id": "STD-243", "name": "Julian Assange", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-19"},
    {"id": "STD-244", "name": "Stella McCartney", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-22"},
    {"id": "STD-245", "name": "Arthur Conan Doyle", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-24"},
    {"id": "STD-246", "name": "Clara Schumann", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-26"},
    {"id": "STD-247", "name": "Victor Hugo", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-01-29"},
    {"id": "STD-248", "name": "Ruby Bridges", "class_name": "Class 10", "section": "D", "enrolled_date": "2026-02-02"},

    # Class 9 - B
    {"id": "STD-321", "name": "Benjamin Franklin", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-10"},
    {"id": "STD-322", "name": "Abigail Adams", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-12"},
    {"id": "STD-323", "name": "Samuel Adams", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-14"},
    {"id": "STD-324", "name": "Hannah Arendt", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-17"},
    {"id": "STD-325", "name": "Gabriel Garcia", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-20"},
    {"id": "STD-326", "name": "Elena Rostova", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-23"},
    {"id": "STD-327", "name": "Caleb Thorne", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-26"},
    {"id": "STD-328", "name": "Violet Baudelaire", "class_name": "Class 9", "section": "B", "enrolled_date": "2026-01-30"},

    # Class 9 - C
    {"id": "STD-341", "name": "Thomas Edison", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-11"},
    {"id": "STD-342", "name": "Ada Coleman", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-13"},
    {"id": "STD-343", "name": "Dylan Thomas", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-16"},
    {"id": "STD-344", "name": "Hazel Grace", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-18"},
    {"id": "STD-345", "name": "Jasper Hale", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-21"},
    {"id": "STD-346", "name": "Ivy Valentine", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-24"},
    {"id": "STD-347", "name": "Tristan Evans", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-27"},
    {"id": "STD-348", "name": "Aurora Borealis", "class_name": "Class 9", "section": "C", "enrolled_date": "2026-01-31"},

    # Class 9 - D
    {"id": "STD-361", "name": "Zachary Taylor", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-12"},
    {"id": "STD-362", "name": "Harper Lee", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-15"},
    {"id": "STD-363", "name": "Xavier Woods", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-18"},
    {"id": "STD-364", "name": "Sienna Miller", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-20"},
    {"id": "STD-365", "name": "Theodore Roosevelt", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-23"},
    {"id": "STD-366", "name": "Piper Chapman", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-25"},
    {"id": "STD-367", "name": "Miles Davis", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-01-28"},
    {"id": "STD-368", "name": "Freya Mikaelson", "class_name": "Class 9", "section": "D", "enrolled_date": "2026-02-01"},

    # Class 8 - A
    {"id": "STD-401", "name": "Oliver Twist", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-10"},
    {"id": "STD-402", "name": "Alice Kingsley", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-12"},
    {"id": "STD-403", "name": "Peter Parker", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-15"},
    {"id": "STD-404", "name": "Wendy Darling", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-18"},
    {"id": "STD-405", "name": "Bruce Wayne", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-20"},
    {"id": "STD-406", "name": "Diana Prince", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-22"},
    {"id": "STD-407", "name": "Clark Kent", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-25"},
    {"id": "STD-408", "name": "Lois Lane", "class_name": "Class 8", "section": "A", "enrolled_date": "2026-01-28"},

    # Class 8 - B
    {"id": "STD-421", "name": "Barry Allen", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-11"},
    {"id": "STD-422", "name": "Iris West", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-14"},
    {"id": "STD-423", "name": "Hal Jordan", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-17"},
    {"id": "STD-424", "name": "Carol Ferris", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-19"},
    {"id": "STD-425", "name": "Arthur Curry", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-21"},
    {"id": "STD-426", "name": "Mera Queen", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-24"},
    {"id": "STD-427", "name": "Victor Stone", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-26"},
    {"id": "STD-428", "name": "Raven Roth", "class_name": "Class 8", "section": "B", "enrolled_date": "2026-01-29"},

    # Class 8 - C
    {"id": "STD-441", "name": "Robin Hood", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-10"},
    {"id": "STD-442", "name": "Marian Fitzwalter", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-13"},
    {"id": "STD-443", "name": "Luke Skywalker", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-16"},
    {"id": "STD-444", "name": "Leia Organa", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-18"},
    {"id": "STD-445", "name": "Han Solo", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-21"},
    {"id": "STD-446", "name": "Padme Amidala", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-24"},
    {"id": "STD-447", "name": "Lando Calrissian", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-27"},
    {"id": "STD-448", "name": "Ahsoka Tano", "class_name": "Class 8", "section": "C", "enrolled_date": "2026-01-30"},

    # Class 8 - D
    {"id": "STD-461", "name": "Percy Jackson", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-12"},
    {"id": "STD-462", "name": "Annabeth Chase", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-15"},
    {"id": "STD-463", "name": "Grover Underwood", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-17"},
    {"id": "STD-464", "name": "Thalia Grace", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-19"},
    {"id": "STD-465", "name": "Nico di Angelo", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-22"},
    {"id": "STD-466", "name": "Piper McLean", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-25"},
    {"id": "STD-467", "name": "Jason Grace", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-28"},
    {"id": "STD-468", "name": "Hazel Levesque", "class_name": "Class 8", "section": "D", "enrolled_date": "2026-01-31"},

    # Class 7 - A
    {"id": "STD-501", "name": "Harry Potter", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-10"},
    {"id": "STD-502", "name": "Hermione Granger", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-12"},
    {"id": "STD-503", "name": "Ron Weasley", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-14"},
    {"id": "STD-504", "name": "Neville Longbottom", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-17"},
    {"id": "STD-505", "name": "Luna Lovegood", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-20"},
    {"id": "STD-506", "name": "Ginny Weasley", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-23"},
    {"id": "STD-507", "name": "Draco Malfoy", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-26"},
    {"id": "STD-508", "name": "Cedric Diggory", "class_name": "Class 7", "section": "A", "enrolled_date": "2026-01-29"},

    # Class 7 - B
    {"id": "STD-521", "name": "Katniss Everdeen", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-11"},
    {"id": "STD-522", "name": "Peeta Mellark", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-13"},
    {"id": "STD-523", "name": "Gale Hawthorne", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-16"},
    {"id": "STD-524", "name": "Primrose Everdeen", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-18"},
    {"id": "STD-525", "name": "Finnick Odair", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-21"},
    {"id": "STD-526", "name": "Johanna Mason", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-24"},
    {"id": "STD-527", "name": "Cinna Stylist", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-27"},
    {"id": "STD-528", "name": "Rue Barnette", "class_name": "Class 7", "section": "B", "enrolled_date": "2026-01-30"},

    # Class 7 - C
    {"id": "STD-541", "name": "Edward Cullen", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-10"},
    {"id": "STD-542", "name": "Bella Swan", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-13"},
    {"id": "STD-543", "name": "Jacob Black", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-15"},
    {"id": "STD-544", "name": "Alice Cullen", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-18"},
    {"id": "STD-545", "name": "Jasper Whitlock", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-21"},
    {"id": "STD-546", "name": "Rosalie Hale", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-24"},
    {"id": "STD-547", "name": "Emmett Cullen", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-26"},
    {"id": "STD-548", "name": "Carlisle Cullen", "class_name": "Class 7", "section": "C", "enrolled_date": "2026-01-29"},

    # Class 7 - D
    {"id": "STD-561", "name": "Bilbo Baggins", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-12"},
    {"id": "STD-562", "name": "Frodo Baggins", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-14"},
    {"id": "STD-563", "name": "Samwise Gamgee", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-17"},
    {"id": "STD-564", "name": "Peregrin Took", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-19"},
    {"id": "STD-565", "name": "Meriadoc Brandybuck", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-22"},
    {"id": "STD-566", "name": "Aragorn Elessar", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-25"},
    {"id": "STD-567", "name": "Legolas Greenleaf", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-28"},
    {"id": "STD-568", "name": "Gimli Gloin", "class_name": "Class 7", "section": "D", "enrolled_date": "2026-01-31"},

    # Class 6 - A
    {"id": "STD-601", "name": "Charlie Bucket", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-10"},
    {"id": "STD-602", "name": "Matilda Wormwood", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-12"},
    {"id": "STD-603", "name": "James Trotter", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-15"},
    {"id": "STD-604", "name": "Sophie Dahl", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-18"},
    {"id": "STD-605", "name": "Danny Champion", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-20"},
    {"id": "STD-606", "name": "George Kranky", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-23"},
    {"id": "STD-607", "name": "Bruno Jenkins", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-26"},
    {"id": "STD-608", "name": "Mary Poppins", "class_name": "Class 6", "section": "A", "enrolled_date": "2026-01-29"},

    # Class 6 - B
    {"id": "STD-621", "name": "Tom Sawyer", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-11"},
    {"id": "STD-622", "name": "Huckleberry Finn", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-14"},
    {"id": "STD-623", "name": "Becky Thatcher", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-16"},
    {"id": "STD-624", "name": "Joe Harper", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-19"},
    {"id": "STD-625", "name": "Sid Sawyer", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-22"},
    {"id": "STD-626", "name": "Amy Lawrence", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-25"},
    {"id": "STD-627", "name": "Alfred Temple", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-27"},
    {"id": "STD-628", "name": "Ben Rogers", "class_name": "Class 6", "section": "B", "enrolled_date": "2026-01-30"},

    # Class 6 - C
    {"id": "STD-641", "name": "Dorothy Gale", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-10"},
    {"id": "STD-642", "name": "Scarecrow Straw", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-13"},
    {"id": "STD-643", "name": "Tin Woodsman", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-15"},
    {"id": "STD-644", "name": "Cowardly Lion", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-18"},
    {"id": "STD-645", "name": "Glinda Good", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-21"},
    {"id": "STD-646", "name": "Oz Pinhead", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-24"},
    {"id": "STD-647", "name": "Toto Barker", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-27"},
    {"id": "STD-648", "name": "Tip Gillikin", "class_name": "Class 6", "section": "C", "enrolled_date": "2026-01-30"},

    # Class 6 - D
    {"id": "STD-661", "name": "Peter Pan", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-11"},
    {"id": "STD-662", "name": "Wendy Moira", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-13"},
    {"id": "STD-663", "name": "John Darling", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-16"},
    {"id": "STD-664", "name": "Michael Darling", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-18"},
    {"id": "STD-665", "name": "Tiger Lily", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-21"},
    {"id": "STD-666", "name": "James Hook", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-24"},
    {"id": "STD-667", "name": "Smee Bosun", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-27"},
    {"id": "STD-668", "name": "Tinker Bell", "class_name": "Class 6", "section": "D", "enrolled_date": "2026-01-30"},
]

def run():
    print(f"Adding/Updating {len(STUDENTS_DATA)} students across all classes and sections...")
    inserted_count = 0
    updated_count = 0

    for s in STUDENTS_DATA:
        res = execute_non_query(
            """INSERT INTO students (id, name, class_name, section, enrolled_date)
               VALUES (%s, %s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE name = VALUES(name), class_name = VALUES(class_name), section = VALUES(section)""",
            (s['id'], s['name'], s['class_name'], s['section'], s['enrolled_date'])
        )
        if res['affected_rows'] == 1:
            inserted_count += 1
        elif res['affected_rows'] == 2:
            updated_count += 1

    print(f"Students table updated: {inserted_count} inserted, {updated_count} refreshed.")

    # Create sample student login accounts for student portal access
    # We will create login credentials for the first student of each class-section
    student_pw_hash = hash_password('student123')
    lead_students = [
        {"id": "STD-221", "name": "Lucas Vance", "email": "lucas@attendx.edu"},
        {"id": "STD-241", "name": "Felix Mendelssohn", "email": "felix@attendx.edu"},
        {"id": "STD-321", "name": "Benjamin Franklin", "email": "benjamin@attendx.edu"},
        {"id": "STD-341", "name": "Thomas Edison", "email": "thomas@attendx.edu"},
        {"id": "STD-361", "name": "Zachary Taylor", "email": "zachary@attendx.edu"},
        {"id": "STD-401", "name": "Oliver Twist", "email": "oliver@attendx.edu"},
        {"id": "STD-421", "name": "Barry Allen", "email": "barry@attendx.edu"},
        {"id": "STD-441", "name": "Robin Hood", "email": "robin@attendx.edu"},
        {"id": "STD-461", "name": "Percy Jackson", "email": "percy@attendx.edu"},
        {"id": "STD-501", "name": "Harry Potter", "email": "harry@attendx.edu"},
        {"id": "STD-521", "name": "Katniss Everdeen", "email": "katniss@attendx.edu"},
        {"id": "STD-541", "name": "Edward Cullen", "email": "edward@attendx.edu"},
        {"id": "STD-561", "name": "Bilbo Baggins", "email": "bilbo@attendx.edu"},
        {"id": "STD-601", "name": "Charlie Bucket", "email": "charlie@attendx.edu"},
        {"id": "STD-621", "name": "Tom Sawyer", "email": "tom@attendx.edu"},
        {"id": "STD-641", "name": "Dorothy Gale", "email": "dorothy@attendx.edu"},
        {"id": "STD-661", "name": "Peter Pan", "email": "peterpan@attendx.edu"},
    ]

    for ls in lead_students:
        execute_non_query(
            """INSERT INTO users (name, email, password_hash, role, student_id)
               VALUES (%s, %s, %s, 'student', %s)
               ON DUPLICATE KEY UPDATE name = VALUES(name), student_id = VALUES(student_id)""",
            (ls['name'], ls['email'], student_pw_hash, ls['id'])
        )

    print("Student user accounts created/updated.")

    # Create sample attendance sessions & records for newly created class sections
    # Session date: 2026-10-10
    session_date = "2026-10-10"
    all_sections = execute_query("SELECT DISTINCT class_name, section FROM students ORDER BY class_name, section")

    for sec in all_sections:
        c_name = sec['class_name']
        s_sec = sec['section']

        # Find existing or insert new session
        existing_sess = execute_query(
            "SELECT id FROM attendance_sessions WHERE session_date = %s AND class_name = %s AND section = %s",
            (session_date, c_name, s_sec),
            fetch_one=True
        )
        if existing_sess:
            actual_session_id = existing_sess['id']
        else:
            actual_session_id = f"ATT-20261010-{c_name.replace(' ', '')}{s_sec}"
            execute_non_query(
                """INSERT INTO attendance_sessions (id, session_date, class_name, section, subject, recorded_by_user_id)
                   VALUES (%s, %s, %s, %s, 'General', 1)""",
                (actual_session_id, session_date, c_name, s_sec)
            )

        # Get students in this class and section
        sec_students = execute_query(
            "SELECT id FROM students WHERE class_name = %s AND section = %s",
            (c_name, s_sec)
        )

        for idx, stu in enumerate(sec_students):
            # Alternating attendance so attendance stats look realistic (~87%)
            status = 'absent' if idx == 2 else 'present'
            marking_method = 'qr' if idx % 2 == 0 else 'manual'
            execute_non_query(
                """INSERT INTO attendance_records (session_id, student_id, status, marking_method)
                   VALUES (%s, %s, %s, %s)
                   ON DUPLICATE KEY UPDATE status = VALUES(status)""",
                (actual_session_id, stu['id'], status, marking_method)
            )

    print("Sample attendance sessions and records seeded across all classes and sections.")

    # Verify total counts
    total_students = execute_query("SELECT COUNT(*) as count FROM students", fetch_one=True)['count']
    total_sections = execute_query("SELECT COUNT(DISTINCT CONCAT(class_name, '-', section)) as count FROM students", fetch_one=True)['count']
    print(f"\nSUCCESS! Total students in database: {total_students} across {total_sections} class-sections.")

if __name__ == '__main__':
    run()
