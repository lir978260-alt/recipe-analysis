import streamlit as st
import base64, requests, json
import pandas as pd
from datetime import datetime, date, timedelta
from supabase import create_client
import extra_streamlit_components as stx

# ==========================================
# 0. 全局状态与基础自适应配置
# ==========================================
st.set_page_config(page_title="AI Health Ecosystem", page_icon="☁️", layout="wide", initial_sidebar_state="collapsed")

for k in ['user', 'editing_id']:
    if k not in st.session_state: st.session_state[k] = None
if 'current_page' not in st.session_state: st.session_state.current_page = "Home"
if 'lang' not in st.session_state: st.session_state.lang = "🇨🇳 简体中文"
if 'theme' not in st.session_state: st.session_state.theme = "☁️ 云朵白 (Cloud Light)"

if 'need_set_cookie' not in st.session_state: st.session_state.need_set_cookie = False
if 'need_del_cookie' not in st.session_state: st.session_state.need_del_cookie = False
if 'logout_flag' not in st.session_state: st.session_state.logout_flag = False

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

# ==========================================
# 1. 核心字典与双语翻译引擎 (i18n)
# ==========================================
i18n = {
    "🇨🇳 简体中文": {
        "sys_lang": "简体中文", "title": "AI 健康全生态", "login": "登录", "set": "设置", "back": "返回大厅",
        "m1": "☁️ AI 智能后厨\n\n看图出菜 · 专家问答", "m2": "🏘️ 美食广场社区\n\n热力排行 · 广场互动",
        "m3": "📈 健康数据管家\n\n数据打卡 · AI 周报", "m4": "👤 我的专属主页\n\n发布记录 · 收藏中心",
        "k_t": "☁️ AI 智能后厨", "k_t1": "📸 看图出菜谱", "k_t2": "💬 营养师问答", "up": "上传食材照片",
        "req": "口味要求 (可选)", "gen": "生成菜谱", "fav": "⭐️ 收藏此篇", "ask": "向营养师提问",
        "up_opt": "上传参考图片 (可选)", "think": "数据传输中...",
        "h_t": "📈 健康数据管家", "h_t1": "📝 数据录入", "h_t2": "📊 分析报告", "d": "选择日期", "w": "体重 (kg)",
        "b": "早餐记录", "l": "午餐记录", "dn": "晚餐记录", "sub": "提交并计算热量", "del": "删除", "edit": "修改",
        "c_t": "🏘️ 美食广场社区", "c_t1": "🔥 热力榜", "c_t2": "💬 交流大厅", "pub": "✨ 发布动态", "like": "赞",
        "tag": "选择标签", "title_in": "输入标题", "desc_in": "输入内容", "log_req": "⚠️ 请先登录",
        "u_t": "👤 我的主页", "u_t1": "📜 历史发布", "u_t2": "⭐ 收藏夹",
        "err": "账号或密码错误", "suc": "操作成功", "out": "退出登录", "reg": "注册新号", "no_data": "暂无数据",
        "id_in": "输入账号", "pwd_in": "输入密码", "new_id": "设置新账号", "new_pwd": "设置新密码", "confirm": "确认",
        "unfav": "🤍 取消收藏", "del_post": "🗑️ 删除此贴", "reply": "💬 回复", "reply_ph": "写下回复...", "send": "发送",
        "rec_dish": "🍲 推荐神仙菜品", "rec_ph": "输入菜名并回车进行搜索...", "voted": "⚠️ 你已经给这道菜投过票啦！", "votes": "票",
        "guess": "💡 猜你想选 (点击直接推荐):", "no_match": "🔍 库中暂无此预设菜品，请点击下方作为新菜推荐：", 
        "rec_custom": "✨ 推荐：{}", "view_lib": "📚 查看系统预设菜品库 (100款)"
    },
    "🇬🇧 English": {
        "sys_lang": "English", "title": "AI Health Ecosystem", "login": "Login", "set": "Settings", "back": "Back to Home",
        "m1": "☁️ AI Kitchen\n\nRecipes & Q&A", "m2": "🏘️ Community\n\nTrending & Social",
        "m3": "📈 Health Tracker\n\nDaily Log & AI Report", "m4": "👤 My Profile\n\nHistory & Favs",
        "k_t": "☁️ AI Kitchen", "k_t1": "📸 Image to Recipe", "k_t2": "💬 Dietitian Q&A", "up": "Upload Ingredients",
        "req": "Preferences (Optional)", "gen": "Generate Recipe", "fav": "⭐️ Save Recipe", "ask": "Ask Dietitian",
        "up_opt": "Upload Image (Optional)", "think": "Transmitting data...",
        "h_t": "📈 Health Tracker", "h_t1": "📝 Data Entry", "h_t2": "📊 Analytics", "d": "Date", "w": "Weight (kg)",
        "b": "Breakfast Log", "l": "Lunch Log", "dn": "Dinner Log", "sub": "Submit & Calc Calories", "del": "Delete", "edit": "Edit",
        "c_t": "🏘️ Community Square", "c_t1": "🔥 Trending", "c_t2": "💬 Discussion", "pub": "✨ Publish", "like": "Like",
        "tag": "Select Tag", "title_in": "Enter Title", "desc_in": "Enter Details", "log_req": "⚠️ Please login first",
        "u_t": "👤 My Profile", "u_t1": "📜 My Posts", "u_t2": "⭐ Favorites",
        "err": "Invalid credentials", "suc": "Success", "out": "Logout", "reg": "Register", "no_data": "No data available",
        "id_in": "Enter ID", "pwd_in": "Enter Password", "new_id": "Create ID", "new_pwd": "Create Password", "confirm": "Confirm",
        "unfav": "🤍 Unfavorite", "del_post": "🗑️ Delete Post", "reply": "💬 Reply", "reply_ph": "Write a reply...", "send": "Send",
        "rec_dish": "🍲 Recommend a Dish", "rec_ph": "Type dish name and press Enter...", "voted": "⚠️ You already voted for this dish!", "votes": "votes",
        "guess": "💡 Suggestions (Click to vote):", "no_match": "🔍 Not in library. Click below to recommend:", 
        "rec_custom": "✨ Recommend: {}", "view_lib": "📚 View System Dish Library (100 Items)"
    }
}
t = i18n[st.session_state.lang]

