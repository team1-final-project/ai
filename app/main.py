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
    pum_name: str
    category_code: str

# ===== 모델 및 컬럼 구조 불러오기 =====
gam_package = joblib.load("./models/gam_model.pkl")
gam = gam_package["model"]
X_columns = gam_package["columns"]

def get_recent_ratio(keyword: str, category_code: str) -> float:
    """최근 4주 클릭수 비율 계산"""
    rel_data = fetch_relkwdstat([keyword])
    recent_avg = rel_data[0].get("최근4주클릭수평균", 0) if rel_data else 0

    today = pd.Timestamp.today()
    start_date, end_date = today - pd.DateOffset(days=30), today

    try:
        search_df = fetch_category_keyword_data(
            start_date=start_date.strftime("%Y-%m-%d"),
            end_date=end_date.strftime("%Y-%m-%d"),
            category=category_code,
            keyword=keyword
        )
    except Exception as e:
        print(f"⚠️ API 호출 실패: {e}")
        search_df = pd.DataFrame(columns=["날짜","클릭량"])

    prev_sum = search_df["클릭량"].sum() if not search_df.empty else 0
    total_clicks = recent_avg * 30
    return (total_clicks / prev_sum) if prev_sum > 0 else 0

def build_test_df(price: float, pum_name: str, keyword: str, category_code: str, target_date: datetime.date) -> pd.DataFrame:
    """예측용 데이터프레임 생성"""
    weekday = target_date.weekday()  # 월=0, 화=1 ... 일=6

    test_data = {
        "1개당가격": price,
        "최근4주클릭수_비율": get_recent_ratio(keyword, category_code),
        "weekday": weekday,
        "pum_name": pum_name
    }
    df = pd.DataFrame([test_data])
    df = pd.get_dummies(df, columns=["pum_name","weekday"], drop_first=True)
    return df.reindex(columns=X_columns, fill_value=0)

@app.post("/predict_week")
def predict_week(req: PredictRequest):
    results = []
    for offset in range(7):  # 오늘 포함 7일
        target_date = datetime.date.today() + datetime.timedelta(days=offset)
        test_df = build_test_df(req.price, req.pum_name, req.keyword, req.category_code, target_date)
        pred_clicks = gam.predict(test_df)[0]
        results.append({
            "예측일": str(target_date),
            "예측요일": target_date.strftime("%A"),
            "예측된 클릭수": pred_clicks
        })
    return {"keyword": req.keyword, "category_code": req.category_code, "results": results}


# ========================= 가격 결정 알고리즘 / API =========================
import math
from typing import Optional, Dict, List
from fastapi import HTTPException
from utils.naver_lowest_price_crawling import fetch_lowest_price_by_catalog

PRICE_STEP = 100
MAX_CHANGE_RATE = 0.20
SALES_CONVERSION_RATE = 0.5
HIGH_STOCK_MULTIPLIER = 2.0
LOW_STOCK_MULTIPLIER = 1.2


class PredictPriceRequest(BaseModel):
    keyword: str               # 상품 이름
    current_price: float       # 현재 가격
    price_change_limit: float  # 최대 변경 가격
    min_price_limit: float     # 최저가 제한
    max_price_limit: float     # 최고가 제한
    current_stock: float       # 현재 재고
    safety_stock: float        # 안전 재고
    category_code: str         # 네이버 검색지표용 카테고리 코드
    catalog_code: str          # 네이버 최저가 조회용 카탈로그 코드
    pum_name: str              # 품목명


def floor_to_step(value: float, step: int = PRICE_STEP) -> float:
    return float(math.floor(value / step) * step)


def ceil_to_step(value: float, step: int = PRICE_STEP) -> float:
    return float(math.ceil(value / step) * step)


def round_change_rate(old_price: float, new_price: float) -> float:
    if old_price <= 0:
        return 0.0
    return round(((new_price - old_price) / old_price) * 100, 1)


def validate_price_request(req: PredictPriceRequest) -> None:
    if req.current_price <= 0:
        raise HTTPException(status_code=400, detail="현재 가격은 0보다 커야 합니다.")
    if req.min_price_limit <= 0:
        raise HTTPException(status_code=400, detail="최저가 제한은 0보다 커야 합니다.")
    if req.max_price_limit <= 0:
        raise HTTPException(status_code=400, detail="최고가 제한은 0보다 커야 합니다.")
    if req.min_price_limit > req.max_price_limit:
        raise HTTPException(status_code=400, detail="최저가 제한은 최고가 제한보다 클 수 없습니다.")
    if req.current_stock < 0:
        raise HTTPException(status_code=400, detail="현재 재고는 0 이상이어야 합니다.")
    if req.safety_stock <= 0:
        raise HTTPException(status_code=400, detail="안전 재고는 0보다 커야 합니다.")
    if req.current_price < req.min_price_limit or req.current_price > req.max_price_limit:
        raise HTTPException(
            status_code=400,
            detail="현재 가격은 최저가 제한과 최고가 제한 사이여야 합니다."
        )

    # 100원 단위 후보가 하나도 없는 제한 범위라면 처리 불가
    min_step_price = ceil_to_step(req.min_price_limit)
    max_step_price = floor_to_step(req.max_price_limit)
    if min_step_price > max_step_price:
        raise HTTPException(
            status_code=400,
            detail="최저가 제한과 최고가 제한 사이에 100원 단위 가격 후보가 없습니다."
        )


