import datetime
import pandas as pd
import joblib
from utils.naver_searchad_relkeyword import fetch_relkwdstat
from utils.naver_shoppinginsite_search import fetch_category_keyword_data

# ===== 상수 선언 =====
KEYWORD = "참깨라면"
PRICE = 2000
PUM_NAME = "라면"
CATEGORY_CODE = "50000006"

# ===== 모델 불러오기 =====
gam_package = joblib.load("./models/gam_model.pkl")
gam = gam_package["model"]
X_columns = gam_package["columns"]

# ===== 최근 4주 클릭 데이터 =====
rel_data = fetch_relkwdstat([KEYWORD])
recent_4weeks_click_avg = rel_data[0].get("최근4주클릭수평균", 0) if rel_data else 0

today = pd.Timestamp.today()
start_date = today - pd.DateOffset(days=30)
end_date = today

try:
    search_df = fetch_category_keyword_data(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        category=CATEGORY_CODE,
        keyword=KEYWORD
    )
except Exception as e:
    print(f"⚠️ API 호출 실패: {e}")
    search_df = pd.DataFrame(columns=["날짜","클릭량"])

prev_sum = search_df["클릭량"].sum() if not search_df.empty else 0
recent_4weeks_click_total = recent_4weeks_click_avg * 30
recent_ratio = (recent_4weeks_click_total / prev_sum) if prev_sum > 0 else 0

# ===== 예측 데이터 생성 =====
tomorrow = datetime.date.today() + datetime.timedelta(days=1)
weekday = tomorrow.weekday() + 1

test_data = {
    "1개당가격": PRICE,
    "최근4주클릭수_비율": recent_ratio,
    "weekday": weekday,
    "pum_name": PUM_NAME
}
test_df = pd.DataFrame([test_data])
test_df = pd.get_dummies(test_df, columns=["pum_name","weekday"], drop_first=True)
test_df = test_df.reindex(columns=X_columns, fill_value=0)

# ===== 예측 수행 =====
pred_clicks = gam.predict(test_df)[0]
print("예측된 클릭수:", pred_clicks)