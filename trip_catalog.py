import copy
import math
from typing import Any, Dict, List, Optional
from urllib.parse import quote


DESTINATION_CENTERS = {
    "shanghai": {"name": "人民广场住宿区", "lat": 31.2304, "lon": 121.4737},
    "hangzhou": {"name": "武林广场住宿区", "lat": 30.2741, "lon": 120.1551},
    "chengdu": {"name": "天府广场住宿区", "lat": 30.6570, "lon": 104.0660},
    "tokyo": {"name": "东京站/银座住宿区", "lat": 35.6812, "lon": 139.7671},
    "kyoto": {"name": "京都站/四条住宿区", "lat": 34.9858, "lon": 135.7588},
}

DESTINATION_KEYS = {
    "上海": "shanghai",
    "shanghai": "shanghai",
    "杭州": "hangzhou",
    "hangzhou": "hangzhou",
    "成都": "chengdu",
    "chengdu": "chengdu",
    "东京": "tokyo",
    "tokyo": "tokyo",
    "京都": "kyoto",
    "kyoto": "kyoto",
}


def _commons_url(filename: str, width: int = 960) -> str:
    encoded = quote(filename.replace(" ", "_"), safe="_(),-'%")
    return f"https://commons.wikimedia.org/wiki/Special:FilePath/{encoded}?width={width}"


def _amap_search(name: str) -> str:
    return f"https://uri.amap.com/search?keyword={quote(name)}&city={quote('上海')}&view=map"


def _dianping_search(name: str) -> str:
    return f"https://www.dianping.com/search/keyword/1/0_{quote(name)}"


def _restaurant(
    name: str,
    cuisine: str,
    dishes: List[str],
    price_per_person: str,
    travel_minutes: int,
    reason: str,
    source_url: str = "",
) -> Dict[str, Any]:
    return {
        "name": name,
        "cuisine": cuisine,
        "signature_dishes": dishes,
        "price_per_person": price_per_person,
        "travel_minutes": travel_minutes,
        "reason": reason,
        "map_url": _amap_search(name),
        "review_url": _dianping_search(name),
        "rating_note": "大众点评评分和排队情况实时变化，请以打开后的页面为准。",
        "source_url": source_url,
    }


KNOWN_POI_COORDINATES = {
    "hangzhou": {
        "西湖环线": (30.2420, 120.1500),
        "灵隐寺": (30.2401, 120.1025),
        "龙井村": (30.2230, 120.1006),
        "西溪湿地": (30.2715, 120.0652),
        "河坊街": (30.2456, 120.1711),
        "中国茶叶博物馆": (30.2265, 120.1090),
        "京杭大运河杭州段": (30.3124, 120.1419),
    },
    "chengdu": {
        "成都大熊猫繁育研究基地": (30.7350, 104.1456),
        "宽窄巷子": (30.6694, 104.0563),
        "武侯祠": (30.6469, 104.0473),
        "锦里": (30.6472, 104.0468),
        "杜甫草堂": (30.6592, 104.0289),
        "人民公园": (30.6599, 104.0573),
        "川菜/火锅体验": (30.6570, 104.0660),
        "青城山": (30.9066, 103.5736),
    },
    "tokyo": {
        "浅草寺与仲见世商店街": (35.7148, 139.7967),
        "上野公园与博物馆区": (35.7156, 139.7730),
        "涩谷与原宿街区": (35.6595, 139.7005),
        "明治神宫": (35.6764, 139.6993),
        "筑地/丰洲市场": (35.6655, 139.7707),
        "东京塔或晴空塔": (35.6586, 139.7454),
        "teamLab 沉浸式展览": (35.6491, 139.7898),
    },
    "kyoto": {
        "伏见稻荷大社": (34.9671, 135.7727),
        "清水寺与二年坂三年坂": (34.9949, 135.7850),
        "岚山竹林与渡月桥": (35.0170, 135.6710),
        "金阁寺": (35.0394, 135.7292),
        "祇园花见小路": (35.0037, 135.7750),
        "锦市场": (35.0050, 135.7647),
        "和服/茶道体验": (35.0048, 135.7756),
    },
}

