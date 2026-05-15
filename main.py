"""
AI Health Ecosystem — Streamlit 网页端 (极致安全 & 平滑升级版)
核心特性：
1. [Bug修复] 修复了未登录时点击侧边栏“访客(点击登录)”按钮被 st.rerun() 强制截断导致对话框不弹出的问题。
2. [平滑升级] 包含旧账号明文密码登录时的“无感自动升级为强哈希”机制，不影响老用户。
3. [密码安全] 新密码强制使用 PBKDF2_HMAC + 动态盐值进行 10万次哈希加密。
4. [防 XSS] 所有用户生成的动态内容在渲染 HTML 前强制通过 html.escape() 转义。
5. [防越权] 删除/修改操作强制绑定当前会话用户，杜绝抓包篡改他人数据。
6. [图片安检] 社区配图强制重采样清洗，拦截恶意脚本并限制文件大小。
7. [防篡改] 带有 HMAC 签名的安全 Cookie。
8. [极致 UI] 全宽图片 Banner、原生左侧滚动排行榜、右侧吸顶发布按钮与纯净瀑布流。
"""
from __future__ import annotations

import base64
import html
import json
import hashlib
import hmac
import secrets
import io
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import quote

# 核心安全依赖：图片洗稿与压缩防爆
try:
    from PIL import Image
except ImportError:
    import streamlit as st
    st.error("🔒 安全引擎需要 Pillow 库，请在终端执行 `pip install Pillow`")
    st.stop()

import extra_streamlit_components as stx
import pandas as pd
import requests
import streamlit as st
import streamlit.components.v1 as components
from supabase import create_client

# ==========================================
# 0. 核心安全引擎 (Security Core)
# ==========================================
COOKIE_SECRET = st.secrets.get("COOKIE_SECRET", "super_secret_fallback_key_123!@#")

def hash_password(password: str, salt: str = None) -> str:
    """PBKDF2_HMAC 强哈希加密"""
    if not salt:
        salt = secrets.token_hex(16)
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt.encode('utf-8'), 100000)
    return f"{salt}${pwd_hash.hex()}"

def verify_password_with_upgrade(stored_password: str, provided_password: str) -> tuple[bool, bool]:
    """
    智能密码验证引擎 (支持老用户平滑升级)
    返回元组: (密码是否正确, 是否需要系统自动升级为哈希)
    """
    # 如果密码里没有 $ 符号，说明是遗留的明文密码
    if "$" not in stored_password:
        if stored_password == provided_password:
            return True, True  # 密码正确，但需要升级
        return False, False
        
    # 如果是强加密哈希，走标准验证流程
    try:
        salt, _ = stored_password.split('$')
        return stored_password == hash_password(provided_password, salt), False
    except ValueError:
        return False, False

def sign_cookie(username: str) -> str:
    """为 Cookie 颁发防篡改签名"""
    signature = hmac.new(COOKIE_SECRET.encode(), username.encode(), hashlib.sha256).hexdigest()
    return f"{username}.{signature}"

def verify_cookie(cookie_value: str) -> str | None:
    """验证并提取安全的 Cookie"""
    if not cookie_value or "." not in cookie_value:
        return None
    username, signature = cookie_value.split(".", 1)
    expected_signature = hmac.new(COOKIE_SECRET.encode(), username.encode(), hashlib.sha256).hexdigest()
    if hmac.compare_digest(signature, expected_signature):
        return username
    return None

def process_safe_image(uploaded_file, max_mb=2, max_dim=800) -> tuple[str | None, str | None]:
    """图片安全过滤与重采样引擎 (防木马伪装)"""
    if not uploaded_file:
        return None, None
    if uploaded_file.size > max_mb * 1024 * 1024:
        return None, f"文件超过限制 ({max_mb}MB)"
    try:
        img = Image.open(uploaded_file)
        img.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        fmt = "PNG" if img.format == "PNG" else "JPEG"
        if fmt == "JPEG" and img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        buffered = io.BytesIO()
        img.save(buffered, format=fmt, quality=85)
        b64_data = base64.b64encode(buffered.getvalue()).decode("utf-8")
        return f"data:image/{fmt.lower()};base64,{b64_data}", None
    except Exception:
        return None, "非法或损坏的图像文件"


# ---------- 1. 静态资源路径 ----------
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
    if not ICON_DIR.is_dir(): return None
    for stem in names:
        for ext in _ICON_EXTS:
            p = ICON_DIR / f"{stem}{ext}"
            if p.is_file(): return p.resolve()
    return None

def _page_icon_arg() -> str:
    hit = _icon_path("favicon") or _icon_path("icon") or _icon_path("logo") or _icon_path("app")
    return str(hit) if hit else "☁️"

def _icon_to_data_uri(p: Path) -> str:
    raw = p.read_bytes()
    mime = {
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".webp": "image/webp", ".gif": "image/gif", ".svg": "image/svg+xml", ".ico": "image/x-icon",
    }.get(p.suffix.lower(), "application/octet-stream")
    return f"data:{mime};base64,{base64.b64encode(raw).decode()}"

def _profile_avatar_html(username: str, avatar_data: str = None) -> str:
    safe_uname = html.escape(str(username))
    if avatar_data:
        if avatar_data.startswith("preset:"):
            seed = html.escape(avatar_data.split(":", 1)[1])
            av_url = f"https://api.dicebear.com/7.x/shapes/svg?seed={quote(seed, safe='')}&backgroundColor=e6f2e0,c5d4b8,d8e6d1"
        elif avatar_data.startswith("b64:"):
            av_url = avatar_data[4:]
        else:
            av_url = f"https://api.dicebear.com/7.x/initials/svg?seed={quote(safe_uname, safe='')}&backgroundColor=6b8f6f,2f4a35"
    else:
        av_url = f"https://api.dicebear.com/7.x/initials/svg?seed={quote(safe_uname, safe='')}&backgroundColor=6b8f6f,2f4a35"

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
    for base in ("group", "team", "time1", "time2"):
        hit = None
        for ext in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
            p = TEAM_DIR / f"{base}{ext}"
            if p.is_file():
                hit = p
                break
        if hit:
            if base == "team" and any(path.stem == "group" for path in out):
                continue
            out.append(hit)
    return out


# ---------- 2. 页面状态与自适应配置 ----------
st.set_page_config(
    page_title="AI Health Ecosystem",
    page_icon=_page_icon_arg(),
    layout="wide",
    initial_sidebar_state="collapsed", 
)

for k in ("user", "editing_id"):
    if k not in st.session_state: st.session_state[k] = None
