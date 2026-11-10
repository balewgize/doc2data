from fastapi.testclient import TestClient

from app.main import app


def test_verticals_and_health():
    with TestClient(app) as client:
        response = client.get("/api/doc2data/verticals")
        assert response.status_code == 200
        verticals = response.json()
        assert {v["id"] for v in verticals} == {"ecommerce", "finance", "logistics", "healthcare"}
        assert all(v["ready"] for v in verticals)

        health = client.get("/api/doc2data/health")
        assert health.status_code == 200
        assert health.json()["provider"] == "mock"


def test_sample_extraction_and_export():
    with TestClient(app) as client:
        response = client.post("/api/doc2data/extract/sample?vertical=ecommerce")
        assert response.status_code == 200
        run = response.json()
        assert run["vertical"] == "ecommerce"
        assert len(run["records"]) == 3
        assert run["status"] == "review"
        assert run["columns"]

        export = client.get(f"/api/doc2data/runs/{run['id']}/export.csv")
        assert export.status_code == 200
        assert "Handle" in export.text
        assert "P-1001" in export.text

        runs = client.get("/api/doc2data/runs")
        assert runs.status_code == 200
        assert any(item["id"] == run["id"] for item in runs.json())


def test_unknown_vertical_is_rejected():
    with TestClient(app) as client:
        response = client.post("/api/doc2data/extract/sample?vertical=nope")
        assert response.status_code == 400


def test_public_samples_run_offline_with_recorded_results():
    with TestClient(app) as client:
        verticals = {v["id"]: v for v in client.get("/api/doc2data/verticals").json()}
        assert all(v["real_sample"] is True for v in verticals.values())

        for vertical in verticals:
            response = client.post(
                f"/api/doc2data/extract/sample?vertical={vertical}&real=true"
            )
            assert response.status_code == 200, response.text
            run = response.json()
            assert run["records"]
            assert run["provider"] == "demo"
            assert run["meta"]["public_sample"] is True
