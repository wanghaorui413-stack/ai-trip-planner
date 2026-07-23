import html
import os
from datetime import date
from urllib.parse import quote
from typing import Any, Dict, List, Tuple

import pydeck as pdk
import requests
import streamlit as st

BASE_API_URL = os.getenv("API_URL", "http://localhost:8000").rstrip("/")
API_ENDPOINT_PATH = os.getenv("API_ENDPOINT_PATH", "/api/plan-trip-options")
API_URL = f"{BASE_API_URL}{API_ENDPOINT_PATH}"
REPLACE_API_URL = f"{BASE_API_URL}/api/replace-poi"
CATALOG_API_URL = f"{BASE_API_URL}/api/poi-catalog"
SELECTED_POIS_API_URL = f"{BASE_API_URL}/api/plan-selected-pois"
CTRIP_HOTELS_URL = "https://hotels.ctrip.com/"

TRAVELER_OPTIONS = {
    "一个人": "solo",
    "两人同行": "couple",
    "朋友结伴": "friends",
    "家庭出游": "family",
    "商务出行": "business",
    "长辈同行": "senior",
}

st.set_page_config(
    page_title="Voyage Studio · AI 行程规划",
    page_icon="✦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
    <style>
    :root {
        --ink: #18231f;
        --forest: #173f32;
        --green: #2f6b52;
        --coral: #e35d42;
        --sun: #f0c75e;
        --paper: #f5f6f1;
        --white: #ffffff;
        --line: #dce2da;
        --muted: #68736d;
    }
    html, body, [class*="css"] {
        font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif;
        color: var(--ink);
    }
    .stApp { background: var(--paper); }
    [data-testid="stHeader"] { background: transparent; }
    [data-testid="stToolbar"] { right: 1rem; }
    .block-container {
        max-width: 1320px;
        padding: 1.6rem 2.5rem 3rem;
    }
    .voyage-hero {
        position: relative;
        margin-bottom: 1.35rem;
        padding: 1.35rem 1.5rem;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: rgba(255,255,255,.88);
        color: var(--ink);
    }
    .voyage-hero::after { content: none; }
    .hero-kicker {
        color: var(--coral);
        font-size: .72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .08rem;
    }
    .voyage-hero h1 {
        max-width: 760px;
        margin: .45rem 0 .35rem;
        color: var(--ink);
        font-size: 1.78rem;
        line-height: 1.22;
        letter-spacing: 0;
    }
    .voyage-hero p {
        max-width: 760px;
        margin: 0;
        color: var(--muted);
        font-size: .92rem;
    }
    .status-row {
        display: flex;
        align-items: center;
        gap: .55rem;
        margin-top: 1.2rem;
        color: #dce8e1;
        font-size: .82rem;
    }
    .status-dot {
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #62c68b;
    }
    .status-dot.offline { background: var(--coral); }
    .section-kicker {
        margin-bottom: .3rem;
        color: var(--coral);
        font-size: .72rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: .08rem;
    }
    .section-title {
        margin: 0 0 1rem;
        color: var(--ink);
        font-size: 1.42rem;
        line-height: 1.25;
        letter-spacing: 0;
    }
    div[data-testid="stForm"] {
        padding: 1.35rem;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--white);
        box-shadow: none;
    }
    div[data-testid="stForm"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stNumberInput"] label {
        color: #4c5852 !important;
        font-size: .82rem !important;
        font-weight: 650 !important;
    }
    .stTextInput input, .stNumberInput input, .stTextArea textarea,
    div[data-baseweb="select"] > div {
        border-color: #d7ddd5 !important;
        border-radius: 6px !important;
        background: #fbfcf9 !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus,
    .stTextArea textarea:focus {
        border-color: var(--green) !important;
        box-shadow: 0 0 0 1px var(--green) !important;
    }
    .stButton > button, .stFormSubmitButton > button {
        min-height: 44px;
        border-radius: 6px;
        font-weight: 700;
    }
    .stFormSubmitButton > button[kind="primary"] {
        border-color: var(--coral);
        background: var(--coral);
    }
    .stFormSubmitButton > button[kind="primary"]:hover {
        border-color: #c84b34;
        background: #c84b34;
    }
    details[data-testid="stExpander"] {
        margin-bottom: .75rem;
        border: 1px solid var(--line) !important;
        border-radius: 8px !important;
        background: var(--white);
        box-shadow: none;
    }
    details[data-testid="stExpander"] summary {
        min-height: 62px;
        font-weight: 750;
    }
    [data-testid="stMetric"] {
        padding: .75rem 0;
        border-top: 1px solid #e6ebe5;
        border-bottom: 1px solid #e6ebe5;
    }
    [data-testid="stMetricLabel"] { color: var(--muted); }
    [data-testid="stMetricValue"] { color: var(--ink); font-size: 1.25rem; }
    .route-preview {
        position: relative;
        min-height: 420px;
        padding: 2rem;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: var(--white);
        overflow: hidden;
    }
    .route-preview h3 {
        max-width: 420px;
        margin: 0;
        color: var(--ink);
        font-size: 1.6rem;
        line-height: 1.25;
        letter-spacing: 0;
    }
    .route-preview p { max-width: 500px; color: var(--muted); }
    .route-line {
        position: absolute;
        left: 2rem;
        right: 2rem;
        bottom: 5.2rem;
        height: 2px;
        background: var(--line);
    }
    .route-line::before, .route-line::after {
        content: "";
        position: absolute;
        top: -6px;
        width: 14px;
        height: 14px;
        border: 3px solid var(--white);
        border-radius: 50%;
        background: var(--coral);
        box-shadow: 0 0 0 1px var(--coral);
    }
    .route-line::before { left: 0; }
    .route-line::after { right: 0; background: var(--forest); box-shadow: 0 0 0 1px var(--forest); }
    .route-codes {
        position: absolute;
        right: 2rem;
        bottom: 6.2rem;
        color: var(--forest);
        font-size: 4.5rem;
        font-weight: 800;
        line-height: 1;
        letter-spacing: 0;
    }
    .route-labels {
        position: absolute;
        left: 2rem;
        right: 2rem;
        bottom: 2.2rem;
        display: flex;
        justify-content: space-between;
        color: var(--muted);
        font-size: .78rem;
        font-weight: 700;
    }
    .day-heading {
        display: flex;
        justify-content: space-between;
        gap: 1rem;
        margin: 1rem 0 .6rem;
        padding-bottom: .6rem;
        border-bottom: 1px solid var(--line);
        color: var(--forest);
        font-weight: 800;
    }
    .poi-row {
        display: grid;
        grid-template-columns: 36px minmax(0, 1fr) auto;
        gap: .75rem;
        align-items: start;
        padding: .8rem 0;
        border-bottom: 1px solid #edf0eb;
    }
    .poi-index {
        color: var(--coral);
        font-size: .76rem;
        font-weight: 800;
    }
    .poi-name { color: var(--ink); font-weight: 750; }
    .poi-reason { margin-top: .2rem; color: var(--muted); font-size: .82rem; line-height: 1.55; }
    .poi-cost { color: var(--forest); font-size: .82rem; font-weight: 750; white-space: nowrap; }
    .outfit-panel {
        margin: .65rem 0;
        padding: .7rem .8rem;
        border-left: 3px solid var(--green);
        border-radius: 6px;
        background: #f2f6f2;
        color: #4f5e56;
        font-size: .8rem;
        line-height: 1.65;
    }
    .outfit-panel strong { color: var(--forest); }
    .city-outfit-card {
        margin: .85rem 0 1rem;
        padding: 1rem 1.1rem;
        border: 1px solid #d8e2da;
        border-left: 4px solid var(--green);
        border-radius: 8px;
        background: #f8fbf7;
    }
    .city-outfit-head { display: flex; justify-content: space-between; gap: .75rem; margin-bottom: .45rem; }
    .city-outfit-title { color: var(--forest); font-size: 1rem; font-weight: 800; }
    .city-outfit-style { color: var(--coral); font-size: .78rem; font-weight: 750; }
    .city-outfit-copy { color: #536159; font-size: .82rem; line-height: 1.6; }
    .outfit-chips { display: flex; flex-wrap: wrap; gap: .4rem; margin-top: .65rem; }
    .outfit-chip { padding: .2rem .5rem; border: 1px solid #d7dfd8; border-radius: 999px; background: var(--white); color: #59655e; font-size: .72rem; }
    .plan-note {
        margin: .75rem 0;
        padding: .8rem 1rem;
        border-left: 3px solid var(--sun);
        background: #fffaf0;
        color: #625b46;
        font-size: .84rem;
    }
    @media (max-width: 800px) {
        .block-container { padding: 1rem 1rem 2rem; }
        .voyage-hero { min-height: 210px; padding: 1.5rem; }
        .voyage-hero h1 { font-size: 1.85rem; }
        .voyage-hero::after { font-size: 4rem; }
        .route-preview { min-height: 330px; }
        .route-codes { font-size: 3.2rem; }
        .poi-row { grid-template-columns: 28px minmax(0, 1fr); }
        .poi-cost { grid-column: 2; }
    }
    .detail-list {
        margin: .4rem 0 1rem;
        border-top: 1px solid var(--line);
    }
    .detail-line, .route-leg {
        display: grid;
        grid-template-columns: minmax(90px, .7fr) minmax(0, 1.6fr) auto;
        gap: .7rem;
        align-items: center;
        padding: .68rem 0;
        border-bottom: 1px solid #e8ece7;
        font-size: .84rem;
    }
    .detail-line strong, .route-leg strong { color: var(--ink); }
    .detail-line span, .route-leg span { color: var(--muted); }
    .detail-line b, .route-leg b { color: var(--forest); white-space: nowrap; }
    .route-summary {
        display: flex;
        flex-wrap: wrap;
        gap: .65rem 1.25rem;
        margin: .65rem 0;
        padding: .7rem 0;
        border-bottom: 1px solid var(--line);
        color: var(--muted);
        font-size: .82rem;
    }
    .route-summary strong { color: var(--forest); }
    [data-testid="stImage"] img {
        width: 100%;
        aspect-ratio: 16 / 10;
        object-fit: cover;
        border-radius: 6px;
    }
    .poi-section {
        margin-top: 1.15rem;
        padding-top: 1.15rem;
        border-top: 1px solid var(--line);
    }
    .poi-heading {
        margin: 0 0 .35rem;
        color: var(--ink);
        font-size: 1.08rem;
        font-weight: 800;
    }
    .poi-summary {
        margin-bottom: .7rem;
        color: var(--muted);
        font-size: .84rem;
        line-height: 1.6;
    }
    .poi-meta {
        margin: .6rem 0;
        color: #48554e;
        font-size: .81rem;
        line-height: 1.65;
    }
    .spend-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        margin: .75rem 0;
        border-top: 1px solid var(--line);
        border-bottom: 1px solid var(--line);
    }
    .spend-item { padding: .65rem .5rem .65rem 0; }
    .spend-item span { display: block; color: var(--muted); font-size: .7rem; }
    .spend-item strong { color: var(--forest); font-size: .9rem; }
    .restaurant-note {
        padding: .8rem 0 .2rem;
        border-top: 2px solid var(--sun);
        color: #445149;
        font-size: .82rem;
        line-height: 1.65;
    }
    .restaurant-note strong { color: var(--ink); }
    .food-module-title {
        margin: 1.35rem 0 .35rem;
        color: var(--forest);
        font-size: .92rem;
        font-weight: 850;
        text-transform: uppercase;
        letter-spacing: .05rem;
    }
    .food-card {
        margin: .55rem 0;
        padding: .85rem 0;
        border-top: 1px solid var(--line);
        color: #445149;
        font-size: .83rem;
        line-height: 1.65;
    }
    .food-card strong { color: var(--ink); }
    .source-links { margin-top: .35rem; display: flex; flex-wrap: wrap; gap: .75rem; }
    .source-links a { color: #1163a5; text-decoration: none; font-size: .78rem; }
    .selector-help { color: var(--muted); font-size: .76rem; line-height: 1.5; }
    .cost-note { color: var(--muted); font-size: .78rem; line-height: 1.55; }
    .quality-strip {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: .55rem;
        margin: .85rem 0 1rem;
    }
    .quality-item {
        min-height: 86px;
        padding: .75rem .8rem;
        border: 1px solid var(--line);
        border-radius: 8px;
        background: rgba(255,255,255,.72);
    }
    .quality-head { display: flex; align-items: center; gap: .4rem; color: var(--muted); font-size: .72rem; font-weight: 750; }
    .quality-dot { width: 7px; height: 7px; border-radius: 50%; background: #aeb7b0; }
    .quality-dot.good { background: #2f8d5b; }
    .quality-dot.warn { background: var(--sun); }
    .quality-value { margin-top: .35rem; color: var(--ink); font-size: .92rem; font-weight: 820; }
    .quality-detail { margin-top: .25rem; color: var(--muted); font-size: .72rem; line-height: 1.45; }
    .date-chip { color: var(--muted); font-size: .8rem; font-weight: 650; }
    .image-credit { margin-top: -.35rem; color: var(--muted); font-size: .67rem; }
    .score-copy { color: var(--muted); font-size: .8rem; line-height: 1.55; }
    @media (max-width: 800px) {
        .detail-line, .route-leg { grid-template-columns: minmax(0, 1fr) auto; }
        .detail-line span, .route-leg span { grid-column: 1 / -1; }
        .spend-grid { grid-template-columns: 1fr; }
        .spend-item { border-bottom: 1px solid #edf0eb; }
        .quality-strip { grid-template-columns: 1fr; }
    }    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=5, show_spinner=False)
def _check_backend(base_url: str) -> Tuple[bool, str]:
    try:
        response = requests.get(f"{base_url}/health", timeout=2)
        response.raise_for_status()
        return True, "规划服务在线"
    except requests.exceptions.RequestException:
        return False, "规划服务未连接"


def _format_money(value: Any, currency: str = "CNY") -> str:
    try:
        return f"¥{float(value):,.0f}" if currency == "CNY" else f"{float(value):,.0f} {currency}"
    except (TypeError, ValueError):
        return f"{value} {currency}"


def _safe(value: Any) -> str:
    return html.escape(str(value or ""))



def _format_plan_dates(plan: Dict[str, Any]) -> str:
    dates = plan.get("travel_dates", [])
    if not dates:
        return "未设定"
    first = dates[0].get("date_label") or dates[0].get("date")
    last = dates[-1].get("date_label") or dates[-1].get("date")
    return first if len(dates) == 1 else f"{first} - {last}"


def _render_data_quality(plan: Dict[str, Any]) -> None:
    items = plan.get("data_quality", {}).get("items", [])
    if not items:
        return
    cards = "".join(
        f"<div class='quality-item'>"
        f"<div class='quality-head'><span class='quality-dot {_safe(item.get('level', 'neutral'))}'></span>{_safe(item.get('label'))}</div>"
        f"<div class='quality-value'>{_safe(item.get('value'))}</div>"
        f"<div class='quality-detail'>{_safe(item.get('detail'))}</div>"
        f"</div>"
        for item in items
    )
    st.markdown(f"<div class='quality-strip'>{cards}</div>", unsafe_allow_html=True)
def _request_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(API_URL, json=payload, timeout=(5, 120))
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"后端返回 {response.status_code}: {detail}")
    return response.json().get("data", {})



@st.cache_data(ttl=60, show_spinner=False)
def _request_catalog(
    destination: str,
    profile_id: str = "comfort",
    preferences: str = "",
    traveler_type: str = "solo",
) -> List[Dict[str, Any]]:
    payload = {
        "destination": destination,
        "profile_id": profile_id,
        "preferences": preferences,
        "traveler_type": traveler_type,
    }
    response = requests.post(CATALOG_API_URL, json=payload, timeout=(5, 30))
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"景点库加载失败: {detail}")
    return response.json().get("data", [])


def _request_selected_plan(payload: Dict[str, Any]) -> Dict[str, Any]:
    response = requests.post(SELECTED_POIS_API_URL, json=payload, timeout=(5, 90))
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"自选路线生成失败: {detail}")
    return response.json().get("data", {})


def _external_search_url(site: str, keyword: str) -> str:
    encoded = quote(keyword)
    if site == "dianping":
        return f"https://www.dianping.com/search/keyword/1/0_{encoded}"
    return f"https://www.xiaohongshu.com/search_result?keyword={encoded}"


def _catalog_names_from_plan(plan: Dict[str, Any], candidate: Dict[str, Any]) -> List[str]:
    try:
        catalog = plan.get("poi_catalog") or _request_catalog(
            plan.get("destination", ""),
            candidate.get("id", "comfort"),
            plan.get("preferences", ""),
            plan.get("traveler_type", "solo"),
        )
        names = [item.get("name", "") for item in catalog if item.get("name")]
    except (requests.exceptions.RequestException, RuntimeError):
        names = []
    for day in candidate.get("daily_plan", []):
        for poi in day.get("pois", []):
            if poi.get("name"):
                names.append(poi["name"])
    return list(dict.fromkeys(names))
def _render_city_outfit(city_outfit: Dict[str, Any]) -> None:
    if not city_outfit:
        return
    chips = "".join(
        f"<span class='outfit-chip'>{_safe(item)}</span>"
        for item in [*city_outfit.get("palette", []), *city_outfit.get("essentials", [])]
    )
    st.markdown(
        f"<div class='city-outfit-card'>"
        f"<div class='city-outfit-head'><span class='city-outfit-title'>城市风格穿搭</span>"
        f"<span class='city-outfit-style'>{_safe(city_outfit.get('style_name'))}</span></div>"
        f"<div class='city-outfit-copy'>{_safe(city_outfit.get('description'))}<br>"
        f"<strong>推荐公式：</strong>{_safe(city_outfit.get('outfit_formula'))}</div>"
        f"<div class='outfit-chips'>{chips}</div></div>",
        unsafe_allow_html=True,
    )
    if city_outfit.get("note"):
        st.caption(f"穿搭提示：{city_outfit['note']}")
def _request_replacement(
    plan: Dict[str, Any],
    candidate: Dict[str, Any],
    day_index: int,
    poi_index: int,
    replacement_name: str = "",
) -> Dict[str, Any]:
    payload = {
        "destination": plan.get("destination", ""),
        "candidate": candidate,
        "day_index": day_index,
        "poi_index": poi_index,
        "replacement_name": replacement_name or None,
        "budget": plan.get("budget_limit"),
        "preferences": plan.get("preferences", ""),
        "traveler_type": plan.get("traveler_type", "solo"),
    }
    response = requests.post(REPLACE_API_URL, json=payload, timeout=(5, 30))
    if not response.ok:
        try:
            detail = response.json().get("detail", response.text)
        except ValueError:
            detail = response.text
        raise RuntimeError(f"景点替换失败: {detail}")
    return response.json().get("data", candidate)


def _render_detail_lines(items: list) -> None:
    rows = "".join(
        f"<div class='detail-line'><strong>{_safe(item['label'])}</strong>"
        f"<span>{_safe(item.get('detail', ''))}</span><b>{_safe(item.get('value', ''))}</b></div>"
        for item in items
    )
    st.markdown(f"<div class='detail-list'>{rows}</div>", unsafe_allow_html=True)


def _render_route_map(day: Dict[str, Any]) -> None:
    points = day.get("map_points", [])
    legs = day.get("route_legs", [])
    if not points or not legs:
        st.info(day.get("route_note", "当前路线暂缺地图坐标。"))
        return

    latitudes = [point["lat"] for point in points]
    longitudes = [point["lon"] for point in points]
    span = max(max(latitudes) - min(latitudes), max(longitudes) - min(longitudes))
    zoom = 11.4 if span < 0.08 else 9.4 if span < 0.25 else 8.1
    layers = [
        pdk.Layer(
            "PathLayer",
            data=legs,
            get_path="path",
            get_color=[47, 107, 82, 190],
            get_width=5,
            width_min_pixels=3,
            pickable=True,
        ),
        pdk.Layer(
            "ScatterplotLayer",
            data=points,
            get_position="[lon, lat]",
            get_fill_color="color",
            get_radius=150,
            radius_min_pixels=7,
            radius_max_pixels=13,
            pickable=True,
        ),
        pdk.Layer(
            "TextLayer",
            data=points,
            get_position="[lon, lat]",
            get_text="order",
            get_color=[255, 255, 255, 255],
            get_size=13,
            get_alignment_baseline="center",
            get_text_anchor="middle",
            pickable=False,
        ),
    ]
    deck = pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(
            latitude=sum(latitudes) / len(latitudes),
            longitude=sum(longitudes) / len(longitudes),
            zoom=zoom,
            pitch=0,
        ),
        map_style="https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
        tooltip={"html": "<b>{label}</b><br>{detail}", "style": {"color": "white"}},
    )
    st.pydeck_chart(deck, use_container_width=True, height=310)
    st.markdown(
        f"<div class='route-summary'>"
        f"<span>往返里程 <strong>{day.get('route_distance_km', 0):.1f} km</strong></span>"
        f"<span>路上时间 <strong>约 {day.get('route_minutes', 0)} 分钟</strong></span>"
        f"<span>交通预算 <strong>{_format_money(day.get('estimated_transport_cost', 0))}</strong></span>"
        f"</div>",
        unsafe_allow_html=True,
    )
    for leg in legs:
        st.markdown(
            f"<div class='route-leg'><strong>{_safe(leg.get('from'))} → {_safe(leg.get('to'))}</strong>"
            f"<span>{_safe(leg.get('mode'))} · 约 {leg.get('minutes', 0)} 分钟</span>"
            f"<b>{leg.get('distance_km', 0):.1f} km</b></div>",
            unsafe_allow_html=True,
        )
    st.caption(day.get("route_note", ""))


def _render_score_details(score: Dict[str, Any]) -> None:
    components = [
        ("预算匹配", "budget_match", 0.35, "越接近预算目标且不超支，得分越高。"),
        ("偏好匹配", "preference_match", 0.25, "景点标签覆盖美食、历史、自然等输入偏好的程度。"),
        ("行程强度", "intensity", 0.20, "每天景点数量是否适合同伴类型，避免过松或过赶。"),
        ("内容多样性", "diversity", 0.20, "景点类别是否丰富，并对重复景点进行扣分。"),
    ]
    st.markdown("综合分 = 各项得分 × 权重，满分 100。它用于比较本次生成的三套方案，不代表景点的绝对质量。")
    for label, key, weight, description in components:
        value = float(score.get(key, 0) or 0)
        st.progress(value / 100, text=f"{label} {value:.0f} / 100 · 权重 {weight:.0%}")
        st.markdown(f"<div class='score-copy'>{description}</div>", unsafe_allow_html=True)



def _render_hotel_booking_panel(plan: Dict[str, Any], candidate: Dict[str, Any]) -> None:
    hotel = candidate.get("hotel_option", {})
    destination = plan.get("destination", "")
    keyword_parts = [destination, hotel.get("tier", ""), hotel.get("name", "")]
    keyword = " ".join(part for part in keyword_parts if part).strip() or "酒店"
    st.markdown(
        f"<div class='food-card'><strong>自选酒店 · 携程</strong><br>"
        f"建议搜索词：{_safe(keyword)}<br>"
        f"当前住宿预算只是行程估算，不代表真实库存、价格、位置和可退政策。"
        f"<div class='source-links'><a href='{CTRIP_HOTELS_URL}' target='_blank'>打开携程酒店</a></div></div>",
        unsafe_allow_html=True,
    )
def _render_cost_expander(
    title: str,
    detail: str,
    value: str,
    rows: List[Dict[str, Any]],
    note: str = "",
) -> None:
    with st.expander(f"{title}　{value}", expanded=False):
        if detail:
            st.markdown(f"<div class='cost-note'>{_safe(detail)}</div>", unsafe_allow_html=True)
        if rows:
            _render_detail_lines(rows)
        if note:
            st.caption(note)


def _render_cost_tabs(plan: Dict[str, Any], candidate: Dict[str, Any], currency: str, score: Dict[str, Any]) -> None:
    breakdown = candidate.get("budget_breakdown", {})
    hotel = candidate.get("hotel_option", {})
    transport = candidate.get("transport_summary", {})
    daily_plan = candidate.get("daily_plan", [])
    people = int(breakdown.get("people", 1) or 1)
    days = max(len(daily_plan), 1)
    overview_tab, hotel_tab, transport_tab, score_tab = st.tabs(["费用总览", "住宿明细", "交通明细", "匹配说明"])

    poi_rows: List[Dict[str, Any]] = []
    food_rows: List[Dict[str, Any]] = []
    for day in daily_plan:
        restaurant_names = []
        for poi in day.get("pois", []):
            admission = float(poi.get("estimated_cost", 0) or 0)
            spend = poi.get("spend_breakdown", {})
            optional_min = spend.get("optional_min", 0)
            optional_max = spend.get("optional_max", 0)
            optional_label = spend.get("optional_label", "可选体验")
            optional = f"{optional_label} {_format_money(optional_min, currency)}-{_format_money(optional_max, currency)}"
            poi_rows.append(
                {
                    "label": f"Day {day.get('day')} · {poi.get('name')}",
                    "detail": f"门票/活动 {_format_money(admission, currency)}/人 × {people} 人；{optional}",
                    "value": _format_money(admission * people, currency),
                }
            )
            restaurant = poi.get("restaurant", {})
            if restaurant.get("name"):
                restaurant_names.append(restaurant["name"])
        food_rows.append(
            {
                "label": f"Day {day.get('day')} 餐饮",
                "detail": "推荐餐厅：" + "、".join(restaurant_names[:4]) if restaurant_names else day.get("meal_suggestion", "按需安排"),
                "value": _format_money(float(breakdown.get("food_total", 0) or 0) / days, currency),
            }
        )

    hotel_detail = hotel.get("breakdown", {})
    hotel_rows = [
        {"label": "住宿档位", "detail": hotel.get("tier", ""), "value": hotel.get("name", "")},
        {
            "label": "间夜结构",
            "detail": f"{hotel_detail.get('rooms', 1)} 间 × {hotel_detail.get('nights', 0)} 晚",
            "value": f"{hotel_detail.get('rooms', 1) * hotel_detail.get('nights', 0)} 间夜",
        },
        {"label": "参考房价", "detail": "每间每晚", "value": _format_money(hotel_detail.get("nightly_rate", 0), currency)},
        {"label": "住宿合计", "detail": hotel_detail.get("includes", ""), "value": _format_money(hotel.get("estimated_total", 0), currency)},
    ]

    transport_detail = transport.get("breakdown", {})
    transport_rows = [
        {
            "label": f"Day {item.get('day')}",
            "detail": f"{item.get('distance_km', 0):.1f} km · 约 {item.get('minutes', 0)} 分钟",
            "value": _format_money(item.get("estimated_cost", 0), currency),
        }
        for item in transport_detail.get("days", [])
    ]

    subtotal = float(breakdown.get("total", 0) or 0) - float(breakdown.get("contingency", 0) or 0)
    contingency_rate = (float(breakdown.get("contingency", 0) or 0) / subtotal * 100) if subtotal else 0
    contingency_rows = [
        {"label": "估算基数", "detail": "景点、餐饮、住宿和市内交通小计", "value": _format_money(subtotal, currency)},
        {"label": "预留比例", "detail": "用于排队、临时加项和价格浮动", "value": f"约 {contingency_rate:.0f}%"},
    ]

    with overview_tab:
        _render_cost_expander(
            "景点/活动",
            "门票与明确收费体验，按同行人数折算。",
            _format_money(breakdown.get("poi_total", 0), currency),
            poi_rows,
            "可选体验只作为消费提醒，不全部计入基础门票。",
        )
        _render_cost_expander(
            "餐饮",
            f"{people} 人 × 每日餐饮预算，并在每日餐饮模块列出候选餐厅。",
            _format_money(breakdown.get("food_total", 0), currency),
            food_rows,
            "餐厅评分、排队和营业状态请打开大众点评/地图后确认。",
        )
        _render_cost_expander("住宿", "按间夜估算，不读取真实酒店库存。", _format_money(breakdown.get("hotel_total", 0), currency), hotel_rows)
        _render_hotel_booking_panel(plan, candidate)
        _render_cost_expander("市内交通", "按当日路线距离估算。", _format_money(breakdown.get("transport_total", 0), currency), transport_rows, transport_detail.get("includes", ""))
        _render_cost_expander("机动预算", "给临时变化留余量。", _format_money(breakdown.get("contingency", 0), currency), contingency_rows)

    with hotel_tab:
        _render_detail_lines(hotel_rows)
        _render_hotel_booking_panel(plan, candidate)

    with transport_tab:
        _render_detail_lines(transport_rows)
        st.caption(transport_detail.get("includes", transport.get("notes", "")))

    with score_tab:
        _render_score_details(score)

def _render_poi(
    plan: Dict[str, Any],
    candidate: Dict[str, Any],
    candidate_index: int,
    day_index: int,
    poi_index: int,
    poi: Dict[str, Any],
    currency: str,
    catalog_names: List[str],
) -> None:
    st.markdown("<div class='poi-section'></div>", unsafe_allow_html=True)
    image_column, content_column = st.columns([0.32, 0.68], gap="medium")
    with image_column:
        if poi.get("image"):
            st.image(poi["image"], use_container_width=True)
            if poi.get("image_source"):
                st.markdown(
                    f"<div class='image-credit'><a href='{_safe(poi['image_source'])}' target='_blank'>{_safe(poi.get('image_credit', '图片来源'))}</a></div>",
                    unsafe_allow_html=True,
                )
        else:
            st.markdown(f"<div class='route-preview' style='min-height:150px;padding:1rem'><strong>{_safe(poi.get('name'))}</strong></div>", unsafe_allow_html=True)

    with content_column:
        title_column, action_column = st.columns([0.68, 0.32], gap="small")
        with title_column:
            st.markdown(f"<div class='poi-heading'>{poi_index + 1:02d} · {_safe(poi.get('name'))}</div>", unsafe_allow_html=True)
            st.caption(f"建议停留 {poi.get('duration_hours', 0):g} 小时 · 最佳时段 {poi.get('best_time', '按开放时间')} ")
        with action_column:
            options = catalog_names or [poi.get("name", "")]
            current_name = poi.get("name", "")
            current_index = options.index(current_name) if current_name in options else 0
            replacement_name = st.selectbox(
                "替换为",
                options=options,
                index=current_index,
                key=f"replace-select-{candidate.get('id')}-{day_index}-{poi_index}-{current_name}",
            )
            if st.button(
                "应用",
                key=f"replace-apply-{candidate.get('id')}-{day_index}-{poi_index}-{current_name}",
                icon=":material/check:",
                use_container_width=True,
            ):
                if replacement_name == current_name:
                    st.info("已是当前景点，请从下拉栏选择另一个景点。")
                else:
                    try:
                        with st.spinner("正在按你的选择重排当天路线..."):
                            updated = _request_replacement(plan, candidate, day_index, poi_index, replacement_name)
                        plan["candidates"][candidate_index] = updated
                        st.session_state["trip_plan"] = plan
                        replacement = updated.get("last_replacement", {})
                        st.toast(f"已将 {replacement.get('from', '原景点')} 替换为 {replacement.get('to', replacement_name)}")
                        st.rerun()
                    except (requests.exceptions.RequestException, RuntimeError) as exc:
                        st.error(str(exc))

        st.markdown(f"<div class='poi-summary'>{_safe(poi.get('summary'))}</div>", unsafe_allow_html=True)
        highlights = " · ".join(poi.get("highlights", []))
        st.markdown(
            f"<div class='poi-meta'><strong>到访亮点</strong>　{_safe(highlights)}<br>"
            f"<strong>安排理由</strong>　{_safe(poi.get('reason'))}<br>"
            f"<strong>实用提示</strong>　{_safe(poi.get('visit_tip'))}</div>",
            unsafe_allow_html=True,
        )

        outfit = poi.get("outfit_advice", {})
        if outfit:
            extras = "、".join(outfit.get("extras", []))
            outfit_keyword = f"{plan.get('destination', '')} {poi.get('name', '')} {outfit.get('style', '')} 穿搭"
            xhs_link = _external_search_url("xiaohongshu", outfit_keyword)
            st.markdown(
                f"<div class='outfit-panel'><strong>穿搭 · {_safe(outfit.get('style'))}</strong><br>"
                f"{_safe(outfit.get('clothing'))}<br>"
                f"<strong>鞋履</strong>　{_safe(outfit.get('shoes'))}　·　<strong>随身</strong>　{_safe(extras)}<br>"
                f"{_safe(outfit.get('tip'))}"
                f"<div class='source-links'><a href='{_safe(xhs_link)}' target='_blank'>小红书灵感搜索</a></div></div>",
                unsafe_allow_html=True,
            )

        spend = poi.get("spend_breakdown", {})
        optional_range = f"{_format_money(spend.get('optional_min', 0), currency)}-{_format_money(spend.get('optional_max', 0), currency)}"
        st.markdown(
            f"<div class='spend-grid'>"
            f"<div class='spend-item'><span>门票/活动</span><strong>{_format_money(spend.get('admission', 0), currency)}</strong></div>"
            f"<div class='spend-item'><span>{_safe(spend.get('optional_label'))}</span><strong>{optional_range}</strong></div>"
            f"<div class='spend-item'><span>预计停留</span><strong>{poi.get('duration_hours', 0):g} 小时</strong></div>"
            f"</div>",
            unsafe_allow_html=True,
        )


def _render_food_module(day: Dict[str, Any], currency: str) -> None:
    restaurants = []
    for poi in day.get("pois", []):
        restaurant = poi.get("restaurant", {})
        if restaurant.get("name"):
            restaurants.append((poi, restaurant))
    if not restaurants:
        return

    st.markdown("<div class='food-module-title'>餐饮安排</div>", unsafe_allow_html=True)
    for poi, restaurant in restaurants:
        dishes = "、".join(restaurant.get("signature_dishes", []))
        review_url = restaurant.get("review_url") or _external_search_url("dianping", restaurant.get("name", ""))
        links = []
        if restaurant.get("map_url"):
            links.append(f"<a href='{_safe(restaurant['map_url'])}' target='_blank'>地图查看</a>")
        if review_url:
            links.append(f"<a href='{_safe(review_url)}' target='_blank'>大众点评搜索</a>")
        if restaurant.get("source_url"):
            links.append(f"<a href='{_safe(restaurant['source_url'])}' target='_blank'>推荐来源</a>")
        link_text = "" if not links else f"<div class='source-links'>{''.join(links)}</div>"
        st.markdown(
            f"<div class='food-card'><strong>{_safe(poi.get('name'))} 附近 · {_safe(restaurant.get('name'))}</strong><br>"
            f"{_safe(restaurant.get('cuisine'))} · 人均 {_safe(restaurant.get('price_per_person'))} · 约 {restaurant.get('travel_minutes', 10)} 分钟可达<br>"
            f"推荐：{_safe(dishes)}。{_safe(restaurant.get('reason'))}<br>"
            f"<span>{_safe(restaurant.get('rating_note', '评分与营业状态请以实时平台为准。'))}</span>{link_text}</div>",
            unsafe_allow_html=True,
        )

def _render_candidate(plan: Dict[str, Any], candidate: Dict[str, Any], candidate_index: int) -> None:
    currency = candidate.get("currency", "CNY")
    score = candidate.get("score", {})
    rank = candidate.get("rank", "")
    title = candidate.get("title", "旅行方案")
    total = candidate.get("total_budget", 0)
    expander_title = f"0{rank}  {title}  ·  {_format_money(total, currency)}  ·  匹配度 {score.get('total', 0):.0f}"

    with st.expander(expander_title, expanded=rank == 1):
        st.markdown(f"**方案策略**　{candidate.get('strategy', '')}")
        metric_cols = st.columns(4)
        metric_cols[0].metric("预计总费用", _format_money(total, currency))
        metric_cols[1].metric("住宿", _format_money(candidate.get("hotel_option", {}).get("estimated_total", 0), currency))
        metric_cols[2].metric("市内交通", _format_money(candidate.get("transport_summary", {}).get("estimated_total", 0), currency))
        metric_cols[3].metric("综合匹配", f"{score.get('total', 0):.0f} / 100")

        if plan.get("budget_limit"):
            ratio = float(total or 0) / float(plan["budget_limit"])
            st.progress(min(max(ratio, 0), 1), text=f"预算使用 {_format_money(total, currency)} / {_format_money(plan['budget_limit'], currency)}")

        warnings = candidate.get("warnings", [])
        if warnings:
            st.warning("；".join(warnings))

        _render_cost_tabs(plan, candidate, currency, score)
        daily_plan = candidate.get("daily_plan", [])
        if not daily_plan:
            st.info("此方案暂时没有每日行程。")
            return

        catalog_names = _catalog_names_from_plan(plan, candidate)
        selected_index = st.selectbox(
            "查看每日行程",
            options=range(len(daily_plan)),
            format_func=lambda index: f"第 {daily_plan[index].get('day', index + 1)} 天 · {daily_plan[index].get('theme', '自由探索')}",
            key=f"candidate-day-{candidate.get('id', rank)}",
        )
        day = daily_plan[selected_index]
        st.markdown(
            f"<div class='day-heading'><span>DAY {day.get('day')}</span><span>{_safe(day.get('theme'))}</span></div>",
            unsafe_allow_html=True,
        )
        _render_route_map(day)
        st.markdown("<div class='food-module-title'>游玩安排</div>", unsafe_allow_html=True)
        for poi_index, poi in enumerate(day.get("pois", [])):
            _render_poi(
                plan,
                candidate,
                candidate_index,
                selected_index,
                poi_index,
                poi,
                currency,
                catalog_names,
            )
        _render_food_module(day, currency)
        st.caption(f"当日交通：{day.get('daily_transport', '公共交通')}")

backend_ok, backend_label = _check_backend(BASE_API_URL)
status_class = "" if backend_ok else " offline"
st.markdown(
    f"""
    <section class="voyage-hero">
        <div class="hero-kicker">Voyage Studio / AI Itinerary</div>
        <h1>把预算、偏好与城市节奏，排成一趟好旅行</h1>
        <p>一次生成三种可比较的行程策略。费用、强度和推荐理由都清楚可见。</p>
        <div class="status-row"><span class="status-dot{status_class}"></span>{backend_label} · {html.escape(BASE_API_URL)}</div>
    </section>
    """,
    unsafe_allow_html=True,
)

input_column, result_column = st.columns([0.36, 0.64], gap="large")

with input_column:
    st.markdown('<div class="section-kicker">01 / Trip brief</div><h2 class="section-title">告诉我这趟旅行的边界</h2>', unsafe_allow_html=True)
    with st.form("trip-planner-form"):
        destination = st.text_input("目的地", value="上海", placeholder="例如：上海、杭州、Tokyo")
        row_a, row_b = st.columns(2)
        with row_a:
            start_date = st.date_input("出发日期", value=date.today())
        with row_b:
            days = st.number_input("旅行天数", min_value=1, max_value=21, value=3, step=1)
        traveler_label = st.selectbox("同行方式", list(TRAVELER_OPTIONS.keys()), index=1)
        budget = st.text_input("总预算", value="8000", placeholder="金额或：经济 / 舒适 / 高端")
        preferences = st.text_area(
            "旅行偏好",
            value="美食、城市漫步、历史文化",
            placeholder="用逗号分隔，例如：自然、亲子、咖啡馆",
            height=104,
        )
        submitted = st.form_submit_button("生成并排序 3 套方案", type="primary", use_container_width=True)
    st.caption("预算为本地估算，仅含目的地内住宿、餐饮、交通与活动，不含往返大交通。")

    current_inputs = {
        "destination": destination.strip() or "上海",
        "days": int(days),
        "start_date": start_date.isoformat(),
        "budget": budget.strip() or None,
        "preferences": preferences.strip(),
        "traveler_type": TRAVELER_OPTIONS[traveler_label],
    }
    if submitted:
        st.session_state["last_trip_inputs"] = current_inputs
    base_inputs = st.session_state.get("last_trip_inputs", current_inputs)

    st.markdown('<div class="section-kicker">02 / POI library</div><h2 class="section-title">自己勾选景点，让系统排路线</h2>', unsafe_allow_html=True)
    profile_options = {"舒适型": "comfort", "经济型": "economy", "体验优先型": "experience_first"}
    profile_label = st.selectbox("路线风格", list(profile_options.keys()), index=0, key="custom-profile")
    custom_days = st.number_input("自选路线天数", min_value=1, max_value=21, value=int(base_inputs.get("days", 3)), step=1, key="custom-days")

    if not backend_ok:
        st.info("后端在线后可加载景点库。")
    else:
        try:
            catalog = _request_catalog(
                base_inputs.get("destination", "上海"),
                profile_options[profile_label],
                base_inputs.get("preferences", ""),
                base_inputs.get("traveler_type", "solo"),
            )
            name_to_label = {item["name"]: item.get("label", item["name"]) for item in catalog if item.get("name")}
            selected_names = st.multiselect(
                "从景点库勾选",
                options=list(name_to_label.keys()),
                format_func=lambda name: name_to_label.get(name, name),
                key="custom-selected-pois",
            )
            if st.button("按勾选景点生成路线", use_container_width=True, icon=":material/route:"):
                if not selected_names:
                    st.warning("请至少勾选一个景点。")
                else:
                    payload = {
                        "destination": base_inputs.get("destination", "上海"),
                        "selected_pois": selected_names,
                        "days": int(custom_days),
                        "start_date": base_inputs.get("start_date"),
                        "budget": base_inputs.get("budget"),
                        "preferences": base_inputs.get("preferences", ""),
                        "traveler_type": base_inputs.get("traveler_type", "solo"),
                        "profile_id": profile_options[profile_label],
                    }
                    with st.spinner("正在按你勾选的景点重排行程..."):
                        st.session_state["trip_plan"] = _request_selected_plan(payload)
                    st.session_state.pop("trip_error", None)
                    st.toast("已生成自选景点路线")
                    st.rerun()
        except (requests.exceptions.RequestException, RuntimeError) as exc:
            st.warning(str(exc))

with result_column:
    st.markdown('<div class="section-kicker">02 / Ranked routes</div><h2 class="section-title">方案对比与每日安排</h2>', unsafe_allow_html=True)

    if submitted:
        if not destination.strip():
            st.error("请先填写目的地。")
        elif not backend_ok:
            st.error("后端没有响应。请先在 VS Code 中启动“Trip Planner: 后端”，等待终端出现 Uvicorn running，再重新生成。")
        else:
            payload = {
                "destination": destination.strip(),
                "days": int(days),
                "start_date": start_date.isoformat(),
                "budget": budget.strip() or None,
                "preferences": preferences.strip(),
                "traveler_type": TRAVELER_OPTIONS[traveler_label],
            }
            try:
                with st.spinner("正在组合预算、偏好与城市知识..."):
                    st.session_state["trip_plan"] = _request_plan(payload)
                    st.session_state.pop("trip_error", None)
            except requests.exceptions.ConnectionError:
                st.session_state["trip_error"] = "无法连接后端。确认 8000 端口的终端仍在运行。"
            except requests.exceptions.Timeout:
                st.session_state["trip_error"] = "后端响应超时。首次加载语义模型可能较慢，请稍后重试。"
            except (requests.exceptions.RequestException, RuntimeError) as exc:
                st.session_state["trip_error"] = str(exc)

    if st.session_state.get("trip_error"):
        st.error(st.session_state["trip_error"])

    plan = st.session_state.get("trip_plan")
    if plan:
        summary_cols = st.columns(5)
        summary_cols[0].metric("目的地", plan.get("destination", destination))
        summary_cols[1].metric("日期", _format_plan_dates(plan))
        summary_cols[2].metric("天数", f"{plan.get('days', days)} 天")
        summary_cols[3].metric("预算上限", _format_money(plan.get("budget_limit", 0), plan.get("currency", "CNY")))
        summary_cols[4].metric("方案", len(plan.get("candidates", [])))

        _render_data_quality(plan)
        _render_city_outfit(plan.get("city_outfit", {}))

        rag = plan.get("rag", {})
        if rag.get("status") == "loading":
            st.info("首轮方案已生成；语义 RAG 正在后台预热，后续生成会自动补充知识库理由。")
        elif rag.get("status") == "error":
            st.warning("语义 RAG 暂不可用，本次使用本地规划器完成方案。")

        for candidate_index, candidate in enumerate(plan.get("candidates", [])):
            _render_candidate(plan, candidate, candidate_index)

        sources = rag.get("sources", [])
        if sources:
            st.caption("知识来源：" + " · ".join(os.path.basename(source) for source in sources))
    elif not st.session_state.get("trip_error"):
        st.markdown(
            """
            <div class="route-preview">
                <h3>先设定旅行边界，再让路线拥有自己的节奏。</h3>
                <p>生成后，这里会按匹配度展示经济型、舒适型与体验优先型方案。</p>
                <div class="route-codes">SHA</div>
                <div class="route-line"></div>
                <div class="route-labels"><span>YOUR BRIEF</span><span>RANKED ROUTES</span></div>
            </div>
            """,
            unsafe_allow_html=True,
        )