def build_test_df_with_ratio(
    price: float,
    pum_name: str,
    recent_ratio: float,
    target_date: datetime.date
) -> pd.DataFrame:
    """
    기존 build_test_df를 건드리지 않기 위해 새로 만든 함수.
    recent_ratio를 미리 한 번만 구해 재사용하도록 분리.
    """
    weekday = target_date.weekday()  # 월=0, 화=1 ... 일=6

    test_data = {
        "1개당가격": price,
        "최근4주클릭수_비율": recent_ratio,
        "weekday": weekday,
        "pum_name": pum_name
    }

    df = pd.DataFrame([test_data])
    df = pd.get_dummies(df, columns=["pum_name", "weekday"], drop_first=True)
    return df.reindex(columns=X_columns, fill_value=0)


def predict_7days_clicks(
    price: float,
    pum_name: str,
    recent_ratio: float
) -> float:
    """
    주어진 가격에 대해 오늘 포함 7일 클릭수를 합산 예측.
    음수 예측이 나오면 0으로 처리.
    """
    total_clicks = 0.0
    today = datetime.date.today()

    for offset in range(7):
        target_date = today + datetime.timedelta(days=offset)
        test_df = build_test_df_with_ratio(price, pum_name, recent_ratio, target_date)
        pred_clicks = float(gam.predict(test_df)[0])
        total_clicks += max(pred_clicks, 0.0)

    return total_clicks


def predict_7days_sales(
    price: float,
    pum_name: str,
    recent_ratio: float
) -> float:
    """
    판매량 = 클릭수 * 50% 가정
    """
    total_clicks = predict_7days_clicks(price, pum_name, recent_ratio)
    return total_clicks * SALES_CONVERSION_RATE


def generate_price_candidates(
    current_price: float,
    min_price_limit: float,
    max_price_limit: float,
    max_change: float,
    mode: str
) -> List[float]:
    """
    mode:
    - "both" : 현재가 ± max_change 범위
    - "up"   : 현재가 ~ 현재가 + max_change 범위
    - "down" : 현재가 - max_change ~ 현재가 범위

    100원 단위 후보를 기본으로 생성하되,
    현재 가격이 100원 단위가 아니어도 현재 가격 자체를 후보에 강제로 포함한다.
    """
    raw_low = max(min_price_limit, current_price - max_change)
    raw_high = min(max_price_limit, current_price + max_change)

    if mode == "up":
        start = ceil_to_step(max(current_price, min_price_limit))
        end = floor_to_step(raw_high)
    elif mode == "down":
        start = ceil_to_step(raw_low)
        end = floor_to_step(min(current_price, max_price_limit))
    elif mode == "both":
        start = ceil_to_step(raw_low)
        end = floor_to_step(raw_high)
    else:
        raise ValueError(f"지원하지 않는 mode 입니다: {mode}")

    candidates: List[float] = []

    if start <= end:
        candidates.extend(
            float(p) for p in range(int(start), int(end) + PRICE_STEP, PRICE_STEP)
        )

    # 현재 가격도 후보에 강제로 포함
    # 단, 실제 탐색 범위(raw_low ~ raw_high)와 제한가 범위 안에 있을 때만 포함
    if raw_low <= current_price <= raw_high and min_price_limit <= current_price <= max_price_limit:
        candidates.append(float(current_price))

    # 중복 제거 + 정렬
    return sorted(set(candidates))

def get_inventory_state(current_stock: float, safety_stock: float) -> str:
    if current_stock >= safety_stock * HIGH_STOCK_MULTIPLIER:
        return "high"
    if current_stock <= safety_stock * LOW_STOCK_MULTIPLIER:
        return "low"
    return "normal"


