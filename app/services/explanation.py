from openai import OpenAI
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def explain_price_change(reason: str, tone: str = "friendly") -> str:
    prompt = f"""
    다음 가격 변동 사유를 쇼핑몰 사용자에게 { '친근하고 이해하기 쉽게' if tone=='friendly' else '공식적이고 간결하게' } 설명해줘.
    사유: "{reason}"
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",  # 최신 모델명 (예: gpt-4o-mini, gpt-4.1 등)
        messages=[{"role": "user", "content": prompt}],
        max_tokens=100,
        temperature=0.7
    )

    return response.choices[0].message.content.strip()