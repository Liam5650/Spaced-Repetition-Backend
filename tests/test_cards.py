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

def test_list_new_cards_only_returns_unlearned(client):
    headers, deck_id = setup_user_deck(client)

    c1 = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "N1", "back": "B1"},
        headers=headers
    ).json()

    c2 = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "N2", "back": "B2"},
        headers=headers
    ).json()

    res = client.get(
        f"/decks/{deck_id}/cards/new",
        headers=headers
    )
    assert res.status_code == 200
    ids = [c["id"] for c in res.json()]
    assert c1["id"] in ids
    assert c2["id"] in ids


def test_learn_card_removes_it_from_new_and_puts_it_in_due(client):
    headers, deck_id = setup_user_deck(client)

    card = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "LearnMe", "back": "Now"},
        headers=headers
    ).json()

    before_new = client.get(
        f"/decks/{deck_id}/cards/new",
        headers=headers
    )
    assert before_new.status_code == 200
    assert card["id"] in [c["id"] for c in before_new.json()]

    learn = client.post(
        f"/cards/{card['id']}/learn",
        headers=headers
    )
    assert learn.status_code == 201

    after_new = client.get(
        f"/decks/{deck_id}/cards/new",
        headers=headers
    )
    assert after_new.status_code == 200
    assert card["id"] not in [c["id"] for c in after_new.json()]

    due = client.get(
        f"/decks/{deck_id}/cards/due",
        headers=headers
    )
    assert due.status_code == 200
    assert card["id"] in [c["id"] for c in due.json()]


def test_learn_card_twice_returns_conflict(client):
    headers, deck_id = setup_user_deck(client)

    card = client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "Dup", "back": "Test"},
        headers=headers
    ).json()

    first = client.post(
        f"/cards/{card['id']}/learn",
        headers=headers
    )
    assert first.status_code == 201

    second = client.post(
        f"/cards/{card['id']}/learn",
        headers=headers
    )
    assert second.status_code == 409
    assert second.json()["detail"] == "Card is already learned"


def test_new_cards_respects_limit(client):
    headers, deck_id = setup_user_deck(client)

    for i in range(15):
        client.post(
            f"/decks/{deck_id}/cards",
            json={"front": f"F{i}", "back": f"B{i}"},
            headers=headers
        )

    res = client.get(
        f"/decks/{deck_id}/cards/new?limit=10",
        headers=headers
    )
    assert res.status_code == 200
    assert len(res.json()) == 10


def test_new_cards_requires_ownership(client):
    headers1, deck1 = setup_user_deck(client, "owner@test.com")
    headers2, _ = setup_user_deck(client, "other@test.com")

    client.post(
        f"/decks/{deck1}/cards",
        json={"front": "X", "back": "Y"},
        headers=headers1
    )

    res = client.get(
        f"/decks/{deck1}/cards/new",
        headers=headers2
    )
    assert res.status_code == 404


def test_due_cards_empty_when_nothing_learned(client):
    headers, deck_id = setup_user_deck(client)

    client.post(
        f"/decks/{deck_id}/cards",
        json={"front": "NotLearned", "back": "Yet"},
        headers=headers
    )

    due = client.get(
        f"/decks/{deck_id}/cards/due",
        headers=headers
    )
    assert due.status_code == 200
    assert due.json() == []