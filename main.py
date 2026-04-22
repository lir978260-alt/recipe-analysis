import streamlit as st
import base64, requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client

# ==========================================
# 0. 全局状态与基础配置
# ==========================================
st.set_page_config(page_title="AI Health Ecosystem", page_icon="🍎", layout="centered")

for k in ['user', 'editing_id']:
    if k not in st.session_state: st.session_state[k] = None
if 'current_page' not in st.session_state: st.session_state.current_page = "Home"
if 'theme' not in st.session_state: st.session_state.theme = "🍎 苹果白 (Apple Light)"
if 'lang' not in st.session_state: st.session_state.lang = "🇨🇳 简体中文"

# ==========================================
# 1. 终极双语字典引擎 (i18n)
# ==========================================
i18n = {
    "🇨🇳 简体中文": {
        "sys_lang": "简体中文", "title": "AI 健康全生态", "login": "登录", "set": "设置", "back": "返回大厅",
        "m1": "🍳 AI 智能后厨\n\n看图出菜 · 专家问答", "m2": "🏘️ 美食广场社区\n\n热力排行 · 广场互动",
        "m3": "📈 健康数据管家\n\n数据打卡 · AI 周报", "m4": "👤 我的专属主页\n\n发布记录 · 收藏中心",
        "k_t": "🍳 AI 智能后厨", "k_t1": "📸 看图出菜谱", "k_t2": "💬 营养师问答", "up": "上传食材照片",
        "req": "口味要求 (可选)", "gen": "生成菜谱", "fav": "⭐️ 收藏此篇", "ask": "向营养师提问",
        "up_opt": "上传参考图片 (可选)", "think": "AI 正在思考...",
        "h_t": "📈 健康数据管家", "h_t1": "📝 数据录入", "h_t2": "📊 分析报告", "d": "选择日期", "w": "体重 (kg)",
        "b": "早餐记录", "l": "午餐记录", "dn": "晚餐记录", "sub": "提交并计算热量", "del": "删除", "edit": "修改",
        "c_t": "🏘️ 美食广场社区", "c_t1": "🔥 热力榜", "c_t2": "💬 交流大厅", "pub": "🚀 发布动态", "like": "赞",
        "tag": "选择标签", "title_in": "输入标题", "desc_in": "输入内容",
        "u_t": "👤 我的主页", "u_t1": "📜 历史发布", "u_t2": "⭐ 收藏夹",
        "err": "账号或密码错误", "suc": "操作成功", "out": "退出登录", "reg": "注册新号", "no_data": "暂无数据"
    },
    "🇬🇧 English": {
        "sys_lang": "English", "title": "AI Health Ecosystem", "login": "Login", "set": "Settings", "back": "Back to Home",
        "m1": "🍳 AI Kitchen\n\nRecipes & Q&A", "m2": "🏘️ Community\n\nTrending & Social",
        "m3": "📈 Health Tracker\n\nDaily Log & AI Report", "m4": "👤 My Profile\n\nHistory & Favs",
        "k_t": "🍳 AI Kitchen", "k_t1": "📸 Image to Recipe", "k_t2": "💬 Dietitian Q&A", "up": "Upload Ingredients",
        "req": "Preferences (Optional)", "gen": "Generate Recipe", "fav": "⭐️ Save Recipe", "ask": "Ask Dietitian",
        "up_opt": "Upload Image (Optional)", "think": "AI is processing...",
        "h_t": "📈 Health Tracker", "h_t1": "📝 Data Entry", "h_t2": "📊 Analytics", "d": "Date", "w": "Weight (kg)",
        "b": "Breakfast Log", "l": "Lunch Log", "dn": "Dinner Log", "sub": "Submit & Calc Calories", "del": "Delete", "edit": "Edit",
        "c_t": "🏘️ Community Square", "c_t1": "🔥 Trending", "c_t2": "💬 Discussion", "pub": "🚀 Publish", "like": "Like",
        "tag": "Select Tag", "title_in": "Enter Title", "desc_in": "Enter Details",
        "u_t": "👤 My Profile", "u_t1": "📜 My Posts", "u_t2": "⭐ Favorites",
        "err": "Invalid credentials", "suc": "Success", "out": "Logout", "reg": "Register", "no_data": "No data available"
    }
}
t = i18n[st.session_state.lang]

