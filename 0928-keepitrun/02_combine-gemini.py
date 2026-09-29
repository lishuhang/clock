#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""合并 RSS 与积压摘要，按最终链接保留最长说明，并以可恢复的多引擎策略翻译标题。"""

import argparse
import datetime
import json
import locale
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TMP_DIR = os.path.join(SCRIPT_DIR, "tmp")
LOG_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

GEMINI_API_KEY = ""
GLM_API_KEY = ""
# v1.26: 免费档最新模型（依据 ai.google.dev 官方定价文档，gemini-3.8-flash 提供 Free of charge 档）
GEMINI_MODEL = "gemini-3.8-flash"
# v1.26: 完全免费档最新模型（依据 docs.bigmodel.cn 官方定价，glm-4.7-flash 输入/输出均免费、200K 上下文；
# 注意 GLM-5.3-Flash 为收费档）
GLM_MODEL = "glm-4.7-flash"

TRANSLATION_BATCH_SIZE = 16
REQUEST_TIMEOUT_SECONDS = 45
ENGINE_RETRIES = 2
GOOGLE_ITEM_DELAY_SECONDS = 0.35
GLM_API_URL = "https://open.bigmodel.cn/api/paas/v4/chat/completions"

TRACKING_PARAM_NAMES = {
    "gclid", "dclid", "fbclid", "gbraid", "wbraid", "msclkid", "yclid",
    "igshid", "ref", "referrer", "ref_src", "source", "src", "campaign",
    "mkt_tok", "spm", "scid", "cmp", "ocid", "feature", "si", "mc_cid",
    "mc_eid", "trk", "tracking", "tracking_id", "from", "via", "output",
}
TRACKING_PARAM_PREFIXES = ("utm_", "mc_", "ga_", "_ga", "oly_", "pk_")
CONTENT_PARAM_PATTERN = re.compile(
    r"^(?:id|p|v|aid|cid|pid|sid|slug|article(?:_id)?|story(?:_id)?|post(?:_id)?|"
    r"video(?:_id)?|content(?:_id)?|item(?:_id)?|news(?:_id)?|episode(?:_id)?)$",
    re.IGNORECASE,
)
SUMMARY_OUTPUT_PATTERN = re.compile(r"^\d{8}-\d{6}\.(?:md|py)$")
# v1.25: 已提取条目的滑动窗口记忆。条目写入摘要后记录其最终 URL（无链接项按标题文本），
# 未来 24 小时内再次出现的新条目将被跳过；超过 24 小时的记录在每次运行时修剪。
ISSUED_MEMORY_PATH = os.path.join(SCRIPT_DIR, "rss_issue_memory.json")
ISSUED_MEMORY_TTL_HOURS = 24
GLM_REFUSAL_MARKERS = (
    "很抱歉，我还未学习到如何回答这个问题的内容",
    "暂时无法提供相关信息",
    "无法提供相关信息",
    "系统检测到输入或生成内容可能包含不安全或敏感内容",
    "避免输入易产生敏感内容的提示语",
    "cannot provide",
    "unable to provide",
    "i cannot help with that",
    "i can't help with that",
)


class GLMContentSafetyRefusal(RuntimeError):
    """GLM 因内容安全策略拒绝整批翻译请求。"""

