from decimal import Decimal

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
        assert health.json()["model"] == "mock"


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


def test_edit_record_persists_updates_warnings_and_export():
    with TestClient(app) as client:
        run = client.post("/api/doc2data/extract/sample?vertical=ecommerce").json()
        assert run["records"][2]["sku"] == "P-1003"

        response = client.patch(
            f"/api/doc2data/runs/{run['id']}/records/2",
            json={"field": "price", "value": "39.00"},
        )
        assert response.status_code == 200
        updated = response.json()
        assert Decimal(str(updated["records"][2]["price"])) == Decimal("39.00")
        assert not any(
            warning["code"] == "missing_required"
            and warning["record_key"] == "P-1003"
            for warning in updated["warnings"]
        )

        reloaded = client.get(f"/api/doc2data/runs/{run['id']}").json()
        assert Decimal(str(reloaded["records"][2]["price"])) == Decimal("39.00")

        export = client.get(f"/api/doc2data/runs/{run['id']}/export.csv")
        assert export.status_code == 200
        assert "39.00" in export.text


def test_edit_revalidates_and_can_make_run_ready():
    with TestClient(app) as client:
        run = client.post("/api/doc2data/extract/sample?vertical=finance").json()
        assert run["status"] == "review"
        assert any(warning["code"] == "total_mismatch" for warning in run["warnings"])

        response = client.patch(
            f"/api/doc2data/runs/{run['id']}/records/1",
            json={"field": "total", "value": "20700.00"},
        )
        assert response.status_code == 200
        updated = response.json()
        assert updated["status"] == "ok"
        assert updated["warnings"] == []

        # Re-saving must not append a second copy of the validation warnings.
        again = client.patch(
            f"/api/doc2data/runs/{run['id']}/records/1",
            json={"field": "total", "value": "20700.00"},
        )
        assert again.status_code == 200
        assert again.json()["warnings"] == []


def test_edit_rejects_invalid_input():
    with TestClient(app) as client:
        run = client.post("/api/doc2data/extract/sample?vertical=ecommerce").json()
        base = f"/api/doc2data/runs/{run['id']}/records/0"

        assert client.patch(base, json={"field": "nope", "value": "x"}).status_code == 400
        assert client.patch(
            "/api/doc2data/runs/missing/records/0",
            json={"field": "price", "value": "1"},
        ).status_code == 404
        assert client.patch(
            f"/api/doc2data/runs/{run['id']}/records/99",
            json={"field": "price", "value": "1"},
        ).status_code == 404
        assert client.patch(base, json={"field": "price", "value": "abc"}).status_code == 422
        assert client.patch(base, json={"field": "currency", "value": "US"}).status_code == 422

        finance = client.post("/api/doc2data/extract/sample?vertical=finance").json()
        assert (
            client.patch(
                f"/api/doc2data/runs/{finance['id']}/records/0",
                json={"field": "invoice_date", "value": "not-a-date"},
            ).status_code
            == 422
        )
