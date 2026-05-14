"""
AI Health Ecosystem — Streamlit 网页端
前端 UI 融合最新设计稿布局；Supabase / DashScope 核心底层逻辑完美保留。
"""
from __future__ import annotations

import base64
import html
import json
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

import extra_streamlit_components as stx
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# ---------- 静态资源路径 ----------
ROOT = Path(__file__).resolve().parent
STATIC = ROOT / "static"
if not STATIC.is_dir():
    _desk = Path.home() / "Desktop" / "static"
    if _desk.is_dir():
        STATIC = _desk
TEAM_DIR = STATIC / "team"
ICON_DIR = STATIC / "icon"
_ICON_EXTS = (".png", ".svg", ".webp", ".ico", ".jpg", ".jpeg")


def _icon_path(*names: str) -> Path | None:
    if not ICON_DIR.is_dir():
        return None
    for stem in names:
        for ext in _ICON_EXTS:
            p = ICON_DIR / f"{stem}{ext}"
            if p.is_file():
                return p.resolve()
    return None


def _page_icon_arg() -> str:
    hit = _icon_path("favicon") or _icon_path("icon") or _icon_path("logo") or _icon_path("app")
    return str(hit) if hit else "☁️"


def _show_icon(*names: str, width: int = 32) -> bool:
    p = _icon_path(*names)
    if p:
        st.image(str(p), width=width)
        return True
    return False


