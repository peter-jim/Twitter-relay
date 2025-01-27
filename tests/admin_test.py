import requests
from test_utils import make_api_request

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000"

# API keys and secrets for testing
ADMIN_API_KEY = "admin_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c"
ADMIN_API_SECRET = "admin_secret_8a4c7b3e2f1d9g6h5j8k7l4m1n3p2q9r"

NORMAL_API_KEY = "normal_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c"
NORMAL_API_SECRET = "normal_secret_9b5d8c4a3e2f1g7h6j9k8l5m2n4p3q0r"

def test_list_api_keys_with_admin():
    """Test GET /admin/api-keys with admin key"""
    url = f"{BASE_URL}/admin/api-keys"
    response = make_api_request('GET', url, ADMIN_API_KEY, ADMIN_API_SECRET)
    print(f"GET {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_list_api_keys_with_normal_key():
    """Test GET /admin/api-keys with normal key (should fail)"""
    url = f"{BASE_URL}/admin/api-keys"
    response = make_api_request('GET', url, NORMAL_API_KEY, NORMAL_API_SECRET)
    print(f"GET {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

def test_create_api_key_success():
    """Test POST /admin/api-keys with valid data"""
    url = f"{BASE_URL}/admin/api-keys"
    payload = {
        "name": "test_key_1",
        "days_valid": 30
    }
    response = make_api_request('POST', url, ADMIN_API_KEY, ADMIN_API_SECRET, payload)
    print(f"POST {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200
    return response.json()["api_key"]["id"]

def test_create_api_key_errors():
    """Test POST /admin/api-keys with invalid data"""
    url = f"{BASE_URL}/admin/api-keys"
    
    # Test missing name
    payload1 = {"days_valid": 30}
    response = make_api_request('POST', url, ADMIN_API_KEY, ADMIN_API_SECRET, payload1)
    print(f"POST {url} (missing name) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 400

    # Test using normal API key
    payload2 = {"name": "test_key_2", "days_valid": 30}
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload2)
    print(f"POST {url} (normal key) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

def test_update_api_key():
    """Test PUT /admin/api-keys/<key_id>"""
    key_id = test_create_api_key_success()
    url = f"{BASE_URL}/admin/api-keys/{key_id}"
    
    # Test disabling API key
    payload = {"is_active": False}
    response = make_api_request('PUT', url, ADMIN_API_KEY, ADMIN_API_SECRET, payload)
    print(f"PUT {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

    # Test using normal API key (should fail)
    response = make_api_request('PUT', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload)
    print(f"PUT {url} (normal key) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

def test_delete_api_key():
    """Test DELETE /admin/api-keys/<key_id>"""
    key_id = test_create_api_key_success()
    url = f"{BASE_URL}/admin/api-keys/{key_id}"
    
    # Test using normal API key (should fail)
    response = make_api_request('DELETE', url, NORMAL_API_KEY, NORMAL_API_SECRET)
    print(f"DELETE {url} (normal key) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

    # Test using admin API key
    response = make_api_request('DELETE', url, ADMIN_API_KEY, ADMIN_API_SECRET)
    print(f"DELETE {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_without_api_key():
    """Test endpoints without any API key"""
    endpoints = [
        ("GET", "/admin/api-keys"),
        ("POST", "/admin/api-keys"),
        ("PUT", "/admin/api-keys/1"),
        ("DELETE", "/admin/api-keys/1")
    ]
    
    for method, path in endpoints:
        url = f"{BASE_URL}{path}"
        response = requests.request(method, url)  # no api key
        print(f"{method} {url} (no key) -> {response.status_code}")
        print("Response:", response.json())
        assert response.status_code == 401

if __name__ == "__main__":
    # Test list API keys
    test_list_api_keys_with_admin()
    test_list_api_keys_with_normal_key()
    
    # Test create API key
    test_create_api_key_success()
    test_create_api_key_errors()
    
    # Test update API key
    test_update_api_key()
    
    # Test delete API key
    test_delete_api_key()
    
    # Test without API key
    test_without_api_key()