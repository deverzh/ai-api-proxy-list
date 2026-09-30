"""Add sequential numbers to all table rows in README.md"""
import re

README_PATH = r"i:\Downloads\ai-api-proxy-list\README.md"

with open(README_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# First restore names that got eaten - the original format before running this script
# Check if names are missing (lines without a markdown link before model column)
# Actually, let me check the first row structure:
# Row 1: | 1 | paintbot | [oneapi.paintbot.top](https://oneapi.paintbot.top) | 多模型 | 60ms |  <- good
# Row 2: | 2 | [api.yidvps.cn](https://api.yidvps.cn) | 多模型 | 61ms |  <- name missing!

# The issue is that the first time numbers were added, some names may have been lost.
# Let me first check the actual current state

# Read a sample of data rows to understand current format
lines = content.split('\n')
table_start_idx = None
table_end_idx = None

for i, line in enumerate(lines):
    if '| # | 名称 | 官网 |' in line:
        table_start_idx = i
    if table_start_idx is not None and i > table_start_idx and line.startswith('\n## 📚'):
        table_end_idx = i
        break
    if table_start_idx is not None and i > table_start_idx + 2 and line.strip() == '' and '|' not in line:
        # Check if next line has ## 📚
        if i + 1 < len(lines) and '## 📚' in lines[i + 1]:
            table_end_idx = i
            break

if table_end_idx is None:
    table_end_idx = len(lines)

# Rebuild table with numbers
new_lines_list = lines[:]
table_lines = lines[table_start_idx:table_end_idx]

new_table_lines = []
num = 1

for line in table_lines:
    stripped = line.strip()
    if not stripped:
        new_table_lines.append(line)
        continue
    if '| # | 名称 |' in stripped or '|:---:|:---' in stripped:
        new_table_lines.append(line)
        continue
    if stripped.startswith('|'):
        # Check if there's already a number (lines like "| N | name | ...")
        parts = [p.strip() for p in stripped.split('|')]
        parts = [p for p in parts if p]  # Remove empty strings from split
        
        # Current format should be: | N | name | [link](url) | models | latency |
        # But some might be: | N | [link](url) | models | latency | (missing name)
        
        if len(parts) >= 4:
            first = parts[0]
            second = parts[1]
            # If second part starts with [ (markdown link), name is missing
            if second.startswith('['):
                # Name was lost, try to extract from the link text
                name_from_link = re.search(r'\[([^\]]+)\]', second)
                restored_name = name_from_link.group(1) if name_from_link else second
                # Reconstruct with number + name + rest
                rest = ' | '.join(parts[1:])
                new_line = f"| {num} | {restored_name} | {rest}"
                new_table_lines.append(new_line)
            else:
                # Format is correct: | N | name | [link] | models | latency |
                # Just ensure number is correct
                rest = ' | '.join(parts[1:])
                new_line = f"| {num} | {rest}"
                new_table_lines.append(new_line)
            num += 1
        else:
            new_table_lines.append(line)
    else:
        new_table_lines.append(line)

# Replace the table section
new_content = '\n'.join(new_lines_list[:table_start_idx]) + '\n' + '\n'.join(new_table_lines) + '\n' + '\n'.join(new_lines_list[table_end_idx:])

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

print(f"Fixed numbering for rows")
