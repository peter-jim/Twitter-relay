import requests

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000"

def test_get_interactions():
    """Test the GET /api/interaction/<media_account> endpoint"""
    url = f"{BASE_URL}/api/interaction/example_account"
    response = requests.get(url)
    print(f"GET {url} -> {response.status_code}")
    if response.status_code == 200:
        print(response.json())

def test_get_user_interactions():
    """Test the GET /api/user/interactions/<user_id> endpoint"""
    url = f"{BASE_URL}/api/user/interactions/123456789"
    response = requests.get(url)
    print(f"GET {url} -> {response.status_code}")
    if response.status_code == 200:
        print(response.json())

def test_manage_accounts():
    """Test the POST /api/accounts endpoint"""
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": "example_account",
        "start_time": "2023-10-01T00:00:00",
        "end_time": "2023-10-31T23:59:59",
        "update_frequency": "daily",
        "expiration_time": "2023-11-01T00:00:00"
    }
    response = requests.post(url, json=payload)
    print(f"POST {url} -> {response.status_code}")
    if response.status_code == 200:
        print(response.json())

if __name__ == "__main__":
    test_get_interactions()
    test_get_user_interactions()
    test_manage_accounts()
