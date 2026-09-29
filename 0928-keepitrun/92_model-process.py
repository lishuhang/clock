#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os
import re
import json
import time
import argparse
from typing import List, Dict

# v1.14: 加载 .env
def _load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
    if not os.path.isfile(env_path): return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line: continue
                key, _, val = line.partition("=")
                key = key.strip(); val = val.strip().strip('"').strip("'")
                if key and key not in os.environ: os.environ[key] = val
    except OSError: pass

_load_dotenv()


# 尝试导入大模型SDK
try:
    import google.generativeai as genai
    HAS_GEMINI = True
except ImportError:
    HAS_GEMINI = False

try:
    from zhipuai import ZhipuAI
    HAS_ZHIPU = True
except ImportError:
    HAS_ZHIPU = False

# ================= 配置区 =================
# 智谱 API Key (Fallback 默认使用)
ZHIPU_API_KEY = os.environ.get("GLM_API_KEY", "")  # v1.14: 从 .env 读取
# v1.26: 完全免费档最新模型（docs.bigmodel.cn 官方定价：输入/输出均免费，200K 上下文）
ZHIPU_MODEL = "glm-4.7-flash"

# Gemini 配置 (如果你通过命令行传入了 API Key 则使用)
# v1.26: 免费档最新模型（ai.google.dev 官方定价：Free of charge 档）
GEMINI_MODEL = "gemini-3.8-flash"

# 批处理大小（避免一次性传入太多导致小模型遗忘或JSON截断）
BATCH_SIZE = 40
# ==========================================

# 解决 Windows 命令行字符编码问题
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        import codecs
        sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())
        sys.stderr = codecs.getwriter("utf-8")(sys.stderr.detach())

def parse_markdown_link(line):
    """提取行中的纯文本标题，用于发给大模型分析，保留完整行用于重建"""
    match = re.match(r'^([-•]\s*)\[(.*?)\]\((.*?)\)(.*)$', line)
    if match:
        return match.group(2).strip() # 纯标题
    
    match_no_link = re.match(r'^([-•]\s*)(.*)$', line)
    if match_no_link:
        return match_no_link.group(2).strip()
        
    return line.strip()

