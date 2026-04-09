import requests

url = "https://apis.data.go.kr/1360000/MidFcstInfoService/getMidLandFcst"
params = {
    "serviceKey": "2184e897ffb4890de84967a55d134c28c767242c09c711bc91f78e307282a5ef",
    "pageNo": 1,
    "numOfRows": 10,
    "dataType": "JSON",
    "regId": "11C20101",   # 천안 지역 코드
    "tmFc": "202603310600" # 어제 06시 발표시각
}

res = requests.get(url, params=params)
print(res.json())