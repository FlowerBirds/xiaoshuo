import edge_tts
import asyncio

async def text_to_speech(text, output_file, voice="zh-CN-XiaoxiaoNeural"):
    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(output_file)

if __name__ == "__main__":
    text = "你好，这是一个使用 edge-tts 生成的语音示例。"
    output_file = "output.mp3"
    asyncio.run(text_to_speech(text, output_file))
    print(f"语音已保存到 {output_file}")