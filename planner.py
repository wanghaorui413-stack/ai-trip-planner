import copy
from datetime import datetime, timedelta
import logging
import re
from typing import Any, Dict, List, Optional

from budget_estimator import (
    CURRENCY,
    estimate_candidate_budget,
    estimate_poi_cost,
    get_traveler_profile,
    normalize_budget_constraint,
    normalize_traveler_type,
)
from itinerary_validator import validate_itineraries
from outfit_advisor import get_city_outfit, get_poi_outfit
from ranker import rank_itineraries, score_candidate
from trip_catalog import build_route_plan, destination_key, enrich_poi_catalog, haversine_km

logger = logging.getLogger(__name__)

CANDIDATE_PROFILES = [
    {
        "id": "economy",
        "title": "经济型",
        "strategy": "控制门票和交通成本，优先城市漫步、公共交通和高性价比餐饮。",
        "hotel_tier": "经济连锁/民宿",
        "hotel_name_suffix": "高性价比住宿",
        "transport_mode": "公共交通 + 步行",
        "meal_style": "本地小吃、简餐和社区餐馆",
        "poi_count": 3,
        "tags": ["budget", "city_walk", "local_life", "food", "landmark"],
    },
    {
        "id": "comfort",
        "title": "舒适型",
        "strategy": "在经典景点、舒适住宿和适度休息之间取得平衡。",
        "hotel_tier": "舒适型酒店",
        "hotel_name_suffix": "舒适精选酒店",
        "transport_mode": "公共交通 + 短途打车",
        "meal_style": "口碑餐厅和轻量特色体验",
        "poi_count": 3,
        "tags": ["comfort", "culture", "history", "nature", "food"],
    },
    {
        "id": "experience_first",
        "title": "体验优先型",
        "strategy": "优先安排特色体验、深度文化和更省心的交通衔接。",
        "hotel_tier": "精品/高端酒店",
        "hotel_name_suffix": "体验型精品酒店",
        "transport_mode": "打车/包车 + 少量步行",
        "meal_style": "特色餐厅、预约制体验和在地风味",
        "poi_count": 4,
        "tags": ["experience", "culture", "food", "viewpoint", "nightlife"],
    },
]

