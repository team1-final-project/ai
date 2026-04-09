import pandas as pd
import matplotlib.pyplot as plt

# 데이터 불러오기
df = pd.read_csv("merged_result.csv", encoding="utf-8-sig")
df["collect_day"] = pd.to_datetime(df["collect_day"])

# 숫자형 변환
df["추정일간클릭수"] = pd.to_numeric(df["추정일간클릭수"], errors="coerce")
df["discount_price"] = pd.to_numeric(df["discount_price"], errors="coerce")

# 한글 폰트 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# ✅ 상품별 시계열 그래프 (검색량 vs 할인가)
for name, group in df.groupby("good_name"):
    plt.figure(figsize=(14,7))
    
    # 스케일 맞추기: 할인가를 검색량 평균에 맞춰서 조정
    avg_search = group["추정일간클릭수"].mean()
    avg_discount = group["discount_price"].mean()
    scale_factor = avg_search / avg_discount if avg_discount != 0 else 1
    scaled_discount = group["discount_price"] * scale_factor
    
    # 추정일간클릭수 (원래 값 그대로)
    plt.plot(group["collect_day"], group["추정일간클릭수"], label="추정일간클릭수", color="blue")
    
    # 할인가 (스케일 맞춤)
    plt.plot(group["collect_day"], scaled_discount, label="할인가(스케일 맞춤)", color="red", linewidth=2)
    
    plt.title(f"{name} - 추정일간클릭수 vs 할인가 (시계열)")
    plt.xlabel("날짜")
    plt.ylabel("값 (추정일간클릭수 기준 스케일)")
    plt.legend()
    plt.grid(True)
    plt.ylim(bottom=0)  # ✅ y축 하한을 0으로 설정
    plt.show()