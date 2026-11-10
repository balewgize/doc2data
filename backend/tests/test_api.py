from fastapi.testclient import TestClient

from app.main import app


def test_verticals_and_health():
    with TestClient(app) as client:
        response = client.get("/api/paperlane/verticals")
        assert response.status_code == 200
        verticals = response.json()
        assert {v["id"] for v in verticals} == {"ecommerce", "finance", "logistics", "healthcare"}

        health = client.get("/api/paperlane/health")
        assert health.status_code == 200
        assert health.json()["provider"] == "mock"


def test_sample_extraction_and_export():
    with TestClient(app) as client:
        response = client.post("/api/paperlane/extract/sample?vertical=ecommerce")
        assert response.status_code == 200
        run = response.json()
        assert run["vertical"] == "ecommerce"
        assert len(run["records"]) == 3
        assert run["status"] == "review"
        assert run["columns"]

        export = client.get(f"/api/paperlane/runs/{run['id']}/export.csv")
        assert export.status_code == 200
        assert "Handle" in export.text
        assert "P-1001" in export.text

        runs = client.get("/api/paperlane/runs")
        assert runs.status_code == 200
        assert any(item["id"] == run["id"] for item in runs.json())


def test_unknown_vertical_is_rejected():
    with TestClient(app) as client:
        response = client.post("/api/paperlane/extract/sample?vertical=nope")
        assert response.status_code == 400


def test_real_samples_are_bundled_but_need_a_real_provider():
    with TestClient(app) as client:
        verticals = {v["id"]: v for v in client.get("/api/paperlane/verticals").json()}
        assert all(v["real_sample"] is True for v in verticals.values())

        # Mock cannot parse the public real-world docs, so the API explains why.
        response = client.post("/api/paperlane/extract/sample?vertical=finance&real=true")
        assert response.status_code == 400
        assert "LLM_PROVIDER=openai" in response.json()["detail"]