DESTINATION_POIS = {
    "shanghai": [
        {"name": "外滩", "category": "landmark", "duration_hours": 2.0, "base_cost": 0, "tags": ["city_walk", "history", "viewpoint"]},
        {"name": "豫园与城隍庙", "category": "history", "duration_hours": 2.5, "base_cost": 40, "tags": ["history", "culture", "food"]},
        {"name": "上海博物馆", "category": "museum", "duration_hours": 2.5, "base_cost": 0, "tags": ["culture", "museum"]},
        {"name": "武康路历史街区", "category": "city_walk", "duration_hours": 2.0, "base_cost": 0, "tags": ["local_life", "history", "cafe"]},
        {"name": "陆家嘴观景区", "category": "viewpoint", "duration_hours": 2.0, "base_cost": 180, "tags": ["landmark", "viewpoint"]},
        {"name": "田子坊", "category": "local_life", "duration_hours": 1.5, "base_cost": 0, "tags": ["shopping", "food", "city_walk"]},
        {"name": "朱家角古镇", "category": "history", "duration_hours": 4.0, "base_cost": 80, "tags": ["history", "culture", "nature"]},
        {"name": "本帮菜体验", "category": "food", "duration_hours": 2.0, "base_cost": 180, "tags": ["food", "experience"]},
        {"name": "新天地石库门街区", "category": "local_life", "duration_hours": 2.0, "base_cost": 0, "tags": ["history", "culture", "food", "city_walk"]},
        {"name": "上海自然博物馆", "category": "museum", "duration_hours": 3.0, "base_cost": 30, "tags": ["museum", "nature", "family"]},
        {"name": "徐汇滨江与西岸美术区", "category": "culture", "duration_hours": 3.0, "base_cost": 80, "tags": ["art", "nature", "city_walk"]},
        {"name": "北外滩滨江", "category": "viewpoint", "duration_hours": 2.0, "base_cost": 0, "tags": ["viewpoint", "city_walk", "landmark"]},
    ],
    "hangzhou": [
        {"name": "西湖环线", "category": "nature", "duration_hours": 3.0, "base_cost": 0, "tags": ["nature", "city_walk", "landmark"]},
        {"name": "灵隐寺", "category": "history", "duration_hours": 2.5, "base_cost": 75, "tags": ["history", "culture"]},
        {"name": "龙井村", "category": "local_life", "duration_hours": 2.5, "base_cost": 80, "tags": ["nature", "tea", "culture"]},
        {"name": "西溪湿地", "category": "nature", "duration_hours": 3.0, "base_cost": 120, "tags": ["nature", "family"]},
        {"name": "河坊街", "category": "food", "duration_hours": 2.0, "base_cost": 80, "tags": ["food", "shopping", "history"]},
        {"name": "中国茶叶博物馆", "category": "museum", "duration_hours": 2.0, "base_cost": 0, "tags": ["culture", "museum", "tea"]},
        {"name": "京杭大运河杭州段", "category": "city_walk", "duration_hours": 2.0, "base_cost": 60, "tags": ["history", "local_life"]},
    ],
    "chengdu": [
        {"name": "成都大熊猫繁育研究基地", "category": "nature", "duration_hours": 3.0, "base_cost": 80, "tags": ["nature", "family"]},
        {"name": "宽窄巷子", "category": "local_life", "duration_hours": 2.0, "base_cost": 0, "tags": ["food", "city_walk", "culture"]},
        {"name": "武侯祠", "category": "history", "duration_hours": 2.0, "base_cost": 60, "tags": ["history", "culture"]},
        {"name": "锦里", "category": "food", "duration_hours": 2.0, "base_cost": 80, "tags": ["food", "shopping", "history"]},
        {"name": "杜甫草堂", "category": "culture", "duration_hours": 2.0, "base_cost": 60, "tags": ["culture", "history"]},
        {"name": "人民公园", "category": "local_life", "duration_hours": 1.5, "base_cost": 40, "tags": ["local_life", "tea", "relaxed"]},
        {"name": "川菜/火锅体验", "category": "food", "duration_hours": 2.0, "base_cost": 180, "tags": ["food", "experience"]},
        {"name": "青城山", "category": "nature", "duration_hours": 5.0, "base_cost": 120, "tags": ["nature", "history"]},
    ],
    "tokyo": [
        {"name": "浅草寺与仲见世商店街", "category": "history", "duration_hours": 2.5, "base_cost": 40, "tags": ["history", "culture", "shopping"]},
        {"name": "上野公园与博物馆区", "category": "museum", "duration_hours": 3.0, "base_cost": 90, "tags": ["culture", "museum", "nature"]},
        {"name": "涩谷与原宿街区", "category": "city_walk", "duration_hours": 3.0, "base_cost": 80, "tags": ["shopping", "local_life", "food"]},
        {"name": "明治神宫", "category": "culture", "duration_hours": 2.0, "base_cost": 0, "tags": ["culture", "nature"]},
        {"name": "筑地/丰洲市场", "category": "food", "duration_hours": 2.0, "base_cost": 180, "tags": ["food", "local_life"]},
        {"name": "东京塔或晴空塔", "category": "viewpoint", "duration_hours": 2.0, "base_cost": 220, "tags": ["landmark", "viewpoint"]},
        {"name": "teamLab 沉浸式展览", "category": "experience", "duration_hours": 2.5, "base_cost": 260, "tags": ["experience", "art"]},
    ],
    "kyoto": [
        {"name": "伏见稻荷大社", "category": "history", "duration_hours": 2.5, "base_cost": 0, "tags": ["history", "culture", "nature"]},
        {"name": "清水寺与二年坂三年坂", "category": "history", "duration_hours": 3.0, "base_cost": 80, "tags": ["history", "culture", "shopping"]},
        {"name": "岚山竹林与渡月桥", "category": "nature", "duration_hours": 3.5, "base_cost": 80, "tags": ["nature", "landmark"]},
        {"name": "金阁寺", "category": "culture", "duration_hours": 1.5, "base_cost": 60, "tags": ["culture", "history"]},
        {"name": "祇园花见小路", "category": "city_walk", "duration_hours": 2.0, "base_cost": 0, "tags": ["culture", "local_life", "nightlife"]},
        {"name": "锦市场", "category": "food", "duration_hours": 2.0, "base_cost": 160, "tags": ["food", "local_life"]},
        {"name": "和服/茶道体验", "category": "experience", "duration_hours": 2.5, "base_cost": 300, "tags": ["experience", "culture"]},
    ],
}

DESTINATION_ALIASES = {
    "上海": "shanghai",
    "杭州": "hangzhou",
    "成都": "chengdu",
    "东京": "tokyo",
    "京都": "kyoto",
}


def _generic_pois(destination: str) -> List[Dict[str, Any]]:
    return [
        {"name": f"{destination}城市地标", "category": "landmark", "duration_hours": 2.0, "base_cost": 40, "tags": ["landmark", "city_walk"]},
        {"name": f"{destination}历史文化街区", "category": "history", "duration_hours": 2.5, "base_cost": 70, "tags": ["history", "culture"]},
        {"name": f"{destination}博物馆/艺术馆", "category": "museum", "duration_hours": 2.5, "base_cost": 60, "tags": ["museum", "culture"]},
        {"name": f"{destination}自然公园", "category": "nature", "duration_hours": 2.5, "base_cost": 50, "tags": ["nature", "family"]},
        {"name": f"{destination}本地美食街", "category": "food", "duration_hours": 2.0, "base_cost": 120, "tags": ["food", "local_life"]},
        {"name": f"{destination}特色体验活动", "category": "experience", "duration_hours": 2.0, "base_cost": 220, "tags": ["experience", "culture"]},
        {"name": f"{destination}观景点", "category": "viewpoint", "duration_hours": 1.5, "base_cost": 120, "tags": ["viewpoint", "landmark"]},
    ]


