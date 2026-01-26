import requests
import json

TOKEN_URL = "https://open.tiktokapis.com/v2/oauth/token/"

data = {
    "client_key": "sbawvbdtg82pizss6u",
    "client_secret": "iNVEE8lBQittGh3ihul4YiMwYmjtiuYp",
    "code": "TKTz99zV2teyX5qoTUqJ04SLLLGnaxVNiZSW6aD34XFAUFYGxenOszfQWtLV81Pefvc7PIdl0ISxa0CGmGJGV43K0FWxJvNd3mSIbtd975ra5ASvloADyqXfx_iwmLaLKnu3tBeHQYKmxD2Fop1C4sTcwOjzUZ4U37SFxxSO-n3yE6MDfsrGqT7wrhCO_3g1HRSSrpguEdzBbrVu%2Av%216427.va",
    "grant_type": "authorization_code",
    "redirect_uri": "https://www.google.com/",
    "code_verifier": "Vn1Shs8Gjj3eyBPV2MEkYJSk1NfHG7w67pB1q0rC0wBccTNh hwbJyJJB_Hzek_85bqFMdEu7H7uxE0vQygE4M9w".replace(" ", "")
}

headers = {
    "Content-Type": "application/x-www-form-urlencoded"
}

print("Initiating Token Exchange via Cloud Proxy...")
try:
    response = requests.post(TOKEN_URL, headers=headers, data=data, timeout=15)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
