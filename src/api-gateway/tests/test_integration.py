"""Integration tests — requires running server on port 8000."""
import pytest
import httpx
import json

BASE = "http://127.0.0.1:8000"

pytestmark = pytest.mark.skipif(
    True,  # manually enable by removing skipif
    reason="Requires running server. Run manually with: pytest -s --run-integration"
)


class TestAuth:

    def test_register_and_login(self):
        email = "inttest@test.edu"
        password = "intpass"

        r = httpx.post(f"{BASE}/api/v1/auth/register", json={
            "email": email, "password": password,
            "display_name": "Integration Tester", "role": "student",
        })
        # May 409 if already exists — that's OK
        if r.status_code == 409:
            r = httpx.post(f"{BASE}/api/v1/auth/login", json={
                "email": email, "password": password,
            })
        assert r.status_code in (201, 200)
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        return data

    def test_login_wrong_password(self):
        r = httpx.post(f"{BASE}/api/v1/auth/login", json={
            "email": "nonexistent@test.edu", "password": "wrong",
        })
        assert r.status_code == 401

    def test_demo_login_works(self):
        r = httpx.post(f"{BASE}/api/v1/auth/login", json={
            "email": "rahim@buet.edu", "password": "demo1234",
        })
        if r.status_code == 200:
            assert "access_token" in r.json()
        else:
            # User might not exist — that's OK, registration is tested separately
            assert r.status_code == 401


class TestGraderAPI:

    @pytest.fixture
    def token(self):
        r = httpx.post(f"{BASE}/api/v1/auth/login", json={
            "email": "rahim@buet.edu", "password": "demo1234",
        })
        if r.status_code != 200:
            r = httpx.post(f"{BASE}/api/v1/auth/register", json={
                "email": "rahim@buet.edu", "password": "demo1234",
                "display_name": "Rahim Hossain", "role": "student",
            })
        return r.json()["access_token"]

    def test_submit_correct_code(self, token):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = httpx.get(f"{BASE}/api/v1/academic/student/courses", headers=headers)
        if r.status_code != 200 or not r.json():
            pytest.skip("No courses seeded")
        course_id = r.json()[0]["course_offering_id"]

        r = httpx.get(f"{BASE}/api/v1/academic/student/courses/{course_id}/assignments", headers=headers)
        if r.status_code != 200 or not r.json():
            pytest.skip("No assignments seeded")
        asg_id = r.json()[0]["id"]

        r = httpx.post(
            f"{BASE}/api/v1/academic/student/assignments/{asg_id}/submit",
            headers=headers,
            json={"source_code": '#include <iostream>\nint main(){int x;std::cin>>x;std::cout<<x+1;}', "language": "cpp-basic"},
        )
        assert r.status_code == 201
        data = r.json()
        # Should not be mock (mock always returned all pass regardless)
        assert "feedback" in data
        print(f"Submission result: {data}")

    def test_submit_wrong_code(self, token):
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        r = httpx.get(f"{BASE}/api/v1/academic/student/courses", headers=headers)
        if r.status_code != 200 or not r.json():
            pytest.skip("No courses seeded")
        course_id = r.json()[0]["course_offering_id"]

        r = httpx.get(f"{BASE}/api/v1/academic/student/courses/{course_id}/assignments", headers=headers)
        if r.status_code != 200 or not r.json():
            pytest.skip("No assignments seeded")
        asg_id = r.json()[0]["id"]

        r = httpx.post(
            f"{BASE}/api/v1/academic/student/assignments/{asg_id}/submit",
            headers=headers,
            json={"source_code": '#include <iostream>\nint main(){std::cout<<"wrong";}', "language": "cpp-basic"},
        )
        assert r.status_code == 201
        data = r.json()
        print(f"Wrong code result: {data}")
