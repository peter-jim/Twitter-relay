import requests
from test_utils import make_api_request

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000"

# Test accounts
TEST_MEDIA_ACCOUNT = "hetu_protocol"
TEST_USERNAME = "Sky201805"
TEST_USER_ID = 993673319512653824

# API keys and secrets for testing
NORMAL_API_KEY = "normal_5ff1c7a75e9f4e1d8f3c3c3c3c3c3c3c"
NORMAL_API_SECRET = "normal_secret_9b5d8c4a3e2f1g7h6j9k8l5m2n4p3q0r"

# Tests that don't require API key
def test_get_interactions():
    """Test the GET /api/interaction/<media_account> endpoint"""
    url = f"{BASE_URL}/api/interaction/{TEST_MEDIA_ACCOUNT}"
    response = requests.get(url)  # no auth
    print(f"GET {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_get_user_interactions():
    """Test the GET /api/user/interactions/<user_id> endpoint"""
    url = f"{BASE_URL}/api/user/interactions/{TEST_USER_ID}"
    response = requests.get(url)  # no auth
    print(f"GET {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

# Tests that require API key
def test_manage_accounts():
    """Test the POST /api/accounts endpoint"""
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,
        "start_time": "2025-01-25T00:00:00Z",
        "update_frequency": "1 week",
    }
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload)
    print(f"POST {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_manage_accounts_errors():
    """Test various error cases for the POST /api/accounts endpoint"""
    url = f"{BASE_URL}/api/accounts"
    
    # Test case 1: Invalid media account
    payload1 = {
        "media_account": "你好打算大大",
        "start_time": "2025-01-20T00:00:00Z",
        "update_frequency": "5 minutes",
    }
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload1)
    print(f"POST {url} (invalid account) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 400

    # Test case 2: Future date too far
    payload2 = {
        "media_account": TEST_MEDIA_ACCOUNT,
        "start_time": "2026-01-20T00:00:00Z",
        "update_frequency": "5 minutes",
    }
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload2)
    print(f"POST {url} (future date) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 400

    # Test case 3: Invalid datetime format
    payload3 = {
        "media_account": TEST_MEDIA_ACCOUNT,
        "start_time": "2026-01-20 00:00:00",
        "update_frequency": "5 minutes",
    }
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload3)
    print(f"POST {url} (invalid format) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 400

    # Test case 4: Invalid update frequency
    payload4 = {
        "media_account": TEST_MEDIA_ACCOUNT,
        "start_time": "2025-01-20T00:00:00Z",
        "update_frequency": "5 years",
    }
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload4)
    print(f"POST {url} (invalid frequency) -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 400

def test_remove_task():
    """Test the DELETE /api/accounts endpoint"""
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,
        "start_time": "2025-01-20T00:00:00Z",
        "update_frequency": "5 minutes",
    }
    response = make_api_request('DELETE', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload)
    print(f"DELETE {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_api_person():
    """Test the POST /api/person endpoint"""
    url = f"{BASE_URL}/api/person"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,
        "username": TEST_USERNAME,
    }
    response = make_api_request('POST', url, NORMAL_API_KEY, NORMAL_API_SECRET, payload)
    print(f"POST {url} -> {response.status_code}")
    print("Response:", response.json())
    assert response.status_code == 200

def test_without_required_api_key():
    """Test endpoints that require API key without providing one"""
    endpoints = [
        ("POST", "/api/accounts"),
        ("DELETE", "/api/accounts"),
        ("POST", "/api/person")
    ]
    
    for method, path in endpoints:
        url = f"{BASE_URL}{path}"
        response = requests.request(method, url)  # no auth
        print(f"{method} {url} (no key) -> {response.status_code}")
        print("Response:", response.json())
        assert response.status_code == 401

def test_with_invalid_api_key():
    """Test endpoints with an invalid API key"""
    invalid_key = "invalid_key_12345"
    invalid_secret = "invalid_secret_12345"
    
    # Test endpoints that require API key
    endpoints = [
        ("POST", "/api/accounts", {
            "media_account": TEST_MEDIA_ACCOUNT,
            "start_time": "2025-01-25T00:00:00Z",
            "update_frequency": "1 week"
        }),
        ("DELETE", "/api/accounts", {
            "media_account": TEST_MEDIA_ACCOUNT,
            "start_time": "2025-01-20T00:00:00Z",
            "update_frequency": "5 minutes"
        }),
        ("POST", "/api/person", {
            "media_account": TEST_MEDIA_ACCOUNT,
            "username": TEST_USERNAME
        })
    ]
    
    for method, path, payload in endpoints:
        url = f"{BASE_URL}{path}"
        response = make_api_request(method, url, invalid_key, invalid_secret, payload)
        print(f"{method} {url} (invalid key) -> {response.status_code}")
        print("Response:", response.json())
        assert response.status_code == 401
        assert response.json()["message"] == "Invalid API key"

if __name__ == "__main__":
    # Run tests that don't require API key
    print("\n=== Running tests without API key ===")
    test_get_interactions()
    test_get_user_interactions()
    
    # Run tests that require API key
    print("\n=== Running tests with API key ===")
    test_manage_accounts()
    test_manage_accounts_errors()
    test_api_person()
    test_remove_task()
    
    # Run tests for missing API key
    print("\n=== Running tests for missing API key ===")
    test_without_required_api_key()

    # Run tests for invalid API key
    print("\n=== Running tests with invalid API key ===")
    test_with_invalid_api_key()
