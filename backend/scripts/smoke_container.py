"""Exercise the built image through HTTP, including its writable dataset path."""
import json
import os
import time
from urllib.request import Request, urlopen
from urllib.error import URLError

BASE = "http://127.0.0.1:8000"

for attempt in range(30):
    try:
        with urlopen(f"{BASE}/health", timeout=3) as response:
            health = json.load(response)
            assert health["status"] == "ok"
            assert health["version"] == os.getenv("GITHUB_SHA", "development")
        break
    except (OSError, TimeoutError):
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

# A second, larger fixture exercises the actual HTTP preview/batch/final flow.
# It remains tiny on disk; the tail intentionally changes the chart distribution.
content = "value,group\n" + "1,early\n" * 10000 + "100,late\n" * 1007
body = (f"--{boundary}\r\n"
        'Content-Disposition: form-data; name="file"; filename="progressive-smoke.csv"\r\n'
        "Content-Type: text/csv\r\n\r\n" + content + f"\r\n--{boundary}--\r\n").encode()
with urlopen(Request(f"{BASE}/api/upload", data=body,
                     headers={"Content-Type": f"multipart/form-data; boundary={boundary}"}), timeout=30) as response:
    large = json.load(response)
with urlopen(f'{BASE}/api/datasets/{large["id"]}/eda/stream', timeout=30) as response:
    events = [json.loads(line[6:]) for line in response.read().decode().splitlines() if line.startswith("data: ")]
assert any(event["stage"] == "preview" for event in events)
assert events[-1]["stage"] == "complete", events[-1]
full = events[-1]["data"]
assert full["analysis"]["processed_rows"] == 11007
groups = next(chart for chart in full["distributions"] if chart["column"] == "group")
assert {entry["value"]: entry["count"] for entry in groups["values"]} == {"early": 10000, "late": 1007}
with urlopen(f'{BASE}/api/datasets/{large["id"]}/eda', timeout=10) as response:
    assert json.load(response)["analysis"]["cached"]
print("Container progressive smoke passed: preview, full tail counts, cached reopen")
