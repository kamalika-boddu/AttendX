import json
from app import app
from auth_utils import generate_student_qr_payload, verify_student_qr_payload
from db import execute_query, execute_non_query

client = app.test_client()

print("=== 1. HMAC-SHA256 QR PAYLOAD GENERATION & VERIFICATION ===")
raw_payload = generate_student_qr_payload("STD-101")
print(f"Generated Payload: {raw_payload[:80]}...")
assert "STD-101" in raw_payload
assert "sig" in raw_payload

# Verify authentic payload
is_valid, stu_id, err = verify_student_qr_payload(raw_payload)
assert is_valid is True, f"Failed verification: {err}"
assert stu_id == "STD-101"
print("PASS: Authentic QR payload verified successfully.")

# Verify tampered payload (altered student ID)
tampered_payload = raw_payload.replace("STD-101", "STD-999")
is_valid_t, _, err_t = verify_student_qr_payload(tampered_payload)
assert is_valid_t is False
assert "signature validation failed" in err_t.lower()
print(f"PASS: Tampered QR payload correctly rejected: {err_t}")

print("\n=== 2. STUDENT QR PASS RETRIEVAL VIA API ===")
s_login = client.post('/api/auth/login', json={'email': 'STD-101', 'password': 'student123', 'role': 'student'})
assert s_login.status_code == 200, s_login.get_json()
s_token = s_login.get_json()['token']
s_headers = {'Authorization': f'Bearer {s_token}'}

qr_res = client.get('/api/student/qr-pass', headers=s_headers)
assert qr_res.status_code == 200, qr_res.get_json()
qr_data = qr_res.get_json()
assert qr_data['success'] is True
assert qr_data['student']['id'] == 'STD-101'
assert qr_data['student']['name'] == 'Alexander Wright'
assert qr_data['student']['class'] == 'Class 10'
assert qr_data['student']['section'] == 'A'
assert 'qrPayload' in qr_data
student_qr = qr_data['qrPayload']
print("PASS: Student retrieved cryptographically signed QR pass successfully.")

print("\n=== 3. TEACHER QR VERIFICATION (MATCHING SESSION) ===")
t_login = client.post('/api/auth/login', json={'email': 'teacher@attendx.edu', 'password': 'teacher123', 'role': 'teacher'})
assert t_login.status_code == 200, t_login.get_json()
t_token = t_login.get_json()['token']
t_headers = {'Authorization': f'Bearer {t_token}'}

test_date = '2026-10-25'
test_class_sec = 'Class 10-A'

# Clean up any leftover test record for test_date
execute_non_query(
    """DELETE r FROM attendance_records r
       JOIN attendance_sessions s ON r.session_id = s.id
       WHERE s.class_name = 'Class 10' AND s.section = 'A' AND s.session_date = %s""",
    (test_date,)
)

verify_res = client.post('/api/attendance/verify-qr-student', headers=t_headers, json={
    'qrPayload': student_qr,
    'classSection': test_class_sec,
    'date': test_date,
    'subject': 'Mathematics'
})
assert verify_res.status_code == 200, verify_res.get_json()
v_data = verify_res.get_json()
assert v_data['success'] is True
assert v_data['student']['id'] == 'STD-101'
assert v_data['student']['name'] == 'Alexander Wright'
assert v_data['alreadyMarked'] is False
print("PASS: Teacher successfully verified student QR for matching class/section.")

print("\n=== 4. TEACHER QR VERIFICATION (MISMATCHED CLASS / SECTION) ===")
wrong_res = client.post('/api/attendance/verify-qr-student', headers=t_headers, json={
    'qrPayload': student_qr,
    'classSection': 'Class 11-B',
    'date': test_date
})
assert wrong_res.status_code == 400
w_data = wrong_res.get_json()
assert w_data['success'] is False
assert w_data['code'] == 'WRONG_CLASS_SECTION'
assert "belongs to Class 10-A, but active session is Class 11-B" in w_data['message']
print(f"PASS: Mismatched cohort scan rejected: {w_data['message']}")

