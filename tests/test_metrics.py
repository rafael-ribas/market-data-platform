def test_metrics_latest(client):
    r = client.get("/metrics/latest")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert "daily_return" in data[0]


def test_metrics_by_symbol_window(client):
    r = client.get("/metrics/BTC?window=7")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) > 0
    assert all(x["symbol"] == "BTC" for x in data)