def _icon_to_data_uri(p: Path) -> str:
    raw = p.read_bytes()
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
        ".svg": "image/svg+xml",
        ".ico": "image/x-icon",
    }.get(p.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"


def _profile_avatar_html(username: str) -> str:
    av_url = f"https://api.dicebear.com/7.x/avataaars/svg?seed={quote(username, safe='')}"
    cam = _icon_path("camera")
    overlay = ""
    if cam:
        uri = _icon_to_data_uri(cam)
        overlay = (
            '<div style="position:absolute;right:6px;bottom:6px;width:40px;height:40px;background:#fff;'
            "border-radius:8px;display:flex;align-items:center;justify-content:center;"
            'box-shadow:0 1px 6px rgba(0,0,0,.22);border:1px solid rgba(0,0,0,.06);">'
            f'<img src="{uri}" style="width:26px;height:26px;object-fit:contain" alt=""/>'
            "</div>"
        )
    return (
        '<div style="position:relative;width:100%;max-width:260px;margin:0 auto 12px auto;">'
        f'<img src="{av_url}" style="width:100%;border-radius:50%;aspect-ratio:1;object-fit:cover;'
        'background:#cfd2cf;display:block;" alt=""/>'
        f"{overlay}</div>"
    )


def _team_images() -> list[Path]:
    out: list[Path] = []
    for base in ("team", "time1", "time2"):
        hit = None
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            p = TEAM_DIR / f"{base}{ext}"
            if p.is_file():
                hit = p
                break
        if hit:
            out.append(hit)
    return out


# ---------- 页面状态与自适应配置 ----------
st.set_page_config(
    page_title="AI Health Ecosystem",
    page_icon=_page_icon_arg(),
    layout="wide",
    initial_sidebar_state="collapsed",
)

for k in ("user", "editing_id"):
    if k not in st.session_state:
        st.session_state[k] = None
if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"
if "lang" not in st.session_state:
    st.session_state.lang = "🇨🇳 简体中文"
if "theme" not in st.session_state:
    st.session_state.theme = "☁️ 云朵白 (Cloud Light)"

for k in ("need_set_cookie", "need_del_cookie"):
    if k not in st.session_state:
        st.session_state[k] = False
if "logout_flag" not in st.session_state:
    st.session_state.logout_flag = False
if "open_login" not in st.session_state:
    st.session_state.open_login = False
if "open_signup" not in st.session_state:
    st.session_state.open_signup = False
if "open_publish" not in st.session_state:
    st.session_state.open_publish = False
if "open_pw" not in st.session_state:
    st.session_state.open_pw = False

cookie_manager = stx.CookieManager(key="cookie_manager")

if st.session_state.need_set_cookie:
    cookie_manager.set("saved_user", st.session_state.user, expires_at=datetime.now() + timedelta(days=30))
    st.session_state.need_set_cookie = False
if st.session_state.need_del_cookie:
    cookie_manager.delete("saved_user")
    st.session_state.need_del_cookie = False

saved_user = cookie_manager.get(cookie="saved_user")
if saved_user and st.session_state.user is None and not st.session_state.logout_flag:
    st.session_state.user = saved_user
    st.rerun()

if st.query_params.get("_home") == "1":
    st.session_state.current_page = "Home"
    st.query_params.clear()
    st.rerun()

# ---------- 双语字典引擎 (i18n) ----------
i18n = {
    "🇨🇳 简体中文": {
        "sys_lang": "简体中文",
        "title": "基于大模型的食谱生成和营养分析工具",
        "login": "登录",
        "signup": "注册",
        "language": "语言",
        "set": "设置",
        "back": "返回大厅",
        "m1": "AI 智能厨房\n可视化食谱生成 + 专家问答",
        "m2": "美食社区\n排行榜 + 交流大厅",
        "m3": "数据管理\n数据记录 + 热量计算",
        "c_t": "🏘️ 美食广场社区",
        "dl_hint": "如果你需要获取更多个性化的食谱……",
        "dl_btn": "点击这里",
        "name_l": "名称",
        "acct_l": "账号",
        "k_t": "☁️ AI 智能后厨",
        "k_t1": "📸 看图出菜谱",
        "k_t2": "💬 营养师问答",
        "vdg": "可视化食谱生成",
        "vdg_help": "你可以直接上传食材照片，在输入框中填写口味偏好与烹饪限制。AI 会结合食材清单与要求生成菜品。你也可以收藏喜欢的菜品。",
        "eqa": "专家问答",
        "eqa_help": "你可以用文字或「文字+图片」提出健康相关问题，AI 将以营养师角色作答。",
        "up": "上传食材照片",
        "req": "附加要求（可选）",
        "gen": "生成菜谱",
        "fav": "⭐️ 收藏此篇",
        "ask": "具体问题描述",
        "up_opt": "上传参考图片（可选）",
        "think": "数据传输中...",
        "h_t": "📈 健康数据管家",
        "h_hist": "历史记录",
        "h_banner": "使用数据管理记录个人信息，并计算三餐热量。",
        "h_chart": "趋势图",
        "h_t1": "📝 数据录入",
        "h_t2": "📊 分析报告",
        "d": "选择日期",
        "w": "体重 (kg)",
        "b": "早餐记录",
        "l": "午餐记录",
        "dn": "晚餐记录",
        "sub": "提交并计算热量",
        "del": "删除",
        "edit": "修改",
        "c_rank": "排行榜",
        "c_t2": "帖子互动",
        "c_hall": "交流大厅 — 欢迎分享你想分享的一切",
        "search_ph": "搜索",
        "search_go": "搜索",
        "nf_add": "没找到？去发布 →",
        "pub": "发布动态",
        "like": "赞",
        "tag": "选择标签",
        "title_in": "输入标题",
        "desc_in": "输入内容",
        "log_req": "⚠️ 请先登录",
        "u_t": "👤 我的主页",
        "u_post": "POST",
        "u_hist": "HISTORY",
        "u_name": "Name",
        "u_acct": "Account",
        "u_pwd": "Password",
        "pwd_edit": "修改密码",
        "new_pwd_title": "NEW PASSWORD",
        "submit": "Submit",
        "close": "关闭",
        "err": "账号或密码错误",
        "suc": "操作成功",
        "out": "退出登录",
        "reg": "注册新号",
        "no_data": "暂无数据",
        "id_in": "输入账号",
        "pwd_in": "输入密码",
        "new_id": "设置新账号",
        "new_pwd": "设置新密码",
        "confirm": "确认",
        "unfav": "🤍 取消收藏",
        "del_post": "🗑️ 删除此贴",
        "reply": "💬 回复",
        "reply_ph": "写下回复...",
        "send": "发送",
        "rec_dish": "🍲 推荐神仙菜品",
        "rec_ph": "输入菜名并回车进行搜索...",
        "voted": "⚠️ 你已经给这道菜投过票啦！",
        "votes": "票",
        "c_vote": "为这道菜投票",
        "guess": "💡 猜你想选 (点击直接推荐):",
        "no_match": "🔍 库中暂无此预设菜品，请点击下方作为新菜推荐：",
        "rec_custom": "✨ 推荐：{}",
        "view_lib": "📚 查看系统预设菜品库 (100款)",
        "about": "关于项目",
        "text": "TEXT",
        "image": "IMAGE",
        "publish": "Publish",
    },
    "🇬🇧 English": {
        "sys_lang": "English",
        "title": "LLM-based recipe generation and nutrition analysis tool",
        "login": "Login",
        "signup": "Signup",
        "language": "Language",
        "set": "Settings",
        "back": "Back to Home",
        "m1": "AI Smart Kitchen\nVisual Dish Generation + Expert Q&A",
        "m2": "Community\nRanking List + Chat Hall",
        "m3": "Data Manager\nRecord Data + Calculate Calories",
        "c_t": "🏘️ Community Square",
        "dl_hint": "If you need to download more recipe resources for personalized needs...",
        "dl_btn": "click here",
        "name_l": "Name",
        "acct_l": "Account",
        "k_t": "☁️ AI Kitchen",
        "k_t1": "📸 Image to Recipe",
        "k_t2": "💬 Dietitian Q&A",
        "vdg": "Visual Dish Generation",
        "vdg_help": "Upload photos of ingredients and fill taste preferences and cooking restrictions. The AI generates dishes from ingredients and your needs. You can also collect favorites.",
        "eqa": "Expert Q&A",
        "eqa_help": "Ask health-related questions in text or text with pictures. The AI answers as a nutritionist.",
        "up": "Upload ingredient photos",
        "req": "Additional Requirements (Optional)",
        "gen": "Generate recipes",
        "fav": "⭐️ Save Recipe",
        "ask": "Specific problem description",
        "up_opt": "Upload reference photos (Optional)",
        "think": "Transmitting data...",
        "h_t": "📈 Health Data Manager",
        "h_hist": "History record",
        "h_banner": "Just use this Data Manager to help you to Record Personal Data and Calculate Three-Meal Calories!",
        "h_chart": "Charts",
        "h_t1": "📝 Data Entry",
        "h_t2": "📊 Analytics",
        "d": "Date",
        "w": "Weight (kg)",
        "b": "Breakfast",
        "l": "Lunch",
        "dn": "Dinner",
        "sub": "Submit",
        "del": "Delete",
        "edit": "Edit",
        "c_rank": "Ranking List",
        "c_t2": "Discussion",
        "c_hall": "CHAT HALL — WELCOME TO SHARE WHATEVER YOU LIKE",
        "search_ph": "Search",
        "search_go": "Search",
        "nf_add": "Not found? Add one →",
        "pub": "Publish",
        "like": "Like",
        "tag": "Select Tag",
        "title_in": "Enter Title",
        "desc_in": "Enter Details",
        "log_req": "⚠️ Please login first",
        "u_t": "👤 My Profile",
        "u_post": "POST",
        "u_hist": "HISTORY",
        "u_name": "Name",
        "u_acct": "Account",
        "u_pwd": "Password",
        "pwd_edit": "Change password",
        "new_pwd_title": "NEW PASSWORD",
        "submit": "Submit",
        "close": "Close",
        "err": "Invalid credentials",
        "suc": "Success",
        "out": "Logout",
        "reg": "Register",
        "no_data": "No data available",
        "id_in": "Enter ID",
        "pwd_in": "Enter Password",
        "new_id": "Create ID",
        "new_pwd": "Create Password",
        "confirm": "Confirm",
        "unfav": "🤍 Unfavorite",
        "del_post": "🗑️ Delete Post",
        "reply": "💬 Reply",
        "reply_ph": "Write a reply...",
        "send": "Send",
        "rec_dish": "🍲 Recommend a Dish",
        "rec_ph": "Type dish name and press Enter...",
        "voted": "⚠️ You already voted for this dish!",
        "votes": "votes",
        "c_vote": "Vote for this dish",
        "guess": "💡 Suggestions (Click to vote):",
        "no_match": "🔍 Not in library. Click below to recommend:",
        "rec_custom": "✨ Recommend: {}",
        "view_lib": "📚 View System Dish Library (100 Items)",
        "about": "About our project",
        "text": "TEXT",
        "image": "IMAGE",
        "publish": "Publish",
    },
}
t = i18n[st.session_state.lang]

# 100款中英双语菜品系统库
dish_library = {
    "🇨🇳 简体中文": [
        "西红柿炒鸡蛋", "西红柿牛腩", "宫保鸡丁", "红烧肉", "清蒸鲈鱼", "麻婆豆腐", "青椒肉丝", "糖醋排骨", "蒜蓉西兰花", "酸菜鱼",
        "北京烤鸭", "回锅肉", "鱼香肉丝", "水煮牛肉", "辣子鸡", "蒜薹炒肉", "地三鲜", "锅包肉", "蚂蚁上树", "葱爆羊肉",
        "孜然羊肉", "糖醋里脊", "木须肉", "韭菜炒鸡蛋", "番茄炒蛋", "紫菜蛋花汤", "酸辣汤", "排骨莲藕汤", "佛跳墙", "东坡肉",
        "白切鸡", "盐焗鸡", "烧鹅", "烤乳猪", "卤水拼盘", "干炒牛河", "扬州炒饭", "腊味煲仔饭", "菠萝咕噜肉", "避风塘炒蟹",
        "剁椒鱼头", "农家小炒肉", "毛氏红烧肉", "腊肉炒肉", "湘西外婆菜", "叫花鸡", "红烧狮子头", "盐水鸭", "大煮干丝", "松鼠鳜鱼",
        "西湖醋鱼", "龙井虾仁", "宫廷豌豆黄", "驴打滚", "老北京炸酱面", "羊肉泡馍", "陕西凉皮", "肉夹馍", "兰州牛肉面", "新疆大盘鸡",
        "烤包子", "手抓羊肉", "酥油茶", "糌粑", "云南汽锅鸡", "过桥米线", "柳州螺蛳粉", "桂林米粉", "广东肠粉", "水晶虾饺",
        "广式烧卖", "蜜汁叉烧包", "虎皮凤爪", "葡式蛋挞", "腊味萝卜糕", "荔湾艇仔粥", "核桃包", "金牌流沙包", "潮汕牛肉火锅", "重庆老火锅",
        "成都串串香", "四川冒菜", "乐山钵钵鸡", "万州烤鱼", "天津煎饼果子", "肉段烧茄子", "东北溜肉段", "东北杀猪菜", "小鸡炖蘑菇", "铁锅炖大鹅",
        "拔丝地瓜", "酱骨架", "葱烧海参", "油焖大虾", "九转大肠", "德州扒鸡", "爆炒腰花", "糖醋鲤鱼", "新疆烤肉串", "台湾卤肉饭",
        "客家三杯鸡", "沙茶牛肉", "蚝烙", "三杯鸭", "梅菜扣肉", "清炖羊肉", "手撕包菜", "酸辣土豆丝", "麻酱拌面", "红油抄手",
    ],
    "🇬🇧 English": [
        "Tomato and Egg Stir-fry", "Tomato Beef Brisket", "Kung Pao Chicken", "Braised Pork Belly", "Steamed Sea Bass", "Mapo Tofu", "Pepper Steak", "Sweet and Sour Spare Ribs", "Garlic Broccoli", "Sauerkraut Fish",
        "Peking Duck", "Twice-cooked Pork", "Fish-Flavored Shredded Pork", "Poached Sliced Beef in Hot Chili Oil", "Spicy Diced Chicken", "Stir-fried Pork with Garlic Scapes", "Di San Xian", "Guo Bao Rou", "Ants Climbing a Tree", "Scallion Stir-fried Mutton",
        "Cumin Mutton", "Sweet and Sour Pork Tenderloin", "Moo Shu Pork", "Scrambled Eggs with Chives", "Scrambled Eggs with Tomato", "Seaweed and Egg Soup", "Hot and Sour Soup", "Pork Rib and Lotus Root Soup", "Buddha Jumps Over the Wall", "Dongpo Pork",
        "Boiled Chicken", "Salt Baked Chicken", "Roast Goose", "Roast Suckling Pig", "Braised Delicacies Platter", "Beef Chow Fun", "Yangzhou Fried Rice", "Claypot Rice with Cured Meat", "Sweet and Sour Pork with Pineapple", "Typhoon Shelter Fried Crab",
        "Steamed Fish Head with Hot Red Peppers", "Stir-fried Pork with Pepper", "Mao's Braised Pork", "Stir-fried Smoked Pork", "Xiangxi Grandma's Veggies", "Beggar's Chicken", "Braised Pork Balls in Brown Sauce", "Salted Duck", "Boiled Shredded Tofu", "Squirrel-shaped Mandarin Fish",
        "West Lake Fish in Vinegar Gravy", "Longjing Shrimp", "Imperial Pea Cake", "Glutinous Rice Rolls", "Noodles with Soybean Paste", "Pita Bread Soaked in Mutton Soup", "Cold Rice Noodles", "Roujiamo", "Lanzhou Beef Noodles", "Big Plate Chicken",
        "Baked Samosa", "Hand-Grabbed Mutton", "Butter Tea", "Tsampa", "Steam Pot Chicken", "Crossing the Bridge Noodles", "Luosifen", "Guilin Rice Noodles", "Rice Noodle Roll", "Har Gow",
        "Shumai", "BBQ Pork Bun", "Chicken Feet", "Egg Tart", "Turnip Cake", "Tingzai Porridge", "Walnut Bun", "Custard Bun", "Chaoshan Beef Hot Pot", "Chongqing Hot Pot",
        "Chuan Chuan Xiang", "Mao Cai", "Bobo Chicken", "Grilled Fish", "Jianbing Guozi", "Fried Pork Chunks with Eggplant", "Sautéed Pork Chunks", "Pork Stew", "Stewed Chicken with Mushrooms", "Iron Pot Stewed Goose",
        "Candied Sweet Potato", "Sauce Bone", "Scallion Braised Sea Cucumber", "Braised Prawns", "Braised Intestines in Brown Sauce", "Dezhou Braised Chicken", "Stir-fried Pork Kidney", "Sweet and Sour Carp", "Mutton Skewers", "Taiwanese Braised Pork Rice",
        "Hakka Three Cup Chicken", "Shacha Beef", "Oyster Omelette", "Three Cup Duck", "Braised Pork with Mustard Greens", "Stewed Mutton", "Hand-torn Cabbage", "Hot and Sour Shredded Potatoes", "Noodles with Sesame Paste", "Wontons in Chili Oil",
    ],
}


@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])


