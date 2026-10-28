"""Exercise the built image through HTTP, including its writable dataset path."""
import json
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE = "http://127.0.0.1:8000"

for attempt in range(30):
    try:
        with urlopen(f"{BASE}/health", timeout=3) as response:
            assert json.load(response)["status"] == "ok"
        break
    except (URLError, TimeoutError):
        if attempt == 29:
            raise
        time.sleep(1)

boundary = "edaverse-container-smoke"
body = (f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="container-smoke.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n"
        "value,group\n1,alpha\n2,beta\n3,alpha\n"
        f"\r\n--{boundary}--\r\n").encode()
request = Request(f"{BASE}/api/upload", data=body,
                  headers={"Content-Type": f"multipart/form-data; boundary={boundary}",
                           "Origin": "https://edaverse.app"})
with urlopen(request, timeout=20) as response:
    assert response.headers["Access-Control-Allow-Origin"] == "https://edaverse.app"
    dataset = json.load(response)
assert dataset["success"] and dataset["shape"] == {"rows": 3, "columns": 2}
assert dataset["storage"]["artifacts"][0]["format"] == "parquet"

with urlopen(f'{BASE}/api/datasets/{dataset["id"]}/eda/stream', timeout=20) as response:
    events = [json.loads(line[6:]) for line in response.read().decode().splitlines()
              if line.startswith("data: ")]
assert events[-1]["stage"] == "complete", events[-1]
assert events[-1]["data"]["analysis"]["rows"] == 3
print("Container smoke passed: health, CORS, upload, Parquet persistence, streamed EDA")