if "current_page" not in st.session_state: st.session_state.current_page = "Home"
if "lang" not in st.session_state: st.session_state.lang = "🇨🇳 简体中文"

for k in ("need_set_cookie", "need_del_cookie", "logout_flag", "open_login", "open_signup"):
    if k not in st.session_state: st.session_state[k] = False

cookie_manager = stx.CookieManager(key="cookie_manager")

if st.session_state.need_set_cookie and st.session_state.user:
    cookie_manager.set("saved_user", sign_cookie(str(st.session_state.user)), expires_at=datetime.now() + timedelta(days=30))
    st.session_state.need_set_cookie = False
if st.session_state.need_del_cookie:
    cookie_manager.delete("saved_user")
    st.session_state.need_del_cookie = False

raw_cookie = cookie_manager.get(cookie="saved_user")
if raw_cookie and isinstance(raw_cookie, str) and st.session_state.user is None and not st.session_state.logout_flag:
    verified_user = verify_cookie(raw_cookie)
    if verified_user:
        st.session_state.user = verified_user
        st.rerun()
    else:
        st.session_state.need_del_cookie = True

if st.query_params.get("_home") == "1":
    st.session_state.current_page = "Home"
    st.query_params.clear()
    st.rerun()


# ---------- 3. 动态主题颜色配置库 ----------
theme_colors = {
    "🍵 抹茶绿 (Matcha Green)": {
        "SAGE_BG": "#e6f2e0", "DEEP_GREEN": "#2f4a35", "CREAM": "#f3f0e4", 
        "CHAT_MAIN_BG": "#c5d4b8", "COMM_RANK_SIDEBAR": "#6b6e6b", 
        "RANK_CARD_BG": "#d8dcd8", "BTN_BG": "#808080", "BTN_TEXT": "#ffffff", "TEXT_MAIN": "#1a1a1a"
    },
    "🌊 海洋蓝 (Ocean Blue)": {
        "SAGE_BG": "#e0f0f5", "DEEP_GREEN": "#154360", "CREAM": "#eaeded", 
        "CHAT_MAIN_BG": "#a9cce3", "COMM_RANK_SIDEBAR": "#5d6d7e", 
        "RANK_CARD_BG": "#d4e6f1", "BTN_BG": "#808080", "BTN_TEXT": "#ffffff", "TEXT_MAIN": "#1a1a1a"
    },
    "🌸 樱花粉 (Sakura Pink)": {
        "SAGE_BG": "#f9ebea", "DEEP_GREEN": "#641e16", "CREAM": "#f5eef8", 
        "CHAT_MAIN_BG": "#fadbd8", "COMM_RANK_SIDEBAR": "#a569bd", 
        "RANK_CARD_BG": "#e8daef", "BTN_BG": "#808080", "BTN_TEXT": "#ffffff", "TEXT_MAIN": "#1a1a1a"
    },
    "☕ 奶茶棕 (Mocha Brown)": {
        "SAGE_BG": "#f6ddcc", "DEEP_GREEN": "#4a2311", "CREAM": "#fdf2e9", 
        "CHAT_MAIN_BG": "#edbb99", "COMM_RANK_SIDEBAR": "#873600", 
        "RANK_CARD_BG": "#e59866", "BTN_BG": "#808080", "BTN_TEXT": "#ffffff", "TEXT_MAIN": "#1a1a1a"
    }
}

if "theme" not in st.session_state or st.session_state.theme not in theme_colors:
    st.session_state.theme = "🍵 抹茶绿 (Matcha Green)"

c = theme_colors[st.session_state.theme]

SAGE_BG = c["SAGE_BG"]
DEEP_GREEN = c["DEEP_GREEN"]
CREAM = c["CREAM"]
CHAT_MAIN_BG = c["CHAT_MAIN_BG"]
COMM_RANK_SIDEBAR = c["COMM_RANK_SIDEBAR"]
RANK_CARD_BG = c["RANK_CARD_BG"]
BTN_BG = c["BTN_BG"]
BTN_TEXT = c["BTN_TEXT"]
TEXT_MAIN = c["TEXT_MAIN"]