COMPANY_MAP = {
    "NVIDIA": ["NVIDIA", "英伟达", "Jensen Huang", "Huang Renxun", "黄仁勋", "GeForce", "RTX", "Blackwell", "H100", "H200", "B100", "B200", "GB200", "Rubin", "CUDA", "显卡", "GPU", "Omniverse", "Vera", "X800"],
    "OpenAI": ["OpenAI", "ChatGPT", "GPT", "Sora", "Sam Altman", "Altman", "奥特曼", "Murati", "DALL-E", "O1", "Strawberry", "Q*", "DevDay", "SearchGPT", "Canvas", "Greg Brockman", "Ilya"],
    "Google": ["Google", "谷歌", "DeepMind", "Gemini", "Sundar Pichai", "Demis Hassabis", "Waymo", "AlphaFold", "Android", "Pixel", "TPU", "DeepResearch", "Veo", "Imagen", "Jarvis", "Project Astra", "NotebookLM"],
    "Microsoft": ["Microsoft", "微软", "Copilot", "Azure", "Satya Nadella", "Nadella", "Windows", "Xbox", "Phi-3", "Phi-4", "Recall", "Surface"],
    "Anthropic": ["Anthropic", "Claude", "Dario Amodei", "Amodei", "Constitutional AI"],
    "Apple": ["Apple", "苹果", "iPhone", "iPad", "Mac", "Siri", "Tim Cook", "Cook", "M4", "M5", "A18", "A19", "Apple Intelligence", "Vision Pro", "Ferret", "MM1"],
    "Meta": ["Meta", "Facebook", "Zuckerberg", "Llama", "Yann LeCun", "LeCun", "PyTorch", "Ray-Ban", "Orion", "Quest", "Threads", "Instagram"],
    "xAI/Tesla": ["xAI", "Grok", "Musk", "Elon Musk", "马斯克", "Tesla", "特斯拉", "Optimus", "SpaceX", "Starlink", "Robotaxi", "FSD"],
    "Amazon": ["Amazon", "亚马逊", "AWS", "Bedrock", "Olympus", "Rufus", "Bezos", "Jassy", "Q "],
    "ByteDance": ["ByteDance", "字节", "Doubao", "豆包", "TikTok", "Liang Rubo", "Zhang Yiming", "张一鸣", "Jimeng", "即梦", "Seed-TTS"],
    "Alibaba": ["Alibaba", "阿里", "Qwen", "通义", "Tongyi", "千问", "Joe Tsai", "Eddie Wu", "蔡崇信", "吴泳铭", "Wan", "Animate Anyone"],
    "Baidu": ["Baidu", "百度", "Ernie", "文心", "Robin Li", "李彦宏", "Apollo"],
    "Tencent": ["Tencent", "腾讯", "Hunyuan", "混元", "Pony Ma", "马化腾", "WeChat"],
    "DeepSeek": ["DeepSeek", "深度求索", "幻方", "Liang Wenfeng", "梁文锋", "Fire-Flyer"],
    "Moonshot": ["Moonshot", "月之暗面", "Kimi", "Yang Zhilin", "杨植麟"],
    "MiniMax": ["MiniMax", "海螺", "Hailuo", "Yan Junjie", "闫俊杰", "Video-01"],
    "01.AI": ["01.AI", "零一万物", "Yi-Large", "Yi-Pro", "Lee Kai-fu", "李开复"],
    "Huawei": ["Huawei", "华为", "Ascend", "昇腾", "Kunpeng", "HarmonyOS", "鸿蒙", "Pura", "Mate", "CANN"],
    "Xiaomi": ["Xiaomi", "小米", "Lei Jun", "SU7", "HyperOS", "XiaoAI", "小爱"],
    "SenseTime": ["SenseTime", "商汤", "Xu Li", "李开复", "SenseNova", "日日新", "Vais"],
    "Adobe": ["Adobe", "Photoshop", "Firefly", "Premiere"],
    "Midjourney/Stability": ["Midjourney", "Stability", "Stable Diffusion", "Runway", "Gen-2", "Gen-3", "Pika", "Suno", "Udio"],
}
PRIORITY_ORDER = [
    "NVIDIA", "OpenAI", "Google", "Microsoft", "Apple", "Meta", "Anthropic",
    "xAI/Tesla", "Huawei", "DeepSeek", "ByteDance", "Alibaba", "Tencent",
    "Baidu", "Amazon", "Moonshot", "MiniMax", "01.AI", "Xiaomi", "SenseTime",
    "Midjourney/Stability", "Adobe",
]


