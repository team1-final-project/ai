import datetime
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from pygam import LinearGAM, s, f

from naver_searchad_relkeyword import fetch_relkwdstat
from naver_shoppinginsite_search import fetch_category_keyword_data

# 1. 데이터 불러오기
df = pd.read_csv("merged_result.csv")

# ✅ 종속변수: 추정일간클릭수
y = df["추정일간클릭수"]

# ✅ 주요 독립변수
X = df[["1개당가격", "최근4주클릭수_비율", "weekday", "pum_name"]]

# 범주형 변수 원-핫 인코딩
X = pd.get_dummies(X, columns=["pum_name", "weekday"], drop_first=True)

# 학습/테스트 데이터 분리
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# ✅ GAM 모델 정의
# s(0): 1개당가격 → spline 곡선 학습
# s(1): 최근4주클릭수_비율 → spline 곡선 학습
# 나머지 변수들은 f()로 범주형 처리
gam = LinearGAM(
    s(0) + s(1) + f(2) + f(3) + f(4)  # 필요한 만큼 직접 나열
).fit(X_train, y_train)

# 평가
y_pred = gam.predict(X_test)
print("테스트셋 R²:", r2_score(y_test, y_pred))
print("테스트셋 MSE:", mean_squared_error(y_test, y_pred))

# 변수별 곡선 확인 (시각화 가능)
for i, term in enumerate(gam.terms):
    if term.isintercept:
        continue
    XX = gam.generate_X_grid(term=i)
    plt = gam.partial_dependence(term=i, X=XX)
    print(f"변수 {i} 곡선 샘플:", plt[:5])  # 앞부분만 출력

# ===== 단일 테스트 예측 =====
keyword = "참깨라면"
price = 2000
pum_name = "라면"

# 최근4주 클릭수 비율 계산
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
    search_df = pd.DataFrame(columns=["날짜", "클릭량"])

if not search_df.empty:
    search_df["날짜"] = pd.to_datetime(search_df["날짜"])
    prev_sum = search_df["클릭량"].sum()
else:
    prev_sum = 0

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
test_df = pd.get_dummies(test_df, columns=["pum_name", "weekday"], drop_first=True)
test_df = test_df.reindex(columns=X.columns, fill_value=0)

# ✅ GAM 예측
y_test_pred = gam.predict(test_df)
pred_clicks = y_test_pred[0]
print("예측된 클릭수:", pred_clicks)

# ✅ 클릭→수요 전환 계수 반영
conversion_coeff = 10000
pred_demand = pred_clicks * conversion_coeff
print("예측된 수요량:", pred_demand)

pred_sales = pred_demand / price
print("예측된 판매량:", pred_sales)