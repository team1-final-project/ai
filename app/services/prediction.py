import datetime
import pandas as pd
import joblib
from utils.naver_searchad_relkeyword import fetch_relkwdstat
from utils.naver_shoppinginsite_search import fetch_category_keyword_data

# 모델 로딩
gam_package = joblib.load("./models/gam_model.pkl")
gam = gam_package["model"]
X_columns = gam_package["columns"]
goodid_encoder = gam_package["goodid_encoder"]

PRICE_FACTORS = [0.6, 0.8, 1.0, 1.2, 1.4]

def get_recent_ratio(keyword: str) -> float:
    rel_data = fetch_relkwdstat([keyword])
    recent_avg = rel_data[0].get("최근4주클릭수평균", 0) if rel_data else 0
    today = pd.Timestamp.today()
    start_date, end_date = today - pd.DateOffset(days=30), today
    try:
        search_df = fetch_category_keyword_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            category="50000006",
            keyword=keyword
        )
    except Exception:
        search_df = pd.DataFrame(columns=["날짜","클릭량"])
    prev_sum = search_df["클릭량"].sum() if not search_df.empty else 0
    total_clicks = recent_avg * 30
    return (total_clicks / prev_sum) if prev_sum > 0 else 0

def build_test_df(price: float, good_id: str, recent_ratio: float, target_date: datetime.date) -> pd.DataFrame:
    weekday = target_date.weekday()
    good_id_enc = goodid_encoder.transform([good_id])[0]
    test_data = {
        "discount_price": price,
        "최근4주클릭수_비율": recent_ratio,
        "weekday": weekday,
        "good_id_enc": good_id_enc
    }
    df = pd.DataFrame([test_data])
    return df.reindex(columns=X_columns, fill_value=0)

def predict_week_logic(keyword: str, price: float, good_id: str):
    results = []
    recent_ratio = get_recent_ratio(keyword)
    for offset in range(7):
        target_date = datetime.date.today() + datetime.timedelta(days=offset)
        day_result = {
            "예측일": str(target_date),
            "예측요일": target_date.strftime("%A"),
            "배율별예측": {}
        }
        for factor in PRICE_FACTORS:
            adj_price = price * factor
            test_df = build_test_df(adj_price, good_id, recent_ratio, target_date)
            pred_clicks = max(0, gam.predict(test_df)[0])
            day_result["배율별예측"][f"{int(factor*100)}%"] = pred_clicks
        results.append(day_result)
    return {"keyword": keyword, "good_id": good_id, "results": results}