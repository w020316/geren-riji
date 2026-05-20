from llm_client import call_llm
from datetime import datetime


def analyze_emotion(text: str) -> dict:
    system_prompt = """你是一个情绪分析专家。请分析用户输入文本中的情绪状态。
返回JSON格式，包含以下字段：
- emotion: 主要情绪（开心/悲伤/焦虑/愤怒/平静/惊喜/疲惫/感动）
- intensity: 情绪强度（1-10，10为最强）
- keywords: 情绪关键词列表
- brief_analysis: 一句话情绪分析

只返回JSON，不要其他内容。"""

    user_message = f"请分析以下文本的情绪：\n\n{text}"
    try:
        result = call_llm(system_prompt, user_message, temperature=0.3)
        import json
        clean = result.strip()
        if clean.startswith("```"):
            clean = clean.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
        return json.loads(clean)
    except Exception:
        return {
            "emotion": "平静",
            "intensity": 5,
            "keywords": [],
            "brief_analysis": "无法精确分析情绪，默认为平静"
        }


def generate_diary(user_input: str, emotion_info: dict, memories: list) -> str:
    memory_text = ""
    if memories:
        memory_items = [m["content"] for m in memories[:5]]
        memory_text = "相关历史记忆：\n" + "\n".join(f"- {m}" for m in memory_items)

    today = datetime.now()
    today_str = today.strftime("%Y年%m月%d日")
    weekday_map = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    weekday = weekday_map[today.weekday()]

    system_prompt = f"""你是一位温暖、细腻的日记撰写助手。根据用户的输入、情绪分析和相关记忆，
为用户生成一篇真挚的日记。

重要规则：
- 今天是{today_str}，{weekday}。日记中必须使用这个真实日期，禁止编造其他日期。
- 日记开头不要写日期标题，直接从正文开始。
- 以第一人称撰写
- 融入情绪分析结果，让日记有情感深度
- 适当引用历史记忆，体现连贯性
- 语言优美但不做作，真实自然
- 篇幅适中（200-500字）
- 末尾可以加一句对未来的期许或感悟"""

    user_message = f"""用户今日输入：{user_input}

情绪分析：{emotion_info.get('emotion', '平静')}（强度：{emotion_info.get('intensity', 5)}）
情绪关键词：{', '.join(emotion_info.get('keywords', []))}
{memory_text}

请为用户生成今天的日记。记住今天是{today_str}。"""

    return call_llm(system_prompt, user_message, temperature=0.8)
