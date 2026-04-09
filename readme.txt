# 📘 프로젝트 실행 가이드 (README)

## 📂 프로젝트 구조
```
ai/
 ├── preprocessing/
 │    └── build_train_dataset.py
 ├── training/
 │    ├── train_gam_model.py
 │    └── predict_clicks.py
 ├── utils/
 │    ├── __init__.py
 │    ├── naver_searchad_relkeyword.py
 │    └── naver_shoppinginsite_search.py
 ├── data/
 │    ├── processed_keyword.csv
 │    └── train_dataset.csv
 └── models/
      └── gam_model.pkl
```

---

## ⚙️ 환경 설정
- Python 3.11 (conda 환경 `py311`)
- 필수 패키지:  
  ```bash
  pip install pandas scikit-learn pygam joblib
  ```

---

## 🚀 실행 방법

### 1. 데이터셋 생성
- `processed_keyword.csv` → `train_dataset.csv` 변환  
- 실행:
  ```powershell
  cd C:\Users\human\Desktop\용현\team1_final_project\ai
  python -m preprocessing.build_train_dataset
  ```
- 결과: `./data/train_dataset.csv` 생성

---

### 2. 모델 학습
- GAM 모델 학습 및 저장  
- 실행:
  ```powershell
  python -m training.train_gam_model
  ```
- 결과: `./models/gam_model.pkl` 저장

---

### 3. 예측 실행
- 학습된 모델 불러와서 클릭수/수요량/판매량 예측  
- 실행:
  ```powershell
  python -m training.predict_clicks
  ```

---