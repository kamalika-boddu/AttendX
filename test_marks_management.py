import json
from app import app
from db import execute_query, execute_non_query

client = app.test_client()

print("=== 1. TEACHER LOGIN & SUBJECTS RETRIEVAL ===")
t_res = client.post('/api/auth/login', json={'email': 'teacher@attendx.edu', 'password': 'teacher123', 'role': 'teacher'})
assert t_res.status_code == 200, t_res.get_json()
t_token = t_res.get_json()['token']
t_headers = {'Authorization': f'Bearer {t_token}'}

subj_res = client.get('/api/subjects', headers=t_headers)
assert subj_res.status_code == 200, subj_res.get_json()
subjects = subj_res.get_json()['subjects']
assert len(subjects) >= 5
print(f"PASS: Retrieved {len(subjects)} subjects successfully.")

print("\n=== 2. CREATE NEW ASSESSMENT IN DRAFT STATUS ===")
test_asm_payload = {
    'name': 'Term 1 Mid Assessment Test',
    'type': 'Mid Exam',
    'subject': 'Mathematics',
    'class': 'Class 10',
    'section': 'A',
    'assessmentDate': '2026-10-15',
    'maxMarks': 100.0,
    'passingMarks': 35.0
}
create_res = client.post('/api/assessments', headers=t_headers, json=test_asm_payload)
assert create_res.status_code == 201, create_res.get_json()
asm_data = create_res.get_json()['assessment']
asm_id = asm_data['id']
assert asm_data['status'] == 'draft'
assert asm_data['totalEnrolled'] == 15
print(f"PASS: Assessment created in DRAFT status with ID: {asm_id} (15 students enrolled).")

print("\n=== 3. STUDENT CANNOT SEE DRAFT ASSESSMENT MARKS ===")
s_res = client.post('/api/auth/login', json={'email': 'STD-101', 'password': 'student123', 'role': 'student'})
assert s_res.status_code == 200, s_res.get_json()
s_token = s_res.get_json()['token']
s_headers = {'Authorization': f'Bearer {s_token}'}

s_marks_res = client.get('/api/student/marks', headers=s_headers)
assert s_marks_res.status_code == 200
s_marks_data = s_marks_res.get_json()
# Ensure draft assessment does NOT appear in student results
res_asm_ids = [r['assessmentId'] for r in s_marks_data['results']]
assert asm_id not in res_asm_ids
print("PASS: Draft assessment is completely hidden from Student Portal.")

print("\n=== 4. INVALID MARKS VALIDATION (EXCEEDING MAXIMUM MARKS) ===")
invalid_marks_payload = {
    'marks': {
        'STD-101': 105.0  # Max is 100.0!
    }
}
inv_res = client.post(f'/api/assessments/{asm_id}/marks', headers=t_headers, json=invalid_marks_payload)
assert inv_res.status_code == 400, inv_res.get_json()
assert 'exceed maximum marks' in inv_res.get_json()['message']
print("PASS: Marks above maximum were rejected with 400 Bad Request.")

negative_marks_payload = {
    'marks': {
        'STD-101': -5.0
    }
}
neg_res = client.post(f'/api/assessments/{asm_id}/marks', headers=t_headers, json=negative_marks_payload)
assert neg_res.status_code == 400, neg_res.get_json()
assert 'cannot be negative' in neg_res.get_json()['message']
print("PASS: Negative marks were rejected with 400 Bad Request.")

print("\n=== 5. TEACHER SAVES MARKS AS DRAFT ===")
draft_marks = {
    'STD-101': 88.0,
    'STD-102': 76.5,
    'STD-103': 30.0,  # Below passing marks (35)
    'STD-104': 95.0
}
save_draft_res = client.post(f'/api/assessments/{asm_id}/marks', headers=t_headers, json={'marks': draft_marks})
assert save_draft_res.status_code == 200, save_draft_res.get_json()
assert save_draft_res.get_json()['assessmentStatus'] == 'draft'
print("PASS: Teacher saved marks as draft successfully.")

# Verify student STILL cannot see these draft marks!
s_marks_res2 = client.get('/api/student/marks', headers=s_headers)
res_asm_ids2 = [r['assessmentId'] for r in s_marks_res2.get_json()['results']]
assert asm_id not in res_asm_ids2
print("PASS: Even after entering draft marks, student portal STILL does not reveal un-published marks.")

print("\n=== 6. TEACHER PUBLISHES MARKS ===")
pub_res = client.post(f'/api/assessments/{asm_id}/publish', headers=t_headers)
assert pub_res.status_code == 200, pub_res.get_json()
assert pub_res.get_json()['status'] == 'published'
print("PASS: Assessment published successfully by teacher.")

