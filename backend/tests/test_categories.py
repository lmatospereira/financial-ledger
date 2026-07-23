def make_category(client, auth_headers, name="Salary", type_="income", color="#00FF00"):
    return client.post(
        "/api/categories",
        json={"name": name, "type": type_, "color": color},
        headers=auth_headers,
    )


def test_create_category(client, auth_headers):
    response = make_category(client, auth_headers)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Salary"
    assert body["type"] == "income"
    assert body["color"] == "#00FF00"
    assert "id" in body


def test_create_category_invalid_color(client, auth_headers):
    response = client.post(
        "/api/categories",
        json={"name": "Bad", "type": "income", "color": "not-a-color"},
        headers=auth_headers,
    )
    assert response.status_code == 422
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["detail"]


def test_list_categories(client, auth_headers):
    make_category(client, auth_headers, name="Salary")
    make_category(client, auth_headers, name="Groceries", type_="expense", color="#FF0000")
    response = client.get("/api/categories", headers=auth_headers)
    assert response.status_code == 200
    names = {c["name"] for c in response.json()}
    assert names == {"Salary", "Groceries"}


def test_update_category(client, auth_headers):
    created = make_category(client, auth_headers).json()
    response = client.put(
        f"/api/categories/{created['id']}",
        json={"name": "Bonus", "type": "income", "color": "#0000FF"},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Bonus"
    assert body["color"] == "#0000FF"


def test_update_category_not_found(client, auth_headers):
    response = client.put(
        "/api/categories/999",
        json={"name": "Bonus", "type": "income", "color": "#0000FF"},
        headers=auth_headers,
    )
    assert response.status_code == 404


def test_delete_category(client, auth_headers):
    created = make_category(client, auth_headers).json()
    response = client.delete(f"/api/categories/{created['id']}", headers=auth_headers)
    assert response.status_code == 204

    response = client.get("/api/categories", headers=auth_headers)
    assert response.json() == []


def test_delete_category_not_found(client, auth_headers):
    response = client.delete("/api/categories/999", headers=auth_headers)
    assert response.status_code == 404


def test_categories_require_auth(client):
    response = client.get("/api/categories")
    assert response.status_code == 401
