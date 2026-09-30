"""
Properly rebuild the table for the new 7-column format:
| # | 名称 | 官网 | 支持模型 | Base URL | API延迟 | 官网延迟 |
"""
import re
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

header = "| # | 名称 | 官网 | 支持模型 | Base URL | API延迟 | 官网延迟 |"
align = "|:---:|:---|:---|:---|:---|:---:|:---:|"
new_lines = [header, align]

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

for i, p in enumerate(providers, 1):
    line = (
        f"| {i} | {p['name']} | [{p['domain']}]({p['homepage']}) | "
        f"{p['models']} | {p['api_url']} | {p['api_latency']} | {p['latency']} |"
    )
    new_lines.append(line)

new_table = "\n".join(new_lines)
new_content = content[:table_start] + new_table + content[table_end:]

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Rebuilt table with {len(providers)} rows in 7-column format.")
