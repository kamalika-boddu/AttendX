import sys
from app import app
from auth_utils import verify_password
from db import execute_query

client = app.test_client()

print("=== 1. TEACHER AUTHENTICATION & ACCESS ===")
t_res = client.post('/api/auth/login', json={'email': 'teacher@attendx.edu', 'password': 'teacher123', 'role': 'teacher'})
assert t_res.status_code == 200, t_res.get_json()
t_token = t_res.get_json()['token']
t_headers = {'Authorization': f'Bearer {t_token}'}
assert client.get('/api/dashboard/summary', headers=t_headers).status_code == 200
assert client.get('/api/students', headers=t_headers).status_code == 200
assert client.get('/api/reports', headers=t_headers).status_code == 200
print("PASS: Teacher authenticated and accessed teacher routes.")

print("=== 2. ADMIN AUTHENTICATION & ACCESS ===")
a_res = client.post('/api/auth/login', json={'email': 'admin@attendx.edu', 'password': 'admin123', 'role': 'admin'})
assert a_res.status_code == 200, a_res.get_json()
a_token = a_res.get_json()['token']
a_headers = {'Authorization': f'Bearer {a_token}'}
assert client.get('/api/dashboard/summary', headers=a_headers).status_code == 200
assert client.get('/api/students', headers=a_headers).status_code == 200
assert client.get('/api/reports', headers=a_headers).status_code == 200
print("PASS: Admin authenticated and accessed admin routes.")

print("=== 3. STUDENT AUTHENTICATION (STUDENT ID & EMAIL) ===")
s_res1 = client.post('/api/auth/login', json={'email': 'STD-101', 'password': 'student123', 'role': 'student'})
assert s_res1.status_code == 200, s_res1.get_json()
s_token1 = s_res1.get_json()['token']
s_res2 = client.post('/api/auth/login', json={'email': 'alexander@attendx.edu', 'password': 'student123', 'role': 'student'})
assert s_res2.status_code == 200, s_res2.get_json()
print("PASS: Student can log in using either Student ID or registered email.")

print("=== 4. STUDENT DASHBOARD & 75% ATTENDANCE METRICS (ALEXANDER WRIGHT) ===")
s_headers = {'Authorization': f'Bearer {s_token1}'}
dash = client.get('/api/student/dashboard', headers=s_headers).get_json()
assert dash['success'] is True
student_obj = dash['student']
assert student_obj['id'] == 'STD-101'
assert student_obj['name'] == 'Alexander Wright'
assert student_obj['class'] == 'Class 10'
assert student_obj['section'] == 'A'
metrics = dash['metrics']
assert metrics['totalConducted'] == 13
assert metrics['attended'] == 12
assert metrics['missed'] == 1
assert metrics['attendancePercentage'] == 92.3
assert metrics['isAboveThreshold'] is True
assert metrics['consecutiveClassesNeeded'] == 0
assert 'currently meet' in metrics['statusMessage']
assert len(dash['history']) == 13
print(f"PASS: Alexander Wright metrics verified: {metrics['attendancePercentage']}% (Attended: {metrics['attended']}/{metrics['totalConducted']}, Needed: {metrics['consecutiveClassesNeeded']})")

print("=== 5. STUDENT WITH BELOW 75% ATTENDANCE (MARCUS JOHNSON) ===")
m_res = client.post('/api/auth/login', json={'email': 'STD-103', 'password': 'student123', 'role': 'student'})
m_token = m_res.get_json()['token']
m_dash = client.get('/api/student/dashboard', headers={'Authorization': f'Bearer {m_token}'}).get_json()
m_metrics = m_dash['metrics']
assert m_metrics['isAboveThreshold'] is False
expected_needed = max(0, 3 * m_metrics['totalConducted'] - 4 * m_metrics['attended'])
assert m_metrics['consecutiveClassesNeeded'] == expected_needed
assert f"Attend the next {expected_needed} classes to reach 75%" in m_metrics['statusMessage']
assert (m_metrics['attended'] + expected_needed) / (m_metrics['totalConducted'] + expected_needed) >= 0.75
print(f"PASS: Marcus Johnson below-75% formula verified: {m_metrics['attendancePercentage']}% -> {m_metrics['consecutiveClassesNeeded']} classes needed.")

print("=== 6. STUDENT WITH 0 CLASSES CONDUCTED (LIAM PATEL) ===")
l_res = client.post('/api/auth/login', json={'email': 'STD-201', 'password': 'student123', 'role': 'student'})
l_token = l_res.get_json()['token']
l_dash = client.get('/api/student/dashboard', headers={'Authorization': f'Bearer {l_token}'}).get_json()
l_metrics = l_dash['metrics']
assert l_metrics['totalConducted'] == 0
assert l_metrics['attendancePercentage'] is None
assert l_metrics['status'] == 'No attendance data yet'
assert l_metrics['consecutiveClassesNeeded'] == 0
print("PASS: Liam Patel 0-classes handling verified: Displays 'No attendance data yet'.")

print("=== 7. CLASS AGGREGATE ATTENDANCE & PRIVACY SAFEGUARD ===")
class_res = client.get('/api/student/class-attendance', headers=s_headers).get_json()
assert class_res['success'] is True
assert class_res['totalStudents'] == 15
assert class_res['totalSessions'] == 14
assert class_res['overallClassRate'] == 87.7
for h in class_res['history']:
    assert 'student_id' not in h
    assert 'name' not in h
    assert 'presentCount' in h
    assert 'absentCount' in h
print("PASS: Class aggregate attendance verified with strict classmate privacy.")

print("=== 8. RBAC SECURITY RESTRICTIONS: STUDENT FORBIDDEN ON TEACHER/ADMIN PAGES ===")
assert client.get('/api/students', headers=s_headers).status_code == 403
assert client.get('/api/reports', headers=s_headers).status_code == 403
assert client.get('/api/dashboard/summary', headers=s_headers).status_code == 403
assert client.get('/api/attendance', headers=s_headers).status_code == 403
assert client.get('/api/attendance/session', headers=s_headers).status_code == 403
assert client.post('/api/students', headers=s_headers, json={'name': 'Hacker'}).status_code == 403
assert client.post('/api/attendance', headers=s_headers, json={'records': {}}).status_code == 403
print("PASS: All 7 protected endpoints return 403 Forbidden for Student role.")

print("=== ALL TESTS COMPLETED SUCCESSFULLY! ===")
