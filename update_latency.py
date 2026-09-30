"""
Update latency values in README.md for the 7-column format.
Sorting: first by API Base URL latency, then by homepage latency.
"""
import re
import subprocess
import platform
import time
import socket
import urllib.request
import urllib.error
from pathlib import Path

README_PATH = Path(__file__).resolve().parent / "README.md"

with open(README_PATH, "r", encoding="utf-8") as f:
    content = f.read()

table_start = content.find("| # | 名称 | 官网 |")
table_end = content.find("\n\n---\n\n## 📚", table_start)
if table_end == -1:
    table_end = content.find("\n\n## 📚", table_start)

table_text = content[table_start:table_end]

lines = table_text.split("\n")

row_re = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*"
    r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|$",
    re.MULTILINE,
)

old_row_re = re.compile(
    r"^\|\s*(\d+)\s*\|\s*(.*?)\s*\|\s*\[([^\]]+)\]\((https?://[^)]+)\)\s*"
    r"\|\s*(.*?)\s*\|\s*(.*?)\s*\|$",
    re.MULTILINE,
)

providers = []
for match in row_re.finditer(table_text):
    providers.append({
        "index": int(match.group(1)),
        "name": match.group(2).strip(),
        "domain": match.group(3).strip(),
        "homepage": match.group(4).strip(),
        "models": match.group(5).strip(),
        "api_url": match.group(6).strip(),
        "api_latency": match.group(7).strip(),
        "latency": match.group(8).strip(),
    })

is_new_format = len(providers) > 0

if not providers:
    for match in old_row_re.finditer(table_text):
        providers.append({
            "index": int(match.group(1)),
            "name": match.group(2).strip(),
            "domain": match.group(3).strip(),
            "homepage": match.group(4).strip(),
            "models": match.group(5).strip(),
            "api_url": "待确认",
            "api_latency": "-",
            "latency": match.group(6).strip(),
        })

print(f"Found {len(providers)} rows to test")

def test_domain(domain):
    """Test domain using ping, TCP, and HTTP."""
    try:
        param = "-n" if platform.system().lower() == "windows" else "-c"
        timeout_param = "-w" if platform.system().lower() == "windows" else "-W"
        timeout_val = "3000" if platform.system().lower() == "windows" else "3"
        result = subprocess.run(
            ["ping", param, "1", timeout_param, timeout_val, domain],
            capture_output=True, text=True, timeout=8
        )
        output = result.stdout + result.stderr
        time_match = re.search(r'时间[=<]\s*(\d+)\s*ms', output, re.IGNORECASE)
        if not time_match:
            time_match = re.search(r'time[=<]\s*([\d.]+)\s*ms', output, re.IGNORECASE)
        if not time_match:
            time_match = re.search(r'(?:平均|Average|最大|Maximum)\s*[=:]\s*(\d+)\s*ms', output, re.IGNORECASE)
        if result.returncode == 0 and time_match:
            return int(float(time_match.group(1))), True
    except:
        pass

    try:
        start = time.time()
        sock = socket.create_connection((domain, 443), timeout=5)
        elapsed = int((time.time() - start) * 1000)
        sock.close()
        return elapsed, True
    except:
        pass

    try:
        start = time.time()
        sock = socket.create_connection((domain, 80), timeout=5)
        elapsed = int((time.time() - start) * 1000)
        sock.close()
        return elapsed, True
    except:
        pass

    for scheme in ['https', 'http']:
        try:
            start = time.time()
            req = urllib.request.Request(f"{scheme}://{domain}", method='HEAD')
            req.add_header('User-Agent', 'Mozilla/5.0')
            resp = urllib.request.urlopen(req, timeout=5)
            elapsed = int((time.time() - start) * 1000)
            return elapsed, True
        except urllib.error.HTTPError as e:
            elapsed = int((time.time() - start) * 1000)
            return elapsed, True
        except:
            continue

    return None, False


new_providers = []
for i, p in enumerate(providers):
    domain = p['domain'].split('/')[0].replace('www.', '')
    
    name_clean = p['name'].lstrip("❌ ").strip()
    while name_clean.startswith("❌"):
        name_clean = name_clean[1:].strip()
    
    latency, ok = test_domain(domain)
    
    if latency is not None:
        latency_str = f"{latency}ms"
        status = "✅"
    else:
        latency_str = "超时"
        name_clean = f"❌ {name_clean}"
        status = "❌"
    
    p['name'] = name_clean
    p['latency'] = latency_str
    new_providers.append(p)
    
    print(f"{i+1:3d}. {status} {name_clean:<30s} {domain:<35s} {latency if latency else '超时'}ms")
    time.sleep(0.05)


def sort_key(p):
    api_latency_val = 999999
    if p['api_latency'] and p['api_latency'] != "-" and p['api_latency'] != "未知":
        try:
            api_latency_val = int(p['api_latency'].replace("ms", ""))
        except ValueError:
            pass

    latency_val = 999999
    if p['latency'] and p['latency'] != "超时" and p['latency'] != "-":
        try:
            latency_val = int(p['latency'].replace("ms", ""))
        except ValueError:
            pass

    api_priority = 0 if api_latency_val < 999999 else 1
    homepage_priority = 0 if latency_val < 999999 else 1

    return (api_priority, api_latency_val, homepage_priority, latency_val, p['name'].lower())


providers_sorted = sorted(new_providers, key=sort_key)


header = "| # | 名称 | 官网 | 支持模型 | Base URL | API延迟 | 官网延迟 |"
align = "|:---:|:---|:---|:---|:---|:---:|:---:|"
new_lines = [header, align]

for i, p in enumerate(providers_sorted, 1):
    line = (
        f"| {i} | {p['name']} | [{p['domain']}]({p['homepage']}) | "
        f"{p['models']} | {p['api_url']} | {p['api_latency']} | {p['latency']} |"
    )
    new_lines.append(line)

new_table = "\n".join(new_lines)
new_content = content[:table_start] + new_table + content[table_end:]

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"\nUpdated {len(new_providers)} entries. Sorted by API latency first, then homepage latency.")
