"""
Rebuild the table from scratch with sequential numbers.
The current table has names that got replaced with domain names.
We fix this by extracting the original names from the raw content or link text.
"""
import re

README_PATH = r"i:\Downloads\ai-api-proxy-list\README.md"

with open(README_PATH, "r", encoding="utf-8") as f:
    content = f.read()

# Find the table
table_start = content.find("| # | 名称 | 官网 | 支持模型 | 官网延迟 |")
table_end = content.find("\n\n---\n\n## 📚", table_start)
if table_end == -1:
    table_end = content.find("\n\n## 📚", table_start)

table_text = content[table_start:table_end]

lines = table_text.split("\n")

header_line = lines[0]  # | # | 名称 | 官网 | 支持模型 | 官网延迟 |
align_line = lines[1]   # |:---:|:---|:---|:---|:---:|

new_lines = [header_line, align_line]

# Known name mappings (domain -> original name) for entries that lost their names
# These are from the original data before numbering
name_map = {
    "oneapi.paintbot.top": "paintbot",
    "api.yidvps.cn": "巨量API",
    "gpt.qt.cool": "晴辰云",
    "yunzhiapi.cn": "云智API",
    "88api.apifox.cn": "88API",
    "ddshub.cc": "DDS (ddshub.cc)",
    "newai.aichat.ink": "小智API",
    "x.dogenet.win": "OhMyGPT",
    "instcopilot-api.com": "InstCopilot API",
    "terminal.pub": "Terminal.Pub",
    "open.api.gu28.top": "boneapi",
    "ai.adbog.com": "草丛GPT中转站",
    "jiekou.ai": "接口AI",
    "timesniper.club": "一元模型",
    "api.suchuang.vip": "速创API",
    "6i2.com": "6i2",
    "buzzai.cc": "BUZZ",
    "dmxapi.cn": "DMXAPI",
    "nodapi.com": "NodAPI",
    "ai.airoe.cn": "AiroeAI",
    "kkidc.com": "快快云安全",
    "xinglianapi.com": "xinglianapi",
    "xiaoruiapi.cc": "小瑞API",
    "monking.ai": "MonkingAI",
    "siliconflow.cn": "硅基流动 SiliconFlow",
    "shengsuanyun.com": "盛算云 Shengsuanyun",
    "compshare.cn": "Compshare (UCloud)",
    "new.lemonapi.site": "柠檬API",
    "aihubmix.com": "AIHubMix",
    "api.chatfire.cn": "chatfire",
    "api.bltcy.ai": "柏拉图AI",
    "35.aigcbest.top": "35-aigcbest",
    "vibecodingapi.ai": "LionCC",
    "api.whatai.cc": "神马中转 API",
    "koalaapi.com": "koalaapi",
    "api.laozhang.ai": "laozhang.ai",
    "2api.rkai6.com": "RK AI",
    "4sapi.com": "星链 4SAPI",
    "cn.nyi.cn": "Flux AI",
    "gptgod.cloud": "gptgod",
    "treerouter.com": "treerouter",
    "s2a.865199.xyz": "Sub2API",
    "api.v3.cm": "v3",
    "api.openai-ch.top": "GalaxyAPI",
    "right.codes": "RightCode",
    "switchbase.vip": "SwitchBase",
    "ccfly.codes": "CCFly",
    "api.owlai.tech": "Owl AI",
    "poixe.com": "Poixe AI",
    "qiuqiutoken.com": "球球Token",
    "api.gueai.com": "GueAi",
    "dawclaudecode.com": "DawCode",
    "nekocode.ai": "NekoCode",
    "api.xinjianya.top": "星见雅 API",
    "chefshop.ai": "ChefShop AI",
    "api.lingyaai.cn": "灵芽 API",
    "xcode.best": "XcodeBest",
    "gptapi.us": "gptapi",
    "huashang.dpdns.org": "猫羽霖API",
    "aigocode.com": "AIGoCode",
    "uuapi.net": "UU API",
    "api.ephone.ai": "ephone",
    "claudecn.top": "ClaudeCN",
    "ai.17nas.com": "镜核 AI",
    "stark-gpt-load.onrender.com": "Stark GPT Load",
    "api.dzzi.ai": "大肘子",
    "e-flowcode.cc": "E-FlowCode",
    "chatapi.onechats.top": "OneChats",
    "picoai.top": "PICO AI",
    "fastapi.aabao.vip": "aabao",
    "findcg.com": "发现AI",
    "crazyrouter.com": "Crazyrouter",
    "deepkey.top": "deepkey",
    "dragoncode.codes": "Dragoncode",
    "api.nekoapi.com": "nekoapi",
    "matrcode.com": "Matr Code",
    "n1n.ai": "n1n.ai",
    "ctok.ai": "CTok.ai",
    "api.gptoai.cc": "ShawnAPI",
    "ai.smartall.cloud": "Smart API",
    "azapi.com.cn": "azapi",
    "qianweikeji.fun": "汪汪の中转站",
    "cca.maya.today": "BMCCA",
    "aihub-global.com": "AI Hub",
    "bytecatcode.org": "ByteCat",
    "aicodemirror.com": "AICodeMirror",
    "timyai.com": "Timy AI",
    "cubence.com": "Cubence",
    "opus.gptuu.com": "gptuu",
    "api.yuegle.com": "YuegleAPI",
    "lxtech.icu": "LX_API",
    "packyapi.com": "PackyCode",
    "timicc.com": "TimiCC",
    "co.yes.vg": "YesCode",
    "anpin.ai": "AnPin AI",
    "chat-api4.087654.xyz": "天絮 API",
    "lemondata.cc": "LemonData",
    "api.ikuncode.cc": "IKunCode",
    "anyone.ai": "ANYONE.AI",
    "api1.zhtec.xyz": "zhtec",
    "aicoding.sh": "AICoding",
    "code.b886.top": "CCTQ",
    "anyrouter.top": "Anyrouter",
    "openrouter.ai": "OpenRouter",
    "dataeyes.ai": "DataEyes AI",
    "console.claudeapi.com": "ClaudeAPI",
    "pateway.ai": "PatewayAI",
    "poloai.top": "PoloAPI",
    "zxai.work": "ZX API",
    "shiyunapi.com": "诗云 API ShiyunApi",
    "yansd666.com": "SmokeDivine AI",
    "codesome.ai": "codesome.ai",
    "xinyuanai666.com": "鑫源AI",
    "mikuapi.org": "MiKu",
    "api.nio.gs": "Nio",
    "new.xjai.cc": "xjai-new",
    "apiyi.com": "API 易",
    "go.sbgpt.site": "sbgpt",
    "wzjself.org": "wzjself中转站",
    "apipro.maynor1024.live": "MaynorAPI",
    "openai-labs.com": "openaiLabs",
    "api.tomchat.fun": "tomchat",
    "cnapi.kksj.org": "kksj",
    "4ksapi.com": "4ksAPI",
    "apinebula.com": "APINebula",
    "aiberm.com": "Aiberm",
    "catclawai.top": "CatClaw API",
    "chunxueapi.com": "ChunXue API",
    "closeai-asia.com": "CloseAI",
    "foxcode.rjj.cc": "FoxCode",
    "kfcv50.link": "KFCV50API",
    "openclaudecode.cn": "Micu API",
    "muskpay.top": "MuskAI",
    "runapi.co": "RunAPI",
    "sssaicode.com": "SSSAiCode",
    "zenmux.ai": "ZenMux",
    "chienapi.top": "chienapi",
    "ggwk1.online": "ggwk1",
    "ofox.ai": "ofox.ai",
    "qnaigc.com": "七牛云 AI",
    "yunwu.ai": "云雾AI",
    "hu.weiyusc.top": "微雨API",
    "api.bbww.top": "旺旺中转站",
    "naapi.cc": "钠 API",
    "vvcode.top": "VVCode",
    "tb-api.mkeai.com": "MKE AI",
    "tokenflux.dev": "词元流动",
    "9router.com": "9Router",
    "abcrelay.com": "ABC Relay",
    "opencode.ai": "OpenCode",
    "duckcoding.ai": "DuckCoding",
    "ocool.ai": "ocool AI",
    "nuwaapi.com": "NUWA",
    "aicodee.com": "极速AI",
    "globalai.vip": "全球AI",
    "chatgtp.cn": "ChatGTP",
    "uniaix.com": "UniAiX",
    "aicanapi.com": "艾可API",
    "jeniya.top": "简易-API中转站",
    "newapi.jianxiaozhi.chat": "简小智API中转站",
    "88996.cloud": "一叶知秋API",
    "ai98.vip": "AI98",
    "aizex.top": "Aizex API",
    "ai.hybgzs.com": "黑与白公益站",
    "aixj.vip": "AI新境",
    "suanzhi.cloud": "酸枝云",
    "api.enencloud.top": "EnenCloud API",
    "codex-api.packycode.com": "PackyAPI",
    "api.hotaruapi.top": "HotaruAPI",
    "api.f2api.com": "F2API",
    "smz6.com": "Smz Ai",
    "vip.undyingapi.com": "Undy API",
    "nano-gpt.com": "NanoGPT",
    "api.zyai.online": "Yun API",
    "ai.fengsili.online": "丰思理 AI",
    "suanzhi.cloud": "酸枝云",
    "monking.ai": "MonkingAI",
}

