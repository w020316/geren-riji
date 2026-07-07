from functools import lru_cache
from openai import OpenAI
from config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL, LLM_TIMEOUT, LLM_MAX_TOKENS


@lru_cache(maxsize=1)
def _get_client() -> OpenAI:
    """复用 OpenAI 客户端，避免每次调用重建连接。"""
    return OpenAI(
        api_key=LLM_API_KEY or "missing",
        base_url=LLM_BASE_URL,
        timeout=LLM_TIMEOUT,
    )


def call_llm(system_prompt: str, user_message: str, temperature: float = 0.7,
             max_tokens: int | None = None) -> str:
    """调用 LLM，返回文本内容。失败时抛出异常由调用方处理。"""
    client = _get_client()
    response = client.chat.completions.create(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        temperature=temperature,
        max_tokens=max_tokens or LLM_MAX_TOKENS,
    )
    return response.choices[0].message.content