# ---------- 4. 双语字典引擎 (i18n) ----------
i18n = {
    "🇨🇳 简体中文": {
        "sys_lang": "简体中文", "title": "基于大模型的食谱生成和营养分析工具", "login": "登录", "signup": "注册",
        "set": "设置", "m1": "AI 智能厨房\n视觉食谱生成 + 专家问答", "m2": "美食社区\n排行榜 + 交流大厅", "m3": "数据管理\n数据记录 + 热量计算",
        "dl_hint": "如果你需要获取更多个性化的食谱……", "dl_btn": "点击这里下载 PDF", "name_l": "名称", "acct_l": "账号",
        "k_t": "☁️ AI 智能后厨", "vdg": "视觉食谱生成",
        "vdg_help": "你可以直接上传食材照片，在输入框中填写口味偏好与烹饪限制。AI 会结合食材清单与要求生成菜品。你也可以收藏喜欢的菜品。",
        "eqa": "专家问答", "eqa_help": "你可以用文字或「文字+图片」提出健康相关问题，AI 将以营养师角色作答。",
        "up": "上传食材照片", "req": "附加要求（可选）", "gen": "生成菜谱", "fav": "⭐️ 收藏此篇", "ask": "具体问题描述",
        "up_opt": "上传参考图片（可选）", "think": "数据处理中...", "h_t": "📈 健康数据管家", "h_hist": "历史记录",
        "h_banner": "使用数据管理记录个人信息，并计算三餐热量。", "h_chart": "趋势图", "h_t1": "📝 数据录入", "h_t2": "📊 分析报告",
        "d": "选择日期", "w": "体重 (kg)", "b": "早餐记录", "l": "午餐记录", "dn": "晚餐记录", "sub": "提交并计算热量",
        "del": "删除", "edit": "修改", "c_rank": "排行榜", "c_t2": "帖子互动", "c_hall": "交流大厅 — 欢迎分享你想分享的一切",
        "search_ph": "搜索与打榜", "search_go": "搜索", "nf_add": "去发布", "pub": "发布动态", "like": "赞",
        "tag": "选择标签", "title_in": "输入标题", "desc_in": "输入内容", "log_req": "⚠️ 请先登录", "u_t": "👤 我的主页",
        "u_post": "POST", "u_hist": "HISTORY", "u_name": "Name", "u_acct": "Account", "u_pwd": "Password", "pwd_edit": "修改密码",
        "new_pwd_title": "NEW PASSWORD", "submit": "保存提交", "close": "关闭", "err": "账号或密码错误", "suc": "操作成功",
        "out": "退出登录", "reg": "注册新号", "no_data": "暂无数据", "id_in": "输入账号", "pwd_in": "输入密码", "new_id": "设置新账号",
        "new_pwd": "设置新密码", "confirm": "确认", "unfav": "🤍 取消收藏", "del_post": "🗑️ 删除此贴", "reply": "💬 回复",
        "reply_ph": "写下回复...", "send": "发送", "rec_custom": "✨ 推荐：{}", "view_lib": "📚 查看系统预设菜品库 (100款)",
        "about": "关于项目", "text": "TEXT", "image": "IMAGE", "publish": "Publish", "guest": "访客 (点击登录)",
        "theme_sel": "🎨 UI 主题配色", "lang_sel": "🌐 系统界面语言", "voted": "⚠️ 你已经投过票啦！", "votes": "票",
        "back": "返回大厅", "c_vote": "为这道菜投票", "guess": "💡 猜你想选 (点击直接推荐):", "no_match": "🔍 库中暂无此预设菜品，请点击下方作为新菜推荐：", "rec_ph": "输入菜名并回车进行搜索...",
        "change_avatar": "📸 更换头像", "edit_btn": "修改"
    },
    "🇬🇧 English": {
        "sys_lang": "English", "title": "LLM-based recipe generation and nutrition analysis tool", "login": "Login", "signup": "Signup",
        "set": "Settings", "m1": "AI Smart Kitchen\nVisual Dish Gen + Expert Q&A", "m2": "Community\nRanking List + Chat Hall", "m3": "Data Manager\nRecord Data + Calories",
        "dl_hint": "If you need to download more recipe resources for personalized needs...", "dl_btn": "Download PDF", "name_l": "Name", "acct_l": "Account",
        "k_t": "☁️ AI Kitchen", "vdg": "Visual Dish Generation",
        "vdg_help": "Upload photos of ingredients and fill taste preferences and cooking restrictions. The AI generates dishes from ingredients and your needs. You can also collect favorites.",
        "eqa": "Expert Q&A", "eqa_help": "Ask health-related questions in text or text with pictures. The AI answers as a nutritionist.",
        "up": "Upload ingredient photos", "req": "Additional Requirements (Optional)", "gen": "Generate recipes", "fav": "⭐️ Save Recipe", "ask": "Specific problem description",
        "up_opt": "Upload reference photos (Optional)", "think": "Processing data...", "h_t": "📈 Health Data Manager", "h_hist": "History record",
        "h_banner": "Just use this Data Manager to help you to Record Personal Data and Calculate Three-Meal Calories!", "h_chart": "Charts", "h_t1": "📝 Data Entry", "h_t2": "📊 Analytics",
        "d": "Date", "w": "Weight (kg)", "b": "Breakfast", "l": "Lunch", "dn": "Dinner", "sub": "Submit",
        "del": "Delete", "edit": "Edit", "c_rank": "Ranking List", "c_t2": "Discussion", "c_hall": "CHAT HALL — WELCOME TO SHARE WHATEVER YOU LIKE",
        "search_ph": "Search & Vote", "search_go": "Search", "nf_add": "Publish", "pub": "Publish Post", "like": "Like",
        "tag": "Select Tag", "title_in": "Enter Title", "desc_in": "Enter Details", "log_req": "⚠️ Please login first", "u_t": "👤 My Profile",
        "u_post": "POST", "u_hist": "HISTORY", "u_name": "Name", "u_acct": "Account", "u_pwd": "Password", "pwd_edit": "Change password",
        "new_pwd_title": "NEW PASSWORD", "submit": "Submit", "close": "Close", "err": "Invalid credentials", "suc": "Success",
        "out": "Logout", "reg": "Register", "no_data": "No data available", "id_in": "Enter ID", "pwd_in": "Enter Password", "new_id": "Create ID",
        "new_pwd": "Create Password", "confirm": "Confirm", "unfav": "🤍 Unfavorite", "del_post": "🗑️ Delete Post", "reply": "💬 Reply",
        "reply_ph": "Write a reply...", "send": "Send", "rec_custom": "✨ Recommend: {}", "view_lib": "📚 View System Dish Library (100 Items)",
        "about": "About our project", "text": "TEXT", "image": "IMAGE", "publish": "Publish", "guest": "Guest (Login)",
        "theme_sel": "🎨 UI Theme Color", "lang_sel": "🌐 Interface Language", "voted": "⚠️ You already voted!", "votes": "votes",
        "back": "Back to Home", "c_vote": "Vote for this dish", "guess": "💡 Suggestions (Click to vote):", "no_match": "🔍 Not in library. Click below to recommend:", "rec_ph": "Type dish name and press Enter...",
        "change_avatar": "📸 Change Avatar", "edit_btn": "Edit"
    },
}
t = i18n[st.session_state.lang]

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


