import pandas as pd
import numpy as np
import holidays
from datetime import datetime

def date_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    입력: df (date 컬럼만 필수)
    출력: 날짜별 파생 컬럼 추가된 df
    """

    # 날짜형 변환 및 정렬
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date").reset_index(drop=True)

    # 현재 연도
    current_year = datetime.now().year

    # ✅ 월 주기성 (사인/코사인 변환)
    month = df["date"].dt.month
    df["month_sin"] = np.sin(2 * np.pi * month / 12)
    df["month_cos"] = np.cos(2 * np.pi * month / 12)

    # ✅ 공휴일 + 주말 여부
    kr_holidays = holidays.KR(years=[current_year])
    is_official_holiday = df["date"].dt.date.isin(kr_holidays.keys())
    is_weekend = df["date"].dt.weekday.isin([5, 6])
    df["isHoliday"] = (is_official_holiday | is_weekend).astype(int)

    # ✅ 연휴 여부 (주말+공휴일 포함, 3일 이상 연속 + 전날 포함)
    df["isHolidaySeq"] = 0
    all_holiday_dates = sorted(set(
        list(kr_holidays.keys()) +
        [d.date() for d in df.loc[is_weekend, "date"]]
    ))

    seqs = []
    temp = [all_holiday_dates[0]]
    for i in range(1, len(all_holiday_dates)):
        if (all_holiday_dates[i] - all_holiday_dates[i-1]).days == 1:
            temp.append(all_holiday_dates[i])
        else:
            seqs.append(temp)
            temp = [all_holiday_dates[i]]
    seqs.append(temp)

    for seq in seqs:
        if len(seq) >= 3:
            seq_with_prev = [seq[0] - pd.Timedelta(days=1)] + seq
            df.loc[df["date"].dt.date.isin(seq_with_prev), "isHolidaySeq"] = 1

    # ✅ 명절 기준 D-Day 계산 (설날, 추석 자동 참조)
    major_holidays = [pd.Timestamp(d) for d, name in kr_holidays.items()
                      if "설날" in name or "추석" in name]

    df["days_from_major_holiday"] = df["date"].apply(
        lambda d: min([(d - mh).days for mh in major_holidays], key=abs)
    )

    # ✅ 최종적으로 date + 파생 컬럼만 반환
    return df[["date", "month_sin", "month_cos", "isHoliday", "isHolidaySeq", "days_from_major_holiday"]]