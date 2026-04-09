# train_gam_model.py
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score
from pygam import LinearGAM, s, f
import joblib

df = pd.read_csv("./data/train_dataset.csv")
y = df["추정일간클릭수"]
X = df[["1개당가격", "최근4주클릭수_비율", "weekday", "pum_name"]]
X = pd.get_dummies(X, columns=["pum_name", "weekday"], drop_first=True)

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

gam = LinearGAM(s(0) + s(1) + f(2) + f(3) + f(4)).fit(X_train, y_train)

y_pred = gam.predict(X_test)
print("테스트셋 R²:", r2_score(y_test, y_pred))
print("테스트셋 MSE:", mean_squared_error(y_test, y_pred))

# 모델 저장
joblib.dump(gam, "./models/gam_model.pkl")