try:
    supabase, api_key = init_db(), st.secrets["ALIYUN_API_KEY"]
except Exception:
    st.error("Database connection failed.")
    st.stop()

theme_colors = {
    "☁️ 云朵白 (Cloud Light)": {"bg": "#fcfcfd", "card": "#ffffff", "text": "#1d1d1f"},
    "🌌 暗夜黑 (Dark Mode)": {"bg": "#1c1c1e", "card": "#2c2c2e", "text": "#f5f5f7"},
    "🍃 抹茶绿 (Nature Mint)": {"bg": "#f4fbf6", "card": "#ffffff", "text": "#2d3a33"},
    "🌊 海洋蓝 (Ocean Blue)": {"bg": "#f4f9ff", "card": "#ffffff", "text": "#0a2540"},
}
c = theme_colors[st.session_state.theme]

# 设计主色（去红化保留，按钮色调设为灰色以确保统一规范）
SAGE_BG = "#d8e6d1"
SIDE_BG = "#6b8f6f"
DEEP_GREEN = "#2f4a35"
CREAM = "#f3f0e4"
MINT_MAIN = "#e6f2e0"
CHAT_MAIN_BG = "#c5d4b8"
COMM_RANK_SIDEBAR = "#6b6e6b"
RANK_CARD_BG = "#d8dcd8"
RESOURCE_DOWNLOAD_URL = "https://c.wss.ink/f/jwbexvk2wer"