def _get_destination_pois(destination: str) -> List[Dict[str, Any]]:
    destination_key = (destination or "").lower()
    for alias, canonical in DESTINATION_ALIASES.items():
        if alias in destination_key:
            return enrich_poi_catalog(destination, DESTINATION_POIS[canonical])
    for keyword, pois in DESTINATION_POIS.items():
        if keyword in destination_key:
            return enrich_poi_catalog(destination, pois)
    return enrich_poi_catalog(destination, _generic_pois(destination))


PREFERENCE_TOKEN_ALIASES = {
    "历史": "history",
    "文化": "culture",
    "博物馆": "museum",
    "美食": "food",
    "餐": "food",
    "自然": "nature",
    "公园": "nature",
    "购物": "shopping",
    "亲子": "family",
    "家庭": "family",
    "夜生活": "nightlife",
    "体验": "experience",
    "街区": "local_life",
    "漫步": "city_walk",
}


def _preference_tokens(preferences: Optional[Any]) -> List[str]:
    if not preferences:
        return []
    if isinstance(preferences, (list, tuple, set)):
        raw = " ".join(str(item) for item in preferences)
    else:
        raw = str(preferences)

    raw_tokens = [token for token in re.split(r"[\s,;，；、/]+", raw.lower()) if token]
    expanded_tokens = []
    for token in raw_tokens:
        expanded_tokens.append(token)
        for keyword, normalized in PREFERENCE_TOKEN_ALIASES.items():
            if keyword in token:
                expanded_tokens.append(normalized)
    return list(dict.fromkeys(expanded_tokens))


def _score_poi(poi: Dict[str, Any], profile: Dict[str, Any], preferences: Optional[Any]) -> float:
    score = 1.0
    poi_terms = " ".join([poi["category"], poi["name"], " ".join(poi.get("tags", []))]).lower()

    for tag in profile.get("tags", []):
        if tag in poi_terms:
            score += 1.2

    for token in _preference_tokens(preferences):
        if token and token in poi_terms:
            score += 1.8

    base_cost = float(poi.get("base_cost", 0))
    if profile["id"] == "economy" and base_cost <= 80:
        score += 1.0
    if profile["id"] == "experience_first" and poi["category"] in {"experience", "food", "viewpoint"}:
        score += 1.3
    if profile["id"] == "comfort" and poi["category"] in {"history", "culture", "nature", "food"}:
        score += 0.9

    return score


def _poi_count_for_profile(profile: Dict[str, Any], traveler_type: Optional[str]) -> int:
    traveler = normalize_traveler_type(traveler_type)
    count = int(profile["poi_count"])
    if traveler in {"family", "senior", "business"}:
        count = max(2, count - 1)
    if traveler == "friends" and profile["id"] == "experience_first":
        count += 1
    return count


def _extract_rag_hint(poi_name: str, rag_context: str) -> str:
    if not rag_context:
        return ""

    normalized_name = re.sub(r"\s+", "", poi_name.lower())
    sentences = re.split(r"(?<=[。.!?])\s+|\n+", rag_context.strip())
    for sentence in sentences:
        normalized_sentence = re.sub(r"\s+", "", sentence.lower())
        if normalized_name[:4] and normalized_name[:4] in normalized_sentence:
            return sentence.strip()[:90]
    return ""


def _build_reason(
    poi: Dict[str, Any],
    preferences: Optional[Any],
    rag_context: str,
    rag_sources: List[str],
) -> str:
    if isinstance(preferences, (list, tuple, set)):
        preference_items = [str(item).strip() for item in preferences if str(item).strip()]
    else:
        preference_items = [item for item in re.split(r"[\s,;，；、/]+", str(preferences or "")) if item]
    preference_text = "、".join(preference_items[:3])
    reason_parts = [
        f"匹配 {poi.get('category')} 主题",
    ]
    if preference_text:
        reason_parts.append(f"兼顾偏好: {preference_text}")

    rag_hint = _extract_rag_hint(poi["name"], rag_context)
    if rag_hint:
        reason_parts.append(f"RAG补充: {rag_hint}")
    elif rag_sources:
        reason_parts.append("RAG资料用于补充到访背景与推荐理由")
    return "；".join(reason_parts)


CATEGORY_LABELS = {
    "landmark": "城市地标",
    "history": "历史文化",
    "museum": "博物馆",
    "city_walk": "街区漫步",
    "viewpoint": "城市观景",
    "local_life": "在地生活",
    "food": "美食体验",
    "nature": "自然风景",
    "culture": "文化体验",
    "experience": "特色体验",
}