# ==========================================
# 2. 动态主题 CSS 引擎
# ==========================================
theme_colors = {
    "🍎 苹果白 (Apple Light)": {"bg": "#fcfcfd", "card": "#ffffff", "text": "#1d1d1f"},
    "🌌 暗夜黑 (Dark Mode)": {"bg": "#1c1c1e", "card": "#2c2c2e", "text": "#f5f5f7"},
    "🍃 抹茶绿 (Nature Mint)": {"bg": "#f4fbf6", "card": "#ffffff", "text": "#2d3a33"}
}
c = theme_colors[st.session_state.theme]

st.markdown(f"""
    <style>
    header[data-testid="stHeader"], footer {{visibility: hidden !important;}}
    .stApp {{ background-color: {c['bg']} !important; }}
    h1, h2, h3, h4, h5, h6, p, span, label {{ color: {c['text']} !important; }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"] {{
        height: 240px !important; border-radius: 28px !important; background-color: {c['card']} !important;
        border: 1px solid rgba(0,0,0,0.04) !important; box-shadow: 0 8px 24px rgba(0,0,0,0.04) !important;
        transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
    }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"]:hover {{
        transform: translateY(-8px) scale(1.02) !important; box-shadow: 0 20px 40px rgba(0,0,0,0.1) !important;
    }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"] p {{
        font-size: 1.4rem !important; font-weight: 600 !important; color: {c['text']} !important; line-height: 1.5 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 数据库连接
@st.cache_resource
def init_db(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
try: supabase, api_key = init_db(), st.secrets["ALIYUN_API_KEY"]
except: st.error("Database connection failed."); st.stop()

# ==========================================
# 3. 极速 AI 引擎调用层 (加入底层语言锁与模型切换)
# ==========================================
def ask_ai(sys_p, usr_p, img=None):
    # 【核心修复 1】强制语言锁：利用底层指令逼迫 AI 输出对应的语言
    sys_p += f" You must explicitly format and output your entire response in {t['sys_lang']}."
    
    # 【核心修复 2】智能切换极速模型：文本用 turbo，视觉用 vl-plus
    model = "qwen-vl-plus" if img else "qwen-turbo"
    
    url, h = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    msg = [{"type": "text", "text": usr_p}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img).decode('utf-8')}"}}] if img else usr_p
    data = {"model": model, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": msg}]} if not img else {"model": model, "messages": [{"role": "user", "content": msg}]}
    try: return requests.post(url, headers=h, json=data).json()['choices'][0]['message']['content']
    except Exception as e: return f"AI Error: {str(e)}"

# ==========================================
# 4. 四大核心模块函数 (全面植入字典引擎)
# ==========================================
def m_kitchen():
    st.subheader(t['k_t'])
    t1, t2 = st.tabs([t['k_t1'], t['k_t2']])
    with t1:
        c1, c2 = st.columns(2)
        up, pref = c1.file_uploader(t['up'], type=['jpg', 'png'], key="f1"), c1.text_input(t['req'])
        if up: c2.image(up)
        if st.button(t['gen']) and up:
            with st.spinner(t['think']):
                res = ask_ai("You are a Master Chef.", f"Identify the ingredients and generate a recipe. Requirements: {pref}", up.getvalue())
                st.session_state['l_rec'] = res; st.markdown(res)
        if st.session_state.get('l_rec') and st.session_state.user and st.button(t['fav']):
            supabase.table('favorites').insert({"username": st.session_state.user, "recipe_content": st.session_state['l_rec']}).execute(); st.success(t['suc'])
    with t2:
        # 【核心修复 3】营养师加入图像识别功能
        up_nutri = st.file_uploader(t['up_opt'], type=['jpg', 'png'], key="f2")
        if up_nutri: st.image(up_nutri, width=300)
        q = st.text_area(t['ask'])
        if st.button(t['sub'] if t['sys_lang']=="简体中文" else "Submit") and q:
            with st.spinner(t['think']):
                st.info(ask_ai("You are a professional Dietitian.", q, up_nutri.getvalue() if up_nutri else None))

def m_health():
    st.subheader(t['h_t'])
    if not st.session_state.user: return st.warning(t['err'])
    t1, t2 = st.tabs([t['h_t1'], t['h_t2']])
    with t1:
        with st.form("d_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d, w = c1.date_input(t['d'], date.today()), c2.number_input(t['w'], 60.0, step=0.1)
            b, l, dn = st.text_input(t['b']), st.text_input(t['l']), st.text_input(t['dn'])
            if st.form_submit_button(t['sub'], type="primary"):
                with st.spinner(t['think']):
                    cal = int(''.join(filter(str.isdigit, ask_ai("Nutrition Calculator", f"Estimate total calories. Return ONLY an integer: Breakfast:{b} Lunch:{l} Dinner:{dn}"))) or 0)
                    payload = {"username": st.session_state.user, "log_date": str(d), "weight": w, "calories": cal, "breakfast": b, "lunch": l, "dinner": dn}
                    if st.session_state.editing_id: supabase.table('diet_logs').update(payload).eq('id', st.session_state.editing_id).execute(); st.session_state.editing_id = None
                    else: supabase.table('diet_logs').insert(payload).execute()
                    st.rerun()
        for r in supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date', desc=True).execute().data:
            with st.expander(f"{r['log_date']} | {r['weight']}kg | {r['calories']}kcal"):
                st.write(f"{t['b']}:{r.get('breakfast','')} {t['l']}:{r.get('lunch','')} {t['dn']}:{r.get('dinner','')}")
                ce, cd = st.columns(2)
                if ce.button(t['edit'], key=f"e_{r['id']}"): st.session_state.editing_id = r['id']; st.rerun()
                if cd.button(t['del'], key=f"d_{r['id']}"): supabase.table('diet_logs').delete().eq('id', r['id']).execute(); st.rerun()
    with t2:
        logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date').execute().data
        if logs: 
            df = pd.DataFrame(logs); df['log_date'] = pd.to_datetime(df['log_date']); df.set_index('log_date', inplace=True)
            st.line_chart(df[['weight', 'calories']])
        else: st.info(t['no_data'])

def m_community():
    st.subheader(t['c_t'])
    t1, t2 = st.tabs([t['c_t1'], t['c_t2']])
    with t1:
        for i, p in enumerate(supabase.table('comments').select('*').order('likes', desc=True).limit(3).execute().data): 
            st.success(f"🏆 NO.{i+1} {p['user_name']}\n\n{p['dish_name']}")
    with t2:
        if st.session_state.user:
            with st.expander(t['pub']):
                tag, dish, cont = st.selectbox(t['tag'], ["#Daily", "#Diet", "#Yummy"] if t['sys_lang']=="English" else ["#日常", "#减脂", "#神仙菜"]), st.text_input(t['title_in']), st.text_area(t['desc_in'])
                if st.button("OK") and dish:
                    supabase.table('comments').insert({"user_name": st.session_state.user, "author_username": st.session_state.user, "dish_name": dish, "comment": cont, "likes": 0, "liked_by": [], "tag": tag}).execute(); st.rerun()
        for r in supabase.table('comments').select("*").order('id', desc=True).execute().data:
            with st.container(border=True):
                st.write(f"**{r['user_name']}** | 🏷️ {r['tag']}\n### {r['dish_name']}\n{r['comment']}")
                lk = r.get('liked_by') or []
                if st.button(f"{t['like']} ({r['likes']})", key=f"l_{r['id']}", disabled=(st.session_state.user in lk)):
                    lk.append(st.session_state.user); supabase.table('comments').update({"likes": r['likes']+1, "liked_by": lk}).eq("id", r['id']).execute(); st.rerun()

def m_user():
    st.subheader(t['u_t'])
    if not st.session_state.user: return st.warning(t['err'])
    t1, t2 = st.tabs([t['u_t1'], t['u_t2']])
    with t1:
        for p in supabase.table('comments').select('*').eq('author_username', st.session_state.user).order('id', desc=True).execute().data: st.info(f"**{p['dish_name']}**\n{p['comment']}")
    with t2:
        for f in supabase.table('favorites').select('*').eq('username', st.session_state.user).order('id', desc=True).execute().data:
            if f.get('recipe_content'): st.expander(t['fav']).markdown(f['recipe_content'])

# ==========================================
# 5. 核心路由与多语言导航
# ==========================================
if st.session_state.current_page == "Home":
    c_title, c_log, c_set = st.columns([6, 2, 2])
    c_title.markdown(f"<h2 style='margin-top:-10px;'>{t['title']}</h2>", unsafe_allow_html=True)
    if c_log.button(f"👤 {st.session_state.user}" if st.session_state.user else f"👤 {t['login']}", use_container_width=True): st.session_state.current_page = "Login"; st.rerun()
    if c_set.button(f"⚙️ {t['set']}", use_container_width=True): st.session_state.current_page = "Settings"; st.rerun()
    st.write("\n\n")
    
    c1, c2 = st.columns(2, gap="large")
    if c1.button(t['m1'], type="primary", use_container_width=True): st.session_state.current_page = "A"; st.rerun()
    if c1.button(t['m2'], type="primary", use_container_width=True): st.session_state.current_page = "C"; st.rerun()
    if c2.button(t['m3'], type="primary", use_container_width=True): st.session_state.current_page = "B"; st.rerun()
    if c2.button(t['m4'], type="primary", use_container_width=True): st.session_state.current_page = "D"; st.rerun()

elif st.session_state.current_page == "Login":
    if st.button(t['back']): st.session_state.current_page = "Home"; st.rerun()
    if st.session_state.user:
        st.success(f"{t['suc']}：{st.session_state.user}")
        if st.button(t['out']): st.session_state.user = None; st.rerun()
    else:
        tb1, tb2 = st.tabs([t['login'], t['reg']])
        with tb1:
            u, p = st.text_input("ID"), st.text_input("PWD", type="password")
            if st.button("OK"):
                if supabase.table('app_users').select('*').eq('username', u).eq('password', p).execute().data: st.session_state.user = u; st.session_state.current_page = "Home"; st.rerun()
                else: st.error(t['err'])
        with tb2:
            nu, np = st.text_input("New ID"), st.text_input("New PWD", type="password")
            if st.button("GO"):
                if supabase.table('app_users').select('*').eq('username', nu).execute().data: st.error(t['err'])
                else: supabase.table('app_users').insert({"username": nu, "password": np}).execute(); st.success(t['suc'])

elif st.session_state.current_page == "Settings":
    if st.button(t['back']): st.session_state.current_page = "Home"; st.rerun()
    st.markdown("---")
    
    st.markdown("### 🎨 Preferences")
    col_t, col_l = st.columns(2)
    with col_t:
        new_th = st.selectbox("Theme", ["🍎 苹果白 (Apple Light)", "🌌 暗夜黑 (Dark Mode)", "🍃 抹茶绿 (Nature Mint)"], index=["🍎 苹果白 (Apple Light)", "🌌 暗夜黑 (Dark Mode)", "🍃 抹茶绿 (Nature Mint)"].index(st.session_state.theme))
        if new_th != st.session_state.theme: st.session_state.theme = new_th; st.rerun()
    with col_l:
        new_la = st.selectbox("Language", ["🇨🇳 简体中文", "🇬🇧 English"], index=["🇨🇳 简体中文", "🇬🇧 English"].index(st.session_state.lang))
        if new_la != st.session_state.lang: st.session_state.lang = new_la; st.rerun()

else:
    if st.button("← " + t['back']): st.session_state.current_page = "Home"; st.rerun()
    st.markdown("---")
    {"A": m_kitchen, "B": m_health, "C": m_community, "D": m_user}[st.session_state.current_page]()
