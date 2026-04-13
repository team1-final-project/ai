import re
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import subprocess

def _parse_lowest_price_from_text(text: str) -> float | None:
    """
    body text에서 '최저 28,970원' 형태를 찾아 숫자만 반환
    """
    if not text:
        return None

    # 줄바꿈/공백이 섞여도 잡히도록 처리
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


def fetch_lowest_price_by_catalog(catalog_code: str) -> float | None:
    """
    네이버 쇼핑 카탈로그 페이지에서 빨간 '최저 xx,xxx원' 가격을 가져온다.
    실패하면 None 반환.
    """
    url = f"https://search.shopping.naver.com/catalog/{catalog_code}"

    # options = Options()
    # # 서버 환경이면 아래 headless 유지
    # options.add_argument("--headless=new")
    # options.add_argument("--disable-gpu")
    # options.add_argument("--no-sandbox")
    # options.add_argument("--disable-dev-shm-usage")
    # options.add_argument("--window-size=1400,1200")
    # options.add_argument(
    #     "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    #     "AppleWebKit/537.36 (KHTML, like Gecko) "
    #     "Chrome/123.0.0.0 Safari/537.36"
    # )

    # driver = webdriver.Chrome(
    #     service=Service(ChromeDriverManager().install()),
    #     options=options
    # )

    subprocess.Popen(r'C:\Program Files\Google\Chrome\Application\chrome.exe --remote-debugging-port=9222 --user-data-dir="C:\chrometemp"')

    option = webdriver.ChromeOptions()
    option.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=option)

    try:
        driver.get(url)

        wait = WebDriverWait(driver, 10)

        # body 로드 대기
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # '최저' 문구가 나타날 때까지 한 번 더 대기
        wait.until(
            lambda d: "최저" in d.find_element(By.TAG_NAME, "body").text
            or "최저가" in d.find_element(By.TAG_NAME, "body").text
        )

        body_text = driver.find_element(By.TAG_NAME, "body").text
        price = _parse_lowest_price_from_text(body_text)
        if price is not None:
            return price

        # fallback 1: page_source에서도 시도
        page_source = driver.page_source
        price = _parse_lowest_price_from_text(page_source)
        if price is not None:
            return price

        # fallback 2: XPath로 '최저' 주변 숫자 찾기 시도
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
                    return float(match.group(1).replace(",", ""))

        return None

    except Exception as e:
        print(f"⚠️ 최저가 조회 실패(catalog_code={catalog_code}): {e}")
        return None

    finally:
        driver.quit()