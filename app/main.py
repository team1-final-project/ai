import datetime
import pandas as pd
import joblib
from fastapi import FastAPI
from pydantic import BaseModel
from utils.naver_searchad_relkeyword import fetch_relkwdstat
from utils.naver_shoppinginsite_search import fetch_category_keyword_data

app = FastAPI()

# ===== 요청 데이터 모델 =====
class PredictRequest(BaseModel):
    keyword: str
    price: float
    good_id: str   # 이제 good_id를 직접 받음

# ===== 모델 및 컬럼 구조 불러오기 =====
gam_package = joblib.load("./models/gam_model.pkl")
gam = gam_package["model"]
X_columns = gam_package["columns"]
goodid_encoder = gam_package["goodid_encoder"]  # 저장된 인코더 불러오기

PRICE_FACTORS = [0.6, 0.8, 1.0, 1.2, 1.4]

def get_recent_ratio(keyword: str) -> float:
    """최근 4주 클릭수 비율 계산"""
    rel_data = fetch_relkwdstat([keyword])
    recent_avg = rel_data[0].get("최근4주클릭수평균", 0) if rel_data else 0

    today = pd.Timestamp.today()
    start_date, end_date = today - pd.DateOffset(days=30), today

    try:
        search_df = fetch_category_keyword_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            category="50000006",  # 식품 카테고리
            keyword=keyword
        )
    except Exception as e:
        print(f"⚠️ API 호출 실패: {e}")
        search_df = pd.DataFrame(columns=["날짜","클릭량"])

    prev_sum = search_df["클릭량"].sum() if not search_df.empty else 0
    total_clicks = recent_avg * 30
    return (total_clicks / prev_sum) if prev_sum > 0 else 0

def build_test_df(price: float, good_id: str, recent_ratio: float, target_date: datetime.date) -> pd.DataFrame:
    """예측용 데이터프레임 생성"""
    weekday = target_date.weekday()  # 월=0, 화=1 ... 일=6
    good_id_enc = goodid_encoder.transform([good_id])[0]

    test_data = {
        "discount_price": price,
        "최근4주클릭수_비율": recent_ratio,
        "weekday": weekday,
        "good_id_enc": good_id_enc
    }
    df = pd.DataFrame([test_data])
    return df.reindex(columns=X_columns, fill_value=0)

@app.post("/predict_week")
def predict_week(req: PredictRequest):
    results = []
    recent_ratio = get_recent_ratio(req.keyword)

    for offset in range(7):  # 오늘 포함 7일
        target_date = datetime.date.today() + datetime.timedelta(days=offset)
        day_result = {
            "예측일": str(target_date),
            "예측요일": target_date.strftime("%A"),
            "배율별예측": {}
        }

        for factor in PRICE_FACTORS:
            price = req.price * factor
            test_df = build_test_df(price, req.good_id, recent_ratio, target_date)

            pred_clicks = max(0, gam.predict(test_df)[0])
            day_result["배율별예측"][f"{int(factor*100)}%"] = pred_clicks

        results.append(day_result)

    return {"keyword": req.keyword, "good_id": req.good_id, "results": results}