print("\n=== 5. TEACHER QR VERIFICATION (TAMPERED / FORGED QR) ===")
bad_sig_res = client.post('/api/attendance/verify-qr-student', headers=t_headers, json={
    'qrPayload': tampered_payload,
    'classSection': test_class_sec,
    'date': test_date
})
assert bad_sig_res.status_code == 400
b_data = bad_sig_res.get_json()
assert b_data['success'] is False
assert b_data['code'] == 'INVALID_QR'
assert "signature validation failed" in b_data['message'].lower()
print("PASS: Forged QR code rejected with INVALID_QR signature error.")

print("\n=== 6. TEACHER RECORDING QR ATTENDANCE (PERSISTENCE) ===")
rec_res = client.post('/api/attendance/record-qr', headers=t_headers, json={
    'studentId': 'STD-101',
    'classSection': test_class_sec,
    'date': test_date,
    'status': 'present',
    'subject': 'Mathematics'
})
assert rec_res.status_code == 200, rec_res.get_json()
r_data = rec_res.get_json()
assert r_data['success'] is True
assert r_data['record']['markingMethod'] == 'qr'
assert r_data['record']['studentId'] == 'STD-101'
assert r_data['record']['status'] == 'present'

# Verify in DB directly
db_rows = execute_query(
    """SELECT r.status, r.marking_method, s.session_date, s.class_name, s.section
       FROM attendance_records r
       JOIN attendance_sessions s ON r.session_id = s.id
       WHERE r.student_id = 'STD-101' AND s.session_date = %s""",
    (test_date,)
)
assert len(db_rows) == 1
assert db_rows[0]['status'] == 'present'
assert db_rows[0]['marking_method'] == 'qr'
print("PASS: Attendance record persisted in MySQL database with marking_method='qr'.")

print("\n=== 7. DUPLICATE ATTENDANCE DETECTION ===")
dup_verify = client.post('/api/attendance/verify-qr-student', headers=t_headers, json={
    'qrPayload': student_qr,
    'classSection': test_class_sec,
    'date': test_date
})
assert dup_verify.status_code == 200
d_data = dup_verify.get_json()
assert d_data['success'] is True
assert d_data['alreadyMarked'] is True
assert d_data['currentStatus'].lower() == 'present'
print("PASS: Duplicate scan accurately detected alreadyMarked=True with current status 'present'.")

print("\n=== 8. RBAC PERMISSIONS ON QR ENDPOINTS ===")
# Student should NOT be able to verify QR or record attendance
s_verify = client.post('/api/attendance/verify-qr-student', headers=s_headers, json={
    'qrPayload': student_qr,
    'classSection': test_class_sec,
    'date': test_date
})
assert s_verify.status_code == 403, f"Expected 403, got {s_verify.status_code}"

s_rec = client.post('/api/attendance/record-qr', headers=s_headers, json={
    'studentId': 'STD-101',
    'classSection': test_class_sec,
    'date': test_date,
    'status': 'present'
})
assert s_rec.status_code == 403, f"Expected 403, got {s_rec.status_code}"

# Teacher should NOT be able to view student QR pass (only student role)
t_qr = client.get('/api/student/qr-pass', headers=t_headers)
assert t_qr.status_code == 403, f"Expected 403, got {t_qr.status_code}"

print("PASS: All RBAC permissions correctly enforced: students cannot mark attendance, teachers cannot access student pass endpoint.")

# Clean up test record
execute_non_query(
    """DELETE r FROM attendance_records r
       JOIN attendance_sessions s ON r.session_id = s.id
       WHERE s.class_name = 'Class 10' AND s.section = 'A' AND s.session_date = %s""",
    (test_date,)
)
execute_non_query(
    """DELETE FROM attendance_sessions
       WHERE class_name = 'Class 10' AND section = 'A' AND session_date = %s""",
    (test_date,)
)

print("\n==========================================")
print("ALL 8 QR ATTENDANCE TEST SUITES PASSED!")
print("==========================================")
