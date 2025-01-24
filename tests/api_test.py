import requests

# Base URL for the API
BASE_URL = "http://127.0.0.1:5000"
TEST_MEDIA_ACCOUNT = "hetu_protocol"


def test_get_interactions():
    """Test the GET /api/interaction/<media_account> endpoint"""
    url = f"{BASE_URL}/api/interaction/{TEST_MEDIA_ACCOUNT}"
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
        "media_account": TEST_MEDIA_ACCOUNT,  # 测试 media account
        "start_time": "2025-01-23T00:00:00Z",
        "update_frequency": "1 week",
    }
    response = requests.post(url, json=payload)
    print(f"POST {url} -> {response.status_code}")
    print("response status code", response.status_code)
    print("response: ", response.json())


def test_manage_accounts_errors1():
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": "你好大大打算",  # 测试 错误的media account
        "start_time": "2025-01-20T00:00:00Z",
        "update_frequency": "5 minutes",
    }
    response = requests.post(url, json=payload)
    print(f"POST {url} -> {response.status_code}")
    print("response status code", response.status_code)
    print("response: ", response.json())

def test_manage_accounts_errors2():
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,  # 测试 media account
        "start_time": "2026-01-20T00:00:00Z",  # 26年
        "update_frequency": "5 minutes",
    }
    response = requests.post(url, json=payload)
    print(f"POST {url} -> {response.status_code}")
    print("response status code", response.status_code)
    print("response: ", response.json())

def test_manage_accounts_errors3():
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,  # 测试 media account
        "start_time": "2026-01-20 00:00:00 ",  # 格式不对
        "update_frequency": "5 minutes",
    }
    response = requests.post(url, json=payload)
    print(f"POST {url} -> {response.status_code}")
    print("response status code", response.status_code)
    print("response: ", response.json())


def test_manage_accounts_errors4():
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,  # 测试 media account
        "start_time": "2026-01-20 00:00:00 ",
        "update_frequency": "5 years",  # 没有years
    }
    response = requests.post(url, json=payload)
    print(f"POST {url} -> {response.status_code}")
    print("response status code", response.status_code)
    print("response: ", response.json())

def test_errors():
    test_manage_accounts_errors1()
    test_manage_accounts_errors2()
    test_manage_accounts_errors3()
    test_manage_accounts_errors4()


def test_remove_task():
    url = f"{BASE_URL}/api/accounts"
    payload = {
        "media_account": TEST_MEDIA_ACCOUNT,  # 测试 media account
        "start_time": "2026-01-20 00:00:00 ",  # 格式不对
        "update_frequency": "5 minutes",
    }
    response = requests.delete(url, json=payload)
    print("response status code", response.status_code)
    print("response: ", response.json())

if __name__ == "__main__":
    # test_get_interactions()
    # test_get_user_interactions()
    # test_errors()
    # test_manage_accounts()
    test_remove_task()
