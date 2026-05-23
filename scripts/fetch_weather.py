"""拉取茂名天气+生活数据 → 写入 src/maoming_weather.js。

每天跑一次即可（免费额度 1000次/天，本脚本消耗 3 次）。
"""
import json, os, sys, gzip
import urllib.request

KEY = "663d5453ccb74fb2ab2223f324345890"
LOCATION = "101282001"
HOST = "k36r728k7c.re.qweatherapi.com"
PROJ = r"C:\Users\Yling\Desktop\maomingrengeceshi"
OUT = os.path.join(PROJ, "src", "maoming_weather.js")


def fetch(path, label):
    """调一次 API，返回 JSON 或 None。"""
    url = f"https://{HOST}{path}&key={KEY}"
    try:
        req = urllib.request.Request(url)
        req.add_header("Accept-Encoding", "gzip")
        resp = urllib.request.urlopen(req, timeout=10)
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        data = json.loads(raw)
        if data.get("code") == "200":
            return data
        print(f"  {label}: code={data.get('code')}", file=sys.stderr)
    except Exception as e:
        print(f"  {label}: {e}", file=sys.stderr)
    return None


# ── 1. 实时天气 ──
now_data = fetch(f"/v7/weather/now?location={LOCATION}", "实时天气")
now = now_data["now"] if now_data else None

# ── 2. 分钟级降水 (免费版不支持，跳过) ──
rain_tip = ""

# ── 3. 生活指数 (穿衣1 运动2 紫外线5 感冒8) ──
idx_data = fetch(f"/v7/indices/1d?type=1,5,9&location={LOCATION}", "生活指数")
indices = {}
if idx_data and "daily" in idx_data:
    for d in idx_data["daily"]:
        indices[d["type"]] = d["text"]  # 如 "穿衣指数：天气热，建议穿短袖"


# ── 组装结果 ──
result = {}

if now:
    text = now["text"]
    temp = now["temp"]
    feels = now["feelsLike"]
    wind = now.get("windDir", "") + " " + now.get("windScale", "") + "级"

    if "雨" in text:
        state = "rain"
    elif "阴" in text or "云" in text:
        state = "cloudy"
    elif "风" in text and ("大" in text or int(now.get("windScale", "0")) >= 5):
        state = "windy"
    else:
        state = "hot"

    result["text"] = text
    result["temp"] = temp
    result["feelsLike"] = feels
    result["wind"] = wind.strip()
    result["humidity"] = now.get("humidity", "")
    result["state"] = state
    result["updated"] = now_data.get("updateTime", "")

if rain_tip:
    result["rainTip"] = rain_tip

# 生活指数精简版 —— 只取第一句话
def short_index(raw):
    """去"XX指数："前缀，保留完整正文。"""
    s = raw.split("指数：")[-1] if "指数：" in raw else raw
    return s.strip()

life = []
if "1" in indices:  # 运动
    txt = short_index(indices["1"])
    life.append("🏃 " + txt if txt else "🏃 看心情运动")
if "5" in indices:  # 紫外线
    txt = short_index(indices["5"])
    life.append("☀️ " + txt if txt else "☀️ 注意防晒")
if "9" in indices:  # 感冒
    txt = short_index(indices["9"])
    life.append("🤧 " + txt if txt else "🤧 注意增减衣物")
if life:
    result["lifeTips"] = life

# 体感吐槽
if now:
    t = int(temp)
    f = int(feels)
    diff = f - t
    if diff >= 5:
        result["feelRoast"] = f"气象台说{t}°C，你的皮肤说{f}°C。这个体感差距，茂名人懂的都懂。"
    elif diff >= 2:
        result["feelRoast"] = f"标称{t}°C，体感{f}°C。闷热不是错觉，是茂名在给你加料。"
    else:
        result["feelRoast"] = f"气温{t}°C，体感{f}°C。不冷不热，茂名难得的好日子。"

if not result:
    print("FAILED: 所有 API 都挂了", file=sys.stderr)
    sys.exit(1)

js = "var REAL_WEATHER=" + json.dumps(result, ensure_ascii=False) + ";"
with open(OUT, "w", encoding="utf-8") as f:
    f.write(js)
print(f"OK: {result.get('text','?')} {result.get('temp','?')}°C | 生活指数:{len(life)}条")