st.markdown(
    f"""
<style>
header[data-testid="stHeader"], footer {{ visibility: hidden !important; height: 0 !important; }}
.stApp {{ background: {SAGE_BG} !important; }}
.block-container {{ max-width: 1280px !important; padding-top: 0.5rem !important; }}

div[data-testid="stButton"] > button {{
  color: {c['text']} !important;
  border-color: rgba(150,150,150,0.25) !important;
}}

.pill-btn > button {{
  background: {DEEP_GREEN} !important;
  color: #fff !important;
  border-radius: 999px !important;
  border: none !important;
  padding: 0.35rem 0.9rem !important;
}}
.side-card button {{
  background: #bdbdbd !important;
  color: #1a1a1a !important;
  border-radius: 16px !important;
  min-height: 88px !important;
  white-space: pre-wrap !important;
  text-align: left !important;
  border: none !important;
}}
a.dl-side-link {{
  display: block;
  width: 100%;
  background: {DEEP_GREEN};
  color: #fff !important;
  text-align: center;
  border-radius: 12px;
  padding: 10px 14px;
  text-decoration: none !important;
  font-weight: 600;
  box-sizing: border-box;
}}
a.dl-side-link:hover {{
  filter: brightness(1.08);
}}
.red-cta > button {{
  background: #9e9e9e !important; 
  color: #fff !important;
  border: none !important;
  border-radius: 12px !important;
}}
.footer-bar {{
  background: {DEEP_GREEN};
  padding: 10px 12px;
  border-radius: 12px;
  margin-top: 8px;
}}
.masonry {{
  column-count: 4;
  column-gap: 10px;
}}
@media (max-width: 1100px) {{
  .masonry {{ column-count: 2; }}
}}
.card-brick {{
  break-inside: avoid;
  background: #fff;
  border-radius: 12px;
  padding: 10px;
  margin: 0 0 10px 0;
  border: 1px solid rgba(0,0,0,0.06);
}}
.rank-row {{
  background: {CREAM};
  border-radius: 10px;
  padding: 10px 12px;
  margin-bottom: 8px;
  display:flex;
  align-items:center;
  justify-content: space-between;
}}
.chat-head {{
  background: {DEEP_GREEN};
  color: #e8ffe8;
  padding: 8px 12px;
  border-radius: 8px;
  font-weight: 600;
  letter-spacing: 0.02em;
}}
.win-dots span {{
  display:inline-block;width:10px;height:10px;border-radius:999px;margin-right:6px;
}}
.chart-box {{
  background: #5a5a5a;
  border-radius: 12px;
  padding: 8px;
  min-height: 220px;
}}
.profile-side {{
  background: {DEEP_GREEN};
  border-radius: 14px;
  padding: 14px;
}}
.section-head {{
  background: {DEEP_GREEN};
  color: #fff;
  padding: 8px 12px;
  border-radius: 8px;
  font-weight: 700;
}}
</style>
""",
    unsafe_allow_html=True,
)


def ask_ai_stream(sys_p, usr_p, img=None):
    usr_p += f"\n\n[CRITICAL INSTRUCTION: You must strictly output your entire response in {t['sys_lang']}! Do not use any other language.]"
    model = "qwen-vl-plus" if img else "qwen-plus"
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    msg_content = [{"type": "text", "text": usr_p}]
    if img:
        img_b64 = base64.b64encode(img).decode("utf-8")
        msg_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
    
    data = {
        "model": model, 
        "messages": [
            {"role": "system", "content": sys_p}, 
            {"role": "user", "content": msg_content}
        ], 
        "stream": True
    }
    try:
        res = requests.post(url, headers=h, json=data, timeout=90, stream=True)
        for line in res.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        chunk_str = line_str[6:]
                        chunk = json.loads(chunk_str)
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta:
                            yield delta
                    except Exception:
                        pass
    except Exception as e:
        yield f"\n\nAI Network Error: {str(e)}"


def ask_ai_sync(sys_p, usr_p):
    model = "qwen-plus"
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model, 
        "messages": [
            {"role": "system", "content": sys_p}, 
            {"role": "user", "content": usr_p}
        ]
    }
    try:
        res = requests.post(url, headers=h, json=data, timeout=30)
        return res.json()["choices"][0]["message"]["content"]
    except Exception:
        return "0"


def _require_login():
    st.session_state.open_login = True
    st.session_state.current_page = "Home"
    st.rerun()


def traffic_dots(uid: str) -> None:
    # 彻底去除原有的红色关闭按钮，改用统一的银灰色保持中性规范
    h = 22
    w = 72
    html = """
<!DOCTYPE html>
<html><head><meta charset="utf-8"></head>
<body style="margin:0;padding:0;background:transparent;">
<div style="display:flex;align-items:center;gap:7px;height:22px;padding:0 2px;">
<button type="button" aria-label="close" style="width:12px;height:12px;border-radius:50%;background:#d1d1d1;border:0.5px solid rgba(0,0,0,.22);cursor:pointer;padding:0;flex-shrink:0;box-shadow:0 1px 2px rgba(0,0,0,.28),inset 0 1px 0 rgba(255,255,255,.35);"
  onclick="(function(){var u=new URL(window.parent.location.href);u.searchParams.set('_home','1');window.parent.location.href=u.toString();})()"></button>
<span style="width:12px;height:12px;border-radius:50%;background:#febc2e;border:0.5px solid rgba(0,0,0,.22);flex-shrink:0;display:inline-block;box-shadow:0 1px 2px rgba(0,0,0,.25),inset 0 1px 0 rgba(255,255,255,.4);"></span>
<span style="width:12px;height:12px;border-radius:50%;background:#28c840;border:0.5px solid rgba(0,0,0,.22);flex-shrink:0;display:inline-block;box-shadow:0 1px 2px rgba(0,0,0,.22),inset 0 1px 0 rgba(255,255,255,.35);"></span>
</div>
</body></html>
"""
    components.html(html, height=h, width=w, scrolling=False, key=f"traffic_{uid}")