def evaluate_price(
    price: float,
    current_stock: float,
    safety_stock: float,
    pum_name: str,
    recent_ratio: float,
    cache: Dict[float, Dict[str, float]]
) -> Dict[str, float]:
    """
    동일 가격 반복 예측 방지를 위해 cache 사용
    """
    if price in cache:
        return cache[price]

    predicted_sales = predict_7days_sales(price, pum_name, recent_ratio)
    remaining_stock = current_stock - predicted_sales
    expected_revenue = price * predicted_sales

    result = {
        "price": float(price),
        "predicted_sales": float(predicted_sales),
        "remaining_stock": float(remaining_stock),
        "expected_revenue": float(expected_revenue),
        "is_safe": remaining_stock >= safety_stock
    }
    cache[price] = result
    return result


def pick_closest_candidate(
    candidates: List[float],
    target_price: float,
    prefer: str = "lower"
) -> float:
    """
    target_price에 가장 가까운 후보 선택
    prefer:
    - "lower": 거리 같으면 더 낮은 가격
    - "higher": 거리 같으면 더 높은 가격
    """
    if not candidates:
        raise ValueError("후보 가격이 없습니다.")

    if prefer == "higher":
        return min(candidates, key=lambda p: (abs(p - target_price), -p))
    return min(candidates, key=lambda p: (abs(p - target_price), p))


def select_best_revenue_candidate(
    candidates: List[float],
    current_stock: float,
    safety_stock: float,
    pum_name: str,
    recent_ratio: float,
    cache: Dict[float, Dict[str, float]]
) -> Dict[str, float]:
    """
    보통/부족 재고 구간용
    1) 안전재고를 만족하는 후보 중 예상매출 최대 선택
    2) 만족 후보가 하나도 없으면, 남는 재고가 가장 많은 후보 선택
    """
    if not candidates:
        raise ValueError("후보 가격이 없습니다.")

    evaluated = [
        evaluate_price(
            price=p,
            current_stock=current_stock,
            safety_stock=safety_stock,
            pum_name=pum_name,
            recent_ratio=recent_ratio,
            cache=cache
        )
        for p in candidates
    ]

    safe_candidates = [x for x in evaluated if x["is_safe"]]

    if safe_candidates:
        return max(
            safe_candidates,
            key=lambda x: (
                x["expected_revenue"],
                x["remaining_stock"],
                -abs(x["price"])  # 동률 보조용
            )
        )

    # 안전재고 만족 후보가 없을 때: 재고 방어 우선
    return max(
        evaluated,
        key=lambda x: (
            x["remaining_stock"],
            x["expected_revenue"],
            x["price"]
        )
    )


def select_best_sales_candidate(
    candidates: List[float],
    current_stock: float,
    safety_stock: float,
    pum_name: str,
    recent_ratio: float,
    cache: Dict[float, Dict[str, float]]
) -> Dict[str, float]:
    """
    재고 많음 + 외부 최저가를 아직 못 가져올 때의 fallback 용도
    많이 팔리는 가격 우선
    """
    if not candidates:
        raise ValueError("후보 가격이 없습니다.")

    evaluated = [
        evaluate_price(
            price=p,
            current_stock=current_stock,
            safety_stock=safety_stock,
            pum_name=pum_name,
            recent_ratio=recent_ratio,
            cache=cache
        )
        for p in candidates
    ]

    return max(
        evaluated,
        key=lambda x: (
            x["predicted_sales"],
            -x["price"]   # 판매량 같으면 더 낮은 가격 선호
        )
    )


