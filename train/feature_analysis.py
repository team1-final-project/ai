import pandas as pd
import statsmodels.api as sm

# 데이터 불러오기
df = pd.read_csv("merged_result.csv")

# 필요한 컬럼만 선택
analysis_cols = [
    "추정일간클릭수", "1개당가격", "최근4주클릭수_비율", "weekday", "pum_name"
]
df = df[analysis_cols].dropna()

# ✅ 숫자형 변환
for col in ["추정일간클릭수", "1개당가격", "최근4주클릭수_비율"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ✅ 범주형 변수 더미 처리
df = pd.get_dummies(df, columns=["pum_name", "weekday"], drop_first=True)

# ✅ 모든 컬럼을 float으로 변환
df = df.astype(float)

# 종속변수와 독립변수 분리
y = df["추정일간클릭수"]
X = df.drop("추정일간클릭수", axis=1)

# 상수항 추가
X = sm.add_constant(X)

# 회귀분석 실행
model = sm.OLS(y, X).fit()
print(model.summary())