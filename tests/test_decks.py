def auth_headers(client, email="deck@test.com"):
    client.post("/signup", json={
        "email": email,
        "password": "password123"
    })
    login = client.post("/login", json={
        "email": email,
        "password": "password123"
    })
    token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_and_list_decks(client):
    headers = auth_headers(client)

    create = client.post(
        "/decks",
        json={"name": "My Deck"},
        headers=headers
    )
    assert create.status_code == 201

    res = client.get("/decks", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["name"] == "My Deck"


def test_deck_ownership(client):
    user1 = auth_headers(client, "user1@test.com")
    user2 = auth_headers(client, "user2@test.com")

    deck = client.post(
        "/decks",
        json={"name": "Private Deck"},
        headers=user1
    ).json()

    res = client.get(f"/decks/{deck['id']}", headers=user2)
    assert res.status_code == 404