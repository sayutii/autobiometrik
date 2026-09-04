import urllib.request
import urllib.error
import json
import time

BASE_URL = "http://127.0.0.1:5000"

def call_api(endpoint):
    url = f"{BASE_URL}{endpoint}"
    print(f"--> Calling: GET {url}")
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            print(f"    HTTP {resp.status} Response: {json.dumps(data)}")
            return resp.status, data
    except urllib.error.HTTPError as e:
        data = json.loads(e.read().decode('utf-8'))
        print(f"    HTTP {e.code} Response: {json.dumps(data)}")
        return e.code, data
    except Exception as e:
        print(f"    Error connecting: {e}")
        return None, None

def run_tests():
    print("==================================================")
    print("Testing AutoBiometrik REST API Endpoints")
    print("==================================================")

    print("\n1. Testing GET /health")
    call_api("/health")

    print("\n2. Testing GET /start_frista?no_peserta=0001234567890")
    call_api("/start_frista?no_peserta=0001234567890")

    print("\n3. Testing GET /start_finger?no_peserta=0001234567890")
    call_api("/start_finger?no_peserta=0001234567890")

    print("\n4. Testing GET /start_finger without no_peserta (Expect 400 Error)")
    call_api("/start_finger")

    print("\n5. Testing GET /stop_frista")
    call_api("/stop_frista")

    print("\n6. Testing GET /stop_finger")
    call_api("/stop_finger")

    print("\n==================================================")
    print("All endpoint tests complete!")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
