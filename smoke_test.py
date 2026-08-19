from fastapi.testclient import TestClient
from app import app

client = TestClient(app)
assert client.get('/api/health').status_code == 200
meta = client.get('/api/metadata')
assert meta.status_code == 200
assert len(meta.json()['features']) == 8
payload = {
    'cement': 350, 'blast_furnace_slag': 100, 'fly_ash': 0, 'water': 180,
    'superplasticizer': 8, 'coarse_aggregate': 1000, 'fine_aggregate': 750, 'age': 28,
}
response = client.post('/api/predict', json=payload)
assert response.status_code == 200, response.text
result = response.json()
assert result['strength_mpa'] >= 0
assert result['band'] in {'Low', 'Moderate', 'High', 'Very high'}
assert client.get('/').status_code == 200
print('SMOKE_TEST_OK', result['strength_mpa'], result['band'])
