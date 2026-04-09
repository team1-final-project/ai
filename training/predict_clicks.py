# predict_clicks.py
import datetime
import pandas as pd
import joblib
from utils.naver_searchad_relkeyword import fetch_relkwdstat
from utils.naver_shoppinginsite_search import fetch_category_keyword_data

# 학습된 모델 불러오기
gam = joblib.load("./models/gam_model.pkl")
X_columns = pd.read_csv("./data/train_dataset.csv")[["1개당가격","최근4주클릭수_비율","weekday","pum_name"]]
X_columns = pd.get_dummies(X_columns, columns=["pum_name","weekday"], drop_first=True).columns

keyword = "참깨라면"
price = 2000
pum_name = "라면"

rel_data = fetch_relkwdstat([keyword])
recent_4weeks_click_avg = rel_data[0].get("최근4주클릭수평균", 0) if rel_data else 0

today = pd.Timestamp.today()
start_date = today - pd.DateOffset(days=30)
end_date = today

try:
    search_df = fetch_category_keyword_data(
        start_date=start_date.strftime("%Y-%m-%d"),
        end_date=end_date.strftime("%Y-%m-%d"),
        category="50000006",
        keyword=keyword
    )
except Exception as e:
    print(f"⚠️ API 호출 실패: {e}")
    search_df = pd.DataFrame(columns=["날짜","클릭량"])

prev_sum = search_df["클릭량"].sum() if not search_df.empty else 0
recent_4weeks_click_total = recent_4weeks_click_avg * 30
recent_ratio = (recent_4weeks_click_total / prev_sum) if prev_sum > 0 else 0

tomorrow = datetime.date.today() + datetime.timedelta(days=1)
weekday = tomorrow.weekday() + 1

test_data = {
    "1개당가격": price,
    "최근4주클릭수_비율": recent_ratio,
    "weekday": weekday,
    "pum_name": pum_name
}
test_df = pd.DataFrame([test_data])
test_df = pd.get_dummies(test_df, columns=["pum_name","weekday"], drop_first=True)
test_df = test_df.reindex(columns=X_columns, fill_value=0)

pred_clicks = gam.predict(test_df)[0]
print("예측된 클릭수:", pred_clicks)

conversion_coeff = 10000
pred_demand = pred_clicks * conversion_coeff
print("예측된 수요량:", pred_demand)

pred_sales = pred_demand / price
print("예측된 판매량:", pred_sales)