import re
import datetime
import secrets
from flask import Flask, request, jsonify, g
from flask_cors import CORS
from config import Config
from db import get_db, execute_query, execute_non_query
from auth_utils import (
    hash_password,
    verify_password,
    generate_jwt_token,
    token_required,
    roles_required,
    generate_student_qr_payload,
    verify_student_qr_payload
)

app = Flask(__name__)
app.config.from_object(Config)

# Enable CORS for frontend
CORS(app, resources={r"/api/*": {"origins": Config.CORS_ORIGINS}}, supports_credentials=True)

# Production Security Headers Middleware
@app.after_request
def set_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['X-XSS-Protection'] = '1; mode=block'
    # Enforce HSTS over HTTPS / reverse proxies
    if request.is_secure or request.headers.get('X-Forwarded-Proto') == 'https':
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
    return response

# Helper regex for email validation
EMAIL_REGEX = re.compile(r'^[^\s@]+@[^\s@]+\.[^\s@]+$')

# -------------------------------------------------------------
# Health Check Endpoint
# -------------------------------------------------------------
@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint to test API and DB connectivity."""
    try:
        db_check = execute_query("SELECT 1 AS status", fetch_one=True)
        return jsonify({
            'success': True,
            'service': 'AttendX REST API',
            'status': 'healthy',
            'database': 'connected' if db_check else 'error'
        }), 200
    except Exception as e:
        return jsonify({
            'success': False,
            'service': 'AttendX REST API',
            'status': 'degraded',
            'database_error': str(e)
        }), 500

# -------------------------------------------------------------
# Authentication Endpoints
# -------------------------------------------------------------
@app.route('/api/auth/register', methods=['POST'])
def register():
    """Register a new user account (teacher, admin, or student) with secure password hashing."""
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    email = (data.get('email') or '').strip().lower()
    password = data.get('password') or ''
    role = (data.get('role') or 'teacher').strip().lower()
    student_id = (data.get('student_id') or data.get('studentId') or '').strip().upper() or None

    # Validation
    if not name:
        return jsonify({'success': False, 'message': 'Full name is required.'}), 400
    if not email:
        return jsonify({'success': False, 'message': 'Email address is required.'}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({'success': False, 'message': 'Please provide a valid email format.'}), 400
    if not password or len(password) < 6:
        return jsonify({'success': False, 'message': 'Password must be at least 6 characters long.'}), 400
    if role not in ['teacher', 'admin', 'student']:
        return jsonify({'success': False, 'message': "Role must be 'teacher', 'admin', or 'student'."}), 400

    try:
        # Check if email is already taken
        existing_user = execute_query(
            "SELECT id FROM users WHERE email = %s",
            (email,),
            fetch_one=True
        )
        if existing_user:
            return jsonify({
                'success': False,
                'message': f"An account with email '{email}' already exists. Please sign in instead."
            }), 409

        if role == 'student':
            if not student_id:
                return jsonify({'success': False, 'message': 'Student ID is required to register a student account.'}), 400
            
            # Verify student exists in students table
            student_record = execute_query("SELECT id, name FROM students WHERE id = %s", (student_id,), fetch_one=True)
            if not student_record:
                return jsonify({
                    'success': False,
                    'message': f"Student ID '{student_id}' does not exist in student records. Please contact your instructor."
                }), 404
            
            # Verify student_id is not already linked
            existing_student_user = execute_query("SELECT id FROM users WHERE student_id = %s", (student_id,), fetch_one=True)
            if existing_student_user:
                return jsonify({
                    'success': False,
                    'message': f"Student ID '{student_id}' is already registered with an account. Please sign in instead."
                }), 409

        # Hash password and insert
        pwd_hash = hash_password(password)
        res = execute_non_query(
            "INSERT INTO users (name, email, password_hash, role, student_id) VALUES (%s, %s, %s, %s, %s)",
            (name, email, pwd_hash, role, student_id)
        )
        user_id = res['last_insert_id']

        # Issue JWT Token
        token = generate_jwt_token(user_id=user_id, email=email, role=role, name=name, student_id=student_id)

        user_data = {
            'id': user_id,
            'name': name,
            'email': email,
            'username': student_id or email,
            'role': role,
            'student_id': student_id
        }

        if role == 'student' and student_id:
            st = execute_query("SELECT class_name, section FROM students WHERE id = %s", (student_id,), fetch_one=True)
            if st:
                user_data['class'] = st['class_name']
                user_data['section'] = st['section']
                user_data['classSection'] = f"{st['class_name']}-{st['section']}"

        return jsonify({
            'success': True,
            'message': 'Account created successfully!',
            'token': token,
            'user': user_data
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Registration error: {str(e)}"}), 500


@app.route('/api/auth/login', methods=['POST'])
def login():
    """Authenticate a user (by email or Student ID) and return a JWT access token."""
    data = request.get_json() or {}
    identifier = (data.get('email') or data.get('identifier') or data.get('student_id') or '').strip()
    password = data.get('password') or ''
    expected_role = (data.get('role') or '').strip().lower()

    if not identifier or not password:
        return jsonify({'success': False, 'message': 'Email/Student ID and password are required.'}), 400

    try:
        user = execute_query(
            "SELECT id, name, email, password_hash, role, student_id FROM users WHERE LOWER(email) = %s OR UPPER(student_id) = %s",
            (identifier.lower(), identifier.upper()),
            fetch_one=True
        )

        if not user or not verify_password(password, user['password_hash']):
            return jsonify({'success': False, 'message': 'Invalid credentials. Please verify your details and password.'}), 401

        # Check role match if requested by frontend
        if expected_role and user['role'] != expected_role:
            return jsonify({
                'success': False,
                'message': f"Invalid credentials for {expected_role.upper()} portal. This account is registered as {user['role'].upper()}."
            }), 401

        token = generate_jwt_token(
            user_id=user['id'],
            email=user['email'],
            role=user['role'],
            name=user['name'],
            student_id=user.get('student_id')
        )

        user_data = {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'username': user.get('student_id') or user['email'],
            'role': user['role'],
            'student_id': user.get('student_id')
        }

        if user['role'] == 'student' and user.get('student_id'):
            st = execute_query("SELECT class_name, section FROM students WHERE id = %s", (user['student_id'],), fetch_one=True)
            if st:
                user_data['class'] = st['class_name']
                user_data['section'] = st['section']
                user_data['classSection'] = f"{st['class_name']}-{st['section']}"

        return jsonify({
            'success': True,
            'message': f"Welcome back, {user['name']}!",
            'token': token,
            'user': user_data
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Login failed: {str(e)}"}), 500


@app.route('/api/auth/me', methods=['GET'])
@token_required
def get_current_user():
    """Return the profile of the currently logged-in user."""
    user_info = dict(g.current_user)
    if user_info.get('role') == 'student' and user_info.get('student_id'):
        st = execute_query("SELECT class_name, section FROM students WHERE id = %s", (user_info['student_id'],), fetch_one=True)
        if st:
            user_info['class'] = st['class_name']
            user_info['section'] = st['section']
            user_info['classSection'] = f"{st['class_name']}-{st['section']}"
    return jsonify({
        'success': True,
        'user': user_info
    }), 200

# -------------------------------------------------------------
# Classes & Sections Endpoint
# -------------------------------------------------------------
@app.route('/api/classes', methods=['GET'])
@token_required
def get_classes():
    """Return unique active classes and sections in the system."""
    try:
        rows = execute_query(
            "SELECT DISTINCT class_name, section, CONCAT(class_name, '-', section) AS classSection FROM students ORDER BY class_name, section"
        )
        classes_set = set()
        sections_set = set()
        combined_list = []

        for r in rows:
            classes_set.add(r['class_name'])
            sections_set.add(r['section'])
            combined_list.append(r['classSection'])

        # Fallback defaults if none in DB yet
        if not classes_set:
            classes_set = {'Class 10', 'Class 9', 'Class 8', 'Class 7', 'Class 6'}
        if not sections_set:
            sections_set = {'A', 'B', 'C', 'D'}

        return jsonify({
            'success': True,
            'availableClasses': sorted(list(classes_set)),
            'availableSections': sorted(list(sections_set)),
            'activeClassSections': sorted(combined_list)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# -------------------------------------------------------------
# Student Management CRUD Endpoints
# -------------------------------------------------------------
@app.route('/api/students', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_students():
    """Get all students with optional class, section, and search filtering."""
    class_filter = request.args.get('class')
    section_filter = request.args.get('section')
    search_query = request.args.get('search', '').strip()

    query = """
        SELECT id, name, class_name, section, enrolled_date,
               CONCAT(class_name, '-', section) AS classSection
        FROM students
        WHERE 1=1
    """
    params = []

    if class_filter and class_filter != 'ALL':
        query += " AND class_name = %s"
        params.append(class_filter)
    if section_filter and section_filter != 'ALL':
        query += " AND section = %s"
        params.append(section_filter)
    if search_query:
        query += " AND (name LIKE %s OR id LIKE %s)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])

    query += " ORDER BY class_name ASC, section ASC, name ASC"

    try:
        students_rows = execute_query(query, params)
        formatted_students = []
        for s in students_rows:
            formatted_students.append({
                'id': s['id'],
                'name': s['name'],
                'class': s['class_name'],
                'section': s['section'],
                'classSection': s['classSection'],
                'enrolledDate': s['enrolled_date'].strftime('%Y-%m-%d') if hasattr(s['enrolled_date'], 'strftime') else str(s['enrolled_date'])
            })
        return jsonify({
            'success': True,
            'count': len(formatted_students),
            'students': formatted_students
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/students', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def add_student():
    """Create a new student with unique ID validation."""
    data = request.get_json() or {}
    student_id = (data.get('id') or '').strip().upper()
    name = (data.get('name') or '').strip()
    class_name = (data.get('class') or data.get('class_name') or '').strip()
    section = (data.get('section') or '').strip().upper()
    enrolled_date = (data.get('enrolledDate') or datetime.date.today().isoformat()).strip()

    # If classSection passed like "Class 10-A", parse it
    if not class_name or not section:
        class_sec = (data.get('classSection') or '').strip()
        if '-' in class_sec:
            parts = class_sec.split('-')
            class_name = class_name or parts[0].strip()
            section = section or parts[1].strip()

    # Validations
    if not student_id:
        return jsonify({'success': False, 'message': 'Student ID is required.'}), 400
    if not name:
        return jsonify({'success': False, 'message': 'Student full name is required.'}), 400
    if not class_name:
        return jsonify({'success': False, 'message': 'Class is required.'}), 400
    if not section:
        return jsonify({'success': False, 'message': 'Section is required.'}), 400

    try:
        # Check duplicate ID
        existing = execute_query(
            "SELECT id FROM students WHERE id = %s",
            (student_id,),
            fetch_one=True
        )
        if existing:
            return jsonify({
                'success': False,
                'message': f"Student ID '{student_id}' is already registered in the system. Student IDs must be unique."
            }), 409

        execute_non_query(
            "INSERT INTO students (id, name, class_name, section, enrolled_date) VALUES (%s, %s, %s, %s, %s)",
            (student_id, name, class_name, section, enrolled_date)
        )

        return jsonify({
            'success': True,
            'message': f"Student {name} ({student_id}) added successfully!",
            'student': {
                'id': student_id,
                'name': name,
                'class': class_name,
                'section': section,
                'classSection': f"{class_name}-{section}",
                'enrolledDate': enrolled_date
            }
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Failed to add student: {str(e)}"}), 500


@app.route('/api/students/<string:student_id>', methods=['PUT'])
@token_required
@roles_required('teacher', 'admin')
def update_student(student_id):
    """Update student details with validation and unique ID check."""
    data = request.get_json() or {}
    new_id = (data.get('id') or student_id).strip().upper()
    name = (data.get('name') or '').strip()
    class_name = (data.get('class') or data.get('class_name') or '').strip()
    section = (data.get('section') or '').strip().upper()

    if not name or not class_name or not section:
        return jsonify({'success': False, 'message': 'Name, class, and section are all required.'}), 400

    try:
        # Check target student exists
        existing = execute_query("SELECT id FROM students WHERE id = %s", (student_id,), fetch_one=True)
        if not existing:
            return jsonify({'success': False, 'message': f"Student with ID '{student_id}' not found."}), 404

        # If ID was changed, verify new ID is not already used by someone else
        if new_id != student_id:
            collision = execute_query("SELECT id FROM students WHERE id = %s", (new_id,), fetch_one=True)
            if collision:
                return jsonify({'success': False, 'message': f"Student ID '{new_id}' is already in use."}), 409

        execute_non_query(
            "UPDATE students SET id = %s, name = %s, class_name = %s, section = %s WHERE id = %s",
            (new_id, name, class_name, section, student_id)
        )

        return jsonify({
            'success': True,
            'message': f"Student {name} updated successfully!",
            'student': {
                'id': new_id,
                'name': name,
                'class': class_name,
                'section': section,
                'classSection': f"{class_name}-{section}"
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Update failed: {str(e)}"}), 500


@app.route('/api/students/<string:student_id>', methods=['DELETE'])
@token_required
@roles_required('teacher', 'admin')
def delete_student(student_id):
    """Delete a student and cascading attendance records."""
    try:
        existing = execute_query("SELECT name FROM students WHERE id = %s", (student_id,), fetch_one=True)
        if not existing:
            return jsonify({'success': False, 'message': f"Student '{student_id}' not found."}), 404

        execute_non_query("DELETE FROM students WHERE id = %s", (student_id,))
        return jsonify({
            'success': True,
            'message': f"Student {existing['name']} ({student_id}) has been removed."
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Delete failed: {str(e)}"}), 500

# -------------------------------------------------------------
# Attendance Marking & Retrieval Endpoints
# -------------------------------------------------------------
@app.route('/api/attendance', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_attendance():
    """
    Get saved attendance sessions with nested records.
    Returns array formatted for frontend:
    [{ id, date, classSection, records: { [studentId]: 'present' | 'absent' } }]
    """
    date_filter = request.args.get('date')
    class_filter = request.args.get('class')
    section_filter = request.args.get('section')

    query = """
        SELECT s.id AS session_id, s.session_date, s.class_name, s.section,
               CONCAT(s.class_name, '-', s.section) AS classSection,
               r.student_id, r.status
        FROM attendance_sessions s
        LEFT JOIN attendance_records r ON s.id = r.session_id
        WHERE 1=1
    """
    params = []

    if date_filter:
        query += " AND s.session_date = %s"
        params.append(date_filter)
    if class_filter and class_filter != 'ALL':
        query += " AND s.class_name = %s"
        params.append(class_filter)
    if section_filter and section_filter != 'ALL':
        query += " AND s.section = %s"
        params.append(section_filter)

    query += " ORDER BY s.session_date DESC, s.class_name ASC, s.section ASC"

    try:
        rows = execute_query(query, params)
        sessions_dict = {}

        for row in rows:
            sid = row['session_id']
            if sid not in sessions_dict:
                s_date = row['session_date'].strftime('%Y-%m-%d') if hasattr(row['session_date'], 'strftime') else str(row['session_date'])
                sessions_dict[sid] = {
                    'id': sid,
                    'date': s_date,
                    'classSection': row['classSection'],
                    'records': {}
                }
            if row['student_id'] and row['status']:
                sessions_dict[sid]['records'][row['student_id']] = row['status']

        return jsonify({
            'success': True,
            'count': len(sessions_dict),
            'attendanceRecords': list(sessions_dict.values())
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/attendance/session', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_single_session():
    """Retrieve existing attendance records for a specific date and classSection."""
    date_str = request.args.get('date')
    class_sec = request.args.get('classSection')

    if not date_str or not class_sec:
        return jsonify({'success': False, 'message': 'date and classSection query parameters required.'}), 400

    parts = class_sec.split('-')
    class_name = parts[0].strip()
    section = parts[1].strip() if len(parts) > 1 else 'A'

    try:
        session = execute_query(
            """
            SELECT id, session_date, class_name, section, CONCAT(class_name, '-', section) AS classSection
            FROM attendance_sessions
            WHERE session_date = %s AND class_name = %s AND section = %s
            """,
            (date_str, class_name, section),
            fetch_one=True
        )

        if not session:
            return jsonify({'success': True, 'exists': False, 'session': None}), 200

        records_rows = execute_query(
            "SELECT student_id, status FROM attendance_records WHERE session_id = %s",
            (session['id'],)
        )
        records_map = {r['student_id']: r['status'] for r in records_rows}

        s_date = session['session_date'].strftime('%Y-%m-%d') if hasattr(session['session_date'], 'strftime') else str(session['session_date'])
        return jsonify({
            'success': True,
            'exists': True,
            'session': {
                'id': session['id'],
                'date': s_date,
                'classSection': session['classSection'],
                'records': records_map
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/attendance', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def save_attendance():
    """
    Save or correct attendance records for a class on a specific date.
    Performs atomic upsert transaction with duplicate prevention.
    """
    data = request.get_json() or {}
    date_str = (data.get('date') or '').strip()
    class_sec = (data.get('classSection') or '').strip()
    records = data.get('records') or {}

    if not date_str:
        return jsonify({'success': False, 'message': 'Date is required.'}), 400
    if not class_sec:
        return jsonify({'success': False, 'message': 'Class and section are required.'}), 400
    if not records or not isinstance(records, dict):
        return jsonify({'success': False, 'message': 'Attendance records dictionary is required.'}), 400

    parts = class_sec.split('-')
    class_name = parts[0].strip()
    section = parts[1].strip() if len(parts) > 1 else 'A'

    # Sanitize statuses
    clean_records = {}
    for sid, st in records.items():
        st_clean = (st or '').strip().lower()
        if st_clean not in ['present', 'absent']:
            return jsonify({'success': False, 'message': f"Invalid status '{st}' for student {sid}. Must be 'present' or 'absent'."}), 400
        clean_records[sid.strip()] = st_clean

    current_user_id = g.current_user.get('id')
    clean_date_tag = date_str.replace('-', '')
    clean_cls_tag = class_sec.replace(' ', '').replace('-', '')
    session_id = f"ATT-{clean_date_tag}-{clean_cls_tag}"

    # Atomic Transaction
    with get_db() as conn:
        with conn.cursor() as cursor:
            # 1. Upsert attendance_sessions
            cursor.execute(
                """
                INSERT INTO attendance_sessions (id, session_date, class_name, section, recorded_by_user_id)
                VALUES (%s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE 
                    updated_at = CURRENT_TIMESTAMP,
                    recorded_by_user_id = VALUES(recorded_by_user_id)
                """,
                (session_id, date_str, class_name, section, current_user_id)
            )

            # Retrieve actual session ID in case unique key matched an existing custom ID
            cursor.execute(
                "SELECT id FROM attendance_sessions WHERE session_date = %s AND class_name = %s AND section = %s",
                (date_str, class_name, section)
            )
            actual_session = cursor.fetchone()
            active_session_id = actual_session['id'] if actual_session else session_id

            # 2. Upsert each student record
            for student_id, status in clean_records.items():
                cursor.execute(
                    """
                    INSERT INTO attendance_records (session_id, student_id, status)
                    VALUES (%s, %s, %s)
                    ON DUPLICATE KEY UPDATE status = VALUES(status), marked_at = CURRENT_TIMESTAMP
                    """,
                    (active_session_id, student_id, status)
                )

    present_count = sum(1 for s in clean_records.values() if s == 'present')
    absent_count = sum(1 for s in clean_records.values() if s == 'absent')

    return jsonify({
        'success': True,
        'message': f"Attendance successfully saved for {class_sec} on {date_str}! ({present_count} Present, {absent_count} Absent)",
        'session': {
            'id': active_session_id,
            'date': date_str,
            'classSection': class_sec,
            'records': clean_records
        }
    }), 200

# -------------------------------------------------------------
# Reports & Analytics Endpoint
# -------------------------------------------------------------
@app.route('/api/reports', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_reports():
    """
    Calculate and return attendance report metrics directly from SQL.
    Computes overall summary, donut ratio, session timelines, and student breakdown.
    """
    date_mode = request.args.get('dateFilterMode', 'ALL')
    start_date = request.args.get('startDate')
    end_date = request.args.get('endDate')
    selected_class = request.args.get('class', 'ALL')
    selected_section = request.args.get('section', 'ALL')
    search_query = request.args.get('search', '').strip()

    today_str = datetime.date.today().isoformat()

    # Build WHERE conditions for sessions
    session_where = ["1=1"]
    session_params = []

    if date_mode == 'TODAY':
        session_where.append("s.session_date = %s")
        session_params.append(today_str)
    elif date_mode == 'CUSTOM':
        if start_date:
            session_where.append("s.session_date >= %s")
            session_params.append(start_date)
        if end_date:
            session_where.append("s.session_date <= %s")
            session_params.append(end_date)

    if selected_class != 'ALL':
        session_where.append("s.class_name = %s")
        session_params.append(selected_class)
    if selected_section != 'ALL':
        session_where.append("s.section = %s")
        session_params.append(selected_section)

    session_sql = f"""
        SELECT s.id, s.session_date, s.class_name, s.section,
               CONCAT(s.class_name, '-', s.section) AS classSection
        FROM attendance_sessions s
        WHERE {' AND '.join(session_where)}
        ORDER BY s.session_date DESC
    """
    filtered_sessions = execute_query(session_sql, session_params)
    filtered_session_ids = [s['id'] for s in filtered_sessions]

    # Fetch students matching class, section, and search query
    student_where = ["1=1"]
    student_params = []
    if selected_class != 'ALL':
        student_where.append("st.class_name = %s")
        student_params.append(selected_class)
    if selected_section != 'ALL':
        student_where.append("st.section = %s")
        student_params.append(selected_section)
    if search_query:
        student_where.append("(st.name LIKE %s OR st.id LIKE %s)")
        student_params.extend([f"%{search_query}%", f"%{search_query}%"])

    student_sql = f"""
        SELECT st.id, st.name, st.class_name, st.section,
               CONCAT(st.class_name, '-', st.section) AS classSection,
               st.enrolled_date
        FROM students st
        WHERE {' AND '.join(student_where)}
        ORDER BY st.class_name ASC, st.section ASC, st.name ASC
    """
    students_list = execute_query(student_sql, student_params)

    # Fetch records for filtered sessions
    records_lookup = {}
    if filtered_session_ids:
        placeholders = ', '.join(['%s'] * len(filtered_session_ids))
        records_rows = execute_query(
            f"SELECT session_id, student_id, status FROM attendance_records WHERE session_id IN ({placeholders})",
            filtered_session_ids
        )
        for r in records_rows:
            key = (r['session_id'], r['student_id'])
            records_lookup[key] = r['status']

    # Compute metrics per student
    student_metrics = []
    total_present_all = 0
    total_absent_all = 0

    for st in students_list:
        st_class_sec = st['classSection']
        # Filter sessions relevant to this student's class
        relevant_sessions = [s for s in filtered_sessions if s['classSection'] == st_class_sec]
        total_sessions = len(relevant_sessions)

        present_count = 0
        absent_count = 0
        for s in relevant_sessions:
            status = records_lookup.get((s['id'], st['id']))
            if status == 'present':
                present_count += 1
            elif status == 'absent':
                absent_count += 1

        total_present_all += present_count
        total_absent_all += absent_count

        # Prevent division by zero
        if total_sessions > 0:
            percentage = round((present_count / total_sessions) * 100, 1)
        else:
            percentage = 0.0

        if total_sessions == 0:
            badge_class = 'badge-neutral'
            badge_label = 'No Sessions'
        elif percentage >= 90:
            badge_class = 'badge-high'
            badge_label = 'Excellent (≥90%)'
        elif percentage >= 75:
            badge_class = 'badge-mid'
            badge_label = 'Good (75–89%)'
        else:
            badge_class = 'badge-low'
            badge_label = 'Warning (<75%)'

        student_metrics.append({
            'student': {
                'id': st['id'],
                'name': st['name'],
                'class': st['class_name'],
                'section': st['section'],
                'classSection': st['classSection']
            },
            'studentClass': st['class_name'],
            'studentSection': st['section'],
            'totalSessions': total_sessions,
            'presentCount': present_count,
            'absentCount': absent_count,
            'percentage': percentage,
            'percentageStr': f"{percentage:.1f}",
            'badgeClass': badge_class,
            'badgeLabel': badge_label
        })

    total_marked = total_present_all + total_absent_all
    overall_rate = round((total_present_all / total_marked) * 100, 1) if total_marked > 0 else 0.0

    # Build timeline bars for filtered sessions
    session_bars = []
    for s in filtered_sessions:
        s_present = sum(1 for (sid, stid), status in records_lookup.items() if sid == s['id'] and status == 'present')
        s_absent = sum(1 for (sid, stid), status in records_lookup.items() if sid == s['id'] and status == 'absent')
        s_total = s_present + s_absent
        s_rate = round((s_present / s_total) * 100) if s_total > 0 else 0
        s_date_str = s['session_date'].strftime('%Y-%m-%d') if hasattr(s['session_date'], 'strftime') else str(s['session_date'])
        session_bars.append({
            'id': s['id'],
            'date': s_date_str,
            'classSection': s['classSection'],
            'presentCount': s_present,
            'absentCount': s_absent,
            'rate': s_rate
        })

    return jsonify({
        'success': True,
        'summary': {
            'totalStudents': len(students_list),
            'totalSessions': len(filtered_sessions),
            'totalPresent': total_present_all,
            'totalAbsent': total_absent_all,
            'totalMarked': total_marked,
            'overallRate': f"{overall_rate:.1f}"
        },
        'studentMetrics': student_metrics,
        'sessionBars': session_bars
    }), 200

# -------------------------------------------------------------
# Dashboard Overview Summary
# -------------------------------------------------------------
@app.route('/api/dashboard/summary', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_dashboard_summary():
    """Return live overview counts and today's attendance metrics."""
    try:
        # Registered students count
        st_count_row = execute_query("SELECT COUNT(*) AS cnt FROM students", fetch_one=True)
        registered_students = st_count_row['cnt'] if st_count_row else 0

        # Active classes/sections count
        cls_count_row = execute_query("SELECT COUNT(DISTINCT CONCAT(class_name, '-', section)) AS cnt FROM students", fetch_one=True)
        active_classes = cls_count_row['cnt'] if cls_count_row else 0

        # Attendance logs count
        logs_count_row = execute_query("SELECT COUNT(*) AS cnt FROM attendance_sessions", fetch_one=True)
        attendance_logs = logs_count_row['cnt'] if logs_count_row else 0

        # Today's attendance
        today_str = datetime.date.today().isoformat()
        today_rows = execute_query(
            """
            SELECT s.id, s.class_name, s.section, CONCAT(s.class_name, '-', s.section) AS classSection,
                   r.student_id, r.status
            FROM attendance_sessions s
            JOIN attendance_records r ON s.id = r.session_id
            WHERE s.session_date = %s
            """,
            (today_str,)
        )

        today_present = sum(1 for r in today_rows if r['status'] == 'present')
        today_absent = sum(1 for r in today_rows if r['status'] == 'absent')
        today_total = today_present + today_absent
        today_rate = round((today_present / today_total) * 100, 1) if today_total > 0 else None

        today_classes = sorted(list(set(r['classSection'] for r in today_rows)))

        # Latest recorded session for context
        latest_session_row = execute_query(
            """
            SELECT s.id, s.session_date, CONCAT(s.class_name, '-', s.section) AS classSection
            FROM attendance_sessions s
            ORDER BY s.session_date DESC, s.created_at DESC
            LIMIT 1
            """,
            fetch_one=True
        )

        latest_session = None
        if latest_session_row:
            l_rows = execute_query(
                "SELECT status FROM attendance_records WHERE session_id = %s",
                (latest_session_row['id'],)
            )
            l_present = sum(1 for r in l_rows if r['status'] == 'present')
            l_absent = sum(1 for r in l_rows if r['status'] == 'absent')
            l_tot = l_present + l_absent
            l_rate = round((l_present / l_tot) * 100, 1) if l_tot > 0 else 0
            l_date_str = latest_session_row['session_date'].strftime('%Y-%m-%d') if hasattr(latest_session_row['session_date'], 'strftime') else str(latest_session_row['session_date'])
            latest_session = {
                'id': latest_session_row['id'],
                'date': l_date_str,
                'classSection': latest_session_row['classSection'],
                'present': l_present,
                'absent': l_absent,
                'rate': l_rate
            }

        # Marks & Assessment Statistics
        marks_stats_row = execute_query(
            """
            SELECT 
                COUNT(*) AS total_assessments,
                SUM(CASE WHEN status = 'draft' THEN 1 ELSE 0 END) AS draft_assessments,
                SUM(CASE WHEN status IN ('published', 'updated') THEN 1 ELSE 0 END) AS published_assessments,
                SUM(CASE WHEN status = 'updated' THEN 1 ELSE 0 END) AS updated_assessments
            FROM assessments
            """,
            fetch_one=True
        )
        marks_stats = {
            'totalAssessments': int(marks_stats_row['total_assessments'] or 0) if marks_stats_row else 0,
            'draftAssessments': int(marks_stats_row['draft_assessments'] or 0) if marks_stats_row else 0,
            'publishedAssessments': int(marks_stats_row['published_assessments'] or 0) if marks_stats_row else 0,
            'updatedAssessments': int(marks_stats_row['updated_assessments'] or 0) if marks_stats_row else 0
        }

        return jsonify({
            'success': True,
            'registeredStudents': registered_students,
            'activeClasses': active_classes,
            'attendanceLogs': attendance_logs,
            'todayAttendance': {
                'date': today_str,
                'present': today_present,
                'absent': today_absent,
                'rate': today_rate,
                'recordedClasses': today_classes
            },
            'latestSession': latest_session,
            'marksStats': marks_stats
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

# -------------------------------------------------------------
# Student Portal Endpoints
# -------------------------------------------------------------
@app.route('/api/student/dashboard', methods=['GET'])
@token_required
@roles_required('student')
def get_student_dashboard():
    """
    Return personalized dashboard statistics for the logged-in student.
    Calculates personal attendance rate, comparison to 75% threshold,
    consecutive classes required, and daily attendance history.
    """
    try:
        student_id = g.current_user.get('student_id')
        if not student_id:
            u = execute_query("SELECT student_id FROM users WHERE id = %s", (g.current_user['id'],), fetch_one=True)
            if u and u.get('student_id'):
                student_id = u['student_id']

        if not student_id:
            return jsonify({
                'success': False,
                'message': 'No student profile linked to this user account.'
            }), 404

        # Fetch student details from students table
        student = execute_query(
            "SELECT id, name, class_name, section, enrolled_date FROM students WHERE id = %s",
            (student_id,),
            fetch_one=True
        )
        if not student:
            return jsonify({
                'success': False,
                'message': f"Student record for ID '{student_id}' not found."
            }), 404

        class_name = student['class_name']
        section = student['section']
        class_sec = f"{class_name}-{section}"

        # Fetch all recorded attendance sessions for this student
        records = execute_query(
            """
            SELECT r.id, r.status, r.marking_method, r.marked_at,
                   s.id AS session_id, s.session_date, s.subject, s.class_name, s.section
            FROM attendance_records r
            JOIN attendance_sessions s ON r.session_id = s.id
            WHERE r.student_id = %s
            ORDER BY s.session_date DESC, s.created_at DESC
            """,
            (student_id,)
        )

        total_conducted = len(records)
        attended_count = sum(1 for r in records if r['status'] == 'present')
        missed_count = sum(1 for r in records if r['status'] == 'absent')

        if total_conducted == 0:
            attendance_percentage = None
            status = 'No attendance data yet'
            is_above_threshold = False
            consecutive_needed = 0
            status_message = 'No attendance data yet'
            explanation = 'No classes have been conducted or recorded yet for your class.'
        else:
            # Attendance percentage = (Classes attended / Total classes conducted) * 100
            attendance_percentage = round((attended_count / total_conducted) * 100, 1)

            # Minimum consecutive additional classes x to reach 75%:
            # (A + x) / (T + x) >= 0.75 <=> x >= max(0, 3*T - 4*A)
            x = max(0, 3 * total_conducted - 4 * attended_count)
            consecutive_needed = x

            if attendance_percentage >= 75.0:
                status = 'Requirement Met'
                is_above_threshold = True
                consecutive_needed = 0
                status_message = 'You currently meet the 75% attendance requirement.'
                explanation = 'Your attendance is in good standing. Keep attending classes consistently to maintain your status.'
            else:
                status = 'Below 75%'
                is_above_threshold = False
                status_message = f"Attend the next {x} class{'es' if x > 1 else ''} to reach 75%"
                explanation = "This calculation assumes that you attend every upcoming class consecutively without any absences."

        # Format daily history
        history = []
        for r in records:
            s_date_str = r['session_date'].strftime('%Y-%m-%d') if hasattr(r['session_date'], 'strftime') else str(r['session_date'])
            history.append({
                'id': r['id'],
                'sessionId': r['session_id'],
                'date': s_date_str,
                'status': r['status'].capitalize(),  # 'Present' or 'Absent'
                'subject': r.get('subject') or 'General',
                'classSection': class_sec,
                'markingMethod': r.get('marking_method') or 'manual'
            })

        # Query published marks for this student
        published_marks_rows = execute_query(
            """
            SELECT sm.id, sm.published_marks, a.id AS assessment_id, a.name AS assessment_name,
                   a.type AS assessment_type, a.subject_name, a.max_marks, a.passing_marks,
                   a.assessment_date, a.published_at, a.status AS assessment_status
            FROM student_marks sm
            JOIN assessments a ON sm.assessment_id = a.id
            WHERE sm.student_id = %s
              AND sm.is_published = TRUE
              AND a.status IN ('published', 'updated')
              AND sm.published_marks IS NOT NULL
            ORDER BY a.assessment_date DESC, a.published_at DESC
            """,
            (student_id,)
        )

        marks_summary = {
            'publishedCount': len(published_marks_rows),
            'hasPublishedMarks': len(published_marks_rows) > 0,
            'averagePercentage': None,
            'recentResults': [],
            'subjectSummaries': []
        }

        if published_marks_rows:
            total_pct = 0.0
            subjects_map = {}
            for row in published_marks_rows:
                mks = float(row['published_marks'])
                mx = float(row['max_marks'])
                pct = round((mks / mx) * 100, 1) if mx > 0 else 0.0
                total_pct += pct
                subj = row['subject_name']
                if subj not in subjects_map:
                    subjects_map[subj] = {'subject': subj, 'totalPct': 0.0, 'count': 0}
                subjects_map[subj]['totalPct'] += pct
                subjects_map[subj]['count'] += 1

                res_item = {
                    'id': row['id'],
                    'assessmentId': row['assessment_id'],
                    'assessmentName': row['assessment_name'],
                    'assessmentType': row['assessment_type'],
                    'subject': subj,
                    'marksObtained': mks,
                    'maxMarks': mx,
                    'passingMarks': float(row['passing_marks']),
                    'percentage': pct,
                    'passed': mks >= float(row['passing_marks']),
                    'date': row['assessment_date'].strftime('%Y-%m-%d') if hasattr(row['assessment_date'], 'strftime') else str(row['assessment_date']),
                    'publishedAt': row['published_at'].strftime('%Y-%m-%d %H:%M') if row.get('published_at') and hasattr(row['published_at'], 'strftime') else str(row.get('published_at') or '')
                }
                if len(marks_summary['recentResults']) < 3:
                    marks_summary['recentResults'].append(res_item)

            marks_summary['averagePercentage'] = round(total_pct / len(published_marks_rows), 1)
            for s_name, s_data in subjects_map.items():
                marks_summary['subjectSummaries'].append({
                    'subject': s_name,
                    'count': s_data['count'],
                    'averagePercentage': round(s_data['totalPct'] / s_data['count'], 1)
                })

        return jsonify({
            'success': True,
            'student': {
                'id': student['id'],
                'name': student['name'],
                'class': class_name,
                'section': section,
                'classSection': class_sec,
                'enrolledDate': student['enrolled_date'].strftime('%Y-%m-%d') if hasattr(student['enrolled_date'], 'strftime') else str(student['enrolled_date'])
            },
            'metrics': {
                'totalConducted': total_conducted,
                'attended': attended_count,
                'missed': missed_count,
                'attendancePercentage': attendance_percentage,
                'status': status,
                'isAboveThreshold': is_above_threshold,
                'consecutiveClassesNeeded': consecutive_needed,
                'statusMessage': status_message,
                'explanation': explanation,
                'targetThreshold': 75.0
            },
            'history': history,
            'marksSummary': marks_summary
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error retrieving student dashboard: {str(e)}"}), 500


@app.route('/api/student/class-attendance', methods=['GET'])
@token_required
@roles_required('student')
def get_student_class_attendance():
    """
    Return aggregate class and section attendance statistics for the student's class.
    Shows total students in class, date-wise present/absent counts, and overall percentage.
    Strictly safeguards classmate privacy by excluding individual student records or login info.
    """
    try:
        student_id = g.current_user.get('student_id')
        if not student_id:
            u = execute_query("SELECT student_id FROM users WHERE id = %s", (g.current_user['id'],), fetch_one=True)
            if u and u.get('student_id'):
                student_id = u['student_id']

        if not student_id:
            return jsonify({'success': False, 'message': 'No student profile linked.'}), 404

        student = execute_query(
            "SELECT class_name, section FROM students WHERE id = %s",
            (student_id,),
            fetch_one=True
        )
        if not student:
            return jsonify({'success': False, 'message': 'Student record not found.'}), 404

        class_name = student['class_name']
        section = student['section']
        class_sec = f"{class_name}-{section}"

        # Total students in class
        st_count = execute_query(
            "SELECT COUNT(*) AS cnt FROM students WHERE class_name = %s AND section = %s",
            (class_name, section),
            fetch_one=True
        )
        total_students = st_count['cnt'] if st_count else 0

        # Date-wise aggregates for this class and section
        sessions = execute_query(
            """
            SELECT s.id, s.session_date, s.subject,
                   SUM(CASE WHEN r.status = 'present' THEN 1 ELSE 0 END) AS present_count,
                   SUM(CASE WHEN r.status = 'absent' THEN 1 ELSE 0 END) AS absent_count,
                   COUNT(r.id) AS total_marked
            FROM attendance_sessions s
            LEFT JOIN attendance_records r ON s.id = r.session_id
            WHERE s.class_name = %s AND s.section = %s
            GROUP BY s.id, s.session_date, s.subject
            ORDER BY s.session_date DESC
            """,
            (class_name, section)
        )

        total_present_all = sum(int(s['present_count'] or 0) for s in sessions)
        total_absent_all = sum(int(s['absent_count'] or 0) for s in sessions)
        total_marked_all = total_present_all + total_absent_all

        overall_rate = round((total_present_all / total_marked_all) * 100, 1) if total_marked_all > 0 else None

        history = []
        for s in sessions:
            pres = int(s['present_count'] or 0)
            abse = int(s['absent_count'] or 0)
            tot = pres + abse
            rate = round((pres / tot) * 100, 1) if tot > 0 else None
            s_date_str = s['session_date'].strftime('%Y-%m-%d') if hasattr(s['session_date'], 'strftime') else str(s['session_date'])
            history.append({
                'sessionId': s['id'],
                'date': s_date_str,
                'subject': s.get('subject') or 'General',
                'presentCount': pres,
                'absentCount': abse,
                'totalMarked': tot,
                'attendanceRate': rate
            })

        return jsonify({
            'success': True,
            'classSection': class_sec,
            'className': class_name,
            'section': section,
            'totalStudents': total_students,
            'totalSessions': len(sessions),
            'totalPresent': total_present_all,
            'totalAbsent': total_absent_all,
            'overallClassRate': overall_rate,
            'history': history
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error retrieving class attendance: {str(e)}"}), 500

# -------------------------------------------------------------
# Student QR Code Pass Endpoint
# -------------------------------------------------------------
@app.route('/api/student/qr-pass', methods=['GET'])
@token_required
@roles_required('student')
def get_student_qr_pass():
    """
    Generate and return a tamper-resistant, cryptographically signed QR pass
    for the logged-in student. Protects personal credentials while providing verifiable identity.
    """
    try:
        student_id = g.current_user.get('student_id')
        if not student_id:
            u = execute_query("SELECT student_id FROM users WHERE id = %s", (g.current_user['id'],), fetch_one=True)
            if u and u.get('student_id'):
                student_id = u['student_id']

        if not student_id:
            return jsonify({'success': False, 'message': 'No student profile linked.'}), 404

        student = execute_query(
            "SELECT id, name, class_name, section, enrolled_date FROM students WHERE id = %s",
            (student_id,),
            fetch_one=True
        )
        if not student:
            return jsonify({'success': False, 'message': 'Student record not found.'}), 404

        # Generate cryptographic signed payload
        qr_payload = generate_student_qr_payload(student['id'])

        return jsonify({
            'success': True,
            'student': {
                'id': student['id'],
                'name': student['name'],
                'class': student['class_name'],
                'section': student['section'],
                'classSection': f"{student['class_name']}-{student['section']}",
                'enrolledDate': student['enrolled_date'].strftime('%Y-%m-%d') if hasattr(student['enrolled_date'], 'strftime') else str(student['enrolled_date'])
            },
            'qrPayload': qr_payload,
            'issuedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error generating student QR pass: {str(e)}"}), 500

# -------------------------------------------------------------
# Teacher QR Attendance Scanner Endpoints
# -------------------------------------------------------------
@app.route('/api/attendance/verify-qr-student', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def verify_qr_student():
    """
    Validate a scanned student QR code payload against backend cryptographic signatures
    and database records. Performs class/section matching and duplicate checks before confirmation.
    """
    data = request.get_json() or {}
    qr_payload = (data.get('qrPayload') or '').strip()
    class_sec = (data.get('classSection') or '').strip()
    session_date = (data.get('date') or '').strip()
    subject = (data.get('subject') or 'General').strip()

    if not qr_payload:
        return jsonify({'success': False, 'code': 'INVALID_QR', 'message': 'QR code data is missing or empty.'}), 400
    if not class_sec or not session_date:
        return jsonify({'success': False, 'code': 'INVALID_SESSION', 'message': 'Active class section and date are required.'}), 400

    # 1. Cryptographic / Token Verification
    is_valid, student_id, err_msg = verify_student_qr_payload(qr_payload)
    if not is_valid:
        return jsonify({
            'success': False,
            'code': 'INVALID_QR',
            'message': f"QR verification failed: {err_msg}"
        }), 400

    # 2. Database Student Lookup
    student = execute_query(
        "SELECT id, name, class_name, section FROM students WHERE id = %s",
        (student_id,),
        fetch_one=True
    )
    if not student:
        return jsonify({
            'success': False,
            'code': 'STUDENT_NOT_FOUND',
            'message': f"Unknown student: Student ID '{student_id}' does not exist in student records."
        }), 404

    # 3. Class and Section Validation
    parts = class_sec.split('-')
    target_class = parts[0].strip()
    target_section = parts[1].strip() if len(parts) > 1 else 'A'

    student_class_sec = f"{student['class_name']}-{student['section']}"
    if student['class_name'].strip().lower() != target_class.lower() or student['section'].strip().lower() != target_section.lower():
        return jsonify({
            'success': False,
            'code': 'WRONG_CLASS_SECTION',
            'message': f"Wrong Class/Section: Student {student['name']} ({student['id']}) belongs to {student_class_sec}, but active session is {class_sec}.",
            'student': {
                'id': student['id'],
                'name': student['name'],
                'class': student['class_name'],
                'section': student['section'],
                'classSection': student_class_sec
            }
        }), 400

    # 4. Duplicate Attendance Check for this Session and Date
    existing_rec = execute_query(
        """
        SELECT r.id, r.status, r.marking_method, s.id AS session_id
        FROM attendance_records r
        JOIN attendance_sessions s ON r.session_id = s.id
        WHERE s.session_date = %s AND s.class_name = %s AND s.section = %s AND r.student_id = %s
        """,
        (session_date, target_class, target_section, student['id']),
        fetch_one=True
    )

    already_marked = existing_rec is not None
    current_status = existing_rec['status'] if existing_rec else None

    status_message = (
        f"Verified: {student['name']} ({student['id']}) belongs to {student_class_sec}."
        if not already_marked
        else f"Warning: {student['name']} ({student['id']}) is already marked {current_status.upper()} for this session."
    )

    return jsonify({
        'success': True,
        'student': {
            'id': student['id'],
            'name': student['name'],
            'class': student['class_name'],
            'section': student['section'],
            'classSection': student_class_sec
        },
        'session': {
            'date': session_date,
            'classSection': class_sec,
            'subject': subject
        },
        'alreadyMarked': already_marked,
        'currentStatus': current_status,
        'message': status_message
    }), 200


@app.route('/api/attendance/record-qr', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def record_qr_attendance():
    """
    Commit a confirmed QR attendance record to MySQL.
    Ensures session exists, marks student Present with marking_method='qr',
    and respects unique database constraints to prevent duplicate entries.
    """
    data = request.get_json() or {}
    student_id = (data.get('studentId') or '').strip().upper()
    class_sec = (data.get('classSection') or '').strip()
    session_date = (data.get('date') or '').strip()
    subject = (data.get('subject') or 'General').strip()
    status = (data.get('status') or 'present').strip().lower()

    if not student_id or not class_sec or not session_date:
        return jsonify({'success': False, 'message': 'Student ID, classSection, and date are required.'}), 400

    if status not in ['present', 'absent']:
        status = 'present'

    try:
        # Verify student exists
        student = execute_query(
            "SELECT id, name, class_name, section FROM students WHERE id = %s",
            (student_id,),
            fetch_one=True
        )
        if not student:
            return jsonify({'success': False, 'message': f"Student '{student_id}' not found."}), 404

        parts = class_sec.split('-')
        target_class = parts[0].strip()
        target_section = parts[1].strip() if len(parts) > 1 else 'A'

        student_class_sec = f"{student['class_name']}-{student['section']}"
        if student['class_name'].strip().lower() != target_class.lower() or student['section'].strip().lower() != target_section.lower():
            return jsonify({
                'success': False,
                'message': f"Student {student['name']} ({student_id}) does not belong to {class_sec}."
            }), 400

        # Find or create session
        session_row = execute_query(
            "SELECT id FROM attendance_sessions WHERE session_date = %s AND class_name = %s AND section = %s",
            (session_date, target_class, target_section),
            fetch_one=True
        )

        user_id = g.current_user['id'] if g.current_user.get('id') else None

        if session_row:
            active_session_id = session_row['id']
            # update subject if specified
            if subject and subject != 'General':
                execute_non_query(
                    "UPDATE attendance_sessions SET subject = %s WHERE id = %s",
                    (subject, active_session_id)
                )
        else:
            active_session_id = f"ATT-{session_date.replace('-', '')}-{target_class.replace(' ', '')}{target_section}-{subject.replace(' ', '')}"
            execute_non_query(
                "INSERT INTO attendance_sessions (id, session_date, class_name, section, subject, recorded_by_user_id) VALUES (%s, %s, %s, %s, %s, %s)",
                (active_session_id, session_date, target_class, target_section, subject, user_id)
            )

        # Upsert record in attendance_records
        execute_non_query(
            """
            INSERT INTO attendance_records (session_id, student_id, status, marking_method, marked_by_user_id)
            VALUES (%s, %s, %s, 'qr', %s)
            ON DUPLICATE KEY UPDATE status = VALUES(status), marking_method = 'qr', marked_by_user_id = VALUES(marked_by_user_id), marked_at = CURRENT_TIMESTAMP
            """,
            (active_session_id, student_id, status, user_id)
        )

        return jsonify({
            'success': True,
            'message': f"Attendance confirmed: {student['name']} ({student_id}) marked {status.upper()} via QR code.",
            'record': {
                'sessionId': active_session_id,
                'studentId': student_id,
                'studentName': student['name'],
                'classSection': class_sec,
                'date': session_date,
                'status': status,
                'markingMethod': 'qr',
                'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat()
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Database save failure: {str(e)}"}), 500


# -------------------------------------------------------------
# Marks Management & Student Results Endpoints
# -------------------------------------------------------------

@app.route('/api/subjects', methods=['GET'])
@token_required
def get_subjects():
    """Return all available curriculum subjects."""
    try:
        rows = execute_query("SELECT id, code, name FROM subjects ORDER BY name ASC")
        return jsonify({
            'success': True,
            'subjects': rows
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Failed to fetch subjects: {str(e)}"}), 500


@app.route('/api/assessments', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_assessments():
    """
    List assessments with optional class, section, subject, and status filters.
    Includes assessed students count, max marks, status, and class turnouts.
    """
    try:
        class_filter = request.args.get('class')
        section_filter = request.args.get('section')
        subject_filter = request.args.get('subject')
        status_filter = request.args.get('status')

        query = """
            SELECT a.id, a.name, a.type, a.subject_name, a.class_name, a.section,
                   CONCAT(a.class_name, '-', a.section) AS classSection,
                   a.assessment_date, a.max_marks, a.passing_marks, a.status,
                   a.published_at, a.created_at, u.name AS created_by_name,
                   (SELECT COUNT(*) FROM students s WHERE s.class_name = a.class_name AND s.section = a.section) AS total_enrolled,
                   (SELECT COUNT(*) FROM student_marks sm WHERE sm.assessment_id = a.id AND sm.draft_marks IS NOT NULL) AS assessed_count,
                   (SELECT COUNT(*) FROM student_marks sm WHERE sm.assessment_id = a.id AND sm.is_published = TRUE AND sm.published_marks IS NOT NULL) AS published_count,
                   (SELECT AVG(sm.draft_marks) FROM student_marks sm WHERE sm.assessment_id = a.id AND sm.draft_marks IS NOT NULL) AS avg_draft_marks
            FROM assessments a
            LEFT JOIN users u ON a.created_by_user_id = u.id
            WHERE 1=1
        """
        params = []

        if class_filter and class_filter != 'ALL':
            query += " AND a.class_name = %s"
            params.append(class_filter)
        if section_filter and section_filter != 'ALL':
            query += " AND a.section = %s"
            params.append(section_filter)
        if subject_filter and subject_filter != 'ALL':
            query += " AND a.subject_name = %s"
            params.append(subject_filter)
        if status_filter and status_filter != 'ALL':
            query += " AND a.status = %s"
            params.append(status_filter)

        query += " ORDER BY a.assessment_date DESC, a.created_at DESC"
        rows = execute_query(query, params)

        assessments = []
        for r in rows:
            max_m = float(r['max_marks'])
            avg_m = float(r['avg_draft_marks']) if r['avg_draft_marks'] is not None else None
            avg_pct = round((avg_m / max_m) * 100, 1) if avg_m is not None and max_m > 0 else None

            assessments.append({
                'id': r['id'],
                'name': r['name'],
                'type': r['type'],
                'subject': r['subject_name'],
                'class': r['class_name'],
                'section': r['section'],
                'classSection': r['classSection'],
                'assessmentDate': r['assessment_date'].strftime('%Y-%m-%d') if hasattr(r['assessment_date'], 'strftime') else str(r['assessment_date']),
                'maxMarks': max_m,
                'passingMarks': float(r['passing_marks']),
                'status': r['status'],  # 'draft', 'published', 'updated'
                'publishedAt': r['published_at'].strftime('%Y-%m-%d %H:%M') if r.get('published_at') and hasattr(r['published_at'], 'strftime') else str(r.get('published_at') or ''),
                'createdAt': r['created_at'].strftime('%Y-%m-%d') if hasattr(r['created_at'], 'strftime') else str(r['created_at']),
                'createdByName': r.get('created_by_name') or 'Instructor',
                'totalEnrolled': r['total_enrolled'],
                'assessedCount': r['assessed_count'],
                'publishedCount': r['published_count'],
                'averageMarks': avg_m,
                'averagePercentage': avg_pct
            })

        return jsonify({
            'success': True,
            'count': len(assessments),
            'assessments': assessments
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error listing assessments: {str(e)}"}), 500


@app.route('/api/assessments', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def create_assessment():
    """
    Create a new assessment in DRAFT status and initialize student mark records
    for all enrolled students in the target class and section.
    """
    try:
        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        asm_type = (data.get('type') or 'Internal Exam').strip()
        subject = (data.get('subject') or '').strip()
        class_name = (data.get('class') or data.get('className') or '').strip()
        section = (data.get('section') or '').strip().upper()
        assessment_date = (data.get('assessmentDate') or data.get('date') or '').strip()

        valid_types = ['Internal Exam', 'Mid Exam', 'Assignment', 'Lab Exam', 'Semester Exam']
        if asm_type not in valid_types:
            return jsonify({'success': False, 'message': f"Invalid assessment type. Must be one of: {', '.join(valid_types)}"}), 400

        if not name or not subject or not class_name or not section or not assessment_date:
            return jsonify({'success': False, 'message': "Assessment name, subject, class, section, and date are required."}), 400

        try:
            max_marks = float(data.get('maxMarks', data.get('max_marks', 100)))
            passing_marks = float(data.get('passingMarks', data.get('passing_marks', 35)))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': "Maximum marks and passing marks must be valid numbers."}), 400

        if max_marks <= 0:
            return jsonify({'success': False, 'message': "Maximum marks must be greater than zero."}), 400
        if passing_marks < 0:
            return jsonify({'success': False, 'message': "Passing marks cannot be negative."}), 400
        if passing_marks > max_marks:
            return jsonify({'success': False, 'message': f"Passing marks ({passing_marks}) cannot exceed maximum marks ({max_marks})."}), 400

        # Generate unique ID
        subj_clean = re.sub(r'[^A-Za-z0-9]', '', subject)[:4].upper()
        clean_class = class_name.replace(' ', '')
        rand_suffix = secrets.token_hex(3).upper()
        date_str = assessment_date.replace('-', '')
        asm_id = f"ASM-{date_str}-{clean_class}{section}-{subj_clean}-{rand_suffix}"

        user_id = g.current_user.get('id')

        execute_non_query(
            """
            INSERT INTO assessments (id, name, type, subject_name, class_name, section,
                                    assessment_date, max_marks, passing_marks, status, created_by_user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'draft', %s)
            """,
            (asm_id, name, asm_type, subject, class_name, section, assessment_date, max_marks, passing_marks, user_id)
        )

        # Pre-populate student_marks for all students currently in this class & section
        enrolled_students = execute_query(
            "SELECT id FROM students WHERE class_name = %s AND section = %s ORDER BY id",
            (class_name, section)
        )
        for s in enrolled_students:
            execute_non_query(
                """
                INSERT INTO student_marks (assessment_id, student_id, draft_marks, published_marks, is_published)
                VALUES (%s, %s, NULL, NULL, FALSE)
                ON DUPLICATE KEY UPDATE updated_at = CURRENT_TIMESTAMP
                """,
                (asm_id, s['id'])
            )

        return jsonify({
            'success': True,
            'message': f"Assessment '{name}' created as Draft for {class_name}-{section} ({len(enrolled_students)} students registered).",
            'assessment': {
                'id': asm_id,
                'name': name,
                'type': asm_type,
                'subject': subject,
                'class': class_name,
                'section': section,
                'classSection': f"{class_name}-{section}",
                'assessmentDate': assessment_date,
                'maxMarks': max_marks,
                'passingMarks': passing_marks,
                'status': 'draft',
                'totalEnrolled': len(enrolled_students),
                'assessedCount': 0
            }
        }), 201
    except Exception as e:
        return jsonify({'success': False, 'message': f"Failed to create assessment: {str(e)}"}), 500


@app.route('/api/assessments/<string:assessment_id>', methods=['GET'])
@token_required
@roles_required('teacher', 'admin')
def get_assessment_detail(assessment_id):
    """
    Get assessment details along with student marks list and class performance summary.
    """
    try:
        asm = execute_query(
            """
            SELECT a.id, a.name, a.type, a.subject_name, a.class_name, a.section,
                   CONCAT(a.class_name, '-', a.section) AS classSection,
                   a.assessment_date, a.max_marks, a.passing_marks, a.status,
                   a.published_at, a.created_at, u.name AS created_by_name
            FROM assessments a
            LEFT JOIN users u ON a.created_by_user_id = u.id
            WHERE a.id = %s
            """,
            (assessment_id,),
            fetch_one=True
        )
        if not asm:
            return jsonify({'success': False, 'message': f"Assessment '{assessment_id}' not found."}), 404

        max_m = float(asm['max_marks'])
        pass_m = float(asm['passing_marks'])

        # Fetch all students in the class/section with their marks
        students_marks_rows = execute_query(
            """
            SELECT s.id AS student_id, s.name AS student_name,
                   sm.id AS mark_id, sm.draft_marks, sm.published_marks, sm.is_published
            FROM students s
            LEFT JOIN student_marks sm ON sm.student_id = s.id AND sm.assessment_id = %s
            WHERE s.class_name = %s AND s.section = %s
            ORDER BY s.id ASC
            """,
            (assessment_id, asm['class_name'], asm['section'])
        )

        students_list = []
        assessed_marks_values = []
        pass_count = 0

        for r in students_marks_rows:
            d_marks = float(r['draft_marks']) if r['draft_marks'] is not None else None
            p_marks = float(r['published_marks']) if r['published_marks'] is not None else None
            is_pub = bool(r['is_published'])

            pct = None
            status_label = 'Not Entered'
            if d_marks is not None:
                assessed_marks_values.append(d_marks)
                pct = round((d_marks / max_m) * 100, 1) if max_m > 0 else 0
                if d_marks >= pass_m:
                    status_label = 'Pass'
                    pass_count += 1
                else:
                    status_label = 'Fail'

            students_list.append({
                'studentId': r['student_id'],
                'studentName': r['student_name'],
                'draftMarks': d_marks,
                'publishedMarks': p_marks,
                'isPublished': is_pub,
                'percentage': pct,
                'status': status_label
            })

        total_enrolled = len(students_list)
        assessed_count = len(assessed_marks_values)
        avg_marks = round(sum(assessed_marks_values) / assessed_count, 2) if assessed_count > 0 else None
        avg_pct = round((avg_marks / max_m) * 100, 1) if avg_marks is not None and max_m > 0 else None
        highest_marks = max(assessed_marks_values) if assessed_count > 0 else None
        lowest_marks = min(assessed_marks_values) if assessed_count > 0 else None
        pass_pct = round((pass_count / assessed_count) * 100, 1) if assessed_count > 0 else 0.0

        performance_summary = {
            'totalEnrolled': total_enrolled,
            'assessedCount': assessed_count,
            'unassessedCount': total_enrolled - assessed_count,
            'averageMarks': avg_marks,
            'averagePercentage': avg_pct,
            'highestMarks': highest_marks,
            'lowestMarks': lowest_marks,
            'passCount': pass_count,
            'failCount': assessed_count - pass_count,
            'passPercentage': pass_pct
        }

        return jsonify({
            'success': True,
            'assessment': {
                'id': asm['id'],
                'name': asm['name'],
                'type': asm['type'],
                'subject': asm['subject_name'],
                'class': asm['class_name'],
                'section': asm['section'],
                'classSection': asm['classSection'],
                'assessmentDate': asm['assessment_date'].strftime('%Y-%m-%d') if hasattr(asm['assessment_date'], 'strftime') else str(asm['assessment_date']),
                'maxMarks': max_m,
                'passingMarks': pass_m,
                'status': asm['status'],
                'publishedAt': asm['published_at'].strftime('%Y-%m-%d %H:%M') if asm.get('published_at') and hasattr(asm['published_at'], 'strftime') else str(asm.get('published_at') or ''),
                'createdAt': asm['created_at'].strftime('%Y-%m-%d') if hasattr(asm['created_at'], 'strftime') else str(asm['created_at']),
                'createdByName': asm.get('created_by_name') or 'Instructor'
            },
            'students': students_list,
            'performanceSummary': performance_summary
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error retrieving assessment details: {str(e)}"}), 500


@app.route('/api/assessments/<string:assessment_id>', methods=['PUT'])
@token_required
@roles_required('teacher', 'admin')
def update_assessment(assessment_id):
    """Update assessment metadata."""
    try:
        asm = execute_query("SELECT id, status, max_marks FROM assessments WHERE id = %s", (assessment_id,), fetch_one=True)
        if not asm:
            return jsonify({'success': False, 'message': f"Assessment '{assessment_id}' not found."}), 404

        data = request.get_json() or {}
        name = (data.get('name') or '').strip()
        assessment_date = (data.get('assessmentDate') or data.get('date') or '').strip()

        try:
            max_marks = float(data.get('maxMarks', asm['max_marks']))
            passing_marks = float(data.get('passingMarks', 35))
        except (ValueError, TypeError):
            return jsonify({'success': False, 'message': "Maximum marks and passing marks must be valid numbers."}), 400

        if max_marks <= 0 or passing_marks < 0 or passing_marks > max_marks:
            return jsonify({'success': False, 'message': "Invalid max marks or passing marks."}), 400

        execute_non_query(
            """
            UPDATE assessments
            SET name = %s, assessment_date = %s, max_marks = %s, passing_marks = %s
            WHERE id = %s
            """,
            (name, assessment_date, max_marks, passing_marks, assessment_id)
        )

        return jsonify({'success': True, 'message': f"Assessment '{name}' updated successfully."}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Update failed: {str(e)}"}), 500


@app.route('/api/assessments/<string:assessment_id>', methods=['DELETE'])
@token_required
@roles_required('teacher', 'admin')
def delete_assessment(assessment_id):
    """Delete an assessment and its marks."""
    try:
        asm = execute_query("SELECT id, name FROM assessments WHERE id = %s", (assessment_id,), fetch_one=True)
        if not asm:
            return jsonify({'success': False, 'message': f"Assessment '{assessment_id}' not found."}), 404

        execute_non_query("DELETE FROM assessments WHERE id = %s", (assessment_id,))
        return jsonify({'success': True, 'message': f"Assessment '{asm['name']}' has been deleted."}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Delete failed: {str(e)}"}), 500


@app.route('/api/assessments/<string:assessment_id>/marks', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def save_assessment_marks(assessment_id):
    """
    Save student marks as DRAFT.
    Validates numeric values, non-negativity, and <= maximum marks.
    Preserves previously published marks for students; transitions published
    assessment to 'updated' status.
    """
    try:
        asm = execute_query(
            "SELECT id, name, status, max_marks, passing_marks, class_name, section FROM assessments WHERE id = %s",
            (assessment_id,),
            fetch_one=True
        )
        if not asm:
            return jsonify({'success': False, 'message': f"Assessment '{assessment_id}' not found."}), 404

        max_marks = float(asm['max_marks'])
        data = request.get_json() or {}
        raw_marks = data.get('marks')

        # Convert raw_marks to dict { studentId: val }
        marks_dict = {}
        if isinstance(raw_marks, dict):
            marks_dict = raw_marks
        elif isinstance(raw_marks, list):
            for item in raw_marks:
                if isinstance(item, dict) and 'studentId' in item:
                    marks_dict[item['studentId']] = item.get('marks')
        else:
            return jsonify({'success': False, 'message': "Marks payload must be an object or array of student marks."}), 400

        # Validate all marks before writing to database
        validated_entries = []
        for s_id, val in marks_dict.items():
            stu_id = str(s_id).strip().upper()
            if val is None or val == '':
                validated_entries.append((stu_id, None))
                continue

            try:
                num_val = float(val)
            except (ValueError, TypeError):
                return jsonify({'success': False, 'message': f"Invalid mark value '{val}' for student {stu_id}. Marks must be numeric."}), 400

            if num_val < 0:
                return jsonify({'success': False, 'message': f"Marks cannot be negative. Student {stu_id} has value {num_val}."}), 400

            if num_val > max_marks:
                return jsonify({
                    'success': False,
                    'message': f"Marks for student {stu_id} ({num_val}) exceed maximum marks ({max_marks})."
                }), 400

            validated_entries.append((stu_id, round(num_val, 2)))

        # Upsert validated marks into student_marks as DRAFT
        for stu_id, m_val in validated_entries:
            execute_non_query(
                """
                INSERT INTO student_marks (assessment_id, student_id, draft_marks, is_published)
                VALUES (%s, %s, %s, FALSE)
                ON DUPLICATE KEY UPDATE draft_marks = VALUES(draft_marks);
                """,
                (assessment_id, stu_id, m_val)
            )

        # Update assessment status:
        # If it was already published, transition to 'updated' so teachers know changes are pending republish
        # If it was draft, keep as 'draft'
        new_status = 'updated' if asm['status'] == 'published' else asm['status']
        if new_status != asm['status']:
            execute_non_query("UPDATE assessments SET status = %s WHERE id = %s", (new_status, assessment_id))

        status_msg = "Draft marks saved successfully!"
        if new_status == 'updated':
            status_msg = "Marks updated in draft mode! Click 'Publish Marks' to make updated results visible to students."

        return jsonify({
            'success': True,
            'message': status_msg,
            'assessmentStatus': new_status,
            'savedCount': len(validated_entries)
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Failed to save marks: {str(e)}"}), 500


@app.route('/api/assessments/<string:assessment_id>/publish', methods=['POST'])
@token_required
@roles_required('teacher', 'admin')
def publish_assessment_marks(assessment_id):
    """
    Publish marks for an assessment:
    Copies draft_marks to published_marks, sets is_published=TRUE,
    and updates assessment status to 'published' with timestamp.
    Only published marks are visible to students.
    """
    try:
        asm = execute_query(
            "SELECT id, name, status, class_name, section FROM assessments WHERE id = %s",
            (assessment_id,),
            fetch_one=True
        )
        if not asm:
            return jsonify({'success': False, 'message': f"Assessment '{assessment_id}' not found."}), 404

        # Commit draft_marks into published_marks
        execute_non_query(
            """
            UPDATE student_marks
            SET published_marks = draft_marks, is_published = TRUE
            WHERE assessment_id = %s AND draft_marks IS NOT NULL
            """,
            (assessment_id,)
        )

        # Update assessment status to published
        execute_non_query(
            """
            UPDATE assessments
            SET status = 'published', published_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (assessment_id,)
        )

        published_count_row = execute_query(
            "SELECT COUNT(*) AS cnt FROM student_marks WHERE assessment_id = %s AND is_published = TRUE AND published_marks IS NOT NULL",
            (assessment_id,),
            fetch_one=True
        )
        pub_count = published_count_row['cnt'] if published_count_row else 0

        return jsonify({
            'success': True,
            'message': f"Assessment '{asm['name']}' published successfully! ({pub_count} student marks are now visible on the Student Portal).",
            'publishedCount': pub_count,
            'status': 'published',
            'publishedAt': datetime.datetime.now(datetime.timezone.utc).isoformat()
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Failed to publish marks: {str(e)}"}), 500


@app.route('/api/student/marks', methods=['GET'])
@token_required
@roles_required('student')
def get_student_marks():
    """
    Return published marks strictly for the authenticated student.
    Draft marks and unverified updates are completely hidden.
    Includes subject summaries, individual assessments, percentages, and pass/fail indicators.
    """
    try:
        student_id = g.current_user.get('student_id')
        if not student_id:
            u = execute_query("SELECT student_id FROM users WHERE id = %s", (g.current_user['id'],), fetch_one=True)
            if u and u.get('student_id'):
                student_id = u['student_id']

        if not student_id:
            return jsonify({'success': False, 'message': 'No student profile linked.'}), 404

        student = execute_query(
            "SELECT id, name, class_name, section FROM students WHERE id = %s",
            (student_id,),
            fetch_one=True
        )
        if not student:
            return jsonify({'success': False, 'message': 'Student record not found.'}), 404

        subject_filter = request.args.get('subject')
        type_filter = request.args.get('type')

        # Strictly query only published marks where is_published = TRUE and status IN ('published', 'updated')
        query = """
            SELECT sm.id, sm.published_marks, a.id AS assessment_id, a.name AS assessment_name,
                   a.type AS assessment_type, a.subject_name, a.max_marks, a.passing_marks,
                   a.assessment_date, a.published_at, a.status AS assessment_status,
                   a.class_name, a.section
            FROM student_marks sm
            JOIN assessments a ON sm.assessment_id = a.id
            WHERE sm.student_id = %s
              AND sm.is_published = TRUE
              AND a.status IN ('published', 'updated')
              AND sm.published_marks IS NOT NULL
        """
        params = [student_id]

        if subject_filter and subject_filter != 'ALL':
            query += " AND a.subject_name = %s"
            params.append(subject_filter)
        if type_filter and type_filter != 'ALL':
            query += " AND a.type = %s"
            params.append(type_filter)

        query += " ORDER BY a.assessment_date DESC, a.published_at DESC"
        rows = execute_query(query, params)

        if not rows:
            return jsonify({
                'success': True,
                'hasPublishedMarks': False,
                'message': 'Your marks have not been published yet.',
                'student': {
                    'id': student['id'],
                    'name': student['name'],
                    'classSection': f"{student['class_name']}-{student['section']}"
                },
                'results': [],
                'subjectSummaries': [],
                'overall': {
                    'totalAssessments': 0,
                    'overallPercentage': None,
                    'passedCount': 0,
                    'failedCount': 0
                }
            }), 200

        results = []
        subjects_map = {}
        total_obtained = 0.0
        total_max = 0.0
        passed_count = 0
        failed_count = 0

        for r in rows:
            m_obt = float(r['published_marks'])
            m_max = float(r['max_marks'])
            m_pass = float(r['passing_marks'])
            pct = round((m_obt / m_max) * 100, 1) if m_max > 0 else 0.0
            is_pass = m_obt >= m_pass

            total_obtained += m_obt
            total_max += m_max
            if is_pass:
                passed_count += 1
            else:
                failed_count += 1

            # Determine letter grade
            if pct >= 90:
                grade = 'A+'
            elif pct >= 80:
                grade = 'A'
            elif pct >= 70:
                grade = 'B'
            elif pct >= 60:
                grade = 'C'
            elif is_pass:
                grade = 'D'
            else:
                grade = 'F'

            subj = r['subject_name']
            if subj not in subjects_map:
                subjects_map[subj] = {
                    'subject': subj,
                    'totalObtained': 0.0,
                    'totalMax': 0.0,
                    'assessmentsCount': 0,
                    'passedCount': 0,
                    'failedCount': 0
                }
            subjects_map[subj]['totalObtained'] += m_obt
            subjects_map[subj]['totalMax'] += m_max
            subjects_map[subj]['assessmentsCount'] += 1
            if is_pass:
                subjects_map[subj]['passedCount'] += 1
            else:
                subjects_map[subj]['failedCount'] += 1

            results.append({
                'id': r['id'],
                'assessmentId': r['assessment_id'],
                'assessmentName': r['assessment_name'],
                'assessmentType': r['assessment_type'],
                'subject': subj,
                'marksObtained': m_obt,
                'maxMarks': m_max,
                'passingMarks': m_pass,
                'percentage': pct,
                'passed': is_pass,
                'grade': grade,
                'date': r['assessment_date'].strftime('%Y-%m-%d') if hasattr(r['assessment_date'], 'strftime') else str(r['assessment_date']),
                'publishedAt': r['published_at'].strftime('%Y-%m-%d %H:%M') if r.get('published_at') and hasattr(r['published_at'], 'strftime') else str(r.get('published_at') or '')
            })

        # Calculate subject summaries
        subject_summaries = []
        for s_name, s_data in subjects_map.items():
            s_pct = round((s_data['totalObtained'] / s_data['totalMax']) * 100, 1) if s_data['totalMax'] > 0 else 0.0
            subject_summaries.append({
                'subject': s_name,
                'totalObtained': round(s_data['totalObtained'], 2),
                'totalMax': round(s_data['totalMax'], 2),
                'averagePercentage': s_pct,
                'assessmentsCount': s_data['assessmentsCount'],
                'passedCount': s_data['passedCount'],
                'failedCount': s_data['failedCount']
            })

        overall_pct = round((total_obtained / total_max) * 100, 1) if total_max > 0 else 0.0

        return jsonify({
            'success': True,
            'hasPublishedMarks': True,
            'student': {
                'id': student['id'],
                'name': student['name'],
                'classSection': f"{student['class_name']}-{student['section']}"
            },
            'results': results,
            'subjectSummaries': subject_summaries,
            'overall': {
                'totalAssessments': len(results),
                'overallPercentage': overall_pct,
                'totalObtained': round(total_obtained, 2),
                'totalMax': round(total_max, 2),
                'passedCount': passed_count,
                'failedCount': failed_count
            }
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f"Error retrieving student marks: {str(e)}"}), 500


if __name__ == '__main__':
    print(f"Starting AttendX Flask Server on {Config.FLASK_HOST}:{Config.FLASK_PORT}...")
    app.run(host=Config.FLASK_HOST, port=Config.FLASK_PORT, debug=Config.FLASK_DEBUG)
