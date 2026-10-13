import json
from app import app

def test_backend_api():
    client = app.test_client()
    print("=== Testing Health Check ===")
    res = client.get('/api/health')
    print("Health Status:", res.status_code, res.get_json())
    assert res.status_code == 200

    print("\n=== Testing Register (new user) ===")
    import time
    reg_email = f"teacher_{int(time.time())}@attendx.edu"
    res = client.post('/api/auth/register', json={
        'name': 'New Faculty Member',
        'email': reg_email,
        'password': 'password123',
        'role': 'teacher'
    })
    print("Register Status:", res.status_code, res.get_json())
    assert res.status_code == 201
    assert 'token' in res.get_json()

    print("\n=== Testing Login (teacher@attendx.edu) ===")
    res = client.post('/api/auth/login', json={
        'email': 'teacher@attendx.edu',
        'password': 'teacher123',
        'role': 'teacher'
    })
    print("Login Status:", res.status_code)
    login_data = res.get_json()
    assert res.status_code == 200
    token = login_data['token']
    headers = {'Authorization': f'Bearer {token}'}
    print("Token received:", token[:25] + "...")

    print("\n=== Testing Get Current User (/api/auth/me) ===")
    res = client.get('/api/auth/me', headers=headers)
    print("Auth Me Status:", res.status_code, res.get_json())
    assert res.status_code == 200

    print("\n=== Testing Students List (/api/students) ===")
    res = client.get('/api/students', headers=headers)
    students_data = res.get_json()
    print("Students count in DB:", students_data.get('count'))
    assert res.status_code == 200
    assert students_data.get('count', 0) >= 8

    print("\n=== Testing Add Student (POST /api/students) ===")
    test_id = 'STD-999'
    # Delete if exists from previous run
    client.delete(f'/api/students/{test_id}', headers=headers)
    res = client.post('/api/students', headers=headers, json={
        'id': test_id,
        'name': 'Test Student 999',
        'class': 'Class 10',
        'section': 'A'
    })
    print("Add Student Status:", res.status_code, res.get_json())
    assert res.status_code == 201

    print("\n=== Testing Duplicate Student ID Prevention ===")
    res = client.post('/api/students', headers=headers, json={
        'id': test_id,
        'name': 'Duplicate Student',
        'class': 'Class 10',
        'section': 'A'
    })
    print("Duplicate Status:", res.status_code, res.get_json())
    assert res.status_code == 409

    print("\n=== Testing Update Student (PUT /api/students/STD-999) ===")
    res = client.put(f'/api/students/{test_id}', headers=headers, json={
        'id': test_id,
        'name': 'Test Student 999 Updated',
        'class': 'Class 10',
        'section': 'A'
    })
    print("Update Student Status:", res.status_code, res.get_json())
    assert res.status_code == 200

    print("\n=== Testing Attendance Marking (POST /api/attendance) ===")
    res = client.post('/api/attendance', headers=headers, json={
        'date': '2026-10-11',
        'classSection': 'Class 10-A',
        'records': {
            'STD-101': 'present',
            'STD-102': 'present',
            'STD-103': 'present',
            'STD-104': 'absent',
            test_id: 'present'
        }
    })
    print("Save Attendance Status:", res.status_code, res.get_json())
    assert res.status_code == 200

    print("\n=== Testing Attendance Report (GET /api/reports) ===")
    res = client.get('/api/reports?dateFilterMode=ALL&class=Class 10&section=A', headers=headers)
    report_data = res.get_json()
    print("Report Summary:", report_data.get('summary'))
    assert res.status_code == 200
    assert report_data['success'] is True

    print("\n=== Testing Delete Student (DELETE /api/students/STD-999) ===")
    res = client.delete(f'/api/students/{test_id}', headers=headers)
    print("Delete Status:", res.status_code, res.get_json())
    assert res.status_code == 200

    print("\n=== ALL BACKEND API TESTS PASSED! ===")

if __name__ == '__main__':
    test_backend_api()
