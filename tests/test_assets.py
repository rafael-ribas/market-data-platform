def test_assets_list(client):
    r = client.get("/assets")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert any(x.get("symbol") == "BTC" for x in data)

def test_assets_get_symbol(client):
    r = client.get("/assets/BTC")
    assert r.status_code == 200
    data = r.json()
    assert data["symbol"] == "BTC"
