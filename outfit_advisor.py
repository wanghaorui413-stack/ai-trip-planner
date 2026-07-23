from copy import deepcopy
from typing import Any, Dict


DEFAULT_CITY_STYLE = {
    "style_name": "轻松城市探索",
    "description": "以舒适、耐走和方便增减为主，保留一件有城市感的简洁单品。",
    "palette": ["中性色", "低饱和蓝", "一点亮色"],
    "outfit_formula": "透气上衣 + 宽松长裤 + 轻便外套 + 舒适步行鞋",
    "essentials": ["轻便外套", "斜挎包", "折叠伞"],
    "note": "这是城市风格建议；出发前请再按实时气温、降雨和个人体感增减衣物。",
}

CITY_STYLE_PROFILES = {
    "shanghai": {
        "style_name": "海派都市感",
        "description": "利落剪裁配一点复古细节，适合街区漫步、建筑摄影与夜景场景。",
        "palette": ["黑白", "海军蓝", "酒红点缀"],
        "outfit_formula": "简洁衬衫/针织上衣 + 直筒裤 + 轻薄风衣 + 乐福鞋/运动鞋",
        "essentials": ["轻薄风衣", "小型斜挎包", "折叠伞"],
        "note": "江边和高层观景处风感更明显，建议带一件防风外层。",
    },
    "hangzhou": {
        "style_name": "清雅江南",
        "description": "柔和色彩与轻盈面料更贴合湖景、茶园和古建氛围。",
        "palette": ["米白", "青绿", "雾灰"],
        "outfit_formula": "棉麻上衣 + 宽松长裤/过膝裙 + 薄开衫 + 防滑步行鞋",
        "essentials": ["薄开衫", "遮阳帽", "折叠伞"],
        "note": "湖边、湿地和茶园湿度偏高，鞋底抓地力比造型更重要。",
    },
    "chengdu": {
        "style_name": "松弛休闲感",
        "description": "宽松、舒适又有一点街头感，适合公园喝茶、美食探索和慢节奏闲逛。",
        "palette": ["卡其", "墨绿", "暖橙点缀"],
        "outfit_formula": "宽松 T 恤/衬衫 + 工装裤 + 轻便运动鞋 + 休闲外套",
        "essentials": ["防油渍外搭", "纸巾", "轻便雨具"],
        "note": "吃火锅或川菜时优先选择易清洁、气味不易附着的外层。",
    },
    "tokyo": {
        "style_name": "简洁层次感",
        "description": "低饱和配色与清晰层次，兼顾大量步行、购物和室内外温差。",
        "palette": ["黑", "灰", "藏蓝"],
        "outfit_formula": "基础款内搭 + 有型外套 + 直筒下装 + 缓震运动鞋",
        "essentials": ["可收纳外套", "轻量托特包", "舒适袜"],
        "note": "日均步数通常较高，先选已经磨合好的鞋，再考虑整体造型。",
    },
    "kyoto": {
        "style_name": "素雅古都感",
        "description": "自然材质和克制配色更贴合寺社、庭院与传统街区。",
        "palette": ["米色", "茶褐", "深绿"],
        "outfit_formula": "素色上衣 + 宽松长裤/过膝裙 + 薄外套 + 易穿脱步行鞋",
        "essentials": ["薄袜", "小方巾", "安静软底鞋"],
        "note": "参观寺社时避免过度暴露；部分室内需要脱鞋，建议穿整洁袜子。",
    },
}