SHANGHAI_POI_DETAILS = {
    "外滩": {
        "summary": "沿万国建筑群步行看黄浦江两岸天际线，适合在日落前后衔接夜景。",
        "highlights": ["万国建筑博览群", "黄浦江天际线", "外白渡桥与夜景"],
        "best_time": "16:30-20:00",
        "visit_tip": "南京东路一侧人流密集，建议从外白渡桥向南单向步行。",
        "lat": 31.2400,
        "lon": 121.4905,
        "image": "assets/pois/shanghai_bund.jpg",
        "image_source": "https://commons.wikimedia.org/wiki/File:Shanghai_skyline_from_the_bund.jpg",
        "image_credit": "Wikimedia Commons · CC0",
        "spend": {"optional_min": 0, "optional_max": 180, "optional_label": "浦江游船/观景体验"},
        "restaurant": _restaurant(
            "晶采轩（外滩中心）",
            "江南与粤式中餐",
            ["时令江南菜", "点心", "精致午市套餐"],
            "¥180-350",
            12,
            "距离外滩步行区较近，适合安排为看夜景前的正餐。",
            "https://www.bundcenter.com/en/restaurant/",
        ),
    },
    "豫园与城隍庙": {
        "summary": "园林、老城厢和传统小吃集中在步行范围内，可组合成半日文化路线。",
        "highlights": ["明代江南园林", "九曲桥与湖心亭", "城隍庙老街小吃"],
        "best_time": "08:30-11:30",
        "visit_tip": "豫园本体和外围商业街客流差异很大，先入园再逛老街更从容。",
        "lat": 31.2270,
        "lon": 121.4921,
        "image": _commons_url("Shanghai Yuyuan Garden (26098852705).jpg"),
        "image_source": "https://commons.wikimedia.org/wiki/File:Shanghai_Yuyuan_Garden_(26098852705).jpg",
        "image_credit": "Esin Üstün · CC BY 2.0",
        "spend": {"optional_min": 30, "optional_max": 150, "optional_label": "茶点/文创/小吃"},
        "restaurant": _restaurant(
            "南翔馒头店（豫园店）",
            "上海点心",
            ["鲜肉小笼", "蟹粉小笼", "传统早点"],
            "¥50-120",
            5,
            "就在豫园商圈内，适合作为早午餐，但热门时段需要排队。",
            "https://english.shanghai.gov.cn/en-Latest-WhatsNew/20240723/42e646b2e7024292ad8d7e732add62b4.html",
        ),
    },
    "上海博物馆": {
        "summary": "以青铜器、陶瓷、书画为核心的中国古代艺术馆，适合预留完整半天。",
        "highlights": ["古代青铜馆", "历代陶瓷馆", "书画与专题展"],
        "best_time": "09:00-12:00",
        "visit_tip": "热门展期建议提前预约；若只停留两小时，优先青铜、陶瓷两个常设展。",
        "lat": 31.2303,
        "lon": 121.4708,
        "image": _commons_url("2008 Shanghai People's Square- Shanghai Museum 2.jpg"),
        "image_source": "https://commons.wikimedia.org/wiki/File:2008_Shanghai_People%27s_Square-_Shanghai_Museum_2.jpg",
        "image_credit": "Gary Todd · CC0",
        "spend": {"optional_min": 0, "optional_max": 120, "optional_label": "特展/讲解/文创"},
        "restaurant": _restaurant(
            "佳家汤包（黄河路店）",
            "上海小吃",
            ["鲜肉汤包", "蟹粉汤包", "蛋皮汤"],
            "¥35-80",
            15,
            "从人民广场步行可达，适合博物馆参观后的高性价比午餐。",
        ),
    },
    "武康路历史街区": {
        "summary": "以武康大楼为起点串联梧桐街区、名人故居与小型咖啡馆。",
        "highlights": ["武康大楼", "巴金故居周边", "梧桐街区建筑漫步"],
        "best_time": "08:00-11:00",
        "visit_tip": "街区适合步行和骑行，周末午后拥挤，清晨更适合建筑摄影。",
        "lat": 31.2061,
        "lon": 121.4332,
        "image": _commons_url("Wukang Road near Huaihai Road, Shanghai.jpg"),
        "image_source": "https://commons.wikimedia.org/wiki/File:Wukang_Road_near_Huaihai_Road,_Shanghai.jpg",
        "image_credit": "SSYoung · CC BY-SA 4.0",
        "spend": {"optional_min": 40, "optional_max": 180, "optional_label": "咖啡/甜点/建筑导览"},
        "restaurant": _restaurant(
            "老吉士酒家",
            "经典本帮菜",
            ["红烧肉", "油爆虾", "酒香草头"],
            "¥180-320",
            12,
            "位于衡山路街区，适合在武康路漫步后体验传统本帮菜。",
        ),
    },
    "陆家嘴观景区": {
        "summary": "高楼观景、滨江步道和金融城夜景组合，适合安排在晴朗傍晚。",
        "highlights": ["上海中心/环球金融中心观景", "陆家嘴环形天桥", "滨江步道"],
        "best_time": "15:30-20:00",
        "visit_tip": "观景台受天气影响明显，能见度低时可改为滨江步道和商场路线。",
        "lat": 31.2397,
        "lon": 121.4998,
        "image": _commons_url("Shanghai, China skyline.jpg"),
        "image_source": "https://commons.wikimedia.org/wiki/File:Shanghai,_China_skyline.jpg",
        "image_credit": "Quintin Soloviev · CC BY 4.0",
        "spend": {"optional_min": 120, "optional_max": 280, "optional_label": "观景台门票/下午茶"},
        "restaurant": _restaurant(
            "鼎泰丰（上海国金中心店）",
            "江南点心与中式料理",
            ["小笼包", "排骨蛋炒饭", "红油抄手"],
            "¥120-220",
            8,
            "位于陆家嘴核心商圈，环境稳定，适合观景前后用餐。",
        ),
    },
    "田子坊": {
        "summary": "石库门里弄中的小店、工作室和餐饮空间，适合轻量闲逛而非赶景点。",
        "highlights": ["石库门里弄", "独立手作与画廊", "泰康路街区"],
        "best_time": "10:00-15:00",
        "visit_tip": "主巷之外的小支路更安静；商业化程度较高，建议控制购物时间。",
        "lat": 31.2098,
        "lon": 121.4643,
        "image": _commons_url("Tianzifang 21644-Shanghai (33029184946).jpg"),
        "image_source": "https://commons.wikimedia.org/wiki/File:Tianzifang_21644-Shanghai_(33029184946).jpg",
        "image_credit": "xiquinhosilva · CC BY 2.0",
        "spend": {"optional_min": 50, "optional_max": 260, "optional_label": "咖啡/手作/文创"},
        "restaurant": _restaurant(
            "田子坊本帮菜馆（泰康路周边）",
            "本帮家常菜",
            ["响油鳝糊", "草头圈子", "葱油拌面"],
            "¥90-180",
            6,
            "优先选择泰康路外围评分稳定的本帮菜馆，避免在最拥挤的主巷久候。",
        ),
    },
    "朱家角古镇": {
        "summary": "位于青浦的水乡古镇，离市中心约 45-50 公里，应单独安排半日或一日。",
        "highlights": ["放生桥", "北大街与水巷", "古镇摇橹船"],
        "best_time": "08:30-15:30",
        "visit_tip": "不要与外滩、豫园安排在同一半天；地铁 17 号线后仍需短途接驳。",
        "lat": 31.1133,
        "lon": 121.0512,
        "remote": True,
        "image": _commons_url("Qingpu Zhujiajiao Bridge in Shanghai.jpg", 750),
        "image_source": "https://commons.wikimedia.org/wiki/File:Qingpu_Zhujiajiao_Bridge_in_Shanghai.jpg",
        "image_credit": "复兴中国 · CC BY-SA 3.0",
        "spend": {"optional_min": 80, "optional_max": 260, "optional_label": "联票/摇橹船/茶馆"},
        "restaurant": _restaurant(
            "放生桥菜馆",
            "水乡本帮菜",
            ["白水鱼", "扎肉", "河鲜与时令菜"],
            "¥100-220",
            8,
            "古镇官方餐饮信息中列出的餐馆，适合在放生桥路线中安排午餐。",
            "https://www.zhujiajiao.com/en/restaurant/",
        ),
    },
    "本帮菜体验": {
        "summary": "把一顿本帮菜作为正式体验，理解浓油赤酱、时令河鲜和海派点心。",
        "highlights": ["经典本帮菜", "时令食材", "上海点心与黄酒搭配"],
        "best_time": "11:30-13:30 / 17:30-20:00",
        "visit_tip": "经典菜分量适合分享，两人以上更容易覆盖不同口味。",
        "lat": 31.2126,
        "lon": 121.4820,
        "image": _commons_url("Xiaolongbao Shanghai.jpg", 500),
        "image_source": "https://commons.wikimedia.org/wiki/File:Xiaolongbao_Shanghai.jpg",
        "image_credit": "Robigasp · CC BY-SA 4.0",
        "spend": {"optional_min": 0, "optional_max": 180, "optional_label": "加菜/黄酒/甜品"},
        "restaurant": _restaurant(
            "上海老饭店",
            "传统本帮菜",
            ["八宝鸭", "油爆虾", "扣三丝"],
            "¥180-350",
            8,
            "老城厢代表性本帮菜选择，适合与豫园片区组合。",
        ),
    },
    "新天地石库门街区": {
        "summary": "石库门建筑、城市更新与餐饮空间集中，适合和人民广场或田子坊串联。",
        "highlights": ["石库门建筑", "中共一大会址周边", "新旧街区对照"],
        "best_time": "10:00-20:00",
        "visit_tip": "商业街与历史街巷并存，建议把建筑步行放在餐饮购物之前。",
        "lat": 31.2195,
        "lon": 121.4753,
        "spend": {"optional_min": 40, "optional_max": 260, "optional_label": "展览/咖啡/购物"},
        "restaurant": _restaurant("新吉士酒楼（新天地周边）", "本帮菜", ["红烧肉", "油爆虾", "蟹粉豆腐"], "¥160-300", 10, "适合作为石库门街区路线中的正式本帮菜用餐。"),
    },
    "上海自然博物馆": {
        "summary": "大型自然史博物馆，展陈密度高，亲子或雨天行程都很合适。",
        "highlights": ["生命长河展厅", "恐龙与古生物", "上海本地生态"],
        "best_time": "09:00-13:00",
        "visit_tip": "周末与假期建议预约早场，亲子游客至少预留三小时。",
        "lat": 31.2354,
        "lon": 121.4613,
        "spend": {"optional_min": 30, "optional_max": 160, "optional_label": "特展/互动项目/文创"},
        "restaurant": _restaurant("静安雕塑公园周边简餐", "中西式简餐", ["本地面点", "轻食", "咖啡"], "¥60-130", 8, "步行距离短，适合博物馆参观后的快速午餐。"),
    },
    "徐汇滨江与西岸美术区": {
        "summary": "黄浦江滨水步道、工业遗存与美术馆构成的开放型文化路线。",
        "highlights": ["滨江步道", "西岸艺术中心", "工业建筑更新"],
        "best_time": "14:00-19:00",
        "visit_tip": "场馆展期差异较大，出发前确认当日开放展览；户外路段较长。",
        "lat": 31.1766,
        "lon": 121.4632,
        "spend": {"optional_min": 60, "optional_max": 260, "optional_label": "展览/咖啡/骑行"},
        "restaurant": _restaurant("西岸滨江餐厅（龙腾大道周边）", "创意中餐与简餐", ["时令套餐", "咖啡甜点", "江景轻食"], "¥100-240", 10, "适合在滨江步行中途休息，优先选择靠近当日展馆的门店。"),
    },
    "北外滩滨江": {
        "summary": "从北侧观看陆家嘴天际线，空间比外滩核心段更舒展。",
        "highlights": ["北外滩滨水空间", "浦东天际线", "日落摄影"],
        "best_time": "16:30-19:30",
        "visit_tip": "与外滩景观相似但视角不同，行程紧张时二选一即可。",
        "lat": 31.2510,
        "lon": 121.4970,
        "spend": {"optional_min": 0, "optional_max": 160, "optional_label": "咖啡/观景体验"},
        "restaurant": _restaurant("上海小南国（北外滩商圈）", "上海本帮菜", ["葱油海蜇", "红烧肉", "酒酿圆子"], "¥150-280", 12, "适合日落后用餐，可与北外滩夜景顺路衔接。"),
    },
}