def load_dotenv():
    """从同目录 .env 读取配置，且不覆盖已有环境变量。"""
    global GEMINI_API_KEY, GLM_API_KEY, GEMINI_MODEL, GLM_MODEL
    env_path = os.path.join(SCRIPT_DIR, ".env")
    if os.path.isfile(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as file:
                for raw_line in file:
                    line = raw_line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = value
        except OSError:
            pass
    GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
    GLM_API_KEY = os.environ.get("GLM_API_KEY", "").strip()
    GEMINI_MODEL = os.environ.get("GEMINI_MODEL", GEMINI_MODEL).strip()
    GLM_MODEL = os.environ.get("GLM_MODEL", GLM_MODEL).strip()


def parse_news_list_file(filepath):
    header_lines, content_lines, footer_lines = [], [], []
    in_content = False
    try:
        with open(filepath, "r", encoding="utf-8") as file:
            lines = file.readlines()
    except OSError as exc:
        print(f"Error parsing {filepath}: {type(exc).__name__}")
        return None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith(("- ", "• ")):
            in_content = True
            content_lines.append(stripped)
        elif in_content:
            footer_lines.append(line)
        else:
            header_lines.append(line)
    return header_lines, content_lines, footer_lines


def resolve_input_path(path_value):
    if os.path.isfile(path_value):
        return os.path.abspath(path_value)
    tmp_path = os.path.join(TMP_DIR, path_value)
    if os.path.isfile(tmp_path):
        return tmp_path
    script_path = os.path.join(SCRIPT_DIR, path_value)
    if os.path.isfile(script_path):
        return script_path
    return ""


def find_pending_summary_files():
    """找到根目录中尚未取走的日期摘要；兼容历史误后缀 `.py`。"""
    pending = []
    for name in os.listdir(SCRIPT_DIR):
        if SUMMARY_OUTPUT_PATTERN.fullmatch(name):
            candidate = os.path.join(SCRIPT_DIR, name)
            if os.path.isfile(candidate):
                pending.append(candidate)
    return sorted(pending)


def collect_input_files(file_args):
    """汇集积压摘要与新 RSS 文件，确保新输出覆盖用户上次取走之后的全部增量。"""
    inputs = []
    seen = set()
    for path in find_pending_summary_files():
        absolute = os.path.abspath(path)
        if absolute not in seen:
            inputs.append(absolute)
            seen.add(absolute)
    for value in file_args:
        path = resolve_input_path(value)
        if not path:
            print(f"Input file not found: {value}")
            continue
        absolute = os.path.abspath(path)
        if absolute not in seen:
            inputs.append(absolute)
            seen.add(absolute)
    return inputs


def parse_markdown_link(line):
    match = re.match(r"^([-•]\s*)\[(.*?)\]\((.*?)\)(.*)$", line)
    if match:
        return match.group(1), match.group(2), match.group(3), match.group(4)
    match = re.match(r"^([-•]\s*)(.*)$", line)
    if match:
        return match.group(1), match.group(2), "", ""
    return "- ", line.lstrip("- ").lstrip("• "), "", ""


def _is_tracking_param(name):
    lowered = name.lower()
    return lowered in TRACKING_PARAM_NAMES or lowered.startswith(TRACKING_PARAM_PREFIXES)


def canonicalize_url(url):
    """对已抓取的文章 URL 去片段、去追踪参数，便于跨文件去重。"""
    if not url:
        return ""
    parsed = urlsplit(url)
    kept = [
        (key, value)
        for key, value in parse_qsl(parsed.query, keep_blank_values=True)
        if not _is_tracking_param(key) and CONTENT_PARAM_PATTERN.fullmatch(key.lower())
    ]
    host = (parsed.hostname or "").lower()
    netloc = host
    if parsed.port and not ((parsed.scheme == "https" and parsed.port == 443) or (parsed.scheme == "http" and parsed.port == 80)):
        netloc = f"{host}:{parsed.port}"
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", urlencode(kept, doseq=True), ""))


def title_score(title):
    return len(re.sub(r"\s+", "", title))


def deduplicate_content_lines(lines):
    """同一最终 URL 保留标题/摘要文字最长的条目；无链接项按完整文本去重。"""
    best_by_key = {}
    for line in lines:
        prefix, title, url, suffix = parse_markdown_link(line)
        normalized_url = canonicalize_url(url)
        key = ("url", normalized_url) if normalized_url else ("text", re.sub(r"\s+", " ", title).strip().lower())
        reconstructed = f"- [{title}]({normalized_url}){suffix}" if normalized_url else f"- {title}{suffix}"
        existing = best_by_key.get(key)
        if existing is None or title_score(title) > title_score(existing["title"]):
            best_by_key[key] = {"line": reconstructed, "title": title}
    return [entry["line"] for entry in best_by_key.values()]


def load_issue_memory():
    """v1.25: 读取已提取条目记忆，丢弃超过 TTL 的记录；文件缺失或损坏时返回空记忆。"""
    try:
        with open(ISSUED_MEMORY_PATH, encoding="utf-8") as fh:
            raw = json.load(fh)
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    cutoff = time.time() - ISSUED_MEMORY_TTL_HOURS * 3600
    memory = {}
    for key, ts in raw.items():
        if isinstance(key, str) and isinstance(ts, (int, float)) and ts >= cutoff:
            memory[key] = ts
    return memory


def issue_memory_key(title, url):
    """v1.25: 与去重规则一致的记忆键：优先最终 URL，无链接项退回标题文本。"""
    normalized_url = canonicalize_url(url)
    if normalized_url:
        return "u|" + normalized_url
    return "t|" + re.sub(r"\s+", " ", title or "").strip().lower()


def filter_recently_issued(lines, memory):
    """v1.25: 丢弃过去 24 小时内已提取过的条目，返回 (保留行, 跳过数)。"""
    kept, dropped = [], 0
    for line in lines:
        _, title, url, _ = parse_markdown_link(line)
        if issue_memory_key(title, url) in memory:
            dropped += 1
            continue
        kept.append(line)
    return kept, dropped


def record_issued_lines(lines, memory):
    """v1.25: 将本次进入摘要的条目记入记忆（以提取时的原始标题为文本键）。"""
    now = time.time()
    for line in lines:
        _, title, url, _ = parse_markdown_link(line)
        memory[issue_memory_key(title, url)] = now


def save_issue_memory(memory):
    """v1.25: 原子写入记忆文件；写入失败不阻断主流程。"""
    try:
        tmp_path = ISSUED_MEMORY_PATH + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as fh:
            json.dump(memory, fh, ensure_ascii=False, indent=1, sort_keys=True)
        os.replace(tmp_path, ISSUED_MEMORY_PATH)
    except OSError as exc:
        print(f"Warning: failed to update issue memory file: {exc}")


def is_primarily_english(text):
    if not text:
        return False
    clean = re.sub(r"\[(.*?)\]\(.*?\)", r"\1", text)
    clean = re.sub(r"[-`*#_~]", "", clean).strip()
    if not clean:
        return False
    ascii_count = sum(1 for char in clean if ord(char) < 128)
    return ascii_count / len(clean) > 0.8


def translation_prompt(texts):
    lines = "\n".join(f"{index + 1}. {text}" for index, text in enumerate(texts))
    return (
        "Translate the following news headlines to Chinese. Maintain the original meaning, "
        "use concise professional wording for a technology briefing, and output exactly one "
        "translation per line in the same order. Do not add numbering, bullets, commentary, "
        "or blank lines.\n\n"
        f"{lines}"
    )


def parse_translation_lines(content, expected_count):
    results = []
    for line in content.strip().splitlines():
        cleaned = re.sub(r"^\d+\.\s*", "", line.strip())
        cleaned = re.sub(r"\*\*", "", cleaned).lstrip("- ").lstrip("• ").strip()
        if cleaned:
            results.append(cleaned)
    if len(results) != expected_count:
        raise RuntimeError(f"Translation count mismatch: sent {expected_count}, got {len(results)}")
    return results


def translate_batch_gemini(api_key, model_name, texts):
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(
        translation_prompt(texts),
        generation_config={"temperature": 0.2, "top_p": 1, "top_k": 1, "max_output_tokens": 8192},
        safety_settings=[
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
        ],
        request_options={"timeout": REQUEST_TIMEOUT_SECONDS},
    )
    return parse_translation_lines(response.text or "", len(texts))


def is_glm_refusal(text):
    normalized = re.sub(r"\s+", " ", (text or "").strip().lower())
    return any(marker.lower() in normalized for marker in GLM_REFUSAL_MARKERS)


def preserve_glm_refusals(source_texts, translations):
    """GLM 对单个受限条目拒绝时保留英语原文，而不是写入拒绝提示。"""
    completed = []
    for source, translated in zip(source_texts, translations):
        if not translated.strip() or is_glm_refusal(translated):
            print("  GLM returned a refusal for one title; preserving the English original.")
            completed.append(source)
        else:
            completed.append(translated)
    return completed


def translate_batch_glm(api_key, model_name, texts):
    """通过官方 HTTP API 调用 GLM；安全拒答交给回退链路并始终保留源标题。"""
    payload = json.dumps(
        {
            "model": model_name,
            "messages": [{"role": "user", "content": translation_prompt(texts)}],
            "temperature": 0.2,
            "max_tokens": 8192,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        GLM_API_URL,
        data=payload,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            data = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            response_text = exc.read().decode("utf-8", errors="replace")
        except OSError:
            response_text = ""
        if is_glm_refusal(response_text):
            raise GLMContentSafetyRefusal("GLM content-safety refusal") from exc
        raise
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError("GLM response missing translated content") from exc
    translations = parse_translation_lines(content or "", len(texts))
    return preserve_glm_refusals(texts, translations)


def translate_batch_google_free(texts):
    results = []
    for text in texts:
        request_url = (
            "https://translate.googleapis.com/translate_a/single?client=gtx&sl=en&tl=zh&dt=t&q="
            f"{urllib.parse.quote(text)}"
        )
        request = urllib.request.Request(request_url, headers={"User-Agent": "Mozilla/5.0"})
        last_error = None
        for attempt in range(ENGINE_RETRIES):
            try:
                with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                    data = json.loads(response.read().decode("utf-8"))
                translated = "".join(segment[0] for segment in data[0] if segment[0]).strip()
                if not translated:
                    raise RuntimeError("empty Google translation")
                results.append(translated)
                break
            except Exception as exc:
                last_error = exc
                if attempt + 1 < ENGINE_RETRIES:
                    time.sleep(2 ** attempt)
        else:
            raise RuntimeError("Google Free Translate request failed") from last_error
        time.sleep(GOOGLE_ITEM_DELAY_SECONDS)
    return results


def configured_engines(requested_engine, gemini_key):
    available = {
        "gemini": (gemini_key, GEMINI_MODEL),
        "glm": (GLM_API_KEY, GLM_MODEL),
        "google_free": ("", ""),
    }
    if requested_engine != "auto":
        return [(requested_engine, *available[requested_engine])]
    engines = []
    if gemini_key:
        engines.append(("gemini", *available["gemini"]))
    if GLM_API_KEY:
        engines.append(("glm", *available["glm"]))
    engines.append(("google_free", "", ""))
    return engines


def call_engine(engine_name, api_key, model_name, texts):
    if engine_name == "gemini":
        return translate_batch_gemini(api_key, model_name, texts)
    if engine_name == "glm":
        return translate_batch_glm(api_key, model_name, texts)
    if engine_name == "google_free":
        return translate_batch_google_free(texts)
    raise RuntimeError(f"Unknown translation engine: {engine_name}")


def translate_with_fallback(texts, engines, active_index):
    """成功后沿用引擎；某引擎反复失败则降级到下一引擎，不丢弃任何标题。"""
    for engine_index in range(active_index, len(engines)):
        engine_name, api_key, model_name = engines[engine_index]
        for attempt in range(ENGINE_RETRIES):
            try:
                if attempt:
                    time.sleep(2 ** attempt)
                print(f"Translating {len(texts)} titles with {engine_name} (attempt {attempt + 1}/{ENGINE_RETRIES})...")
                return call_engine(engine_name, api_key, model_name, texts), engine_index, False
            except GLMContentSafetyRefusal:
                print("  GLM content-safety refusal detected; trying the next engine without dropping English source titles.")
            except Exception as exc:
                print(f"  {engine_name} failed: {type(exc).__name__}")
        if engine_index + 1 < len(engines):
            print(f"  Falling back from {engine_name} to {engines[engine_index + 1][0]}...")

    print("  All translation engines failed; preserving original titles so the output artifact is still complete.")
    return list(texts), len(engines) - 1, True


def parse_money_value(text):
    lowered = text.lower()
    usd_match = re.search(r"\$\s*(\d+(?:\.\d+)?)\s*([mbk]?)", lowered)
    if usd_match:
        multiplier = {"k": 1_000, "m": 1_000_000, "b": 1_000_000_000}.get(usd_match.group(2), 1)
        return True, float(usd_match.group(1)) * multiplier * 7.2
    cny_match = re.search(r"(\d+(?:\.\d+)?)\s*(亿|万)", lowered)
    if cny_match:
        return True, float(cny_match.group(1)) * (100_000_000 if cny_match.group(2) == "亿" else 10_000)
    text_match = re.search(r"(\d+(?:\.\d+)?)\s*(million|billion)", lowered)
    if text_match:
        return True, float(text_match.group(1)) * (1_000_000 if text_match.group(2) == "million" else 1_000_000_000) * 7.2
    return False, 0.0


def classify_and_sort_items(items):
    investment_items = []
    buckets = {name: [] for name in PRIORITY_ORDER}
    unclassified = []
    source_pattern = re.compile(r"\s*\([^)]*?\)$", re.IGNORECASE)
    investment_keywords = ["融资", "获投", "筹资", "募资", "投资", "raised", "funding", "financing", "series a", "series b", "seed round", "invest"]

    for item in items:
        normalized = item if item.startswith(("- ", "• ")) else "- " + item
        _, title, _, _ = parse_markdown_link(normalized)
        lowered = title.lower()
        has_money, money_value = parse_money_value(title)
        if has_money and any(keyword in lowered for keyword in investment_keywords):
            investment_items.append((money_value, normalized))
            continue

        comparable = source_pattern.sub("", title).lower()
        for company in PRIORITY_ORDER:
            if any(keyword.lower() in comparable for keyword in COMPANY_MAP[company]):
                buckets[company].append(normalized)
                break
        else:
            unclassified.append(normalized)

    output = [item for _, item in sorted(investment_items, key=lambda pair: pair[0], reverse=True)]
    if output:
        output.append("")
    for company in PRIORITY_ORDER:
        if buckets[company]:
            try:
                output.extend(sorted(buckets[company], key=locale.strxfrm))
            except Exception:
                output.extend(sorted(buckets[company]))
            output.append("")
    if unclassified:
        try:
            output.extend(sorted(unclassified, key=locale.strxfrm))
        except Exception:
            output.extend(sorted(unclassified))
    while output and not output[-1]:
        output.pop()
    return output


def next_output_path():
    """生成不与现有摘要冲突的时间戳 Markdown 文件名。"""
    candidate_time = datetime.datetime.now().replace(microsecond=0)
    while True:
        candidate = os.path.join(SCRIPT_DIR, f"{candidate_time.strftime('%Y%m%d-%H%M%S')}.md")
        if not os.path.exists(candidate):
            return candidate
        candidate_time += datetime.timedelta(seconds=1)


def write_summary_atomically(output_path, header_lines, output_lines, footer_lines):
    temporary_path = output_path + ".tmp"
    try:
        with open(temporary_path, "w", encoding="utf-8") as file:
            if header_lines:
                file.writelines(header_lines)
                if not header_lines[-1].endswith("\n"):
                    file.write("\n")
            for line in output_lines:
                file.write(line + "\n")
            if footer_lines:
                if output_lines and output_lines[-1].strip():
                    file.write("\n")
                file.writelines(footer_lines)
        os.replace(temporary_path, output_path)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


def remove_superseded_summaries(summary_paths, output_path):
    removed = 0
    output_absolute = os.path.abspath(output_path)
    for path in summary_paths:
        if os.path.abspath(path) == output_absolute:
            continue
        try:
            os.unlink(path)
            removed += 1
        except OSError as exc:
            print(f"Warning: could not remove superseded summary {os.path.basename(path)}: {type(exc).__name__}")
    return removed


def main():
    parser = argparse.ArgumentParser(description="Merge, deduplicate, translate and retain one cumulative RSS summary.")
    parser.add_argument("files", nargs="*", help="可选的 RSS Markdown 文件；省略时只收敛根目录积压摘要")
    parser.add_argument("-api", default=None, help="Gemini API key override")
    parser.add_argument("-engine", choices=["gemini", "glm", "google_free", "auto"], default="auto")
    args = parser.parse_args()

    load_dotenv()
    gemini_key = args.api.strip() if args.api else GEMINI_API_KEY
    engines = configured_engines(args.engine, gemini_key)
    print("Translation engine order: " + " -> ".join(engine[0] for engine in engines))

    pending_summaries = find_pending_summary_files()
    input_files = collect_input_files(args.files)
    if pending_summaries:
        print(f"Pending summaries detected: {len(pending_summaries)}; merging them before new RSS input.")
    if not input_files:
        raise RuntimeError("No readable RSS or pending summary files were found")

    all_lines, first_header, first_footer = [], [], []
    for index, file_path in enumerate(input_files):
        parsed = parse_news_list_file(file_path)
        if not parsed:
            continue
        header, content, footer = parsed
        if index == 0:
            first_header, first_footer = header, footer
        all_lines.extend(content)

    print(f"Total content lines loaded across all inputs: {len(all_lines)}")
    unique_lines = deduplicate_content_lines(all_lines)
    print(f"Total unique lines loaded: {len(unique_lines)}")
    issue_memory = load_issue_memory()
    unique_lines, issued_dropped = filter_recently_issued(unique_lines, issue_memory)
    if issued_dropped:
        print(f"Past-{ISSUED_MEMORY_TTL_HOURS}h already-issued duplicates removed: {issued_dropped}")
    if not unique_lines:
        print("All entries were already issued within the past 24 hours; no new summary needed.")
        save_issue_memory(issue_memory)
        return
    chinese_lines, english_lines = [], []
    for line in unique_lines:
        if is_primarily_english(line):
            english_lines.append(line)
        else:
            chinese_lines.append(line)
    print(f"Chinese lines: {len(chinese_lines)}, English lines: {len(english_lines)}")

    translated_lines = []
    active_engine_index = 0
    degraded = False
    for start in range(0, len(english_lines), TRANSLATION_BATCH_SIZE):
        batch = english_lines[start:start + TRANSLATION_BATCH_SIZE]
        metadata, titles = [], []
        for line in batch:
            _, title, url, suffix = parse_markdown_link(line)
            titles.append(title)
            metadata.append((url, suffix))
        translations, active_engine_index, batch_degraded = translate_with_fallback(titles, engines, active_engine_index)
        degraded = degraded or batch_degraded
        for translated_title, (url, suffix) in zip(translations, metadata):
            translated_lines.append(f"- [{translated_title}]({url}){suffix}" if url else f"- {translated_title}{suffix}")

    output_lines = classify_and_sort_items(chinese_lines + translated_lines)
    output_path = next_output_path()
    write_summary_atomically(output_path, first_header, output_lines, first_footer)
    record_issued_lines(unique_lines, issue_memory)
    save_issue_memory(issue_memory)
    print(f"Issue memory now holds {len(issue_memory)} key(s) within the past {ISSUED_MEMORY_TTL_HOURS}h.")
    removed = remove_superseded_summaries(pending_summaries, output_path)

    if degraded:
        print("Warning: one or more batches retained the original title after all translation engines failed.")
    if removed:
        print(f"Removed {removed} superseded pending summary file(s).")
    print(f"Process complete. Saved to: {output_path}")


if __name__ == "__main__":
    main()