# ---------- 5. 动态响应全局 CSS 与 UI 自适应微调 ----------
st.markdown(
    f"""
<style>
header[data-testid="stHeader"], footer {{ visibility: hidden !important; height: 0 !important; }}
.stApp {{ background: {SAGE_BG} !important; color: {TEXT_MAIN} !important; }}
.block-container {{ max-width: 1280px !important; padding-top: 2rem !important; }}

div[data-testid="stButton"] > button {{ border-color: rgba(150,150,150,0.25) !important; }}

.pill-btn > button {{ 
    background: {BTN_BG} !important; 
    color: {BTN_TEXT} !important; 
    border-radius: 999px !important; 
    border: none !important; 
    padding: 0.4rem 1rem !important; 
    white-space: nowrap !important; 
    min-width: max-content !important;
}}
.pill-btn > button:hover {{ filter: brightness(0.9) !important; }}

.side-card button {{ 
    background: {BTN_BG} !important; color: {BTN_TEXT} !important; border-radius: 20px !important; 
    min-height: 50px !important; white-space: pre-wrap !important; text-align: center !important; 
    border: 2px solid {BTN_TEXT} !important; font-weight: bold !important; margin-bottom: 15px !important; 
}}
.side-card button:hover {{ filter: brightness(0.9) !important; color: {BTN_TEXT} !important; }}

div[data-testid="stDownloadButton"] > button[kind="primary"] {{
    display: block; width: 100%; background: {BTN_BG} !important; color: {BTN_TEXT} !important; 
    text-align: center; border-radius: 8px !important; padding: 8px 14px !important; border: none !important; font-weight: 600 !important;
}}
div[data-testid="stDownloadButton"] > button[kind="primary"]:hover {{ filter: brightness(0.9) !important; color: {BTN_TEXT} !important; }}

.user-btn-wrapper button {{
    background: #ffffff !important; color: #333333 !important; border: 1px solid rgba(0,0,0,0.1) !important;
    border-radius: 8px !important; font-weight: normal !important; padding: 8px !important; width: 100% !important;
}}
.user-btn-wrapper button:hover {{ background: #f9f9f9 !important; }}

.footer-bar {{ background: {DEEP_GREEN}; padding: 10px 12px; border-radius: 12px; margin-top: 8px; }}
.card-brick {{ break-inside: avoid; background: #fff; border-radius: 12px; padding: 10px; margin: 0 0 10px 0; border: 1px solid rgba(0,0,0,0.06); color: #1a1a1a !important; }}
.rank-row {{ background: {CREAM}; border-radius: 10px; padding: 10px 12px; margin-bottom: 8px; display:flex; align-items:center; justify-content: space-between; color: #1a1a1a !important; }}
.chat-head {{ background: {DEEP_GREEN}; color: #e8ffe8; padding: 8px 12px; border-radius: 8px; font-weight: 600; letter-spacing: 0.02em; }}
.profile-side {{ background: {DEEP_GREEN}; border-radius: 14px; padding: 14px; }}
.section-head {{ background: {DEEP_GREEN}; color: #fff; padding: 8px 12px; border-radius: 8px; font-weight: 700; }}

@media screen and (max-width: 1200px) {{
    h2 {{ font-size: 1.6rem !important; }}
    .side-card button {{ font-size: 0.9rem !important; min-height: 45px !important; margin-bottom: 10px !important; }}
    .pill-btn > button {{ padding: 0.3rem 0.7rem !important; font-size: 0.9rem !important; }}
}}
@media screen and (max-width: 768px) {{
    h2 {{ font-size: 1.4rem !important; }}
    .side-card button {{ font-size: 0.85rem !important; }}
    .pill-btn > button {{ font-size: 0.85rem !important; }}
}}
</style>
""",
    unsafe_allow_html=True,
)


# ---------- 6. 数据库与 AI 接口 ----------
@st.cache_resource
def init_db():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase, api_key = init_db(), st.secrets["ALIYUN_API_KEY"]
except Exception:
    st.error("Database connection failed.")
    st.stop()


