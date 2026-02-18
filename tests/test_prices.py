def test_prices_symbol(client):
    r = client.get("/prices/BTC")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert data[0]["symbol"] == "BTC"
    assert "price" in data[0]
    assert "date" in data[0]

def test_prices_symbol_range(client):
    r = client.get("/prices/BTC?start=2025-01-02&end=2025-01-05")
    assert r.status_code == 200
    data = r.json()
    assert len(data) >= 1
