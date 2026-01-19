def test_signup_and_login(client):
    signup = client.post(
        "/signup",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert signup.status_code == 201

    login = client.post(
        "/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )
    assert login.status_code == 200

    data = login.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_me_with_token(client):
    client.post("/signup", json={
        "email": "me@test.com",
        "password": "password123"
    })

    login = client.post("/login", json={
        "email": "me@test.com",
        "password": "password123"
    })

    token = login.json()["access_token"]

    res = client.get(
        "/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert res.status_code == 200
    data = res.json()
    assert "user_id" in data
    assert isinstance(data["user_id"], int)