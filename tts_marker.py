
import os
import requests
from bs4 import BeautifulSoup
import json
import edge_tts
import asyncio
import aiofiles
import logging

logger = logging.getLogger(__name__)

def fetch_next_chapter(save_dir="books"):
    # 读取起始章节号
    start_chapter = 1
    start_file = os.path.join("start.txt")
    if os.path.exists(start_file):
        with open(start_file, "r", encoding="utf-8") as sf:
            try:
                start_chapter = int(sf.read().strip())
            except Exception:
                start_chapter = 1
    books_json = os.path.join("books.json")
    contents_file = os.path.join("contents.txt")

    # 仅用 books.json 判断已下载章节
    if os.path.exists(books_json):
        with open(books_json, "r", encoding="utf-8") as f:
            books_map = json.load(f)
    else:
        books_map = {}
    downloaded = set(books_map.keys())

    # 读取目录
    with open(contents_file, "r", encoding="utf-8") as f:
        lines = [line.strip() for line in f if line.strip()]

    # 遍历目录，找到第一个未下载且大于等于起始章节的章节
    import re
    chapter_num_pattern = re.compile(r'第(\d+)章')
    for line in lines:
        if ' ' not in line:
            continue
        url, title = line.split(' ', 1)
        # 提取章节号
        match = chapter_num_pattern.search(title)
        if not match:
            continue
        chapter_num = int(match.group(1))
        if chapter_num < start_chapter:
            continue
        base_url, html_name = url.rsplit('/', 1)
        chapter_id = html_name.replace('.html', '')
        txt_name = f"{chapter_id}.txt"
        txt_path = os.path.join(save_dir, txt_name)
        if chapter_id in downloaded:
            continue

        logger.info(f"开始下载: {title}")
        # 下载两页内容，正文在id=booktxt下，每段在p元素中
        all_content = [title]
        for page in [1, 2]:
            page_url = f"{base_url}/{chapter_id}_{page}.html"
            try:
                resp = requests.get(page_url, timeout=10)
                resp.encoding = resp.apparent_encoding
                if resp.status_code != 200:
                    logger.warning(f"Failed to fetch {page_url}: {resp.status_code}")
                    continue
                soup = BeautifulSoup(resp.text, "html.parser")
                content_div = soup.find("div", id="booktxt")
                if content_div:
                    paragraphs = [p.get_text(strip=True) for p in content_div.find_all('p')]
                    content = "\n".join(paragraphs)
                else:
                    content = ""
                all_content.append(content)
            except Exception as e:
                logger.error(f"Error fetching {page_url}: {e}")
                continue

        full_content = "".join(all_content).strip()
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(full_content)

        # 更新books.json
        books_map[chapter_id] = {
            "title": title,
            "txt": txt_path,
            "html": url
        }
        with open(books_json, "w", encoding="utf-8") as f2:
            json.dump(books_map, f2, ensure_ascii=False, indent=2)


        logger.info(f"已保存: {title} {txt_name}")
        return title, txt_path

    return None, None

def generate_mp3(filename, voice="zh-CN-XiaoxiaoNeural", mp3_dir="mp3"):
    os.makedirs(mp3_dir, exist_ok=True)
    with open(filename, "r", encoding="utf-8") as f:
        text = f.read()
    mp3_filename = os.path.splitext(os.path.basename(filename))[0] + ".mp3"
    mp3_path = os.path.join(mp3_dir, mp3_filename)
    tts = edge_tts.Communicate(text, voice=voice)

    async def save_mp3():
        async with aiofiles.open(mp3_path, "wb") as out_mp3:
            async for chunk in tts.stream():
                if chunk["type"] == "audio":
                    await out_mp3.write(chunk["data"])

    # Use aiofiles for async file writing
    asyncio.run(save_mp3())

    logger.info(f"MP3已生成: {mp3_path}")

    # 更新books.json，添加mp3路径
    books_json = os.path.join("books.json")
    txt_name = os.path.basename(filename)
    if os.path.exists(books_json):
        with open(books_json, "r", encoding="utf-8") as f:
            books_map = json.load(f)
    else:
        books_map = {}
    key = os.path.splitext(txt_name)[0]
    # 更新或添加mp3路径
    if key in books_map:
        chapter = books_map[key]
        chapter["mp3"] = mp3_path

    with open(books_json, "w", encoding="utf-8") as f:
        json.dump(books_map, f, ensure_ascii=False, indent=2)

    return mp3_path


def update_chapter():
    title, txt_path = fetch_next_chapter()
    generate_mp3(txt_path)

    logger.info(f"章节《{title}》的音频已生成。")

def reload_mp3(txt, title=None):
    mp3_path = generate_mp3(txt)

    logger.info(f"章节《{title}》的音频已生成。")
    return mp3_path