def m_kitchen():
    L, R = st.columns(2, gap="large")
    with L:
        st.markdown(f"<div style='background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:10px;font-weight:700'>{t['vdg']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top:8px;background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:12px;font-size:0.95rem'>{t['vdg_help']}</div>", unsafe_allow_html=True)
        up = st.file_uploader(t["up"], type=["jpg", "png"], key="f1")
        pref = st.text_input(t["req"])
        if up:
            st.image(up, use_column_width=True)
        if st.button(t["gen"], use_container_width=True) and up:
            with st.spinner(t["think"]):
                res_stream = ask_ai_stream(
                    "You are a Master Chef.",
                    f"Identify ingredients and generate a professional recipe. Preferences: {pref}",
                    up.getvalue(),
                )
                st.session_state["l_rec"] = st.write_stream(res_stream)
        if st.session_state.get("l_rec") and st.session_state.user and st.button(t["fav"]):
            try:
                supabase.table("favorites").insert({"username": st.session_state.user, "recipe_content": st.session_state["l_rec"]}).execute()
                st.success(t["suc"])
            except Exception as e:
                st.error(f"DB Error: {e}")
    with R:
        rh1, rh2 = st.columns([0.78, 0.22])
        with rh1:
            st.markdown(
                f"<div style='background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:10px;font-weight:700'>{t['eqa']}</div>",
                unsafe_allow_html=True,
            )
        with rh2:
            st.markdown("<div style='padding-top:6px'>", unsafe_allow_html=True)
            traffic_dots("kitchen_eq")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='margin-top:8px;background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:12px;font-size:0.95rem'>{t['eqa_help']}</div>", unsafe_allow_html=True)
        up_nutri = st.file_uploader(t["up_opt"], type=["jpg", "png"], key="f2")
        if up_nutri:
            st.image(up_nutri, use_column_width=True)
        q = st.text_area(t["ask"])
        if st.button(t["confirm"], use_container_width=True) and q:
            with st.spinner(t["think"]):
                res_stream = ask_ai_stream("You are a professional Dietitian.", q, up_nutri.getvalue() if up_nutri else None)
                st.write_stream(res_stream)


def m_health():
    if not st.session_state.user:
        _require_login()
    st.markdown(
        f"<div style='background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:10px;margin-bottom:10px'>{t['h_banner']}</div>",
        unsafe_allow_html=True,
    )
    ht1, ht2 = st.columns([0.09, 0.91])
    with ht1:
        traffic_dots("health_win")
    with ht2:
        st.empty()
    left, right = st.columns([1, 2], gap="medium")
    with left:
        st.markdown(f"**{t['h_hist']}**")
        logs_data = supabase.table("diet_logs").select("*").eq("username", st.session_state.user).order("log_date", desc=True).execute().data
        for r in logs_data:
            with st.expander(f"{r['log_date']} | {r['weight']}kg | {r['calories']}kcal"):
                st.write(f"{t['b']}:{r.get('breakfast','')} {t['l']}:{r.get('lunch','')} {t['dn']}:{r.get('dinner','')}")
                ce, cd = st.columns(2)
                if ce.button(t["edit"], key=f"e_{r['id']}"):
                    st.session_state.editing_id = r["id"]
                    st.rerun()
                if cd.button(t["del"], key=f"d_{r['id']}"):
                    try:
                        supabase.table("diet_logs").delete().eq("id", r["id"]).execute()
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))
    with right:
        st.markdown(f"<div class='chart-box'>", unsafe_allow_html=True)
        logs = supabase.table("diet_logs").select("*").eq("username", st.session_state.user).order("log_date").execute().data
        if logs:
            df = pd.DataFrame(logs)
            df["log_date"] = pd.to_datetime(df["log_date"])
            df.set_index("log_date", inplace=True)
            st.line_chart(df[["weight", "calories"]])
        else:
            st.caption(t["no_data"])
        st.markdown("</div>", unsafe_allow_html=True)

        with st.form("d_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d = c1.date_input(t["d"], date.today())
            # 【完美融合点】：此处体重最小值放宽为20.0，默认值已设为你要求的40.0
            w = c2.number_input(t["w"], min_value=20.0, value=40.0, step=0.1)
            b = st.text_input(t["b"])
            l = st.text_input(t["l"])
            dn = st.text_input(t["dn"])
            if st.form_submit_button(t["sub"], type="primary"):
                cal_str = ask_ai_sync("Nutrition Calculator", f"Estimate total calories. Return ONLY an integer: Breakfast:{b} Lunch:{l} Dinner:{dn}")
                cal = int("".join(filter(str.isdigit, cal_str)) or 0)
                payload = {
                    "username": st.session_state.user,
                    "log_date": str(d),
                    "weight": w,
                    "calories": cal,
                    "breakfast": b,
                    "lunch": l,
                    "dinner": dn,
                }
                try:
                    if st.session_state.editing_id:
                        supabase.table("diet_logs").update(payload).eq("id", st.session_state.editing_id).execute()
                        st.session_state.editing_id = None
                    else:
                        supabase.table("diet_logs").insert(payload).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"DB Error: {e}")

        if st.session_state.editing_id:
            st.caption(f"Editing record id={st.session_state.editing_id} (submit form to save)")


def _submit_vote(dish_name: str):
    try:
        exist = supabase.table("dish_ranking").select("*").eq("dish_name", dish_name).execute().data
        if exist:
            record = exist[0]
            voters = record.get("voted_by", [])
            if not isinstance(voters, list):
                voters = []
            if st.session_state.user in voters:
                st.warning(t["voted"])
            else:
                voters.append(st.session_state.user)
                supabase.table("dish_ranking").update({"votes": record["votes"] + 1, "voted_by": voters}).eq("id", record["id"]).execute()
                st.rerun()
        else:
            supabase.table("dish_ranking").insert({"dish_name": dish_name, "votes": 1, "voted_by": [st.session_state.user]}).execute()
            st.rerun()
    except Exception as e:
        st.error(f"DB Error: {e}")