print("\n=== 7. STUDENT CAN NOW SEE THEIR OWN PUBLISHED MARKS ===")
s_marks_res3 = client.get('/api/student/marks', headers=s_headers)
assert s_marks_res3.status_code == 200
s_results = s_marks_res3.get_json()['results']
target_result = next((r for r in s_results if r['assessmentId'] == asm_id), None)
assert target_result is not None, "Published mark not found for STD-101"
assert target_result['marksObtained'] == 88.0
assert target_result['maxMarks'] == 100.0
assert target_result['percentage'] == 88.0
assert target_result['passed'] is True
assert target_result['grade'] == 'A'
print(f"PASS: Student STD-101 retrieved published marks: {target_result['marksObtained']}/{target_result['maxMarks']} ({target_result['percentage']}%, Grade: {target_result['grade']}).")

print("\n=== 8. STUDENT CANNOT SEE OTHER STUDENTS' RESULTS ===")
# Student cannot pass a student_id parameter to view other students
tamper_res = client.get('/api/student/marks?student_id=STD-103', headers=s_headers)
t_results = tamper_res.get_json()['results']
for r in t_results:
    # Everything returned belongs strictly to STD-101
    if r['assessmentId'] == asm_id:
        assert r['marksObtained'] == 88.0, "Leaked other student's mark!"
print("PASS: Student API strictly scopes results to authenticated user (STD-101), preventing access to STD-103.")

print("\n=== 9. RULE #6: UPDATED MARKS REMAIN HIDDEN UNTIL REPUBLISHED ===")
# Teacher edits STD-101's mark from 88 to 99 in draft mode
edit_draft_res = client.post(f'/api/assessments/{asm_id}/marks', headers=t_headers, json={'marks': {'STD-101': 99.0}})
assert edit_draft_res.status_code == 200
assert edit_draft_res.get_json()['assessmentStatus'] == 'updated'

# Student must STILL see the previously published mark (88.0), NOT 99.0!
s_marks_res4 = client.get('/api/student/marks', headers=s_headers)
target_result4 = next((r for r in s_marks_res4.get_json()['results'] if r['assessmentId'] == asm_id), None)
assert target_result4['marksObtained'] == 88.0, f"Leaked draft modification! Expected 88.0, got {target_result4['marksObtained']}"
print("PASS: Modified draft mark (99.0) remained hidden; student continues to see previously published mark (88.0).")

# Teacher republishes marks
repub_res = client.post(f'/api/assessments/{asm_id}/publish', headers=t_headers)
assert repub_res.status_code == 200

# Now student sees the updated republished mark (99.0)
s_marks_res5 = client.get('/api/student/marks', headers=s_headers)
target_result5 = next((r for r in s_marks_res5.get_json()['results'] if r['assessmentId'] == asm_id), None)
assert target_result5['marksObtained'] == 99.0
assert target_result5['grade'] == 'A+'
print("PASS: After republication, student now sees updated mark (99.0, A+).")

print("\n=== 10. CLASS PERFORMANCE SUMMARY FOR TEACHER ===")
detail_res = client.get(f'/api/assessments/{asm_id}', headers=t_headers)
assert detail_res.status_code == 200
perf = detail_res.get_json()['performanceSummary']
assert perf['assessedCount'] == 4
assert perf['highestMarks'] == 99.0
assert perf['lowestMarks'] == 30.0
assert perf['passCount'] == 3  # 99, 76.5, 95 passed; 30 failed (< 35)
assert perf['failCount'] == 1
assert perf['passPercentage'] == 75.0
print(f"PASS: Class performance summary verified: Assessed={perf['assessedCount']}, High={perf['highestMarks']}, Low={perf['lowestMarks']}, PassRate={perf['passPercentage']}%.")

print("\n=== 11. RBAC SECURITY RESTRICTIONS ===")
# Student forbidden on teacher assessment endpoints
assert client.get('/api/assessments', headers=s_headers).status_code == 403
assert client.post('/api/assessments', headers=s_headers, json={}).status_code == 403
assert client.post(f'/api/assessments/{asm_id}/marks', headers=s_headers, json={}).status_code == 403
assert client.post(f'/api/assessments/{asm_id}/publish', headers=s_headers).status_code == 403
print("PASS: All teacher marks management endpoints return 403 Forbidden for Student role.")

# Clean up test assessment
client.delete(f'/api/assessments/{asm_id}', headers=t_headers)
print("PASS: Test assessment cleaned up cleanly.")

print("\n==========================================")
print("ALL 11 MARKS MANAGEMENT TEST SUITES PASSED!")
print("==========================================")
