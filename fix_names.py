"""Fix missing names in the table - restore names from markdown link text."""
import re

README_PATH = r"i:\Downloads\ai-api-proxy-list\README.md"

with open(README_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Find the table
table_start = content.find("| # | 名称 | 官网 | 支持模型 | 官网延迟 |")
table_end = content.find("\n\n## 📚", table_start)
table_text = content[table_start:table_end]

lines = table_text.split("\n")

header_line = lines[0]
align_line = lines[1]
new_lines = [header_line, align_line]

for line in lines[2:]:
    stripped = line.strip()
    if not stripped:
        new_lines.append(line)
        continue
    if not stripped.startswith("|"):
        new_lines.append(line)
        continue
    
    # Split by pipe
    parts = stripped.split(" | ")
    
    # parts[0] = "| N" or "| 1" etc.
    num_part = parts[0].lstrip("| ").strip()
    
    # parts[1] could be a name or a markdown link
    second = parts[1].strip()
    
    if second.startswith("["):
        # Name is missing - extract from markdown link [text](url)
        link_match = re.match(r"\[([^\]]+)\]", second)
        restored_name = link_match.group(1) if link_match else second
        # Rebuild
        rest = " | ".join(parts[2:])
        new_line = f"| {num_part} | {restored_name} | {rest}"
        # Ensure trailing pipe
        if not new_line.endswith(" |"):
            new_line = new_line.rstrip() + " |"
        new_lines.append(new_line)
    else:
        # Name is present
        rest = " | ".join(parts[1:])
        new_line = f"| {num_part} | {rest}"
        if not new_line.endswith(" |"):
            new_line = new_line.rstrip() + " |"
        new_lines.append(new_line)

new_table = "\n".join(new_lines)
new_content = content.replace(table_text, new_table)

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

# Verify
with open(README_PATH, "r", encoding="utf-8") as f:
    verify = f.read()

verify_start = verify.find("| # | 名称 | 官网 |")
rows = verify[verify_start:].split("\n")[2:]
sample = [r for r in rows if r.strip().startswith("|")][:10]
print("First 10 rows after fix:")
for r in sample:
    print(r)
