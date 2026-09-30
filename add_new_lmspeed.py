"""
Add meaningful new commercial relay services from lmspeed to the README.
These are services with proper commercial-style domains (not personal CLI proxies, HF spaces, etc.)
"""
import re

README_PATH = r"i:\Downloads\ai-api-proxy-list\README.md"

# New meaningful commercial services from lmspeed (filtered from 242 candidates)
# Only those with proper domain names that look like commercial API relay services
new_entries = [
    ("OfoxAI", "ofox.ai", "多模型"),
    ("VVCode", "vvcode.top", "多模型"),
    ("MKE AI", "tb-api.mkeai.com", "多模型"),
    ("词元流动", "tokenflux.dev", "多模型"),
    ("9Router", "9router.com", "多模型"),
    ("ABC Relay", "abcrelay.com", "多模型"),
    ("OpenCode", "opencode.ai", "多模型"),
    ("DuckCoding", "duckcoding.ai", "多模型"),
    ("ocool AI", "ocool.ai", "多模型"),
    ("NUWA", "nuwaapi.com", "多模型"),
    ("极速AI", "aicodee.com", "多模型"),
    ("巨量API", "api.yidvps.cn", "多模型"),
    ("晴辰云", "gpt.qt.cool", "多模型"),
    ("丰思理 AI", "ai.fengsili.online", "多模型"),
    ("全球AI", "globalai.vip", "多模型"),
    ("ChatGTP", "chatgtp.cn", "多模型"),
    ("UniAiX", "uniaix.com", "多模型"),
    ("艾可API", "aicanapi.com", "多模型"),
    ("简易-API中转站", "jeniya.top", "多模型"),
    ("简小智API中转站", "newapi.jianxiaozhi.chat", "多模型"),
    ("小智API", "newai.aichat.ink", "多模型"),
    ("一叶知秋API", "88996.cloud", "多模型"),
    ("AI98", "ai98.vip", "多模型"),
    ("Aizex API", "aizex.top", "多模型"),
    ("黑与白公益站", "ai.hybgzs.com", "多模型"),
    ("AI新境", "aixj.vip", "多模型"),
    ("酸枝云", "suanzhi.cloud", "多模型"),
    ("MonkingAI", "monking.ai", "多模型"),
    ("EnenCloud API", "api.enencloud.top", "多模型"),
    ("PackyAPI", "codex-api.packycode.com", "多模型"),
    ("HotaruAPI", "api.hotaruapi.top", "多模型"),
    ("AiroeAI", "ai.airoe.cn", "多模型"),
    ("InstCopilot API", "instcopilot-api.com", "多模型"),
    ("GPTBest", "gptbest", "多模型"),
    ("F2API", "api.f2api.com", "多模型"),
    ("GPTs API", "gptsapi", "多模型"),
    ("Smz Ai", "smz6.com", "多模型"),
    ("Undy API", "vip.undyingapi.com", "多模型"),
    ("NanoGPT", "nano-gpt.com", "多模型"),
    ("Yun API", "api.zyai.online", "多模型"),
]

# Read current README
with open(README_PATH, "r", encoding="utf-8") as f:
    readme = f.read()

# Find insertion point (before the data sources section)
insert_point = readme.find("\n\n## 📚 数据来源")

# Build new rows
new_rows = ""
for name, domain, models in new_entries:
    url = f"https://{domain}"
    new_rows += f"| {name} | [{domain}]({url}) | {models} |  |\n"

# Insert before data sources
new_readme = readme[:insert_point] + "\n" + new_rows + readme[insert_point:]

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_readme)

print(f"Added {len(new_entries)} new entries to README")