def call_llm(sys_prompt: str, user_prompt: str, gemini_api_key: str = None) -> str:
    """统一的 LLM 调用接口，优先 Gemini，失败或无Key则 Fallback 到智谱"""
    result = None
    
    # 尝试使用 Gemini
    if HAS_GEMINI and gemini_api_key:
        try:
            genai.configure(api_key=gemini_api_key)
            model = genai.GenerativeModel(GEMINI_MODEL)
            # Gemini system prompt 可以合并到 user_prompt，或者使用 system_instruction
            full_prompt = f"System Instruction:\n{sys_prompt}\n\nUser Input:\n{user_prompt}"
            response = model.generate_content(
                full_prompt,
                generation_config={"temperature": 0.1}
            )
            result = response.text
            return result
        except Exception as e:
            print(f"[Warn] Gemini 调用失败: {e}，正在 Fallback 到智谱 GLM Flash...")
    
    # Fallback 使用智谱 GLM Flash
    if HAS_ZHIPU:
        try:
            client = ZhipuAI(api_key=ZHIPU_API_KEY)
            response = client.chat.completions.create(
                model=ZHIPU_MODEL,
                messages=[
                    {"role": "system", "content": sys_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.1
            )
            result = response.choices[0].message.content
            return result
        except Exception as e:
            print(f"[Error] 智谱调用也失败了: {e}")
            return ""
            
    print("[Error] 缺少大模型 SDK。请安装 google-generativeai 或 zhipuai")
    return ""

def extract_json(text: str):
    """从 LLM 返回的文本中提取 JSON"""
    if not text:
        return None
    try:
        # 尝试匹配 ```json ... ```
        match = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL | re.IGNORECASE)
        if match:
            return json.loads(match.group(1))
        # 尝试匹配 [...] 或 {...}
        match = re.search(r'(\[.*\]|\{.*\})', text, re.DOTALL)
        if match:
            return json.loads(match.group(1))
        # 兜底直接解析
        return json.loads(text)
    except Exception as e:
        print(f"[Warn] JSON 解析失败: {e}\n模型返回原文:\n{text[:200]}...")
        return None

def categorize_batch(items_dict: Dict[int, str], gemini_api_key: str = None) -> List[Dict]:
    """对一批标题进行分类"""
    sys_prompt = """You are an expert tech news editor. Your task is to filter a list of news headlines for a professional daily briefing focused on AI, Semiconductors, Enterprise Tech, and Big Tech companies.
    
Categorize each headline into one of the following:
1. "KEEP": Core tech news (e.g., product launches, AI breakthroughs, major funding, corporate strategies).
2. "IRRELEVANT": E-commerce deals, discounts, consumer appliance reviews (e.g., coffee makers, washing machines), entertainment, gaming hardware sales, or general lifestyle news.
3. "REVIEW": Clickbait (e.g., "shocking secret"), vague metaphorical titles (e.g., "The wall fell"), forum opinions/questions, or long interview quotes that aren't hard news.

Output format MUST be strict JSON array:
[
  {"id": ID_NUMBER, "category": "KEEP|IRRELEVANT|REVIEW"}
]"""

    user_prompt = ""
    for idx, title in items_dict.items():
        user_prompt += f"[{idx}] {title}\n"

    retries = 2
    for _ in range(retries):
        resp_text = call_llm(sys_prompt, user_prompt, gemini_api_key)
        parsed_json = extract_json(resp_text)
        if parsed_json and isinstance(parsed_json, list):
            return parsed_json
        time.sleep(1)
        
    # 如果全失败，默认全部 REVIEW 保底
    return [{"id": k, "category": "REVIEW"} for k in items_dict.keys()]

def deduplicate_keep_items(keep_items: Dict[int, str], gemini_api_key: str = None) -> List[List[int]]:
    """全局去重：寻找报道同一事件的重复新闻"""
    if not keep_items:
        return []
        
    sys_prompt = """You are an expert tech news editor. Below is a list of tech news headlines. Many headlines report on the EXACT SAME news event from different sources or with different phrasings.
Your task is to group the IDs of headlines that cover the SAME event.

Output a JSON array of arrays. Each inner array contains the IDs (as integers) of headlines about the same event. 
If a headline is unique and doesn't share an event with others, it should be in an array by itself.

Example output strictly in JSON:
[[1, 5], [2], [3, 4, 6]]"""

    user_prompt = ""
    for idx, title in keep_items.items():
        user_prompt += f"[{idx}] {title}\n"
        
    retries = 2
    for _ in range(retries):
        resp_text = call_llm(sys_prompt, user_prompt, gemini_api_key)
        parsed_json = extract_json(resp_text)
        if parsed_json and isinstance(parsed_json, list):
            return parsed_json
        time.sleep(1)
        
    # 如果全失败，默认各自独立
    return [[k] for k in keep_items.keys()]

def main():
    parser = argparse.ArgumentParser(description="Use LLM to clean, filter and deduplicate RSS markdown files.")
    parser.add_argument('file', help='Input markdown file')
    parser.add_argument('-api', help='Google Gemini API Key (Optional, uses Zhipu by default)', default=None)
    args = parser.parse_args()

    input_path = args.file
    if not os.path.exists(input_path):
        print(f"[Error] 找不到文件: {input_path}")
        sys.exit(1)

    # 1. 解析 Markdown 文件
    header_lines = []
    content_lines = []
    footer_lines = []
    in_content = False

    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("- ") or stripped.startswith("• "):
                in_content = True
                content_lines.append(stripped)
            else:
                if not in_content:
                    header_lines.append(stripped)
                else:
                    footer_lines.append(stripped)

    print(f"[*] 共读取到 {len(content_lines)} 条新闻待处理...")

    # 2. 映射 ID 到完整行和纯标题
    id_to_line = {}
    id_to_title = {}
    for idx, line in enumerate(content_lines):
        id_to_line[idx] = line
        id_to_title[idx] = parse_markdown_link(line)

    # 3. 分批执行分类
    print("[*] 第一阶段：正在执行垃圾信息过滤与分类...")
    categories = {"KEEP": [], "IRRELEVANT": [], "REVIEW": []}
    
    items_list = list(id_to_title.items())
    for i in range(0, len(items_list), BATCH_SIZE):
        batch = dict(items_list[i:i+BATCH_SIZE])
        print(f"    - 正在处理 {i} 到 {min(i+BATCH_SIZE, len(items_list))} 条...")
        results = categorize_batch(batch, args.api)
        
        # 将结果归类
        for item in results:
            try:
                item_id = int(item.get("id"))
                cat = item.get("category", "REVIEW").upper()
                if cat not in categories: cat = "REVIEW"
                categories[cat].append(item_id)
            except Exception as e:
                pass # 忽略解析错误的个别行

    # 确保没有遗漏的 ID
    processed_ids = set(categories["KEEP"] + categories["IRRELEVANT"] + categories["REVIEW"])
    for idx in id_to_title.keys():
        if idx not in processed_ids:
            categories["REVIEW"].append(idx)

    print(f"[*] 分类完成: KEEP({len(categories['KEEP'])}), REVIEW({len(categories['REVIEW'])}), IRRELEVANT({len(categories['IRRELEVANT'])})")

    # 4. 全局去重 (针对 KEEP 类)
    print("[*] 第二阶段：正在对核心新闻进行交叉比对去重...")
    keep_items_dict = {idx: id_to_title[idx] for idx in categories["KEEP"]}
    
    unique_keeps = []
    duplicates = []
    
    if keep_items_dict:
        clusters = deduplicate_keep_items(keep_items_dict, args.api)
        # 解析聚类结果
        covered_keep_ids = set()
        for cluster in clusters:
            if not cluster: continue
            # 确保传入的是整型，并过滤出真实存在的 ID
            valid_cluster = [int(x) for x in cluster if int(x) in keep_items_dict]
            if not valid_cluster: continue
            
            # 选第一个作为主新闻保留
            main_id = valid_cluster[0]
            unique_keeps.append(main_id)
            covered_keep_ids.add(main_id)
            
            # 其余的作为重复新闻
            for dup_id in valid_cluster[1:]:
                duplicates.append(dup_id)
                covered_keep_ids.add(dup_id)
                
        # 找回可能被 LLM 漏掉的 ID
        for idx in categories["KEEP"]:
            if idx not in covered_keep_ids:
                unique_keeps.append(idx)

    # 5. 生成最终 Markdown 输出
    filename, ext = os.path.splitext(input_path)
    output_path = f"{filename}_processed{ext}"
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 写回头部
        for line in header_lines:
            f.write(line + "\n")
        if header_lines: f.write("\n")
            
        # 写入核心早报 (KEEP 去重后)
        f.write("## 📌 核心早报 (已筛选去重)\n\n")
        if unique_keeps:
            for idx in unique_keeps:
                f.write(id_to_line[idx] + "\n")
        else:
            f.write("无。\n")
        f.write("\n")
            
        # 写入待核查
        if categories["REVIEW"]:
            f.write("## 🔍 待核查 / 深度长文 / 社区讨论\n\n")
            for idx in categories["REVIEW"]:
                f.write(id_to_line[idx] + "\n")
            f.write("\n")
            
        # 写入重复项
        if duplicates:
            f.write("## 🗂️ 重复 / 相似报道\n\n")
            for idx in duplicates:
                f.write(id_to_line[idx] + "\n")
            f.write("\n")
            
        # 写入不相关
        if categories["IRRELEVANT"]:
            f.write("## 🗑️ 不相关 / 广告带货 / 生活泛娱乐\n\n")
            for idx in categories["IRRELEVANT"]:
                f.write(id_to_line[idx] + "\n")
            f.write("\n")

        # 写回尾部
        for line in footer_lines:
            f.write(line + "\n")

    print(f"[√] 处理完成！去重后核心早报剩余: {len(unique_keeps)} 条。")
    print(f"[√] 文件已保存至: {output_path}")

if __name__ == "__main__":
    main()