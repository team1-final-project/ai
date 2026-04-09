import time
import pandas as pd
from utils.naver_shoppinginsite_search import fetch_category_keyword_data
from utils.naver_searchad_relkeyword import fetch_relkwdstat   # ✅ RelKwdStat 호출 모듈

INPUT_PATH = "./data/processed_keyword.csv"
OUTPUT_PATH = "./data/train_dataset.csv"

# ✅ 데이터 로드 및 기본 처리
df = pd.read_csv(INPUT_PATH)
df["collect_day"] = pd.to_datetime(df["collect_day"])
df["weekday"] = df["collect_day"].dt.weekday

# ✅ 원본 컬럼 정제 (월평균클릭수도 정제는 하지만 이후 계산에는 사용하지 않음)
for col in ["일간검색수", "월평균클릭수", "월간검색수"]:
    if col in df.columns:
        df[col] = (
            df[col]
            .astype(str)
            .str.replace(",", "")
            .astype(float)
        )

results = []

# ✅ good_id 단위로 처리
for good_id, group in df.groupby("good_id"):
    print(f"🔍 good_id: {good_id} → API 데이터 수집 중...")

    keyword = group["검색키워드"].iloc[0]

    # ✅ 1. RelKwdStat API 먼저 호출 → 최근4주클릭수평균 확보
    rel_data = fetch_relkwdstat([keyword])
    if rel_data:
        recent_4weeks_click_avg = rel_data[0].get("최근4주클릭수평균", 0)
    else:
        recent_4weeks_click_avg = 0

    # ✅ 2. ShoppingInsight API 호출 (기간별 클릭량 데이터)
    start_date = group["collect_day"].min().strftime("%Y-%m-%d")
    end_date = pd.Timestamp.today().strftime("%Y-%m-%d")

    try:
        search_df = fetch_category_keyword_data(
            start_date=start_date,
            end_date=end_date,
            category="50000006",   # 식품 카테고리 코드
            keyword=keyword
        )
    except Exception as e:
        print(f"⚠️ API 호출 실패: {e}")
        search_df = pd.DataFrame(columns=["날짜", "클릭량"])

    print(f"✅ good_id: {good_id} → 병합 중...")

    if not search_df.empty:
        search_df["날짜"] = pd.to_datetime(search_df["날짜"])
    else:
        search_df = pd.DataFrame({"날짜": group["collect_day"], "클릭량": [0]*len(group)})

    merged = group.merge(search_df, left_on="collect_day", right_on="날짜", how="left")

    # ✅ 3. 지난달 클릭량 합계 계산
    if not search_df.empty and "클릭량" in search_df.columns and "날짜" in search_df.columns:
        print(f"✅ good_id: {good_id} → 클릭량 데이터 처리 중...")
        search_df["날짜"] = pd.to_datetime(search_df["날짜"])
        
        today = pd.Timestamp.today()
        start_date = today - pd.DateOffset(months=1)
        end_date = today
        
        prev_month_df = search_df[
            (search_df["날짜"] >= start_date) & (search_df["날짜"] < end_date)
        ]
        
        prev_month_sum = prev_month_df["클릭량"].sum()
    else:
        prev_month_sum = 0

    merged["지난달클릭량합계"] = prev_month_sum

    # ✅ 4. 최근4주클릭수평균 기반 계산 (30일 총합 환산)
    recent_4weeks_click_total = recent_4weeks_click_avg * 30

    merged["최근4주클릭수평균"] = recent_4weeks_click_avg
    merged["최근4주클릭수총합(30일기준)"] = recent_4weeks_click_total

    merged["최근4주클릭수_비율"] = merged.apply(
        lambda row: (recent_4weeks_click_total / prev_month_sum) if prev_month_sum > 0 else 0,
        axis=1
    )

     # ✅ 추정일간클릭수 계산
    merged["추정일간클릭수"] = merged["최근4주클릭수_비율"] * merged["클릭량"].fillna(0)

    results.append(merged)
    time.sleep(0.3)

# ✅ 최종 결과 저장
final_df = pd.concat(results, ignore_index=True)
final_df.to_csv(OUTPUT_PATH, index=False, encoding="utf-8-sig")
print(f"✅ 최종 결과 저장 완료 → {OUTPUT_PATH}")