def m_community():
    rank_col, main_col = st.columns([1, 3], gap="medium")
    with rank_col:
        st.markdown(
            f"<div style='background:{COMM_RANK_SIDEBAR};border-radius:12px;padding:12px 10px 10px 10px;margin-bottom:8px'>"
            f"<div style='font-family:Georgia,serif;font-weight:700;color:#fafafa;margin:0'>{t['c_rank']}</div></div>",
            unsafe_allow_html=True,
        )
        top_dishes = supabase.table("dish_ranking").select("*").order("votes", desc=True).limit(8).execute().data
        if top_dishes:
            for d in top_dishes:
                row_l, row_r = st.columns([0.78, 0.22], gap="small")
                with row_l:
                    st.markdown(
                        f"<div class='rank-row' style='background:{RANK_CARD_BG};color:#1a1a1a;border:1px solid rgba(0,0,0,.08)'>"
                        f"<span><b>{d['dish_name']}</b> — {d['votes']} {t['votes']}</span></div>",
                        unsafe_allow_html=True,
                    )
                with row_r:
                    st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                    hp = _icon_path("heart")
                    if hp:
                        st.image(str(hp), width=26)
                    if st.session_state.user:
                        if st.button(
                            " " if hp else "♥",
                            key=f"hv_{d['id']}",
                            help=t["c_vote"],
                            use_container_width=True,
                        ):
                            _submit_vote(d["dish_name"])
        else:
            st.info(t["no_data"])

    with main_col:
        st.markdown(f"<div class='chat-head'>{t['c_hall']}</div>", unsafe_allow_html=True)
        cd1, cd2 = st.columns([0.12, 0.88])
        with cd1:
            traffic_dots("community_hall")
        with cd2:
            st.empty()

        comments_data = supabase.table("comments").select("*").order("id", desc=True).execute().data
        parts = [
            f"<div style='background:{CHAT_MAIN_BG};padding:12px;border-radius:12px;margin-top:4px;'><div class='masonry'>"
        ]
        for r in comments_data:
            parts.append(
                "<div class='card-brick'>"
                f"<div style='font-weight:700'>{r.get('dish_name','')}</div>"
                f"<div style='opacity:.85;font-size:.9rem'>{r.get('user_name','')}</div>"
                f"<div style='margin-top:6px'>{r.get('comment','')}</div>"
                "</div>"
            )
        parts.append("</div></div>")
        st.markdown("".join(parts), unsafe_allow_html=True)

        st.markdown(f"**{t['c_t2']}**")
        for r in comments_data:
            with st.container(border=True):
                st.write(f"**{r['user_name']}** | 🏷️ {r['tag']}\n### {r['dish_name']}\n{r['comment']}")
                lk = r.get("liked_by") if isinstance(r.get("liked_by"), list) else []
                has_liked = (st.session_state.user in lk) if st.session_state.user else False
                if st.button(f"{t['like']} ({r.get('likes', 0)})", key=f"l_{r['id']}", disabled=(not st.session_state.user or has_liked)):
                    lk.append(st.session_state.user)
                    try:
                        supabase.table("comments").update({"likes": int(r.get("likes", 0)) + 1, "liked_by": lk}).eq("id", r["id"]).execute()
                        st.rerun()
                    except Exception:
                        pass
                reps = r.get("replies") if isinstance(r.get("replies"), list) else []
                if reps:
                    st.markdown("---")
                    for rep in reps:
                        st.caption(f"💬 **{rep.get('u', 'User')}**: {rep.get('t', '')}")
                if st.session_state.user:
                    with st.expander(t["reply"]):
                        rep_text = st.text_input(t["reply_ph"], key=f"rt_{r['id']}")
                        if st.button(t["send"], key=f"rs_{r['id']}") and rep_text:
                            reps.append({"u": st.session_state.user, "t": rep_text})
                            try:
                                supabase.table("comments").update({"replies": reps}).eq("id", r["id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

        st.markdown("<div class='footer-bar'>", unsafe_allow_html=True)
        fc1, fc2, fc3, fc4 = st.columns([4, 1, 2, 1])
        with fc1:
            if st.session_state.user:
                sp = _icon_path("search")
                if sp:
                    sico, sinp = st.columns([0.09, 0.91], gap="small")
                    with sico:
                        st.markdown("<div style='margin-top:10px'></div>", unsafe_allow_html=True)
                        st.image(str(sp), width=22)
                    with sinp:
                        q = st.text_input("q", label_visibility="collapsed", placeholder=t["search_ph"], key="comm_search")
                else:
                    q = st.text_input("q", label_visibility="collapsed", placeholder=t["search_ph"], key="comm_search")
            else:
                st.caption(t["log_req"])
                q = ""
        with fc2:
            st.write("")
            if st.session_state.user and st.button(t["search_go"], key="comm_go"):
                st.session_state["_dish_q"] = st.session_state.get("comm_search", "")
        with fc3:
            if st.session_state.user and st.button(t["nf_add"], key="nfadd"):
                st.session_state.open_publish = True
                st.rerun()
        with fc4:
            if st.session_state.user:
                pp = _icon_path("plus")
                if pp:
                    st.image(str(pp), width=32)
                if st.button(" " if pp else "➕", key="bigplus", type="primary", use_container_width=True, help=t["nf_add"]):
                    st.session_state.open_publish = True
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        # 【完美融合点】：此前的100款智能联想搜库与动态建库算法结合于此
        dish_q = st.session_state.pop("_dish_q", None)
        if dish_q and st.session_state.user:
            lib = dish_library[st.session_state.lang]
            dish_clean = dish_q.strip()
            matches = [d for d in lib if dish_clean.lower() in d.lower()]
            if matches:
                st.caption(t["guess"])
                cols = st.columns(4)
                for i, match in enumerate(matches[:4]):
                    if cols[i % 4].button(match, key=f"match_{i}", use_container_width=True):
                        _submit_vote(match)
                if dish_clean not in matches and st.button(t["rec_custom"].format(dish_clean), use_container_width=True):
                    _submit_vote(dish_clean)
            else:
                st.caption(t["no_match"])
                if st.button(t["rec_custom"].format(dish_clean), key="rec_cust", use_container_width=True):
                    _submit_vote(dish_clean)
            with st.expander(t["view_lib"]):
                formatted_lib = "".join(
                    [
                        f"<div style='flex:1 0 21%;margin:6px;padding:10px;background:#fff;border-radius:12px;border:1px solid rgba(0,0,0,.06);text-align:center'>🍲 {d}</div>"
                        for d in lib
                    ]
                )
                st.markdown(f"<div style='display:flex;flex-wrap:wrap;justify-content:space-between'>{formatted_lib}</div>", unsafe_allow_html=True)


@st.dialog(t["pub"])
def dlg_publish():
    tag_opts = ["#Daily", "#Diet", "#Yummy"] if t["sys_lang"] == "English" else ["#日常", "#减脂", "#神仙菜"]
    tag = st.selectbox(t["tag"], tag_opts)
    dish = st.text_input(t["title_in"])
    cont = st.text_area(t["desc_in"])
    _ = st.file_uploader(t["image"], type=["jpg", "png"], key="pubimg")
    c1, c2 = st.columns(2)
    if c1.button(t["close"]):
        st.session_state.open_publish = False
        st.rerun()
    if c2.button(t["publish"], type="primary") and dish:
        try:
            supabase.table("comments").insert(
                {
                    "user_name": st.session_state.user,
                    "author_username": st.session_state.user,
                    "dish_name": dish,
                    "comment": cont,
                    "likes": 0,
                    "liked_by": [],
                    "tag": tag,
                    "replies": [],
                }
            ).execute()
            st.session_state.open_publish = False
            st.rerun()
        except Exception as e:
            st.error(str(e))


@st.dialog(t["new_pwd_title"])
def dlg_pw():
    npw = st.text_input(t["new_pwd"], type="password")
    a1, a2 = st.columns(2)
    if a1.button(t["close"]):
        st.session_state.open_pw = False
        st.rerun()
    if a2.button(t["submit"], type="primary") and npw:
        try:
            supabase.table("app_users").update({"password": npw}).eq("username", st.session_state.user).execute()
            st.session_state.open_pw = False
            st.success(t["suc"])
            st.rerun()
        except Exception as e:
            st.error(str(e))


def _save_profile_name(key: str):
    if not st.session_state.user:
        return
    nv = (st.session_state.get(key) or "").strip()
    if not nv:
        return
    try:
        supabase.table("app_users").update({"profile_name": nv}).eq("username", st.session_state.user).execute()
    except Exception:
        st.session_state["_profile_warn"] = "如需保存姓名，请在 Supabase 的 app_users 表添加 profile_name (text) 字段。"


def m_profile():
    if not st.session_state.user:
        _require_login()
    L, R = st.columns([2, 1], gap="medium")
    with L:
        st.markdown(f"<div class='section-head'>{t['u_post']}</div>", unsafe_allow_html=True)
        my_posts = supabase.table("comments").select("*").eq("author_username", st.session_state.user).order("id", desc=True).execute().data
        pcs = st.columns(3)
        if not my_posts:
            st.info(t["no_data"])
        else:
            for i, p in enumerate(my_posts[:9]):
                with pcs[i % 3]:
                    with st.container(border=True):
                        st.markdown(f"**{p.get('dish_name','')}**")
                        st.caption((p.get("comment") or "")[:120])
                        if st.button(t["del_post"], key=f"dp_{p['id']}"):
                            try:
                                supabase.table("comments").delete().eq("id", p["id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

        st.markdown(f"<div class='section-head' style='margin-top:14px'>{t['u_hist']}</div>", unsafe_allow_html=True)
        favs = supabase.table("favorites").select("*").eq("username", st.session_state.user).order("id", desc=True).execute().data
        fcs = st.columns(3)
        if not favs:
            st.info(t["no_data"])
        else:
            for i, f in enumerate(favs[:9]):
                with fcs[i % 3]:
                    with st.container(border=True):
                        if f.get("recipe_content"):
                            with st.expander(t["fav"]):
                                st.markdown(f["recipe_content"])
                        if st.button(t["unfav"], key=f"uf_{f['id']}"):
                            try:
                                supabase.table("favorites").delete().eq("id", f["id"]).execute()
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

    with R:
        st.markdown("<div class='profile-side'>", unsafe_allow_html=True)
        pr1, pr2 = st.columns([0.62, 0.38])
        with pr1:
            st.empty()
        with pr2:
            st.markdown("<div style='text-align:right;padding:4px 0'>", unsafe_allow_html=True)
            traffic_dots("profile_side")
            st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(_profile_avatar_html(st.session_state.user), unsafe_allow_html=True)
        urow = supabase.table("app_users").select("*").eq("username", st.session_state.user).execute().data
        prof = (urow[0] if urow else {}) or {}
        default_name = prof.get("profile_name") or st.session_state.user
        nk = f"pn_{st.session_state.user}"
        if nk not in st.session_state:
            st.session_state[nk] = default_name
        st.text_input(t["u_name"], key=nk, on_change=lambda k=nk: _save_profile_name(k))
        st.text_input(t["u_acct"], value=st.session_state.user, disabled=True)
        pen = _icon_path("pencil")
        pw1, pw2 = st.columns([0.76, 0.24])
        with pw1:
            st.text_input(t["u_pwd"], value="********", disabled=True)
        with pw2:
            st.markdown("<div style='height:2.4rem'></div>", unsafe_allow_html=True)
            if pen:
                st.image(str(pen), width=30)
                if st.button(" ", key="pwd_edit", help=t["pwd_edit"], type="primary", use_container_width=True):
                    st.session_state.open_pw = True
            else:
                if st.button(t["pwd_edit"], key="pwd_edit", use_container_width=True):
                    st.session_state.open_pw = True
        if st.button(t["out"], type="primary", use_container_width=True, key="logout_profile"):
            st.session_state.user = None
            st.session_state.need_del_cookie = True
            st.session_state.logout_flag = True
            st.session_state.current_page = "Home"
            st.rerun()
        if st.session_state.get("_profile_warn"):
            st.warning(st.session_state.pop("_profile_warn"))
        st.markdown("</div>", unsafe_allow_html=True)

    if st.session_state.get("open_pw"):
        dlg_pw()


def m_about():
    imgs = _team_images()
    if not imgs:
        st.warning("未找到 static/team 下的 team / time1 / time2 图片，请将文件放入项目 static 目录。")
        return
    st.markdown("<div style='max-height:88vh;overflow-y:auto;padding-right:8px'>", unsafe_allow_html=True)
    for p in imgs:
        st.image(str(p), use_column_width=True)
    st.markdown("</div>", unsafe_allow_html=True)


@st.dialog(t["login"])
def dlg_login():
    u = st.text_input(t["id_in"])
    p = st.text_input(t["pwd_in"], type="password")
    a, b = st.columns(2)
    if a.button(t["close"]):
        st.session_state.open_login = False
        st.rerun()
    if b.button(t["confirm"], type="primary"):
        try:
            if supabase.table("app_users").select("*").eq("username", u).eq("password", p).execute().data:
                st.session_state.user = u
                st.session_state.need_set_cookie = True
                st.session_state.logout_flag = False
                st.session_state.open_login = False
                st.rerun()
            else:
                st.error(t["err"])
        except Exception as e:
            st.error(str(e))


@st.dialog(t["signup"])
def dlg_signup():
    nu = st.text_input(t["new_id"])
    np = st.text_input(t["new_pwd"], type="password")
    a, b = st.columns(2)
    if a.button(t["close"]):
        st.session_state.open_signup = False
        st.rerun()
    if b.button(t["confirm"], type="primary"):
        try:
            if supabase.table("app_users").select("*").eq("username", nu).execute().data:
                st.error(t["err"])
            else:
                supabase.table("app_users").insert({"username": nu, "password": np}).execute()
                st.session_state.open_signup = False
                st.success(t["suc"])
                st.rerun()
        except Exception as e:
            st.error(str(e))


def render_home():
    side, main = st.columns([0.28, 0.72], gap="large")
    with side:
        st.markdown(f"<div style='background:{SIDE_BG};padding:14px;border-radius:14px;min-height:720px'>", unsafe_allow_html=True)
        st.markdown("### ")
        st.markdown('<div class="side-card">', unsafe_allow_html=True)
        _show_icon("kitchen", "ai_kitchen", "m1", width=36)
        if st.button(t["m1"], key="nav_m1", use_container_width=True):
            st.session_state.current_page = "A"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="side-card">', unsafe_allow_html=True)
        _show_icon("community", "hall", "m2", width=36)
        if st.button(t["m2"], key="nav_m2", use_container_width=True):
            st.session_state.current_page = "C"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown('<div class="side-card">', unsafe_allow_html=True)
        _show_icon("data", "health", "chart", "m3", width=36)
        if st.button(t["m3"], key="nav_m3", use_container_width=True):
            st.session_state.current_page = "B"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<div style='color:#fff;margin:12px 0 6px 0;font-size:0.95rem'>{t['dl_hint']}</div>", unsafe_allow_html=True)
        dl1, dl2 = st.columns([0.82, 0.18], gap="small")
        with dl1:
            st.markdown(
                f"<a class='dl-side-link' href='{html.escape(RESOURCE_DOWNLOAD_URL)}' "
                "target='_blank' rel='noopener noreferrer'>"
                f"{html.escape(t['dl_btn'])}</a>",
                unsafe_allow_html=True,
            )
        with dl2:
            cu = _icon_path("cursor")
            if cu:
                st.image(str(cu), width=34)

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        na1, na2 = st.columns([0.72, 0.28], gap="small")
        with na1:
            st.markdown(
                f"<div style='color:#fff;padding-top:6px'>{t['name_l']} / {t['acct_l']}</div>",
                unsafe_allow_html=True,
            )
        with na2:
            pu = _icon_path("user")
            if pu:
                st.image(str(pu), width=40)
            else:
                st.markdown("<div style='color:#fff;font-size:1.6rem;line-height:1'>👤</div>", unsafe_allow_html=True)

        if st.button((st.session_state.user or "Guest"), key="side_user", use_container_width=True):
            if st.session_state.user:
                st.session_state.current_page = "D"
            else:
                st.session_state.open_login = True
            st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

    with main:
        top = st.columns([5, 1, 1, 1, 1])
        top[0].markdown(
            f"<h2 style='margin:0;padding-top:6px;font-family:Georgia,\"Times New Roman\",serif;font-weight:700'>{t['title']}</h2>",
            unsafe_allow_html=True,
        )
        with top[1]:
            st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
            if _icon_path("settings", "gear", "cog"):
                sg1, sg2 = st.columns([0.35, 0.65])
                with sg1:
                    _show_icon("settings", "gear", "cog", width=22)
                with sg2:
                    if st.button(" ", key="home_set", help=t["set"]):
                        st.session_state.current_page = "Settings"
                        st.rerun()
            else:
                if st.button("⚙️", key="home_set", help=t["set"]):
                    st.session_state.current_page = "Settings"
                    st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with top[2]:
            st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
            if st.button(t["login"], use_container_width=True):
                st.session_state.open_login = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with top[3]:
            st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
            if st.button(t["signup"], use_container_width=True):
                st.session_state.open_signup = True
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)
        with top[4]:
            st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
            if st.button(t["language"], use_container_width=True):
                st.session_state.lang = "🇨🇳 简体中文" if st.session_state.lang == "🇬🇧 English" else "🇬🇧 English"
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.caption("Group3 / Product Owner: TrungHieu Le")

        c0, c1, c2 = st.columns([1, 2, 1])
        with c1:
            if st.button(t["about"], use_container_width=True):
                st.session_state.current_page = "About"
                st.rerun()
            st.caption("Scrollable long page uses static/team: team, time1, time2")

            with st.container(border=True):
                w1, w2 = st.columns([0.14, 0.86])
                with w1:
                    traffic_dots("home_device")
                with w2:
                    st.markdown(
                        "<div style='padding-top:2px;color:#333;font-size:0.85rem;font-weight:600'>"
                        "ABOUT OUR PROJECT · Recipe Nutrition Generator</div>",
                        unsafe_allow_html=True,
                    )
                st.markdown(
                    "<div style='background:linear-gradient(180deg,#1a4a6e 0%,#0d2840 100%);height:110px;border-radius:10px;"
                    "margin:10px 0 8px 0;display:flex;align-items:center;justify-content:center;color:#b8d4ec;font-size:12px;"
                    "letter-spacing:.04em'>Midterm progress preview</div>",
                    unsafe_allow_html=True,
                )
                st.markdown(
                    "<div style='display:flex;gap:10px;flex-wrap:wrap'>"
                    "<div style='flex:1;min-width:120px;height:38px;background:#fff;border-radius:10px;border:1px solid rgba(0,0,0,.12)'></div>"
                    "<div style='flex:1;min-width:120px;height:38px;background:#fff;border-radius:10px;border:1px solid rgba(0,0,0,.12)'></div>"
                    "</div>",
                    unsafe_allow_html=True,
                )

    if st.session_state.open_login:
        dlg_login()
    if st.session_state.open_signup:
        dlg_signup()


# ---------- 路由导航 ----------
if st.session_state.current_page == "Home":
    render_home()

elif st.session_state.current_page == "Login":
    st.session_state.current_page = "Home"
    st.session_state.open_login = True
    st.rerun()

elif st.session_state.current_page == "Settings":
    s1, s2 = st.columns([0.12, 0.88])
    with s1:
        st.markdown("<div style='padding-top:8px'>", unsafe_allow_html=True)
        traffic_dots("settings_top")
        st.markdown("</div>", unsafe_allow_html=True)
    with s2:
        st.markdown(f"### {t['set']}")
    st.markdown("---")
    col_t, col_l = st.columns(2)
    with col_t:
        theme_opts = list(theme_colors.keys())
        new_th = st.selectbox("Theme / 主题", theme_opts, index=theme_opts.index(st.session_state.theme))
        if new_th != st.session_state.theme:
            st.session_state.theme = new_th
            st.rerun()
    with col_l:
        lang_opts = ["🇨🇳 简体中文", "🇬🇧 English"]
        new_la = st.selectbox("Language / 语言", lang_opts, index=lang_opts.index(st.session_state.lang))
        if new_la != st.session_state.lang:
            st.session_state.lang = new_la
            st.rerun()

elif st.session_state.current_page == "About":
    u1, u2 = st.columns([0.12, 0.88])
    with u1:
        st.markdown("<div style='padding-top:4px'>", unsafe_allow_html=True)
        traffic_dots("about_top")
        st.markdown("</div>", unsafe_allow_html=True)
    with u2:
        st.empty()
    m_about()

else:
    if st.session_state.current_page == "A":
        m_kitchen()
    elif st.session_state.current_page == "B":
        m_health()
    elif st.session_state.current_page == "C":
        m_community()
        if st.session_state.get("open_publish") and st.session_state.user:
            dlg_publish()
    elif st.session_state.current_page == "D":
        m_profile()