CATEGORY_OUTFITS = {
    "landmark": ("利落打卡", "简洁上衣配直筒下装，外搭有轮廓感的轻薄外套", "舒适且上镜的步行鞋", ["斜挎包", "轻便防风层"], "兼顾长时间步行与拍照，避免第一次穿的新鞋。"),
    "history": ("克制人文", "素色上衣配过膝下装或长裤，准备可遮肩的轻薄外层", "防滑、易穿脱的软底鞋", ["薄袜", "小方巾"], "寺庙、宗教及传统场所宜避免过度暴露，并遵守现场着装礼仪。"),
    "culture": ("素雅人文", "低饱和上衣配长裤或过膝裙，整体简洁不过度暴露", "安静舒适的软底鞋", ["薄外套", "轻便小包"], "传统场所优先选择得体、方便行走和久站的搭配。"),
    "museum": ("简约艺文", "简洁内搭配薄开衫或轻西装，应对室内空调温差", "安静、缓震的软底鞋", ["薄开衫", "小型托特包"], "避免会发出明显摩擦声或带有大量易碰饰件的服装。"),
    "nature": ("轻户外", "透气速干上衣配活动自如的长裤，外加轻量防风防泼水层", "抓地防滑的运动鞋/徒步鞋", ["遮阳帽", "防晒用品", "驱蚊用品"], "优先考虑防晒、防滑和活动范围，草木较多处建议穿长裤。"),
    "city_walk": ("城市漫步", "透气上衣配宽松下装，并用轻薄外套增加层次", "已经磨合好的缓震步行鞋", ["斜挎包", "防磨脚贴"], "预计步数较高，鞋袜舒适度优先于造型。"),
    "viewpoint": ("高处观景", "利落内搭配防风外层，下装避免过于飘逸", "包脚且抓地稳定的鞋", ["防风外套", "固定性好的帽子"], "高处、江边或傍晚可能风大，注意保暖并固定随身配饰。"),
    "food": ("轻松觅食", "耐脏易清洁的上衣配宽松腰部下装，可加一件可脱洗外搭", "方便排队和走动的轻便鞋", ["纸巾", "可折叠购物袋"], "火锅、烧烤等场景尽量避免浅色难打理面料和宽大袖口。"),
    "local_life": ("在地松弛", "基础款上衣配休闲长裤，用城市配色的小单品提亮", "轻便防滑的休闲鞋", ["贴身斜挎包", "折叠袋"], "街巷和市集人流较多，穿着以行动方便、随身物品好收纳为主。"),
    "experience": ("灵活体验", "活动自如的基础层配容易穿脱的外层，避免复杂垂坠装饰", "包脚、防滑的轻便鞋", ["发圈", "小方巾"], "参与手作或沉浸式活动前，以现场着装说明为准。"),
}

DESTINATION_ALIASES = {"上海": "shanghai", "杭州": "hangzhou", "成都": "chengdu", "东京": "tokyo", "京都": "kyoto"}


def _destination_key(destination: str) -> str:
    normalized = (destination or "").strip().lower()
    for alias, canonical in DESTINATION_ALIASES.items():
        if alias in normalized:
            return canonical
    return next((key for key in CITY_STYLE_PROFILES if key in normalized), "default")


def get_city_outfit(destination: str) -> Dict[str, Any]:
    """Return season-neutral style guidance for a destination."""
    return deepcopy(CITY_STYLE_PROFILES.get(_destination_key(destination), DEFAULT_CITY_STYLE))


def get_poi_outfit(destination: str, poi: Dict[str, Any]) -> Dict[str, Any]:
    """Return practical outfit guidance for one attraction and its activity type."""
    category = str(poi.get("category", "landmark")).lower()
    style, clothing, shoes, extras, tip = deepcopy(CATEGORY_OUTFITS.get(category, CATEGORY_OUTFITS["landmark"]))
    tags = {str(tag).lower() for tag in poi.get("tags", [])}
    if "nightlife" in tags:
        extras.append("夜间薄外套")
        tip += " 夜间返程可增加一件醒目或带反光细节的外层。"
    if "nature" in tags and category not in {"nature", "history"}:
        extras.append("防晒/驱蚊用品")
    if "shopping" in tags:
        extras.append("可折叠购物袋")
    return {
        "style": style,
        "clothing": clothing,
        "shoes": shoes,
        "extras": list(dict.fromkeys(extras)),
        "tip": tip,
        "city_style": get_city_outfit(destination)["style_name"],
    }