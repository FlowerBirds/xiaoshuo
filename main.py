import os
import sys
import requests
from bs4 import BeautifulSoup
import edge_tts
import asyncio

def fetch_chapter(chapter_num, save_dir="books"):
    base_url = "https://www.bqg5.com/0_785/"
    html_name = f"{188686 + chapter_num - 70}.html"  # 修正章节号偏移
    url = base_url + html_name
    # 检查是否已存在对应章节的txt文件
    if os.path.exists(save_dir):
        for fname in os.listdir(save_dir):
            if fname.startswith(f"第{chapter_num}章"):
                print(f"已存在: {fname}")
                return os.path.join(save_dir, fname)
    try:
        resp = requests.get(url, timeout=10, verify=False)
        resp.encoding = resp.apparent_encoding
        if resp.status_code != 200:
            print(f"Failed to fetch {url}: {resp.status_code}")
            return None

        soup = BeautifulSoup(resp.text, "html.parser")
        title = soup.find("div", class_="bookname").find("h1").get_text(strip=True)
        # 去掉标题中的“（求订阅）”
        title = title.replace("（求订阅）", "").replace("(求订阅)", "").strip()
        content_div = soup.find("div", id="content")
        if not content_div:
            print(f"Content not found for chapter {chapter_num}")
            return None
        content = content_div.get_text(separator="\n", strip=True).replace('\xa0', ' ').replace('&nbsp;', ' ')
        # 去掉内容中的“（求订阅）”字样
        content = content.replace("（求订阅）", "").replace("(求订阅)", "").strip()

        os.makedirs(save_dir, exist_ok=True)
        filename = os.path.join(save_dir, f"{title}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(title + "\n\n" + content)
        print(f"Downloaded: {title}")
        return filename

    except Exception as e:
        print(f"Error fetching chapter {chapter_num}: {e}")
        return None

if __name__ == "__main__":
    if len(sys.argv) != 2 or not sys.argv[1].isdigit():
        print("用法: python main.py 章节数(如120)")
        sys.exit(1)
    chapter_num = int(sys.argv[1])
    filename = fetch_chapter(chapter_num)
    if filename:
        mp3_dir = "mp3"
        os.makedirs(mp3_dir, exist_ok=True)
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
        mp3_filename = os.path.splitext(os.path.basename(filename))[0] + ".mp3"
        mp3_path = os.path.join(mp3_dir, mp3_filename)
        tts = edge_tts.Communicate(text, voice="zh-CN-XiaoxiaoNeural")
        with open(mp3_path, "wb") as out_mp3:
            async def save_mp3():
                async for chunk in tts.stream():
                    if chunk["type"] == "audio":
                        out_mp3.write(chunk["data"])
            asyncio.run(save_mp3())