import pytest
from fastapi.testclient import TestClient

from helperinlaw.api.main import app, set_service
from helperinlaw.service import Service


@pytest.fixture()
def client(service: Service) -> TestClient:
    set_service(service)
    return TestClient(app)


def test_ask(client: TestClient) -> None:
    r = client.post(
        "/ask",
        json={
            "question": "grounds for refusing bail under Section 439 CrPC",
            "style": {"depth": "quick"},
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["citations"] and body["verification"]["verified"] >= 1
    assert body["disclaimer"] == "Research aid, not legal advice."


def test_validation_and_404(client: TestClient) -> None:
    assert client.post("/ask", json={"question": ""}).status_code == 422
    assert client.post("/search", json={"query": "bail", "limit": 99}).status_code == 422
    assert client.get("/cases/nope").status_code == 404
    assert client.get("/cases/fs_2015_mehta/paragraphs/99").status_code == 404
    assert client.put("/profile", json={"verification": False}).status_code == 422


def test_read_routes(client: TestClient) -> None:
    assert client.get("/cases/fs_2015_mehta").json()["citation"] == "(2015) 3 FSR 101"
    assert client.get("/cases/fs_2015_mehta/paragraphs/7").json()[0]["n"] == 7
    assert client.get("/cases/fs_2016_verma/citing").json()[0]["treatment"] == "overruled"
    assert client.get("/statutes/BNS/103").json()["cases"]
    assert (
        client.post("/search", json={"query": "dowry death"}).json()[0]["case_id"]
        == "fs_2018_desai"
    )
    assert (
        client.post(
            "/cases/fs_2021_shaikh/chat", json={"question": "Is anticipatory bail limited in time?"}
        ).status_code
        == 200
    )


def test_profile_and_feedback(client: TestClient) -> None:
    assert client.put("/profile?profile_id=api", json={"tone": "plain"}).json()["tone"] == "plain"
    assert client.get("/profile?profile_id=api").json()["version"] == 2
    assert client.post("/feedback", json={"answer_id": 1, "rating": 1}).json()["ok"]
    assert client.post("/feedback", json={"answer_id": 1, "rating": 5}).status_code == 422
    assert client.delete("/profile?profile_id=api").json() == {"deleted": True}
    assert client.get("/health").json()["cases"] == 8


def test_links_resolve_to_readable_pages(client: TestClient) -> None:
    body = client.post(
        "/ask", json={"question": "grounds for refusing bail under Section 439 CrPC"}
    ).json()
    c = body["citations"][0]
    assert c["url"].endswith(f"/cases/{c['case_id']}/view#para-{c['para']}") and c["statutes"]
    page = client.get(f"/cases/{c['case_id']}/view")
    assert page.status_code == 200 and f"id='para-{c['para']}'" in page.text
    assert "/statutes/CrPC/439/view" in page.text  # statute mentions are linked
    law = body["laws"][0]
    assert law["official_url"].startswith("https://") and law["url"].endswith("/view")
    st = client.get("/statutes/CrPC/439/view")
    assert st.status_code == 200 and "Arjun Mehta" in st.text and "BNSS 483" in st.text
    assert client.get("/statutes/BNS/103/view").text.count("class='card'") == 2
    assert len(client.get("/cases").json()) == 8
