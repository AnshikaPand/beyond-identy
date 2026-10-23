"""
Test suite for Video Interviews & LGBTQ+ Community Voices feature.
Tests retrieval, category filtering, search, posting new video interviews,
and embed URL parsing.
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database import Base, engine
from app.models import VideoInterview

client = TestClient(app)


def test_get_video_interviews_list():
    """Verify GET /api/videos returns seed video interviews successfully."""
    response = client.get("/api/videos")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 4

    first = data[0]
    assert "title" in first
    assert "interviewee_name" in first
    assert "embed_url" in first
    assert "category" in first


def test_filter_video_interviews_by_category():
    """Verify category filtering works."""
    response = client.get("/api/videos?category=Workplace")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    for item in data:
        assert "workplace" in item["category"].lower()


def test_search_video_interviews():
    """Verify search by keyword or interviewee name."""
    response = client.get("/api/videos?search=Trinetra")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert any("Trinetra" in item["interviewee_name"] for item in data)


def test_post_video_interview_success():
    """Verify posting a new video interview creates and embeds it properly."""
    payload = {
        "title": "Empowering Rural Queer Youth in Tamil Nadu",
        "interviewee_name": "Karthik Subramaniam",
        "identity_tag": "Gay & Grassroots Organizer (he/him)",
        "category": "Community Advocacy",
        "video_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "key_quote": "Community is born the moment we stop hiding.",
        "duration": "16 mins",
        "location": "Madurai, Tamil Nadu",
        "description": "Karthik shares his journey establishing village support networks and legal aid for queer youth.",
    }
    response = client.post("/api/videos", json=payload)
    assert response.status_code == 201
    created = response.json()
    assert created["title"] == payload["title"]
    assert created["interviewee_name"] == payload["interviewee_name"]
    assert "embed/dQw4w9WgXcQ" in created["embed_url"]
    assert "img.youtube.com/vi/dQw4w9WgXcQ" in created["thumbnail_url"]

    # Verify it now appears in the list
    get_res = client.get(f"/api/videos/{created['id']}")
    assert get_res.status_code == 200
    assert get_res.json()["title"] == payload["title"]

    # Clean up
    del_res = client.delete(f"/api/videos/{created['id']}")
    assert del_res.status_code == 200


def test_post_video_interview_validation():
    """Verify validation errors when required fields are missing."""
    res_no_title = client.post("/api/videos", json={"title": "", "interviewee_name": "Test", "video_url": "https://youtube.com/watch?v=abc"})
    assert res_no_title.status_code == 400

    res_no_name = client.post("/api/videos", json={"title": "Test Title", "interviewee_name": "", "video_url": "https://youtube.com/watch?v=abc"})
    assert res_no_name.status_code == 400

    res_no_url = client.post("/api/videos", json={"title": "Test Title", "interviewee_name": "Test", "video_url": ""})
    assert res_no_url.status_code == 400


def test_upload_phone_video_file():
    """Verify phone video direct file upload endpoint."""
    import io
    dummy_video_bytes = b"FAKE_MP4_HEADER_AND_VIDEO_BYTES_TEST"
    files = {
        "file": ("mobile_recording_sample.mp4", io.BytesIO(dummy_video_bytes), "video/mp4")
    }
    response = client.post("/api/videos/upload-file", files=files)
    assert response.status_code == 200
    data = response.json()
    assert "video_url" in data
    assert data["video_url"].startswith("/static/uploads/videos/phone_video_")
    assert data["video_url"].endswith(".mp4")
    assert "filename" in data


def test_upload_phone_video_interview_multipart():
    """Verify posting a complete phone video interview with video file and form data."""
    import io
    from pathlib import Path

    dummy_video_bytes = b"PHONE_CAMERA_RECORDING_BYTES"
    files = {
        "file": ("phone_interview_chennai.mov", io.BytesIO(dummy_video_bytes), "video/quicktime")
    }
    data = {
        "title": "Living Proud in Chennai: A Transgender IT Professional",
        "interviewee_name": "Revathi Natarajan",
        "identity_tag": "Transgender Woman & Tech Engineer (she/her)",
        "category": "Workplace Equality",
        "key_quote": "My skills speak louder than social prejudices.",
        "location": "Chennai, Tamil Nadu",
        "duration": "12 mins",
        "description": "Revathi shares her experience transitioning in a software corporation in Chennai.",
    }

    response = client.post("/api/videos/upload", data=data, files=files)
    assert response.status_code == 201
    created = response.json()

    assert created["title"] == data["title"]
    assert created["interviewee_name"] == data["interviewee_name"]
    assert created["video_url"].startswith("/static/uploads/videos/phone_video_")
    assert created["video_url"].endswith(".mov")
    assert created["embed_url"] == created["video_url"]

    # Clean up DB record
    del_res = client.delete(f"/api/videos/{created['id']}")
    assert del_res.status_code == 200

    # Clean up created file if exists
    filename = Path(created["video_url"]).name
    target_file = Path(__file__).parent.parent / "app" / "static" / "uploads" / "videos" / filename
    if target_file.exists():
        try:
            target_file.unlink()
        except Exception:
            pass


def test_upload_phone_video_validation():
    """Verify error handling on multipart upload when required fields or file are missing."""
    import io
    # Missing title
    files = {"file": ("test.mp4", io.BytesIO(b"data"), "video/mp4")}
    res = client.post("/api/videos/upload", data={"title": "", "interviewee_name": "Test"}, files=files)
    assert res.status_code in (400, 422)

    # Missing interviewee name
    files2 = {"file": ("test.mp4", io.BytesIO(b"data"), "video/mp4")}
    res2 = client.post("/api/videos/upload", data={"title": "Test Title", "interviewee_name": ""}, files=files2)
    assert res2.status_code in (400, 422)

    # Missing file
    res3 = client.post("/api/videos/upload", data={"title": "Test Title", "interviewee_name": "Test"})
    assert res3.status_code in (400, 422)