DEFAULT_SPEND = {
    "food": {"optional_min": 20, "optional_max": 160, "optional_label": "加餐/特色体验"},
    "viewpoint": {"optional_min": 0, "optional_max": 180, "optional_label": "观景/摄影体验"},
    "museum": {"optional_min": 0, "optional_max": 120, "optional_label": "特展/文创"},
    "history": {"optional_min": 20, "optional_max": 150, "optional_label": "讲解/文创"},
}


def destination_key(destination: str) -> Optional[str]:
    value = (destination or "").lower()
    for alias, key in DESTINATION_KEYS.items():
        if alias in value:
            return key
    return None


def enrich_poi_catalog(destination: str, pois: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    key = destination_key(destination)
    details = SHANGHAI_POI_DETAILS if key == "shanghai" else {}
    enriched = []
    for raw_poi in pois:
        poi = copy.deepcopy(raw_poi)
        detail = copy.deepcopy(details.get(poi["name"], {}))
        poi.update(detail)
        if key in KNOWN_POI_COORDINATES and poi["name"] in KNOWN_POI_COORDINATES[key]:
            lat, lon = KNOWN_POI_COORDINATES[key][poi["name"]]
            poi.setdefault("lat", lat)
            poi.setdefault("lon", lon)
        poi.setdefault("summary", f"围绕{poi['name']}安排一段有重点、不过度赶路的到访体验。")
        poi.setdefault("highlights", [poi["name"], "在地文化", "自由探索"])
        poi.setdefault("best_time", "09:00-17:00")
        poi.setdefault("visit_tip", "出发前确认开放时间与预约要求。")
        poi.setdefault("remote", False)
        poi.setdefault("spend", copy.deepcopy(DEFAULT_SPEND.get(poi["category"], {"optional_min": 0, "optional_max": 120, "optional_label": "可选体验"})))
        poi.setdefault(
            "restaurant",
            {
                "name": f"{poi['name']}附近本地餐馆",
                "cuisine": "当地风味",
                "signature_dishes": ["本地时令菜", "招牌小吃"],
                "price_per_person": "¥60-150",
                "travel_minutes": 10,
                "reason": "优先选择步行可达且近期评分稳定的本地餐馆。",
                "map_url": "",
                "source_url": "",
            },
        )
        enriched.append(poi)
    return enriched


def haversine_km(first: Dict[str, Any], second: Dict[str, Any]) -> float:
    if not all(first.get(field) is not None and second.get(field) is not None for field in ("lat", "lon")):
        return 0.0
    radius = 6371.0
    lat1, lon1 = math.radians(first["lat"]), math.radians(first["lon"])
    lat2, lon2 = math.radians(second["lat"]), math.radians(second["lon"])
    dlat, dlon = lat2 - lat1, lon2 - lon1
    value = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(value), math.sqrt(1 - value))


