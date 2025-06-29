import os
import json
import time
import urllib.parse
import urllib.request
import http.client
import tempfile
import asyncio
BASE_URL = "https://www.hepsiemlak.com"
COOKIE_PATH = os.path.join(tempfile.gettempdir(), "cookie_hepsiemlak.txt")
if os.path.exists(COOKIE_PATH):
    with open(COOKIE_PATH, "r", encoding="utf-8") as f:
        cookie = f.read().strip()
else:
    cookie = ""

ID_LIST_ENDPOINT = BASE_URL + "/api/realty-map/?mapSize=2500&intent=satilik&city=sakarya&mainCategory=konut&mapCornersEnabled=true"
USER_AGENTS = [
    ["Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36", 0.1]
]
CAPTCHA_ERR = "Hata. Robot doğrulamasını geçmek gerekebilir.\nYönerge: https://github.com/arfelious/hepsiemlak-scraper/blob/main/captcha.md"

def get_weighted_random(lst):
    total_weight = sum(weight for _, weight in lst)
    rnd = total_weight * os.urandom(4)[0] / 255.0
    for item, weight in lst:
        rnd -= weight
        if rnd <= 0:
            return item
    return lst[-1][0]

def get_random_user_agent(os_type):
    filtered_agents = [ua for ua in USER_AGENTS if ua[0].lower() == os_type.lower()]
    return get_weighted_random(filtered_agents) if filtered_agents else get_weighted_random(USER_AGENTS)

def extract_user_agent(cookie):
    match = cookie.find("device_info=")
    if match != -1:
        try:
            start = match + len("device_info=")
            end = cookie.find(";", start)
            device_info = json.loads(urllib.parse.unquote(cookie[start:end]))
            return device_info.get("user_agent", None)
        except Exception as e:
            print("Error parsing device_info cookie:", e)
    return None

def get_options(cookie):
    user_agent = extract_user_agent(cookie)
    if not user_agent:
        os_type = "Linux"
        user_agent = get_random_user_agent(os_type)
    return {
        "headers": {
            "Referer": "https://www.hepsiemlak.com/tekirdag-kiralik/yazlik",
            "Referrer-Policy": "no-referrer-when-downgrade",
            "accept": "*/*",
            "accept-language": "tr-TR,tr;q=0.9",
            "cache-control": "no-cache",
            "pragma": "no-cache",
            "sec-ch-ua": "\"Not(A:Brand\";v=\"99\", \"Google Chrome\";v=\"133\", \"Chromium\";v=\"133\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "script",
            "sec-fetch-mode": "no-cors",
            "sec-fetch-site": "same-origin",
            "cookie": cookie,
            "user-agent":"node"
        },
        "method": "GET"
    }

IMG_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
def remove_images(obj):
    keys_to_delete = [key for key, val in obj.items() if isinstance(val, str) and any(ext in val for ext in IMG_EXTS)]
    for key in keys_to_delete:
        del obj[key]
    for key, val in obj.items():
        if isinstance(val, dict):
            remove_images(val)

cookie_store = {}

def parse_set_cookie(set_cookie_headers):
    if not set_cookie_headers:
        return
    cookies = set_cookie_headers.split(", ") if isinstance(set_cookie_headers, str) else set_cookie_headers
    for cookie in cookies:
        parts = cookie.split(";")[0].strip()
        if "=" in parts:
            key, value = parts.split("=", 1)
            cookie_store[key.strip()] = value.strip()

def get_cookie_header():
    return "; ".join(f"{k}={v}" for k, v in cookie_store.items())

async def sfetch(url, options=None, depth=0):
    options = options or {}
    method = options.get("method", "GET")
    headers = options.get("headers", {})

    headers["Cookie"] = get_cookie_header()
    
    parsed_url = urllib.parse.urlparse(url)
    conn = http.client.HTTPSConnection(parsed_url.netloc)

    path = parsed_url.path
    if parsed_url.query:
        path += "?" + parsed_url.query

    try:
        conn.request(method, path, headers=headers)
        response = conn.getresponse()
        status = response.status
        set_cookie = response.getheader("Set-Cookie")

        if set_cookie:
            parse_set_cookie(set_cookie)

        data = response.read().decode("utf-8")
        conn.close()

        if status == 403 and depth<5:
            location = response.getheader("Location")
            if not location and 'fa: "' in data:
                location = BASE_URL + data.split('fa: "')[1].split('"')[0].replace("\\", "")
            if location:
                wait_time = 5 + (2 * asyncio.get_event_loop().time() % 1)
                await asyncio.sleep(wait_time)
                return await sfetch(urllib.parse.urljoin(url, location), options, depth + 1)

        return data

    except Exception as e:
        print(f"Hata: {e}")
        return None

async def get_listing_ids():
    response_text = await sfetch(ID_LIST_ENDPOINT, get_options(cookie))
    if response_text:
        try:
            if "Just a moment..." in response_text:
                raise Exception(CAPTCHA_ERR)
            parsed = json.loads(response_text)
            return [x["listingId"] for x in parsed.get("realties", [])]
        except Exception as e:
            print((str(e) if "Hata" in str(e) else "Hata. İlan ID'leri alınamadı.")+"\nSunucudan gelen yanıt:", response_text[:50], "...")
    return []

async def get_listing(listing_id):
    url = f"{BASE_URL}/api/realties/{listing_id}"
    response_text = await sfetch(url, get_options(cookie))
    if response_text:
        try:
            if "Just a moment..." in response_text:
                raise Exception(CAPTCHA_ERR)
            parsed = json.loads(response_text)
            if "exception" in parsed:
                raise Exception("Hata. Sunucudan gelen hata mesajı: " + ", ".join(parsed.get("errors", [])))
            realty_detail = parsed.get("realtyDetail", {})
            remove_images(realty_detail)
            realty_detail.pop("breadcrumbs", None)
            return json.dumps(realty_detail, ensure_ascii=False)
        except Exception as e:
            print(str(e))
            print("Hata. İlan bilgileri alınamadı.\nSunucudan gelen yanıt:", response_text[:50], "...")
    return None

def parse_set_cookie(set_cookie_header):
    global cookie
    if not set_cookie_header:
        return

    new_cookies = {}
    cookies = set_cookie_header.split("; ")
    for cookie_part in cookies:
        if "=" in cookie_part:
            key, value = cookie_part.split("=", 1)
            new_cookies[key.strip()] = value.strip()

    cookie = "; ".join(f"{k}={v}" for k, v in new_cookies.items())
    with open(COOKIE_PATH, "w", encoding="utf-8") as f:
        f.write(cookie)

def get_cookie_header():
    return cookie

async def main():
    while True:
        command = input("İşlem: (al/listele/cookie): ").strip().lower()
        if command == "al":
            listing_id = input("İlan ID: ").strip()
            listing = await get_listing(listing_id)
            if listing:
                print(listing)
        elif command == "listele":
            listing_ids = await get_listing_ids()
            if listing_ids:
                max_per_line = os.get_terminal_size().columns // 16
                for i, listing_id in enumerate(listing_ids):
                    print(listing_id.rjust(15), end=" ")
                    if (i + 1) % max_per_line == 0:
                        print()
                print("\nListelenen ilanların başkaları tarafından alınmadığını kontrol etmeyi unutmayın.")
        elif command == "cookie":
            new_cookie = input("Cookie: ").strip()
            parse_set_cookie(new_cookie)
        else:
            print("Geçersiz işlem.")

if __name__ == "__main__":
    asyncio.run(main())