WEEKDAY_LABELS = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def _canonical_destination_key(destination: str) -> Optional[str]:
    key = destination_key(destination)
    if key:
        return key
    value = (destination or "").lower()
    for alias, canonical in DESTINATION_ALIASES.items():
        if alias in value:
            return canonical
    for canonical in DESTINATION_POIS:
        if canonical in value:
            return canonical
    return None


def _normalize_start_date(start_date: Optional[Any]) -> Optional[Any]:
    if not start_date:
        return None
    try:
        return datetime.strptime(str(start_date)[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def _date_payload(start_date: Optional[Any], day_offset: int) -> Dict[str, str]:
    start = _normalize_start_date(start_date)
    if not start:
        return {}
    current = start + timedelta(days=day_offset)
    weekday = WEEKDAY_LABELS[current.weekday()]
    return {
        "date": current.isoformat(),
        "weekday": weekday,
        "date_label": f"{current.month}月{current.day}日 · {weekday}",
    }


def _travel_dates(start_date: Optional[Any], days: int) -> List[Dict[str, str]]:
    return [_date_payload(start_date, offset) for offset in range(max(int(days or 0), 0)) if _date_payload(start_date, offset)]


def _summarize_data_quality(
    destination: str,
    candidates: List[Dict[str, Any]],
    rag_sources: List[str],
) -> Dict[str, Any]:
    canonical = _canonical_destination_key(destination)
    first_candidate = candidates[0] if candidates else {}
    days = first_candidate.get("daily_plan", [])
    total_days = len(days)
    mapped_days = sum(1 for day in days if day.get("map_status") == "ready")
    catalog_status = "内置城市景点库" if canonical else "通用城市模板"
    map_status = "完整" if total_days and mapped_days == total_days else "部分" if mapped_days else "缺坐标"
    return {
        "city_key": canonical,
        "catalog_status": catalog_status,
        "map_status": map_status,
        "mapped_days": mapped_days,
        "total_days": total_days,
        "rag_status": "有本地知识库补充" if rag_sources else "暂无本地知识库命中",
        "items": [
            {
                "label": "景点库",
                "value": catalog_status,
                "detail": "内置库可支持下拉替换和景点坐标；通用模板仅适合初稿。",
                "level": "good" if canonical else "warn",
            },
            {
                "label": "地图坐标",
                "value": f"{mapped_days}/{total_days} 天可绘制" if total_days else "未生成",
                "detail": "缺坐标时继续生成行程，但不绘制地图路线。",
                "level": "good" if total_days and mapped_days == total_days else "warn",
            },
            {
                "label": "RAG 知识库",
                "value": "已命中" if rag_sources else "未命中",
                "detail": "RAG 只补充推荐理由；没有命中时使用本地规划器。",
                "level": "good" if rag_sources else "neutral",
            },
            {
                "label": "价格/营业",
                "value": "需实时核验",
                "detail": "酒店、餐厅评分、门票和营业状态均可能随日期变化。",
                "level": "warn",
            },
        ],
    }


def _profile_by_id(profile_id: str) -> Dict[str, Any]:
    return next((profile for profile in CANDIDATE_PROFILES if profile["id"] == profile_id), CANDIDATE_PROFILES[1])


def _build_poi_payload(
    poi: Dict[str, Any],
    profile: Dict[str, Any],
    destination: str,
    preferences: Optional[Any],
    rag_context: str,
    rag_sources: List[str],
) -> Dict[str, Any]:
    admission = estimate_poi_cost(
        poi["category"],
        profile["id"],
        destination,
        poi.get("base_cost"),
    )
    spend = copy.deepcopy(poi.get("spend", {}))
    restaurant = copy.deepcopy(poi.get("restaurant", {}))
    return {
        "name": poi["name"],
        "category": poi["category"],
        "duration_hours": poi["duration_hours"],
        "estimated_cost": admission,
        "reason": _build_reason(poi, preferences, rag_context, rag_sources),
        "tags": poi.get("tags", []),
        "outfit_advice": get_poi_outfit(destination, poi),
        "summary": poi.get("summary", ""),
        "highlights": poi.get("highlights", []),
        "best_time": poi.get("best_time", ""),
        "visit_tip": poi.get("visit_tip", ""),
        "lat": poi.get("lat"),
        "lon": poi.get("lon"),
        "remote": poi.get("remote", False),
        "image": poi.get("image", ""),
        "image_source": poi.get("image_source", ""),
        "image_credit": poi.get("image_credit", ""),
        "spend_breakdown": {
            "admission": admission,
            "meal_reference": restaurant.get("price_per_person", "按实际点餐"),
            "optional_min": spend.get("optional_min", 0),
            "optional_max": spend.get("optional_max", 0),
            "optional_label": spend.get("optional_label", "可选体验"),
            "note": "均为人均参考；餐饮与市内交通已在方案总预算中统一估算。",
        },
        "restaurant": restaurant,
    }


def _distance_between_pois(first: Dict[str, Any], second: Dict[str, Any]) -> float:
    if first.get("lat") is None or second.get("lat") is None:
        return 0.0
    return haversine_km(first, second)


def _choose_day_pois(
    remaining: List[Dict[str, Any]],
    all_pois: List[Dict[str, Any]],
    per_day: int,
    day_index: int,
    profile: Dict[str, Any],
    preferences: Optional[Any],
) -> List[Dict[str, Any]]:
    if remaining:
        seed = remaining.pop(0)
    else:
        seed = all_pois[day_index % len(all_pois)]

    selected = [seed]
    if seed.get("remote"):
        return selected

    while len(selected) < per_day and remaining:
        last = selected[-1]
        compatible = [poi for poi in remaining if not poi.get("remote")]
        if not compatible:
            break
        compatible.sort(
            key=lambda poi: (
                _score_poi(poi, profile, preferences)
                - _distance_between_pois(last, poi) * 0.28
            ),
            reverse=True,
        )
        nearest = compatible[0]
        if _distance_between_pois(last, nearest) > 18:
            break
        remaining.remove(nearest)
        selected.append(nearest)
    return selected


def _refresh_day_route(
    day_payload: Dict[str, Any],
    destination: str,
    profile: Dict[str, Any],
    traveler_type: Optional[str],
) -> Dict[str, Any]:
    people = get_traveler_profile(traveler_type)["people"]
    route = build_route_plan(destination, day_payload.get("pois", []), profile["id"], people)
    day_payload.update(route)
    modes = list(dict.fromkeys(leg["mode"] for leg in route.get("route_legs", [])))
    day_payload["daily_transport"] = " + ".join(modes) if modes else profile["transport_mode"]
    categories = list(dict.fromkeys(poi["category"] for poi in day_payload.get("pois", [])))
    day_payload["theme"] = " · ".join(CATEGORY_LABELS.get(category, category) for category in categories)
    return day_payload


def _build_daily_plan(
    destination: str,
    days: int,
    profile: Dict[str, Any],
    preferences: Optional[Any],
    traveler_type: Optional[str],
    rag_context: str,
    rag_sources: List[str],
    start_date: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    pois = sorted(
        _get_destination_pois(destination),
        key=lambda poi: _score_poi(poi, profile, preferences),
        reverse=True,
    )
    per_day = _poi_count_for_profile(profile, traveler_type)
    remaining = list(pois)
    daily_plan = []

    for day_index in range(days):
        selected = _choose_day_pois(
            remaining=remaining,
            all_pois=pois,
            per_day=per_day,
            day_index=day_index,
            profile=profile,
            preferences=preferences,
        )
        day_payload = {
            "day": day_index + 1,
            **_date_payload(start_date, day_index),
            "theme": "",
            "pois": [
                _build_poi_payload(
                    poi,
                    profile,
                    destination,
                    preferences,
                    rag_context,
                    rag_sources,
                )
                for poi in selected
            ],
            "meal_suggestion": profile["meal_style"],
        }
        daily_plan.append(
            _refresh_day_route(day_payload, destination, profile, traveler_type)
        )

    return daily_plan


def list_destination_poi_catalog(
    destination: str,
    profile_id: str = "comfort",
    preferences: Optional[Any] = None,
    traveler_type: Optional[str] = "solo",
) -> List[Dict[str, Any]]:
    profile = _profile_by_id(profile_id)
    catalog = []
    for poi in _get_destination_pois(destination):
        payload = _build_poi_payload(
            poi=poi,
            profile=profile,
            destination=destination,
            preferences=preferences,
            rag_context="",
            rag_sources=[],
        )
        payload["category_label"] = CATEGORY_LABELS.get(payload.get("category"), payload.get("category", ""))
        payload["label"] = (
            f"{payload['name']} · {payload['category_label']} · "
            f"{payload.get('duration_hours', 0):g} 小时"
        )
        catalog.append(payload)
    return catalog


def _order_selected_pois(
    pois: List[Dict[str, Any]],
    profile: Dict[str, Any],
    preferences: Optional[Any],
) -> List[Dict[str, Any]]:
    remaining = sorted(
        list(pois),
        key=lambda poi: _score_poi(poi, profile, preferences),
        reverse=True,
    )
    if not remaining:
        return []

    ordered = [remaining.pop(0)]
    while remaining:
        current = ordered[-1]
        remaining.sort(
            key=lambda poi: (
                _distance_between_pois(current, poi)
                - _score_poi(poi, profile, preferences) * 0.04
            )
        )
        ordered.append(remaining.pop(0))
    return ordered


def _group_selected_pois(
    selected_pois: List[Dict[str, Any]],
    days: int,
    profile: Dict[str, Any],
    preferences: Optional[Any],
) -> List[List[Dict[str, Any]]]:
    if not selected_pois:
        return []

    requested_days = max(1, int(days or 1))
    day_count = min(requested_days, len(selected_pois))
    remote = [poi for poi in selected_pois if poi.get("remote")]
    central = [poi for poi in selected_pois if not poi.get("remote")]
    groups: List[List[Dict[str, Any]]] = []

    remote_slots = min(len(remote), max(day_count - (1 if central else 0), 0))
    for poi in remote[:remote_slots]:
        groups.append([poi])

    remaining_remote = remote[remote_slots:]
    ordered_central = _order_selected_pois([*central, *remaining_remote], profile, preferences)
    remaining_days = max(day_count - len(groups), 1 if ordered_central else 0)
    if ordered_central:
        chunk_size = max(1, (len(ordered_central) + remaining_days - 1) // remaining_days)
        for offset in range(0, len(ordered_central), chunk_size):
            groups.append(ordered_central[offset : offset + chunk_size])

    return groups[:day_count]


def _build_daily_plan_from_selected_pois(
    destination: str,
    selected_pois: List[Dict[str, Any]],
    days: int,
    profile: Dict[str, Any],
    preferences: Optional[Any],
    traveler_type: Optional[str],
    start_date: Optional[Any] = None,
) -> List[Dict[str, Any]]:
    groups = _group_selected_pois(selected_pois, days, profile, preferences)
    daily_plan = []
    for day_index, group in enumerate(groups, start=1):
        day_payload = {
            "day": day_index,
            **_date_payload(start_date, day_index - 1),
            "theme": "",
            "pois": [
                _build_poi_payload(
                    poi=poi,
                    profile=profile,
                    destination=destination,
                    preferences=preferences,
                    rag_context="",
                    rag_sources=[],
                )
                for poi in group
            ],
            "meal_suggestion": profile["meal_style"],
            "selected_by_user": True,
        }
        daily_plan.append(_refresh_day_route(day_payload, destination, profile, traveler_type))
    return daily_plan


def _candidate_from_daily_plan(
    destination: str,
    days: int,
    profile: Dict[str, Any],
    budget: Optional[Any],
    preferences: Optional[Any],
    traveler_type: Optional[str],
    daily_plan: List[Dict[str, Any]],
    title: str,
    strategy: str,
) -> Dict[str, Any]:
    nights = max(days - 1, 0)
    candidate = {
        "id": profile["id"],
        "title": title,
        "strategy": strategy,
        "currency": CURRENCY,
        "daily_plan": daily_plan,
        "hotel_option": {
            "name": f"{destination}{profile['hotel_name_suffix']}",
            "tier": profile["hotel_tier"],
            "nights": nights,
            "estimated_total": 0,
            "reason": "根据方案定位估算住宿档位，不调用真实酒店库存或价格接口。",
        },
        "transport_summary": {
            "mode": profile["transport_mode"],
            "estimated_total": 0,
            "notes": "仅估算目的地内交通，不包含往返大交通。",
        },
        "budget_breakdown": {},
        "total_budget": 0,
        "score": {},
        "warnings": [],
        "tags": profile["tags"],
    }
    breakdown = estimate_candidate_budget(candidate, destination, days, traveler_type)
    candidate["budget_breakdown"] = breakdown
    candidate["total_budget"] = breakdown["total"]
    candidate["hotel_option"]["estimated_total"] = breakdown["hotel_total"]
    candidate["transport_summary"]["estimated_total"] = breakdown["transport_total"]
    _apply_budget_details(candidate, breakdown, days)
    return candidate


def plan_selected_pois(
    destination: str,
    selected_pois: List[str],
    days: int,
    budget: Optional[Any],
    preferences: Optional[Any] = None,
    traveler_type: Optional[str] = "solo",
    profile_id: str = "comfort",
    start_date: Optional[Any] = None,
) -> Dict[str, Any]:
    if not destination:
        return {"error": "destination is required"}
    cleaned_names = [name for name in selected_pois if name]
    if not cleaned_names:
        return {"error": "至少选择一个景点"}

    catalog = _get_destination_pois(destination)
    catalog_by_name = {poi["name"]: poi for poi in catalog}
    missing = [name for name in cleaned_names if name not in catalog_by_name]
    if missing:
        return {"error": f"景点库中没有：{'、'.join(missing)}"}

    profile = _profile_by_id(profile_id)
    selected_catalog = [catalog_by_name[name] for name in dict.fromkeys(cleaned_names)]
    daily_plan = _build_daily_plan_from_selected_pois(
        destination=destination,
        selected_pois=selected_catalog,
        days=days,
        profile=profile,
        preferences=preferences,
        traveler_type=traveler_type,
        start_date=start_date,
    )
    effective_days = max(1, len(daily_plan))
    candidate = _candidate_from_daily_plan(
        destination=destination,
        days=effective_days,
        profile=profile,
        budget=budget,
        preferences=preferences,
        traveler_type=traveler_type,
        daily_plan=daily_plan,
        title="我的自选路线",
        strategy="仅使用你勾选的景点，并按距离、远郊独立性和每日强度自动重排行程。",
    )
    candidate["selected_pois"] = [poi["name"] for poi in selected_catalog]

    ranked = rank_itineraries(
        [candidate],
        budget=budget,
        days=effective_days,
        preferences=preferences,
        traveler_type=traveler_type,
    )
    validated = validate_itineraries(
        ranked,
        budget=budget,
        days=effective_days,
        traveler_type=traveler_type,
    )
    return {
        "destination": destination,
        "city_outfit": get_city_outfit(destination),
        "days": effective_days,
        "start_date": _normalize_start_date(start_date).isoformat() if _normalize_start_date(start_date) else None,
        "travel_dates": _travel_dates(start_date, effective_days),
        "budget_limit": normalize_budget_constraint(budget, effective_days, traveler_type),
        "preferences": preferences or "",
        "traveler_type": normalize_traveler_type(traveler_type),
        "currency": CURRENCY,
        "source": "selected_pois",
        "data_quality": _summarize_data_quality(destination, validated, []),
        "poi_catalog": list_destination_poi_catalog(destination, profile["id"], preferences, traveler_type),
        "candidates": validated,
    }
def _apply_budget_details(candidate: Dict[str, Any], breakdown: Dict[str, Any], days: int) -> None:
    nights = breakdown.get("nights", 0)
    rooms = breakdown.get("rooms", 1)
    hotel_total = breakdown.get("hotel_total", 0)
    divisor = max(nights * rooms, 1)
    candidate["hotel_option"]["breakdown"] = {
        "rooms": rooms,
        "nights": nights,
        "nightly_rate": round(hotel_total / divisor, 2) if nights else 0,
        "room_charge": hotel_total,
        "includes": "参考房费；不含真实库存、押金及临时加价。",
    }
    candidate["transport_summary"]["breakdown"] = {
        "days": [
            {
                "day": day.get("day"),
                "distance_km": day.get("route_distance_km", 0),
                "minutes": day.get("route_minutes", 0),
                "estimated_cost": day.get("estimated_transport_cost", 0),
            }
            for day in candidate.get("daily_plan", [])
        ],
        "average_per_day": round(breakdown.get("transport_total", 0) / max(days, 1), 2),
        "includes": "住宿区往返、景点间接驳；不含机场/高铁站与跨城交通。",
    }

def _build_candidate(
    destination: str,
    days: int,
    profile: Dict[str, Any],
    budget: Optional[Any],
    preferences: Optional[Any],
    traveler_type: Optional[str],
    rag_context: str,
    rag_sources: List[str],
    start_date: Optional[Any] = None,
) -> Dict[str, Any]:
    daily_plan = _build_daily_plan(
        destination=destination,
        days=days,
        profile=profile,
        preferences=preferences,
        traveler_type=traveler_type,
        rag_context=rag_context,
        rag_sources=rag_sources,
        start_date=start_date,
    )
    nights = max(days - 1, 0)
    candidate = {
        "id": profile["id"],
        "title": profile["title"],
        "strategy": profile["strategy"],
        "currency": CURRENCY,
        "daily_plan": daily_plan,
        "hotel_option": {
            "name": f"{destination}{profile['hotel_name_suffix']}",
            "tier": profile["hotel_tier"],
            "nights": nights,
            "estimated_total": 0,
            "reason": "根据方案定位估算住宿档位，不调用真实酒店库存或价格接口。",
        },
        "transport_summary": {
            "mode": profile["transport_mode"],
            "estimated_total": 0,
            "notes": "仅估算目的地内交通，不包含往返大交通。",
        },
        "budget_breakdown": {},
        "total_budget": 0,
        "score": {},
        "warnings": [],
        "tags": profile["tags"],
    }

    breakdown = estimate_candidate_budget(candidate, destination, days, traveler_type)
    candidate["budget_breakdown"] = breakdown
    candidate["total_budget"] = breakdown["total"]
    candidate["hotel_option"]["estimated_total"] = breakdown["hotel_total"]
    candidate["transport_summary"]["estimated_total"] = breakdown["transport_total"]
    _apply_budget_details(candidate, breakdown, days)

    budget_limit = normalize_budget_constraint(budget, days, traveler_type)
    if budget_limit:
        candidate["budget_gap"] = round(budget_limit - candidate["total_budget"], 2)

    return candidate


def replace_candidate_poi(
    candidate: Dict[str, Any],
    destination: str,
    day_index: int,
    poi_index: int,
    budget: Optional[Any],
    preferences: Optional[Any],
    traveler_type: Optional[str],
    replacement_name: Optional[str] = None,
) -> Dict[str, Any]:
    updated = copy.deepcopy(candidate)
    profile = _profile_by_id(updated.get("id", "comfort"))
    daily_plan = updated.get("daily_plan", [])
    if not (0 <= day_index < len(daily_plan)):
        raise ValueError("day_index is out of range")
    day = daily_plan[day_index]
    if not (0 <= poi_index < len(day.get("pois", []))):
        raise ValueError("poi_index is out of range")

    current = day["pois"][poi_index]
    used_names = {
        poi.get("name")
        for plan_day in daily_plan
        for poi in plan_day.get("pois", [])
    }
    catalog = _get_destination_pois(destination)
    replacement = None
    if replacement_name:
        replacement = next((poi for poi in catalog if poi["name"] == replacement_name), None)
        if not replacement:
            raise ValueError(f"景点库中没有：{replacement_name}")
        duplicate_names = used_names - {current.get("name")}
        if replacement["name"] in duplicate_names:
            raise ValueError("该景点已在当前方案中，请选择未重复的景点")
    else:
        alternatives = [poi for poi in catalog if poi["name"] not in used_names]
        if not alternatives:
            day_names = {poi.get("name") for poi in day.get("pois", [])}
            alternatives = [poi for poi in catalog if poi["name"] not in day_names]
        if not alternatives:
            raise ValueError("没有更多可替换景点")

        neighbors = [poi for index, poi in enumerate(day["pois"]) if index != poi_index]

        def replacement_score(poi: Dict[str, Any]) -> float:
            preference_score = _score_poi(poi, profile, preferences)
            distances = [_distance_between_pois(poi, neighbor) for neighbor in neighbors]
            route_penalty = (sum(distances) / len(distances)) * 0.32 if distances else 0
            remote_penalty = 8 if poi.get("remote") and neighbors else 0
            return preference_score - route_penalty - remote_penalty

        replacement = max(alternatives, key=replacement_score)
    day["pois"][poi_index] = _build_poi_payload(
        replacement,
        profile,
        destination,
        preferences,
        "",
        [],
    )
    _refresh_day_route(day, destination, profile, traveler_type)

    breakdown = estimate_candidate_budget(updated, destination, len(daily_plan), traveler_type)
    updated["budget_breakdown"] = breakdown
    updated["total_budget"] = breakdown["total"]
    updated["hotel_option"]["estimated_total"] = breakdown["hotel_total"]
    updated["transport_summary"]["estimated_total"] = breakdown["transport_total"]
    _apply_budget_details(updated, breakdown, len(daily_plan))
    updated["score"] = score_candidate(
        updated,
        budget_limit=normalize_budget_constraint(budget, len(daily_plan), traveler_type),
        preferences=preferences,
        traveler_type=traveler_type,
    )
    updated["last_replacement"] = {
        "from": current.get("name"),
        "to": replacement["name"],
        "day": day_index + 1,
    }
    return updated

def plan_trip(
    destination: str,
    days: int,
    budget: Optional[Any],
    preferences: Optional[Any] = None,
    traveler_type: Optional[str] = "solo",
    rag_context: str = "",
    rag_sources: Optional[List[str]] = None,
    start_date: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Generates budget-aware itinerary candidates and ranks them.
    RAG context is used only to enrich recommendation reasons; the planner,
    estimator, ranker, and validator remain deterministic and local.
    """
    if not destination:
        return {"error": "destination is required"}
    try:
        normalized_days = int(days)
    except (TypeError, ValueError):
        return {"error": "days must be an integer"}
    if normalized_days <= 0:
        return {"error": "days must be greater than 0"}

    rag_sources = rag_sources or []
    candidates = [
        _build_candidate(
            destination=destination,
            days=normalized_days,
            profile=profile,
            budget=budget,
            preferences=preferences,
            traveler_type=traveler_type,
            rag_context=rag_context,
            rag_sources=rag_sources,
            start_date=start_date,
        )
        for profile in CANDIDATE_PROFILES
    ]

    ranked = rank_itineraries(
        candidates,
        budget=budget,
        days=normalized_days,
        preferences=preferences,
        traveler_type=traveler_type,
    )
    validated = validate_itineraries(
        ranked,
        budget=budget,
        days=normalized_days,
        traveler_type=traveler_type,
    )

    result = {
        "destination": destination,
        "city_outfit": get_city_outfit(destination),
        "days": normalized_days,
        "start_date": _normalize_start_date(start_date).isoformat() if _normalize_start_date(start_date) else None,
        "travel_dates": _travel_dates(start_date, normalized_days),
        "budget_limit": normalize_budget_constraint(budget, normalized_days, traveler_type),
        "preferences": preferences or "",
        "traveler_type": normalize_traveler_type(traveler_type),
        "currency": CURRENCY,
        "data_quality": _summarize_data_quality(destination, validated, rag_sources),
        "rag": {
            "used_for": "explanation_and_recommendation_reasons_only",
            "sources": rag_sources,
        },
        "candidates": validated,
    }
    logger.info("Generated %s itinerary candidates for %s.", len(validated), destination)
    return result


def generate_itinerary_candidates(
    destination: str,
    days: int,
    budget: Optional[Any],
    preferences: Optional[Any] = None,
    traveler_type: Optional[str] = "solo",
    rag_context: str = "",
    rag_sources: Optional[List[str]] = None,
) -> Dict[str, Any]:
    return plan_trip(
        destination=destination,
        days=days,
        budget=budget,
        preferences=preferences,
        traveler_type=traveler_type,
        rag_context=rag_context,
        rag_sources=rag_sources,
    )