def _transport_estimate(distance: float, profile_id: str, people: int) -> Dict[str, Any]:
    if distance <= 1.2:
        return {"mode": "步行", "minutes": max(8, round(distance * 14)), "cost": 0}
    if profile_id == "experience_first" and distance <= 18:
        return {
            "mode": "打车",
            "minutes": round(10 + distance * 2.7),
            "cost": round(16 + distance * 3.2),
        }
    if distance <= 6:
        return {
            "mode": "地铁 + 步行",
            "minutes": round(16 + distance * 4.5),
            "cost": 4 * people,
        }
    if distance <= 20:
        return {
            "mode": "地铁 + 短途打车",
            "minutes": round(22 + distance * 3.2),
            "cost": 8 * people + 18,
        }
    return {
        "mode": "市域地铁 + 短途打车",
        "minutes": round(38 + distance * 1.05),
        "cost": 12 * people + 35,
    }


def build_route_plan(
    destination: str,
    day_pois: List[Dict[str, Any]],
    profile_id: str,
    people: int,
) -> Dict[str, Any]:
    key = destination_key(destination)
    center = copy.deepcopy(DESTINATION_CENTERS.get(key))
    located = [poi for poi in day_pois if poi.get("lat") is not None and poi.get("lon") is not None]
    if not center or len(located) != len(day_pois):
        return {
            "map_points": [],
            "route_legs": [],
            "route_distance_km": 0,
            "route_minutes": 0,
            "estimated_transport_cost": 0,
            "route_note": "该目的地暂缺完整坐标，地图暂不绘制；交通采用城市日均估算。若要支持地图，需要为该城市补充住宿区中心和景点坐标，或接入地理编码服务。",
            "map_status": "missing_coordinates",
        }

    points = [
        {
            "label": center["name"],
            "lat": center["lat"],
            "lon": center["lon"],
            "order": "H",
            "kind": "hotel",
            "color": [23, 63, 50, 220],
        }
    ]
    for index, poi in enumerate(day_pois, start=1):
        points.append(
            {
                "label": poi["name"],
                "lat": poi["lat"],
                "lon": poi["lon"],
                "order": str(index),
                "kind": "poi",
                "color": [227, 93, 66, 230],
            }
        )

    route_nodes = [center, *day_pois, center]
    legs = []
    for index in range(len(route_nodes) - 1):
        start, end = route_nodes[index], route_nodes[index + 1]
        distance = haversine_km(start, end)
        estimate = _transport_estimate(distance, profile_id, people)
        from_name = start.get("name", center["name"])
        to_name = end.get("name", center["name"])
        legs.append(
            {
                "from": from_name,
                "to": to_name,
                "distance_km": round(distance, 1),
                "mode": estimate["mode"],
                "minutes": estimate["minutes"],
                "estimated_cost": estimate["cost"],
                "path": [[start["lon"], start["lat"]], [end["lon"], end["lat"]]],
                "label": f"{from_name} → {to_name}",
                "detail": f"{distance:.1f} km · {estimate['mode']} · 约 {estimate['minutes']} 分钟",
            }
        )

    total_distance = round(sum(leg["distance_km"] for leg in legs), 1)
    total_minutes = sum(leg["minutes"] for leg in legs)
    total_cost = sum(leg["estimated_cost"] for leg in legs)
    has_remote = any(poi.get("remote") for poi in day_pois)
    note = "远郊专线日：已与市中心景点拆分，建议早出发。" if has_remote else "路线按住宿区往返估算，实际时间受候车与拥堵影响。"
    return {
        "map_points": points,
        "route_legs": legs,
        "route_distance_km": total_distance,
        "route_minutes": total_minutes,
        "estimated_transport_cost": round(total_cost, 2),
        "route_note": note,
        "map_status": "ready",
    }