# ==========================================
# 扩充：100款中英双语菜品系统库
# ==========================================
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
        "客家三杯鸡", "沙茶牛肉", "蚝烙", "三杯鸭", "梅菜扣肉", "清炖羊肉", "手撕包菜", "酸辣土豆丝", "麻酱拌面", "红油抄手"
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
        "Hakka Three Cup Chicken", "Shacha Beef", "Oyster Omelette", "Three Cup Duck", "Braised Pork with Mustard Greens", "Stewed Mutton", "Hand-torn Cabbage", "Hot and Sour Shredded Potatoes", "Noodles with Sesame Paste", "Wontons in Chili Oil"
    ]
}

@st.cache_resource
def init_db(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
try: supabase, api_key = init_db(), st.secrets["ALIYUN_API_KEY"]
except: st.error("Database connection failed."); st.stop()

# ==========================================
# 2. 自适应 CSS 引擎与色彩管理
# ==========================================
theme_colors = {
    "☁️ 云朵白 (Cloud Light)": {"bg": "#fcfcfd", "card": "#ffffff", "text": "#1d1d1f"},
    "🌌 暗夜黑 (Dark Mode)": {"bg": "#1c1c1e", "card": "#2c2c2e", "text": "#f5f5f7"},
    "🍃 抹茶绿 (Nature Mint)": {"bg": "#f4fbf6", "card": "#ffffff", "text": "#2d3a33"},
    "🌊 海洋蓝 (Ocean Blue)": {"bg": "#f4f9ff", "card": "#ffffff", "text": "#0a2540"}
}
c = theme_colors[st.session_state.theme]

st.markdown(f"""
    <style>
    header[data-testid="stHeader"], footer {{visibility: hidden !important;}}
    .stApp, .stApp > header {{ background-color: {c['bg']} !important; }}
    h1, h2, h3, h4, h5, h6, p, span, label, div[data-testid="stMarkdownContainer"] {{ color: {c['text']} !important; }}
    
    .block-container {{ max-width: 1200px !important; padding-top: 2rem !important; padding-bottom: 2rem !important; }}
    
    div[data-testid="stButton"] > button {{ color: {c['text']} !important; border-color: rgba(150,150,150,0.3) !important; }}
    div[data-testid="stButton"] > button:disabled {{ background-color: transparent !important; opacity: 0.4 !important; border: 1px solid rgba(150,150,150,0.2) !important; }}
    
    section[data-testid="stMain"] div.stButton > button[kind="primary"] {{
        min-height: 180px !important; height: auto !important; padding: 1.5rem !important; border-radius: 24px !important; 
        background-color: {c['card']} !important; border: 1px solid rgba(0,0,0,0.06) !important; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important; transition: all 0.3s ease-in-out !important; 
        width: 100% !important; display: flex !important; align-items: center !important; justify-content: center !important;
    }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"]:hover {{ transform: translateY(-6px) scale(1.01) !important; box-shadow: 0 12px 24px rgba(0,0,0,0.08) !important; }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"] p {{ font-size: clamp(1.1rem, 2vw, 1.4rem) !important; font-weight: 600 !important; line-height: 1.5 !important; white-space: pre-wrap !important; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 流式 AI 引擎调用层
# ==========================================
def ask_ai_stream(sys_p, usr_p, img=None):
    usr_p += f"\n\n[CRITICAL INSTRUCTION: You must strictly output your entire response in {t['sys_lang']}! Do not use any other language.]"
    model = "qwen-vl-plus" if img else "qwen-plus"
    url, h = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    msg_content = [{"type": "text", "text": usr_p}]
    if img: msg_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img).decode('utf-8')}"}})
    data = {"model": model, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": msg_content}], "stream": True}
    try: 
        res = requests.post(url, headers=h, json=data, timeout=90, stream=True)
        for line in res.iter_lines():
            if line and line.decode('utf-8').startswith('data: ') and line.decode('utf-8') != 'data