def decide_price(
    current_price: float,
    price_change_limit: float,
    min_price_limit: float,
    max_price_limit: float,
    current_stock: float,
    safety_stock: float,
    market_lowest_price: Optional[float],
    pum_name: str,
    recent_ratio: float
) -> Dict[str, float]:
    """
    최종 가격 결정 함수
    """
    max_change = price_change_limit
    inventory_state = get_inventory_state(current_stock, safety_stock)
    cache: Dict[float, Dict[str, float]] = {}

    # 재고 많음: 최저가 기반 rule-based
    if inventory_state == "high":
        if market_lowest_price is not None:
            market_lowest_price = float(market_lowest_price)

            # case 1) 현재 가격이 최저가 이하 -> 유지 또는 최저가 근처로 인상
            if current_price <= market_lowest_price:
                candidates = generate_price_candidates(
                    current_price=current_price,
                    min_price_limit=min_price_limit,
                    max_price_limit=max_price_limit,
                    max_change=max_change,
                    mode="up"
                )

                # 최저가를 넘지 않는 범위에서 최대한 가깝게
                target_price = min(
                    current_price + max_change,
                    market_lowest_price,
                    max_price_limit
                )

                if not candidates:
                    final_price = floor_to_step(min(max(current_price, min_price_limit), max_price_limit))
                else:
                    final_price = pick_closest_candidate(candidates, target_price, prefer="higher")

            # case 2) 최대로 내려도 최저가 이하가 되는 가격 -> 최저가보다 약간 아래로
            elif current_price - max_change <= market_lowest_price:
                candidates = generate_price_candidates(
                    current_price=current_price,
                    min_price_limit=min_price_limit,
                    max_price_limit=max_price_limit,
                    max_change=max_change,
                    mode="down"
                )

                # 100원 단위에서 "최저가보다 약간 아래"
                target_price = floor_to_step(market_lowest_price - 1)
                target_price = max(target_price, min_price_limit)

                if not candidates:
                    final_price = floor_to_step(min(max(current_price, min_price_limit), max_price_limit))
                else:
                    final_price = pick_closest_candidate(candidates, target_price, prefer="lower")

            # case 3) 최대로 내려도 아직 최저가보다 비쌈 -> 최대한 하락
            else:
                candidates = generate_price_candidates(
                    current_price=current_price,
                    min_price_limit=min_price_limit,
                    max_price_limit=max_price_limit,
                    max_change=max_change,
                    mode="down"
                )

                target_price = max(current_price - max_change, min_price_limit)

                if not candidates:
                    final_price = floor_to_step(min(max(current_price, min_price_limit), max_price_limit))
                else:
                    final_price = pick_closest_candidate(candidates, target_price, prefer="lower")

            chosen = evaluate_price(
                price=final_price,
                current_stock=current_stock,
                safety_stock=safety_stock,
                pum_name=pum_name,
                recent_ratio=recent_ratio,
                cache=cache
            )
            return chosen

        # 외부 최저가를 아직 못 가져오는 동안의 fallback
        candidates = generate_price_candidates(
            current_price=current_price,
            min_price_limit=min_price_limit,
            max_price_limit=max_price_limit,
            max_change=max_change,
            mode="both"
        )

        if not candidates:
            raise HTTPException(status_code=400, detail="재고 많음 상태에서 생성 가능한 가격 후보가 없습니다.")

        return select_best_sales_candidate(
            candidates=candidates,
            current_stock=current_stock,
            safety_stock=safety_stock,
            pum_name=pum_name,
            recent_ratio=recent_ratio,
            cache=cache
        )

    # 재고 보통: 상승/하락 전체 후보 중, 안전재고 만족 + 예상매출 최대
    if inventory_state == "normal":
        candidates = generate_price_candidates(
            current_price=current_price,
            min_price_limit=min_price_limit,
            max_price_limit=max_price_limit,
            max_change=max_change,
            mode="both"
        )

        if not candidates:
            raise HTTPException(status_code=400, detail="재고 보통 상태에서 생성 가능한 가격 후보가 없습니다.")

        return select_best_revenue_candidate(
            candidates=candidates,
            current_stock=current_stock,
            safety_stock=safety_stock,
            pum_name=pum_name,
            recent_ratio=recent_ratio,
            cache=cache
        )

    # 재고 부족: 상승 후보 중, 안전재고 만족 + 예상매출 최대
    candidates = generate_price_candidates(
        current_price=current_price,
        min_price_limit=min_price_limit,
        max_price_limit=max_price_limit,
        max_change=max_change,
        mode="up"
    )

    if not candidates:
        raise HTTPException(status_code=400, detail="재고 부족 상태에서 생성 가능한 가격 후보가 없습니다.")

    return select_best_revenue_candidate(
        candidates=candidates,
        current_stock=current_stock,
        safety_stock=safety_stock,
        pum_name=pum_name,
        recent_ratio=recent_ratio,
        cache=cache
    )


@app.post("/predict_price")
def predict_price(req: PredictPriceRequest):
    validate_price_request(req)

    # 검색지표는 한 번만 가져와서 재사용
    recent_ratio = get_recent_ratio(req.keyword, req.category_code)

    # 카탈로그 기반 외부 최저가
    # TODO: 나중에 fetch_lowest_price_by_catalog 내부 구현 교체
    market_lowest_price = fetch_lowest_price_by_catalog(req.catalog_code)

    chosen = decide_price(
        current_price=req.current_price,
        price_change_limit=req.price_change_limit,
        min_price_limit=req.min_price_limit,
        max_price_limit=req.max_price_limit,
        current_stock=req.current_stock,
        safety_stock=req.safety_stock,
        market_lowest_price=market_lowest_price,
        pum_name=req.pum_name,
        recent_ratio=recent_ratio
    )

    changed_price = float(chosen["price"])
    expected_sales = round(float(chosen["predicted_sales"]), 2)
    change_rate = round_change_rate(req.current_price, changed_price)

    return {
        "keyword": req.keyword,
        "change_price": changed_price,
        "expect_sale_amount": expected_sales,
        "change_rate": change_rate,
        "market_lowest_price": market_lowest_price
    }
