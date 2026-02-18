def test_correlation_ok(client):
    r = client.get("/correlation?asset1=BTC&asset2=ETH&window=7")
    assert r.status_code == 200
    data = r.json()
    assert data["asset1"] == "BTC"
    assert data["asset2"] == "ETH"
    assert "correlation" in data  # pode ser float ou null dependendo do cálculo

def test_correlation_same_assets_422(client):
    r = client.get("/correlation?asset1=BTC&asset2=BTC&window=7")
    assert r.status_code == 422
