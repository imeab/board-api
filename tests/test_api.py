"""실제 PostgreSQL(docker compose의 db)에 연결해서 API 전체 흐름을 확인하는 테스트"""
import uuid

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:  # with: lifespan 실행 (테이블 생성)
        yield c


def signup_and_login(client, name="테스터"):
    email = f"{uuid.uuid4().hex[:8]}@test.com"
    password = "password1234"
    r = client.post("/api/v1/auth/signup", json={"email": email, "password": password, "name": name})
    assert r.status_code == 201, r.text
    r = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_health(client):
    assert client.get("/health").json() == {"status": "ok"}


def test_signup_validation_and_duplicate(client):
    r = client.post("/api/v1/auth/signup", json={"email": "not-email", "password": "123", "name": "a"})
    assert r.status_code == 422
    body = r.json()
    assert body["success"] is False and body["error"]["code"] == "VALIDATION_ERROR"
    assert {d["field"] for d in body["error"]["details"]} == {"email", "password", "name"}

    email = f"{uuid.uuid4().hex[:8]}@test.com"
    payload = {"email": email, "password": "password1234", "name": "중복"}
    assert client.post("/api/v1/auth/signup", json=payload).status_code == 201
    r = client.post("/api/v1/auth/signup", json=payload)
    assert r.status_code == 409 and r.json()["error"]["code"] == "CONFLICT"


def test_login_fail_and_auth_required(client):
    r = client.post("/api/v1/auth/login", json={"email": "nobody@test.com", "password": "wrongpass"})
    assert r.status_code == 401

    assert client.post("/api/v1/posts", json={"title": "t", "content": "c"}).status_code == 401
    r = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid.token"})
    assert r.status_code == 401 and r.json()["error"]["message"] == "유효하지 않은 토큰입니다."


def test_post_crud_and_owner_check(client):
    owner = signup_and_login(client, "작성자")
    other = signup_and_login(client, "다른사람")

    # 작성
    r = client.post("/api/v1/posts", json={"title": "첫 글", "content": "내용"}, headers=owner)
    assert r.status_code == 201
    post_id = r.json()["id"]
    assert r.json()["author"]["name"] == "작성자"

    # 상세 조회 (조회수 증가)
    assert client.get(f"/api/v1/posts/{post_id}").json()["view_count"] == 1
    assert client.get(f"/api/v1/posts/{post_id}").json()["view_count"] == 2

    # 목록 + 검색
    r = client.get("/api/v1/posts", params={"keyword": "첫 글", "size": 5})
    assert r.status_code == 200 and any(p["id"] == post_id for p in r.json()["items"])

    # 다른 사람은 수정/삭제 불가 (403)
    r = client.patch(f"/api/v1/posts/{post_id}", json={"title": "해킹"}, headers=other)
    assert r.status_code == 403 and r.json()["error"]["code"] == "FORBIDDEN"
    assert client.delete(f"/api/v1/posts/{post_id}", headers=other).status_code == 403

    # 작성자는 수정 가능 (보낸 필드만 변경)
    r = client.patch(f"/api/v1/posts/{post_id}", json={"title": "수정한 글"}, headers=owner)
    assert r.status_code == 200
    assert r.json()["title"] == "수정한 글" and r.json()["content"] == "내용"

    # 댓글
    r = client.post(f"/api/v1/posts/{post_id}/comments", json={"content": "댓글"}, headers=other)
    assert r.status_code == 201
    comment_id = r.json()["id"]
    assert client.delete(f"/api/v1/comments/{comment_id}", headers=owner).status_code == 403
    assert len(client.get(f"/api/v1/posts/{post_id}/comments").json()) == 1

    # 삭제 → 댓글도 같이 삭제, 이후 404
    assert client.delete(f"/api/v1/posts/{post_id}", headers=owner).status_code == 204
    assert client.get(f"/api/v1/posts/{post_id}").status_code == 404
    assert client.get(f"/api/v1/posts/{post_id}/comments").status_code == 404


def test_blank_title_rejected(client):
    headers = signup_and_login(client)
    r = client.post("/api/v1/posts", json={"title": "   ", "content": "c"}, headers=headers)
    assert r.status_code == 422
