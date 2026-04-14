import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess


def _parse_lowest_price_from_text(text: str) -> float | None:
    """
    body text에서 '최저 28,970원' 형태를 찾아 숫자만 반환
    """
    if not text:
        return None

    normalized = re.sub(r"\s+", " ", text)

    patterns = [
        r"최저\s*([\d,]+)\s*원",
        r"최저가\s*([\d,]+)\s*원",
    ]

    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            return float(match.group(1).replace(",", ""))

    return None


def _parse_catalog_name_from_text(text: str) -> str | None:
    """
    body text에서 '브랜드 카탈로그' 아래의 상품명을 추출
    예: CJ제일제당 비비고 육개장 500g 1개
    """
    if not text:
        return None

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    for i, line in enumerate(lines):
        if "브랜드 카탈로그" in line:
            for j in range(i + 1, min(i + 6, len(lines))):
                candidate = lines[j]

                excluded_keywords = [
                    "리뷰", "찜", "최저", "원", "배송", "무료",
                    "구매가기", "공식인증", "수량", "kcal", "로딩 중"
                ]
                if any(keyword in candidate for keyword in excluded_keywords):
                    continue

                if len(candidate) >= 3:
                    return candidate

    normalized = re.sub(r"\s+", " ", text)
    match = re.search(
        r"브랜드\s*카탈로그\s*(.+?)(?:최저|배송|리뷰|찜|수량|공식인증|구매가기)",
        normalized
    )
    if match:
        return match.group(1).strip()

    return None


def _create_driver() -> webdriver.Chrome:
    subprocess.Popen(r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrometemp"')

    option = webdriver.ChromeOptions()
    option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

    return webdriver.Chrome(options=option)


def fetch_catalog_info_by_catalog(catalog_code: str) -> dict:
    """
    브라우저를 한 번만 열어서
    - 최저가
    - 카탈로그명
    을 함께 가져온다.

    반환 예시:
    {
        "catalog_code": "51929189219",
        "catalog_name": "CJ제일제당 비비고 육개장 500g 1개",
        "lowest_price": 4510.0
    }
    """
    url = f"https://search.shopping.naver.com/catalog/{catalog_code}"
    driver = _create_driver()

    try:
        driver.get(url)

        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        body_text = driver.find_element(By.TAG_NAME, "body").text
        page_source = driver.page_source

        # 보안 페이지 감지
        blocked_keywords = [
            "보안 확인을 완료해 주세요",
            "captcha",
            "스팸을 방지",
            "실제 사용자임을 확인",
        ]
        joined_text = f"{driver.title}\n{body_text}\n{page_source[:2000]}".lower()
        if any(keyword.lower() in joined_text for keyword in blocked_keywords):
            print(f"⚠️ 네이버 보안 페이지 감지(catalog_code={catalog_code})")
            return {
                "catalog_code": catalog_code,
                "catalog_name": None,
                "lowest_price": None,
            }

        lowest_price = _parse_lowest_price_from_text(body_text)
        if lowest_price is None:
            lowest_price = _parse_lowest_price_from_text(page_source)

        catalog_name = _parse_catalog_name_from_text(body_text)
        if catalog_name is None:
            catalog_name = _parse_catalog_name_from_text(page_source)

        # fallback: XPath로 최저가 탐색
        if lowest_price is None:
            xpath_candidates = [
                "//*[contains(text(), '최저')]/following::*[contains(text(), '원')][1]",
                "//*[contains(text(), '최저가')]/following::*[contains(text(), '원')][1]",
            ]

            for xpath in xpath_candidates:
                elements = driver.find_elements(By.XPATH, xpath)
                for el in elements:
                    text = el.text.strip()
                    match = re.search(r"([\d,]+)\s*원", text)
                    if match:
                        lowest_price = float(match.group(1).replace(",", ""))
                        break
                if lowest_price is not None:
                    break

        return {
            "catalog_code": catalog_code,
            "catalog_name": catalog_name,
            "lowest_price": lowest_price,
        }

    except Exception as e:
        print(f"⚠️ 카탈로그 정보 조회 실패(catalog_code={catalog_code}): {e}")
        return {
            "catalog_code": catalog_code,
            "catalog_name": None,
            "lowest_price": None,
        }

    finally:
        driver.quit()


# 필요하면 기존 함수명도 유지 가능
def fetch_lowest_price_by_catalog(catalog_code: str) -> float | None:
    return fetch_catalog_info_by_catalog(catalog_code)["lowest_price"]


def fetch_catalog_name_by_catalog(catalog_code: str) -> str | None:
    return fetch_catalog_info_by_catalog(catalog_code)["catalog_name"]