"""API 스모크 테스트: health / diseases / diagnose / history 전 구간."""


def test_health(client, model_available):
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["version"]
    # 체크포인트는 저장소에 없을 수 있다. 현재 상태를 정직하게 보고하는지만 확인한다
    assert body["model_loaded"] is model_available


def test_diseases_seeded(client):
    res = client.get("/api/v1/diseases")
    assert res.status_code == 200
    diseases = res.json()
    assert len(diseases) >= 9
    categories = {d["category"] for d in diseases}
    assert {"disease", "normal"} <= categories


def test_disease_detail_and_404(client):
    disease_id = client.get("/api/v1/diseases").json()[0]["id"]
    res = client.get(f"/api/v1/diseases/{disease_id}")
    assert res.status_code == 200
    assert res.json()["id"] == disease_id

    assert client.get("/api/v1/diseases/999999").status_code == 404


def test_diagnose_rejects_non_image(client):
    res = client.post(
        "/api/v1/diagnose",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert res.status_code == 400


def test_diagnose_rejects_empty_file(client):
    res = client.post(
        "/api/v1/diagnose",
        files={"file": ("empty.jpg", b"", "image/jpeg")},
    )
    assert res.status_code == 400


def test_diagnose_and_history_flow(client, sample_image):
    res = client.post(
        "/api/v1/diagnose",
        files={"file": ("leaf.jpg", sample_image, "image/jpeg")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["disease_name"]
    assert 0.0 <= body["confidence"] <= 1.0
    assert len(body["top_predictions"]) >= 1
    assert body["category"] in ("disease", "normal")

    history = client.get("/api/v1/history").json()
    assert history["total"] >= 1
    assert any(item["id"] == body["id"] for item in history["items"])

    detail = client.get(f"/api/v1/history/{body['id']}")
    assert detail.status_code == 200
    assert detail.json()["disease_name"] == body["disease_name"]


def test_history_detail_404(client):
    res = client.get("/api/v1/history/00000000-0000-0000-0000-000000000000")
    assert res.status_code == 404


def test_history_pagination_params(client):
    assert client.get("/api/v1/history?page=0").status_code == 422
    assert client.get("/api/v1/history?size=101").status_code == 422
    res = client.get("/api/v1/history?page=1&size=1")
    assert res.status_code == 200
    assert len(res.json()["items"]) <= 1


def test_diagnose_rejects_oversized_image(client, oversized_image):
    res = client.post(
        "/api/v1/diagnose",
        files={"file": ("huge.jpg", oversized_image, "image/jpeg")},
    )
    assert res.status_code == 413
    assert "1MB" in res.json()["detail"]


def test_diagnose_rejects_corrupt_image(client):
    """Content-Type만 이미지인 파일은 추론 전에 400으로 걸러야 한다."""
    res = client.post(
        "/api/v1/diagnose",
        files={"file": ("fake.jpg", b"not really a jpeg" * 100, "image/jpeg")},
    )
    assert res.status_code == 400


def test_refine_records_second_image(client, sample_image, second_image):
    created = client.post(
        "/api/v1/diagnose",
        files={"file": ("leaf.jpg", sample_image, "image/jpeg")},
    ).json()
    assert created["refined_image_url"] is None

    refined = client.post(
        f"/api/v1/diagnose/{created['id']}/refine",
        files={"file": ("underside.jpg", second_image, "image/jpeg")},
    )
    assert refined.status_code == 200
    body = refined.json()

    # 2차 촬영 사진이 기록되고, 1차 사진과 구분된다
    assert body["refined_image_url"]
    assert body["refined_image_url"] != body["image_url"]
    assert body["image_url"] == created["image_url"]

    # 새 레코드가 아니라 기존 진단이 갱신되며, 상세 조회로도 추적된다
    assert body["id"] == created["id"]
    detail = client.get(f"/api/v1/history/{created['id']}").json()
    assert detail["refined_image_url"] == body["refined_image_url"]


def test_refine_rejects_oversized_image(client, sample_image, oversized_image):
    created = client.post(
        "/api/v1/diagnose",
        files={"file": ("leaf.jpg", sample_image, "image/jpeg")},
    ).json()
    res = client.post(
        f"/api/v1/diagnose/{created['id']}/refine",
        files={"file": ("huge.jpg", oversized_image, "image/jpeg")},
    )
    assert res.status_code == 413


def test_refine_unknown_diagnosis_404(client, second_image):
    res = client.post(
        "/api/v1/diagnose/00000000-0000-0000-0000-000000000000/refine",
        files={"file": ("underside.jpg", second_image, "image/jpeg")},
    )
    assert res.status_code == 404


def test_diagnose_works_without_checkpoint(client, sample_image, monkeypatch):
    """체크포인트가 없는 환경(클린 클론·CI)에서도 진단 전 구간이 동작해야 한다."""
    from app.services import ml_service

    monkeypatch.setattr(ml_service, "_load_model", lambda: None)
    monkeypatch.setattr(ml_service, "_load_pair_model", lambda: None)

    res = client.post(
        "/api/v1/diagnose",
        files={"file": ("leaf.jpg", sample_image, "image/jpeg")},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["disease_name"]
    assert body["top_predictions"]
    assert 0.0 <= body["confidence"] <= 1.0
