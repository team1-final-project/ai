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
    pum_id: str   # 이제 pum_id를 직접 받음

# ===== 모델 및 컬럼 구조 불러오기 =====
gam_package = joblib.load("./models/gam_model.pkl")
gam = gam_package["model"]
X_columns = gam_package["columns"]
goodid_encoder = gam_package["goodid_encoder"]  # 저장된 인코더 불러오기

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
            category="",  # category_code는 더 이상 필요 없음
            keyword=keyword
        )
    except Exception as e:
        print(f"⚠️ API 호출 실패: {e}")
        search_df = pd.DataFrame(columns=["날짜","클릭량"])

    prev_sum = search_df["클릭량"].sum() if not search_df.empty else 0
    total_clicks = recent_avg * 30
    return (total_clicks / prev_sum) if prev_sum > 0 else 0

def build_test_df(price: float, pum_id: str, keyword: str, target_date: datetime.date) -> pd.DataFrame:
    """예측용 데이터프레임 생성"""
    weekday = target_date.weekday()  # 월=0, 화=1 ... 일=6
    pum_id_enc = goodid_encoder.transform([pum_id])[0]

    test_data = {
        "1개당가격": price,
        "최근4주클릭수_비율": get_recent_ratio(keyword),
        "weekday": weekday,
        "pum_id_enc": pum_id_enc
    }
    df = pd.DataFrame([test_data])
    return df.reindex(columns=X_columns, fill_value=0)

@app.post("/predict_week")
def predict_week(req: PredictRequest):
    results = []
    for offset in range(7):  # 오늘 포함 7일
        target_date = datetime.date.today() + datetime.timedelta(days=offset)
        test_df = build_test_df(req.price, req.pum_id, req.keyword, target_date)
        pred_clicks = max(0, gam.predict(test_df)[0])  # 음수값은 0으로 잘라내기
        results.append({
            "예측일": str(target_date),
            "예측요일": target_date.strftime("%A"),
            "예측된 클릭수": pred_clicks
        })
    return {"keyword": req.keyword, "pum_id": req.pum_id, "results": results}