num = 1
for line in lines[2:]:
    stripped = line.strip()
    if not stripped or not stripped.startswith("|"):
        new_lines.append(line)
        continue
    
    # Split line to extract parts
    parts = stripped.split(" | ")
    
    # Get the number part
    num_part = parts[0].lstrip("| ").strip()
    
    # Check what's in position 1
    second = parts[1].strip() if len(parts) > 1 else ""
    
    # Check if second starts with [ (markdown link = name missing)
    if second.startswith("["):
        # Extract domain from link
        link_match = re.match(r"\[([^\]]+)\]", second)
        domain_from_link = link_match.group(1) if link_match else ""
        
        # Look up the name
        original_name = name_map.get(domain_from_link, domain_from_link)
        
        rest = " | ".join(parts[2:])
        new_line = f"| {num} | {original_name} | {rest}"
        if not new_line.endswith("|"):
            new_line = new_line.rstrip() + " |"
        new_lines.append(new_line)
    else:
        # Name is present
        rest = " | ".join(parts[1:])
        new_line = f"| {num} | {rest}"
        if not new_line.endswith("|"):
            new_line = new_line.rstrip() + " |"
        new_lines.append(new_line)
    
    num += 1

new_table = "\n".join(new_lines)
new_content = content.replace(table_text, new_table)

with open(README_PATH, "w", encoding="utf-8") as f:
    f.write(new_content)

# Verify
with open(README_PATH, "r", encoding="utf-8") as f:
    verify = f.read()
    
verify_start = verify.find("| # | 名称 | 官网 |")
rows = [r for r in verify[verify_start:].split("\n") if r.strip().startswith("|") and not "名称" in r and not ":---" in r]
print(f"Fixed {len(rows)} rows. Sample:")
for r in rows[:15]:
    print(r)
