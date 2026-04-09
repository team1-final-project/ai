from openai import OpenAI
import pandas as pd

client = OpenAI()

df = pd.read_csv("merged_result.csv", encoding="utf-8-sig")
catalog_names = df["good_name"].unique()

def to_user_keywords(name):
    prompt = f"""
    다음 상품명을 실제 사용자가 검색할 법한 키워드로 변환해줘.
    - 브랜드명은 생략
    - 중량, 수량은 '박스', '대용량', '묶음' 같은 표현으로 단순화
    - 짧고 직관적인 검색어 여러 개 제안
    상품명: {name}
    """
    response = client.chat.completions.create(
        model="gpt-4o-mini",   # 최신 모델명
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

# 샘플 실행
for name in catalog_names[:5]:
    print(name, "→", to_user_keywords(name))