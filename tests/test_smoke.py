def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200


def test_me_requires_auth(client):
    res = client.get("/me")
    assert res.status_code == 401