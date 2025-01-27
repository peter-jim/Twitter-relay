import requests

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000"

# API keys for testing
# This admin key should match the one in init_admin.sql
ADMIN_API_KEY = "admin_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c"

# This normal key should match the one in init_admin.sql
NORMAL_API_KEY = "normal_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c"

def get_headers(api_key):
    """Helper function to create headers with API key"""
    return {"X-API-Key": api_key}

def test_list_api_keys_with_admin():
    """Test GET /admin/api-keys with admin key"""
    url = f"{BASE_URL}/admin/api-keys"
    response = requests.get(url, headers=get_headers(ADMIN_API_KEY))
    print(f"GET {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_list_api_keys_with_normal_key():
    """Test GET /admin/api-keys with normal key (should fail)"""
    url = f"{BASE_URL}/admin/api-keys"
    response = requests.get(url, headers=get_headers(NORMAL_API_KEY))
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
    response = requests.post(url, headers=get_headers(ADMIN_API_KEY), json=payload)
    print(f"POST {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200
    return response.json()["api_key"]["id"]

def test_create_api_key_errors():
    """Test POST /admin/api-keys with invalid data"""
    url = f"{BASE_URL}/admin/api-keys"
    
    # Test missing name
    payload1 = {"days_valid": 30}
    response = requests.post(url, headers=get_headers(ADMIN_API_KEY), json=payload1)
    print(f"POST {url} (missing name) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 400

    # Test using normal API key
    payload2 = {"name": "test_key_2", "days_valid": 30}
    response = requests.post(url, headers=get_headers(NORMAL_API_KEY), json=payload2)
    print(f"POST {url} (normal key) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

def test_update_api_key():
    """Test PUT /admin/api-keys/<key_id>"""
    # Create a new API key first
    key_id = test_create_api_key_success()
    
    url = f"{BASE_URL}/admin/api-keys/{key_id}"
    
    # Test disabling API key
    payload = {"is_active": False}
    response = requests.put(url, headers=get_headers(ADMIN_API_KEY), json=payload)
    print(f"PUT {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

    # Test using normal API key (should fail)
    response = requests.put(url, headers=get_headers(NORMAL_API_KEY), json=payload)
    print(f"PUT {url} (normal key) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

def test_delete_api_key():
    """Test DELETE /admin/api-keys/<key_id>"""
    # Create a new API key first
    key_id = test_create_api_key_success()
    
    url = f"{BASE_URL}/admin/api-keys/{key_id}"
    
    # Test using normal API key (should fail)
    response = requests.delete(url, headers=get_headers(NORMAL_API_KEY))
    print(f"DELETE {url} (normal key) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 403

    # Test using admin API key
    response = requests.delete(url, headers=get_headers(ADMIN_API_KEY))
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
        response = requests.request(method, url)
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