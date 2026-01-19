def auth_headers(client, email="card@test.com"):
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


def setup_user_deck(client, email="card@test.com"):
    headers = auth_headers(client, email)

    deck = client.post(
        "/decks",
        json={"name": "Card Deck"},
        headers=headers
    ).json()

    return headers, deck["id"]


def test_create_and_list_cards(client):
    headers, deck_id = setup_user_deck(client)

    create = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "Hello", "back": "World"},
        headers=headers
    )
    assert create.status_code == 201

    res = client.get(
        f"/decks/{deck_id}/cards",
        headers=headers
    )
    assert res.status_code == 200
    assert len(res.json()) == 1
    assert res.json()[0]["front"] == "Hello"


def test_card_ownership(client):
    headers1, deck1 = setup_user_deck(client, "a@test.com")
    headers2, _ = setup_user_deck(client, "b@test.com")

    card = client.post(
        f"/decks/{deck1}/cards",
        json={"front": "A", "back": "B"},
        headers=headers1
    ).json()

    res = client.delete(
        f"/cards/{card['id']}",
        headers=headers2
    )
    assert res.status_code == 404