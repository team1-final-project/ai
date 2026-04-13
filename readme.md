
# 📘 프로젝트 실행 가이드

## 📂 프로젝트 구조
```
ai/
 ├── app/
 │    └── main.py
 ├── training/
 │    ├── predict_clicks.ipynb
 │    ├── train_model.ipynb
 │    └── view_graph.ipynb
 ├── utils/
 │    ├── __init__.py
 │    ├── naver_searchad_relkeyword.py
 │    └── naver_shoppinginsite_search.py
 ├── data/
 │    ├── processed_keyword.py
 │    └── train_dataset.csv
 └── models/
      ├── gam_model.pkl
      └── nn_model.pkl
```

---

## ⚙️ 환경 설정
- Python 3.11 (conda 환경 `py311`)
- 필수 패키지 설치:
```bash
pip install pandas scikit-learn joblib torch fastapi uvicorn pygam
```

---

## 🚀 FastAPI 서버 실행
- predict_week API 엔드포인트 실행
```Powershell
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

- app.main:app → main.py 안의 app = FastAPI() 객체 실행
- --reload → 코드 변경 시 자동 재시작
- --host 127.0.0.1 → 로컬에서만 접속 가능
- --port 8000 → 접속 포트 (브라우저에서 http://127.0.0.1:8000/docs 확인 가능)

---