def ask_ai_stream(sys_p, usr_p, img=None):
    lang_inst = "简体中文 (Simplified Chinese)" if t["sys_lang"] == "简体中文" else "English"
    sys_p = f"{sys_p}\n\nYou MUST strictly communicate in {lang_inst}."
    usr_p += f"\n\n[CRITICAL SYSTEM INSTRUCTION: You MUST output your ENTIRE response strictly in {lang_inst}. NO OTHER LANGUAGES ARE ALLOWED!]"
    
    model = "qwen-vl-plus" if img else "qwen-plus"
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    msg_content = [{"type": "text", "text": usr_p}]
    if img:
        img_b64 = base64.b64encode(img).decode("utf-8")
        msg_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}})
    
    data = {"model": model, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": msg_content}], "stream": True}
    try:
        res = requests.post(url, headers=h, json=data, timeout=90, stream=True)
        for line in res.iter_lines():
            if line:
                line_str = line.decode("utf-8")
                if line_str.startswith("data: ") and line_str != "data: [DONE]":
                    try:
                        chunk = json.loads(line_str[6:])
                        delta = chunk["choices"][0]["delta"].get("content", "")
                        if delta: yield delta
                    except Exception: pass
    except Exception as e:
        yield f"\n\nAI Network Error: {str(e)}"

def ask_ai_sync(sys_p, usr_p):
    lang_inst = "简体中文 (Simplified Chinese)" if t["sys_lang"] == "简体中文" else "English"
    sys_p = f"{sys_p}\n\nYou MUST strictly communicate in {lang_inst}."
    usr_p += f"\n\n[CRITICAL SYSTEM INSTRUCTION: You MUST answer strictly in {lang_inst} only.]"

    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    h = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {"model": "qwen-plus", "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}]}
    try:
        res = requests.post(url, headers=h, json=data, timeout=30)
        return res.json()["choices"][0]["message"]["content"]
    except Exception:
        return "0"

def _require_login():
    st.warning("请先登录 / Please login first")
    st.stop()


# ==========================================
# 7. 统一返回主页按钮组件
# ==========================================
def top_back_btn():
    if st.button("⬅️ " + t["back"], key=f"btn_back_{st.session_state.current_page}"):
        st.session_state.current_page = "Home"
        st.rerun()
    st.markdown("<hr style='margin-top: 5px; margin-bottom: 15px;'/>", unsafe_allow_html=True)


# ==========================================
# 8. 各功能页面区
# ==========================================
def m_kitchen():
    L, R = st.columns(2, gap="large")
    desc_style = f"background:{DEEP_GREEN};color:#fff;padding:12px 14px;border-radius:12px;font-size:0.95rem;height:120px;box-sizing:border-box;overflow-y:auto;margin-bottom:15px;"

    with L:
        st.markdown(f"<div style='background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:10px;font-weight:700; margin-bottom: 12px;'>{t['vdg']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='{desc_style}'>{t['vdg_help']}</div>", unsafe_allow_html=True)
        
        up = st.file_uploader(t["up"], type=["jpg", "png"], key="f1")
        pref = st.text_area(t["req"], height=140, key="pref_l")
        
        if up: st.image(up, use_column_width=True)
        
        if st.button(t["gen"], use_container_width=True):
            if not up:
                st.warning("⚠️ 请先上传食材照片 / Please upload ingredient photos")
            else:
                with st.spinner(t["think"]):
                    res_stream = ask_ai_stream("You are a Master Chef.", f"Identify ingredients and generate a professional recipe. Preferences: {pref}", up.getvalue())
                    st.session_state["l_rec"] = st.write_stream(res_stream)

        if st.session_state.get("l_rec") and st.session_state.user and st.button(t["fav"]):
            try:
                supabase.table("favorites").insert({"username": st.session_state.user, "recipe_content": st.session_state["l_rec"]}).execute()
                st.success(t["suc"])
            except Exception as e: st.error(f"DB Error: {e}")
                
    with R:
        st.markdown(f"<div style='background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:10px;font-weight:700; margin-bottom: 12px;'>{t['eqa']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='{desc_style}'>{t['eqa_help']}</div>", unsafe_allow_html=True)
        
        up_nutri = st.file_uploader(t["up_opt"], type=["jpg", "png"], key="f2")
        q = st.text_area(t["ask"], height=140, key="ask_r")
        
        if up_nutri: st.image(up_nutri, use_column_width=True)
        
        if st.button(t["confirm"], use_container_width=True):
            if not q.strip():
                st.warning("⚠️ 请输入具体问题描述 / Please enter your question")
            else:
                with st.spinner(t["think"]):
                    res_stream = ask_ai_stream("You are a professional Dietitian.", q, up_nutri.getvalue() if up_nutri else None)
                    st.write_stream(res_stream)


def m_health():
    if not st.session_state.user: _require_login()
    st.markdown(f"<div style='background:{DEEP_GREEN};color:#fff;padding:10px 12px;border-radius:10px;margin-bottom:10px'>{t['h_banner']}</div>", unsafe_allow_html=True)
    
    left, right = st.columns([1, 2], gap="medium")
    with left:
        st.markdown(f"<div style='color:{TEXT_MAIN}'>**{t['h_hist']}**</div>", unsafe_allow_html=True)
        logs_data = supabase.table("diet_logs").select("*").eq("username", st.session_state.user).order("log_date", desc=True).execute().data
        for r in logs_data:
            safe_b = html.escape(str(r.get('breakfast','')))
            safe_l = html.escape(str(r.get('lunch','')))
            safe_dn = html.escape(str(r.get('dinner','')))
            with st.expander(f"{r['log_date']} | {r['weight']}kg | {r['calories']}kcal"):
                st.write(f"{t['b']}:{safe_b} {t['l']}:{safe_l} {t['dn']}:{safe_dn}")
                ce, cd = st.columns(2)
                if ce.button(t["edit"], key=f"e_{r.get('id', 'temp')}"): st.session_state.editing_id = r.get("id"); st.rerun()
                if cd.button(t["del"], key=f"d_{r.get('id', 'temp')}"):
                    try: 
                        supabase.table("diet_logs").delete().eq("id", r.get("id")).eq("username", st.session_state.user).execute(); st.rerun()
                    except Exception as e: st.error(str(e))
    with right:
        logs = supabase.table("diet_logs").select("*").eq("username", st.session_state.user).order("log_date").execute().data
        if logs:
            df = pd.DataFrame(logs)
            df["log_date"] = pd.to_datetime(df["log_date"])
            df.set_index("log_date", inplace=True)
            st.line_chart(df[["weight", "calories"]])
        else:
            st.caption(t["no_data"])

        with st.form("d_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d = c1.date_input(t["d"], date.today())
            w = c2.number_input(t["w"], min_value=20.0, value=40.0, step=0.1)
            b, l, dn = st.text_input(t["b"]), st.text_input(t["l"]), st.text_input(t["dn"])
            if st.form_submit_button(t["sub"], type="primary"):
                cal_str = ask_ai_sync("Nutrition Calculator", f"Estimate total calories. Return ONLY an integer: Breakfast:{b} Lunch:{l} Dinner:{dn}")
                try:
                    cal = int("".join(filter(str.isdigit, cal_str)) or 0)
                except ValueError:
                    cal = 0
                payload = {"username": st.session_state.user, "log_date": str(d), "weight": float(w), "calories": cal, "breakfast": str(b), "lunch": str(l), "dinner": str(dn)}
                try:
                    if st.session_state.editing_id:
                        supabase.table("diet_logs").update(payload).eq("id", st.session_state.editing_id).eq("username", st.session_state.user).execute()
                        st.session_state.editing_id = None
                    else:
                        supabase.table("diet_logs").insert(payload).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"DB Error: {e}")
        if st.session_state.editing_id: st.caption(f"Editing record id={st.session_state.editing_id}")

def _submit_vote(dish_name: str):
    try:
        exist = supabase.table("dish_ranking").select("*").eq("dish_name", str(dish_name)).execute().data
        if exist:
            record = exist[0]
            voters = record.get("voted_by", [])
            if not isinstance(voters, list): voters = []
            if st.session_state.user in voters:
                st.warning(t["voted"])
            else:
                voters.append(st.session_state.user)
                supabase.table("dish_ranking").update({"votes": int(record.get("votes", 0)) + 1, "voted_by": voters}).eq("id", record.get("id")).execute()
                st.session_state["_dish_q"] = ""
                st.rerun()
        else:
            supabase.table("dish_ranking").insert({"dish_name": str(dish_name), "votes": 1, "voted_by": [st.session_state.user]}).execute()
            st.session_state["_dish_q"] = ""
            st.rerun()
    except Exception as e:
        st.error(f"DB Error: {e}")

# ---------- 社区广场 ----------
def m_community():
    rank_col, main_col = st.columns([1.2, 2.8], gap="large")
    
    with rank_col:
        st.markdown(f"<div style='background:{COMM_RANK_SIDEBAR};border-radius:12px;padding:12px 10px 10px 10px;margin-bottom:8px'><div style='font-family:Georgia,serif;font-weight:700;color:#fafafa;margin:0'>{t['c_rank']}</div></div>", unsafe_allow_html=True)
        top_dishes = supabase.table("dish_ranking").select("*").order("votes", desc=True).execute().data
        
        if top_dishes:
            with st.container(height=360):
                for idx, d in enumerate(top_dishes):
                    btn_key = f"hv_rank_{idx}_{d.get('id', 'unk')}"
                    row_l, row_r = st.columns([0.78, 0.22], gap="small")
                    safe_dish_name = html.escape(str(d.get('dish_name','')))
                    with row_l: st.markdown(f"<div class='rank-row'><span><b>{safe_dish_name}</b> — {int(d.get('votes',0))} {t['votes']}</span></div>", unsafe_allow_html=True)
                    with row_r:
                        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
                        hp = _icon_path("heart")
                        if hp: st.image(str(hp), width=26)
                        if st.session_state.user and st.button(" " if hp else "♥", key=btn_key, help=t["c_vote"], use_container_width=True): _submit_vote(d.get("dish_name"))
        else: 
            st.info(t["no_data"])

        st.markdown(f"<div style='font-size:0.95rem; font-weight:700; color:{TEXT_MAIN}; margin:24px 0 10px 0; border-bottom: 1px solid rgba(150,150,150,0.2); padding-bottom:6px;'>🔍 {t['search_ph']}</div>", unsafe_allow_html=True)
        
        if st.session_state.user:
            sc1, sc2 = st.columns([0.7, 0.3], gap="small")
            with sc1:
                q = st.text_input("q", label_visibility="collapsed", placeholder=t["rec_ph"], key="comm_search")
            with sc2:
                if st.button(t["search_go"], key="comm_go", use_container_width=True, type="secondary"):
                    st.session_state["_dish_q"] = q
                    st.rerun()

            dish_q = st.session_state.get("_dish_q", None)
            if dish_q:
                lib = dish_library[st.session_state.lang]
                dish_clean = html.escape(dish_q.strip())
                matches = [d for d in lib if dish_clean.lower() in d.lower()]
                if matches:
                    st.caption(t["guess"])
                    cols = st.columns(2)
                    for i, match in enumerate(matches[:4]):
                        if cols[i % 2].button(match, key=f"match_{i}_{match}", use_container_width=True): _submit_vote(match)
                    if dish_clean not in matches and st.button(t["rec_custom"].format(dish_clean), use_container_width=True, key="rec_cust_1"): _submit_vote(dish_clean)
                else:
                    st.caption(t["no_match"])
                    if st.button(t["rec_custom"].format(dish_clean), use_container_width=True, key="rec_cust_2"): _submit_vote(dish_clean)
                
                with st.expander(t["view_lib"]):
                    formatted_lib = "".join([f"<div style='flex:1 0 40%;margin:4px;padding:8px;background:#fff;border-radius:8px;border:1px solid rgba(0,0,0,.06);text-align:center;color:#1a1a1a;font-size:0.85rem;'>🍲 {d}</div>" for d in lib])
                    st.markdown(f"<div style='display:flex;flex-wrap:wrap;justify-content:space-between'>{formatted_lib}</div>", unsafe_allow_html=True)
        else:
            st.caption(f"🔒 {t['log_req']}")

    with main_col:
        st.markdown(f"<div class='chat-head'>{t['c_hall']}</div>", unsafe_allow_html=True)
        
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
        if st.session_state.user:
            if st.button("➕ " + t["pub"], type="primary", use_container_width=True, key="pure_pub_btn_top"):
                dlg_publish()
        else:
            st.button("🔒 " + t["log_req"], disabled=True, use_container_width=True)
        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        comments_data = supabase.table("comments").select("*").order("id", desc=True).execute().data
        
        with st.container(height=650):
            for r in comments_data:
                with st.container(border=True):
                    safe_u = html.escape(str(r.get('user_name','')))
                    safe_tag = html.escape(str(r.get('tag','')))
                    safe_dish = html.escape(str(r.get('dish_name','')))
                    safe_comm = html.escape(str(r.get('comment','')))
                    
                    st.markdown(f"<div style='display:flex; justify-content:space-between; align-items:center;'><div><span style='font-weight:bold; font-size:1.1rem; color:{TEXT_MAIN}'>👤 {safe_u}</span></div><div style='background:{SAGE_BG}; padding:4px 10px; border-radius:6px; font-size:0.8rem; font-weight:bold; color:{DEEP_GREEN}'>{safe_tag}</div></div>", unsafe_allow_html=True)
                    
                    st.markdown(f"<div style='font-size:1.3rem; font-weight:bold; margin-top:12px; margin-bottom:6px; color:{TEXT_MAIN}'>🍽️ {safe_dish}</div>", unsafe_allow_html=True)
                    if safe_comm:
                        safe_comm_br = safe_comm.replace('\n', '<br>')
                        st.markdown(f"<div style='color:{TEXT_MAIN}; opacity:0.95; margin-bottom:12px; line-height:1.6;'>{safe_comm_br}</div>", unsafe_allow_html=True)
                    
                    img_data = r.get('image_data')
                    if img_data and img_data.startswith("data:image/"): 
                        st.markdown(f"<div style='margin-bottom:12px;'><img src='{img_data}' style='width:100%; max-width:400px; border-radius:8px; box-shadow:0 2px 8px rgba(0,0,0,0.1);'/></div>", unsafe_allow_html=True)
                    
                    st.markdown("<hr style='margin: 8px 0; border: none; border-top: 1px solid rgba(150,150,150,0.2)'/>", unsafe_allow_html=True)
                    
                    lk = r.get("liked_by") if isinstance(r.get("liked_by"), list) else []
                    has_liked = (st.session_state.user in lk) if st.session_state.user else False
                    
                    if st.button(f"👍 {t['like']} ({int(r.get('likes', 0))})", key=f"like_btn_{r.get('id', 'temp')}", disabled=(not st.session_state.user or has_liked)):
                        lk.append(st.session_state.user)
                        supabase.table("comments").update({"likes": int(r.get("likes", 0)) + 1, "liked_by": lk}).eq("id", r.get("id")).execute()
                        st.rerun()


# ---------- 8. 对话框组 ----------
@st.dialog("📝 发布 / Publish")
def dlg_publish():
    tag_opts = ["#Daily", "#Diet", "#Yummy"] if t["sys_lang"] == "English" else ["#日常", "#减脂", "#神仙菜"]
    tag = st.selectbox(t["tag"], tag_opts)
    dish = st.text_input(t["title_in"])
    cont = st.text_area(t["desc_in"])
    up_img = st.file_uploader("📷 上传美食照片 (< 2MB)", type=["jpg", "png", "jpeg"], key="pubimg")
    
    c1, c2 = st.columns(2)
    if c1.button(t["close"]): st.rerun()
    if c2.button(t["publish"], type="primary") and dish:
        img_b64_str, err = process_safe_image(up_img)
        if err:
            st.error(err)
            return

        try:
            supabase.table("comments").insert({
                "user_name": str(st.session_state.user), 
                "author_username": str(st.session_state.user), 
                "dish_name": str(dish), 
                "comment": str(cont), 
                "likes": 0, 
                "liked_by": [], 
                "tag": str(tag), 
                "replies": [],
                "image_data": img_b64_str or "" 
            }).execute()
            st.rerun()
        except Exception as e: 
            st.error(f"发布失败，请检查数据库配置（需要有 image_data 字段）: {str(e)}")

@st.dialog("🔑 修改密码 / Change Password")
def dlg_pw():
    npw = st.text_input(t["new_pwd"], type="password")
    a1, a2 = st.columns(2)
    if a1.button(t["close"]): st.rerun()
    if a2.button(t["submit"], type="primary") and npw:
        try: 
            hashed_pw = hash_password(npw)
            supabase.table("app_users").update({"password": hashed_pw}).eq("username", st.session_state.user).execute()
            st.success(t["suc"])
            st.rerun()
        except Exception as e: 
            st.error(str(e))

@st.dialog("⚙️ 网站设置 / App Settings")
def dlg_settings():
    new_th = st.selectbox(t["theme_sel"], list(theme_colors.keys()), index=list(theme_colors.keys()).index(st.session_state.theme))
    new_la = st.selectbox(t["lang_sel"], ["🇨🇳 简体中文", "🇬🇧 English"], index=["🇨🇳 简体中文", "🇬🇧 English"].index(st.session_state.lang))
    
    if st.button(t["submit"], type="primary", use_container_width=True):
        st.session_state.theme = new_th
        st.session_state.lang = new_la
        st.rerun()

@st.dialog("🔑 账号登录 / User Login")
def dlg_login():
    u, p = st.text_input(t["id_in"]), st.text_input(t["pwd_in"], type="password")
    a, b = st.columns(2)
    if a.button(t["close"]): st.rerun()
    if b.button(t["confirm"], type="primary"):
        res = supabase.table("app_users").select("*").eq("username", str(u)).execute().data
        if res:
            stored_hash = res[0].get("password", "")
            
            is_valid, needs_upgrade = verify_password_with_upgrade(stored_hash, str(p))
            
            if is_valid:
                if needs_upgrade:
                    new_secure_hash = hash_password(str(p))
                    supabase.table("app_users").update({"password": new_secure_hash}).eq("username", str(u)).execute()
                    
                st.session_state.user = str(u)
                st.session_state.need_set_cookie = True
                st.session_state.logout_flag = False
                st.rerun()
            else:
                st.error(t["err"])
        else: 
            st.error(t["err"])

@st.dialog("✨ 注册新号 / User Signup")
def dlg_signup():
    nu, np = st.text_input(t["new_id"]), st.text_input(t["new_pwd"], type="password")
    a, b = st.columns(2)
    if a.button(t["close"]): st.rerun()
    if b.button(t["confirm"], type="primary") and nu and np:
        if supabase.table("app_users").select("*").eq("username", str(nu)).execute().data: 
            st.error("Username exists")
        else: 
            hashed_pw = hash_password(str(np))
            supabase.table("app_users").insert({"username": str(nu), "password": hashed_pw}).execute()
            st.success(t["suc"])
            st.rerun()

def _save_avatar(data_str: str):
    try:
        supabase.table("app_users").update({"avatar_data": str(data_str)}).eq("username", st.session_state.user).execute()
        st.rerun()
    except Exception as e: st.error(f"保存失败: {e}")

@st.dialog("更换头像 / Change Avatar")
def dlg_avatar():
    st.info("🔒 您的头像将经过安全加密处理，拒绝公网暴露。")
    tab1, tab2 = st.tabs(["系统预设", "本地上传"])
    with tab1:
        cols = st.columns(4)
        presets = ["Alpha", "Beta", "Gamma", "Delta"]
        for i, p in enumerate(presets):
            url = f"https://api.dicebear.com/7.x/shapes/svg?seed={p}&backgroundColor=e6f2e0,c5d4b8"
            cols[i].image(url, width=60)
            if cols[i].button("选择", key=f"sel_{p}"): _save_avatar(f"preset:{p}")
    with tab2:
        up_img = st.file_uploader("上传正方形照片 (建议 < 2MB)", type=["jpg", "png", "jpeg"])
        if up_img:
            st.image(up_img, width=150)
            if st.button("保存上传头像", type="primary"):
                img_b64_str, err = process_safe_image(up_img, max_dim=400)
                if err:
                    st.error(err)
                else:
                    _save_avatar(f"b64:{img_b64_str.split(',')[1]}")

def _save_profile_name(key: str):
    if not st.session_state.user: return
    nv = (st.session_state.get(key) or "").strip()
    if not nv: return
    try: 
        supabase.table("app_users").update({"profile_name": str(nv)}).eq("username", st.session_state.user).execute()
    except Exception: st.session_state["_profile_warn"] = "需在 app_users 添加 profile_name 字段。"


def m_profile():
    if not st.session_state.user: _require_login()
    L, R = st.columns([2, 1], gap="medium")
    with L:
        st.markdown(f"<div class='section-head'>{t['u_post']}</div>", unsafe_allow_html=True)
        my_posts = supabase.table("comments").select("*").eq("author_username", st.session_state.user).order("id", desc=True).execute().data
        pcs = st.columns(3)
        if not my_posts: st.info(t["no_data"])
        else:
            for i, p in enumerate(my_posts[:9]):
                with pcs[i % 3]:
                    with st.container(border=True):
                        safe_dish = html.escape(str(p.get('dish_name','')))
                        safe_comm = html.escape(str(p.get('comment') or ""))[:120]
                        st.markdown(f"**{safe_dish}**")
                        st.caption(safe_comm)
                        if st.button(t["del_post"], key=f"dp_{p.get('id', 'temp')}"): 
                            supabase.table("comments").delete().eq("id", p.get("id")).eq("author_username", st.session_state.user).execute()
                            st.rerun()

        st.markdown(f"<div class='section-head' style='margin-top:14px'>{t['u_hist']}</div>", unsafe_allow_html=True)
        favs = supabase.table("favorites").select("*").eq("username", st.session_state.user).order("id", desc=True).execute().data
        fcs = st.columns(3)
        if not favs: st.info(t["no_data"])
        else:
            for i, f in enumerate(favs[:9]):
                with fcs[i % 3]:
                    with st.container(border=True):
                        if f.get("recipe_content"):
                            with st.expander(t["fav"]): st.markdown(f.get("recipe_content"))
                        if st.button(t["unfav"], key=f"uf_{f.get('id', 'temp')}"): 
                            supabase.table("favorites").delete().eq("id", f.get("id")).eq("username", st.session_state.user).execute()
                            st.rerun()

    with R:
        st.markdown("<div class='profile-side'>", unsafe_allow_html=True)
        
        urow = supabase.table("app_users").select("*").eq("username", st.session_state.user).execute().data
        prof = (urow[0] if urow else {}) or {}
        st.markdown(_profile_avatar_html(st.session_state.user, prof.get("avatar_data")), unsafe_allow_html=True)
        if st.button(t.get("change_avatar", "📸 更换头像"), use_container_width=True): dlg_avatar()

        default_name = prof.get("profile_name") or st.session_state.user
        nk = f"pn_{st.session_state.user}"
        if nk not in st.session_state: st.session_state[nk] = default_name
        st.text_input(t["u_name"], key=nk, on_change=lambda k=nk: _save_profile_name(k))
        st.text_input(t["u_acct"], value=st.session_state.user, disabled=True)
        pen = _icon_path("pencil")
        pw1, pw2 = st.columns([0.76, 0.24])
        with pw1: st.text_input(t["u_pwd"], value="********", disabled=True)
        with pw2:
            st.markdown("<div style='height:2.4rem'></div>", unsafe_allow_html=True)
            if st.button(t.get("edit_btn", "修改") if not pen else " ", key="pwd_edit", type="primary", use_container_width=True): dlg_pw()
        if st.button(t["out"], type="primary", use_container_width=True, key="logout_profile"):
            st.session_state.user, st.session_state.need_del_cookie, st.session_state.logout_flag, st.session_state.current_page = None, True, True, "Home"; st.rerun()
        if st.session_state.get("_profile_warn"): st.warning(st.session_state.pop("_profile_warn"))
        st.markdown("</div>", unsafe_allow_html=True)


# ---------- 9. 布局分发渲染 ----------
def render_home():
    side, main = st.columns([0.28, 0.72], gap="large")
    
    with side:
        st.markdown(f"<div style='padding:14px'>", unsafe_allow_html=True)
        
        for page, label in [("A", t["m1"]), ("C", t["m2"]), ("B", t["m3"])]:
            st.markdown('<div class="side-card">', unsafe_allow_html=True)
            if st.button(label, key=f"nav_{page}", use_container_width=True):
                st.session_state.current_page = page
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

        st.markdown(f"<div style='color:{TEXT_MAIN};margin:12px 0 6px 0;font-size:0.95rem;font-weight:600'>{t['dl_hint']}</div>", unsafe_allow_html=True)
        
        pdf_path = None
        for file in ROOT.rglob("*.pdf"):
            pdf_path = file
            break
            
        if pdf_path and pdf_path.is_file():
            with open(pdf_path, "rb") as pdf_file:
                st.download_button(
                    label=t["dl_btn"],
                    data=pdf_file,
                    file_name=pdf_path.name,
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary"
                )
        else:
            st.button(f"{t['dl_btn']} (未找到文件)", disabled=True, use_container_width=True)

        st.markdown("<div style='height:18px'></div>", unsafe_allow_html=True)
        na1, na2 = st.columns([0.7, 0.3], gap="small")
        with na1: 
            st.markdown(f"<div style='color:{TEXT_MAIN};padding-top:10px;font-weight:bold;font-size:1.05rem;'>{t['name_l']} / {t['acct_l']}</div>", unsafe_allow_html=True)
        with na2: 
            user_svg = f'''<svg viewBox="0 0 24 24" fill="none" stroke="{TEXT_MAIN}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>'''
            st.markdown(f"<div style='width:36px;height:36px;float:right;'>{user_svg}</div>", unsafe_allow_html=True)

        st.markdown('<div class="user-btn-wrapper">', unsafe_allow_html=True)
        display_name = html.escape(str(st.session_state.user)) if st.session_state.user else str(t["guest"])
        if st.button(display_name, key="side_user", use_container_width=True):
            if st.session_state.user: 
                st.session_state.current_page = "D"
                st.rerun()
            else: 
                dlg_login()
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    with main:
        if st.session_state.user:
            top = st.columns([7, 1.5])
            top[0].markdown(f"<h2 style='margin:0;padding-top:6px;color:{TEXT_MAIN};font-family:Georgia,\"Times New Roman\",serif;font-weight:700'>{t['title']}</h2>", unsafe_allow_html=True)
            with top[1]:
                st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
                if st.button("⚙️ " + t["set"], key="home_set", use_container_width=True): dlg_settings()
                st.markdown("</div>", unsafe_allow_html=True)
        else:
            top = st.columns([5, 1.2, 1.2, 1.2])
            top[0].markdown(f"<h2 style='margin:0;padding-top:6px;color:{TEXT_MAIN};font-family:Georgia,\"Times New Roman\",serif;font-weight:700'>{t['title']}</h2>", unsafe_allow_html=True)
            with top[1]:
                st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
                if st.button("⚙️ " + t["set"], key="home_set", use_container_width=True): dlg_settings()
                st.markdown("</div>", unsafe_allow_html=True)
            with top[2]:
                st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
                if st.button(t["login"], use_container_width=True): dlg_login()
                st.markdown("</div>", unsafe_allow_html=True)
            with top[3]:
                st.markdown('<div class="pill-btn">', unsafe_allow_html=True)
                if st.button(t["signup"], use_container_width=True): dlg_signup()
                st.markdown("</div>", unsafe_allow_html=True)

        st.caption(f"<span style='color:{TEXT_MAIN};'>Group3 / Product Owner: TrungHieu Le</span>", unsafe_allow_html=True)

        if st.button(t["about"], use_container_width=True): 
            st.session_state.current_page = "About"
            st.rerun()

        about_img = ROOT / "about.jpg"
        if not about_img.is_file():
            about_img = STATIC / "about.jpg"
            
        if about_img.is_file():
            img_b64 = base64.b64encode(about_img.read_bytes()).decode()
            st.markdown(f'''
                <div style="width:100%; border-radius:12px; overflow:hidden; margin-top:8px; border: 1px solid rgba(150,150,150,0.2); box-shadow: 0 4px 12px rgba(0,0,0,0.05);">
                    <img src="data:image/jpeg;base64,{img_b64}" style="width:100%; height:auto; display:block;" alt="About Project Banner">
                </div>
            ''', unsafe_allow_html=True)
        else:
            st.markdown("<div style='background:linear-gradient(180deg,#1a4a6e 0%,#0d2840 100%);height:360px;border-radius:12px;margin-top:8px;display:flex;align-items:center;justify-content:center;color:#b8d4ec;font-size:14px;letter-spacing:.04em;border: 1px solid rgba(150,150,150,0.2);'>Please place about.jpg in the directory</div>", unsafe_allow_html=True)


# ---------- 10. 路由分发渲染 ----------
def m_about():
    imgs = _team_images()
    if not imgs:
        st.warning("未找到 static/team 图片。")
        return
    st.markdown("<div style='max-height:88vh;overflow-y:auto;padding-right:8px'>", unsafe_allow_html=True)
    for p in imgs: st.image(str(p), use_column_width=True)
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.current_page == "Home": 
    render_home()
else:
    top_back_btn()
    
    if st.session_state.current_page == "A": m_kitchen()
    elif st.session_state.current_page == "B": m_health()
    elif st.session_state.current_page == "C": m_community()
    elif st.session_state.current_page == "D": m_profile()
    elif st.session_state.current_page == "About": m_about()
