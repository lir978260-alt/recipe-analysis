import streamlit as st
import base64, requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client

# ==========================================
# 0. 全局状态与基础配置
# ==========================================
st.set_page_config(page_title="AI Health Ecosystem", page_icon="🍎", layout="centered")

# 初始化所有全局状态
for k in ['user', 'editing_id']:
    if k not in st.session_state: st.session_state[k] = None
if 'current_page' not in st.session_state: st.session_state.current_page = "首页"
if 'theme' not in st.session_state: st.session_state.theme = "🍎 苹果白 (Apple Light)"
if 'lang' not in st.session_state: st.session_state.lang = "🇨🇳 简体中文"

# --- 国际化 (i18n) 字典 ---
i18n = {
    "🇨🇳 简体中文": {
        "title": "AI 健康全生态", "login": "登录", "set": "设置", "back": "返回首页",
        "m1": "🍳 AI 智能后厨\n\n看图出菜 · 专家问答", "m2": "🏘️ 美食广场社区\n\n热力排行 · 广场互动",
        "m3": "📈 健康数据管家\n\n数据打卡 · AI 周报", "m4": "👤 我的专属主页\n\n发布记录 · 收藏中心"
    },
    "🇬🇧 English": {
        "title": "AI Health Ecosystem", "login": "Login", "set": "Settings", "back": "Back to Home",
        "m1": "🍳 AI Kitchen\n\nRecipes & Nutritionist", "m2": "🏘️ Community\n\nTrending & Sharing",
        "m3": "📈 Health Tracker\n\nDaily Logs & AI Reports", "m4": "👤 My Profile\n\nHistory & Favorites"
    }
}
t = i18n[st.session_state.lang]

# --- 动态主题 CSS 引擎 ---
theme_colors = {
    "🍎 苹果白 (Apple Light)": {"bg": "#fbfbfd", "card": "#ffffff", "text": "#1d1d1f", "border": "rgba(0,0,0,0.04)"},
    "🌌 暗夜黑 (Dark Mode)": {"bg": "#1c1c1e", "card": "#2c2c2e", "text": "#f5f5f7", "border": "rgba(255,255,255,0.05)"},
    "🍃 抹茶绿 (Nature Mint)": {"bg": "#f4fbf6", "card": "#ffffff", "text": "#2d3a33", "border": "rgba(46, 139, 87, 0.1)"}
}
c = theme_colors[st.session_state.theme]

st.markdown(f"""
    <style>
    /* 隐藏官方痕迹 */
    header[data-testid="stHeader"], footer {{visibility: hidden !important;}}
    
    /* 动态全局颜色 */
    .stApp {{ background-color: {c['bg']} !important; }}
    h1, h2, h3, h4, h5, h6, p, span {{ color: {c['text']} !important; }}
    
    /* 巨型卡片通用样式 */
    section[data-testid="stMain"] div.stButton > button[kind="primary"] {{
        height: 240px !important; border-radius: 28px !important; 
        background-color: {c['card']} !important; border: 1px solid {c['border']} !important; 
        box-shadow: 0 8px 24px rgba(0,0,0,0.04) !important;
        transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
    }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"] p {{
        font-size: 1.4rem !important; font-weight: 600 !important; line-height: 1.5 !important;
    }}
    
    /* 炫彩悬浮动效 (为四个功能分别注入 橙、蓝、绿、紫 简约发光效果) */
    section[data-testid="stMain"] div.stButton > button[kind="primary"]:hover {{
        transform: translateY(-8px) scale(1.02) !important;
    }}
    </style>
""", unsafe_allow_html=True)

# 数据库连接
@st.cache_resource
def init_db(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
try: supabase, api_key = init_db(), st.secrets["ALIYUN_API_KEY"]
except: st.error("配置错误"); st.stop()

# ==========================================
# 1. AI 引擎调用层
# ==========================================
def ask_ai(sys_p, usr_p, img=None):
    url, h = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions', {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    msg = [{"type": "text", "text": usr_p}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64.b64encode(img).decode('utf-8')}"}}] if img else usr_p
    data = {"model": "qwen-vl-plus" if img else "qwen-plus", "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": msg}]} if not img else {"model": "qwen-vl-plus", "messages": [{"role": "user", "content": msg}]}
    try: return requests.post(url, headers=h, json=data).json()['choices'][0]['message']['content']
    except: return "0"

# ==========================================
# 2. 四大核心模块函数 (纯净业务逻辑)
# ==========================================
def m_kitchen():
    st.subheader("🍳 AI 智能后厨")
    t1, t2 = st.tabs(["📸 看图出菜谱", "💬 营养师问答"])
    with t1:
        c1, c2 = st.columns(2)
        up, pref = c1.file_uploader("食材照", type=['jpg', 'png']), c1.text_input("要求", placeholder="少油/快手")
        if up: c2.image(up)
        if st.button("生成菜谱") and up:
            with st.spinner("思考中..."):
                res = ask_ai("", f"识别食材，按要求 {pref} 给菜谱", up.getvalue())
                st.session_state['l_rec'] = res; st.markdown(res)
        if st.session_state.get('l_rec') and st.session_state.user and st.button("收藏菜谱"):
            supabase.table('favorites').insert({"username": st.session_state.user, "recipe_content": st.session_state['l_rec']}).execute(); st.success("已收藏")
    with t2:
        q = st.text_area("提问")
        if st.button("提交") and q: st.info(ask_ai("你是专业营养师", q))

def m_health():
    st.subheader("📈 健康数据管家")
    if not st.session_state.user: return st.warning("请登录")
    t1, t2 = st.tabs(["📝 数据录入", "📊 分析报告"])
    with t1:
        with st.form("d_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d, w = c1.date_input("日期", date.today()), c2.number_input("体重", 60.0, step=0.1)
            b, l, dn = st.text_input("早餐"), st.text_input("午餐"), st.text_input("晚餐")
            if st.form_submit_button("提交/保存", type="primary"):
                with st.spinner("计算中..."):
                    cal = int(''.join(filter(str.isdigit, ask_ai("营养计算器", f"根据描述估算总卡路里，仅返回整数:早{b}午{l}晚{dn}"))) or 0)
                    payload = {"username": st.session_state.user, "log_date": str(d), "weight": w, "calories": cal, "breakfast": b, "lunch": l, "dinner": dn}
                    if st.session_state.editing_id: supabase.table('diet_logs').update(payload).eq('id', st.session_state.editing_id).execute(); st.session_state.editing_id = None
                    else: supabase.table('diet_logs').insert(payload).execute()
                    st.rerun()
        for r in supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date', desc=True).execute().data:
            with st.expander(f"{r['log_date']} | {r['weight']}kg | {r['calories']}kcal"):
                st.write(f"早:{r.get('breakfast','')} 午:{r.get('lunch','')} 晚:{r.get('dinner','')}")
                ce, cd = st.columns(2)
                if ce.button("修改", key=f"e_{r['id']}"): st.session_state.editing_id = r['id']; st.rerun()
                if cd.button("删除", key=f"d_{r['id']}"): supabase.table('diet_logs').delete().eq('id', r['id']).execute(); st.rerun()
    with t2:
        logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date').execute().data
        if logs: 
            df = pd.DataFrame(logs); df['log_date'] = pd.to_datetime(df['log_date']); df.set_index('log_date', inplace=True)
            st.line_chart(df[['weight', 'calories']])

def m_community():
    st.subheader("🏘️ 美食广场社区")
    t1, t2 = st.tabs(["🔥 热力榜", "💬 交流大厅"])
    with t1:
        for i, p in enumerate(supabase.table('comments').select('*').order('likes', desc=True).limit(3).execute().data): 
            st.success(f"🏆 NO.{i+1} {p['user_name']}\n\n{p['dish_name']}")
    with t2:
        if st.session_state.user:
            with st.expander("✍️ 发布动态"):
                tag, dish, cont = st.selectbox("标签", ["日常", "减脂", "神仙菜"]), st.text_input("标题"), st.text_area("内容")
                if st.button("提交") and dish:
                    supabase.table('comments').insert({"user_name": st.session_state.user, "author_username": st.session_state.user, "dish_name": dish, "comment": cont, "likes": 0, "liked_by": [], "tag": tag}).execute(); st.rerun()
        for r in supabase.table('comments').select("*").order('id', desc=True).execute().data:
            with st.container(border=True):
                st.write(f"**{r['user_name']}** | 🏷️ {r['tag']}\n### {r['dish_name']}\n{r['comment']}")
                lk = r.get('liked_by') or []
                if st.button(f"赞 ({r['likes']})", key=f"l_{r['id']}", disabled=(st.session_state.user in lk)):
                    lk.append(st.session_state.user); supabase.table('comments').update({"likes": r['likes']+1, "liked_by": lk}).eq("id", r['id']).execute(); st.rerun()

def m_user():
    st.subheader("👤 我的主页")
    if not st.session_state.user: return st.warning("请登录")
    t1, t2 = st.tabs(["📜 历史发布", "⭐ 收藏夹"])
    with t1:
        for p in supabase.table('comments').select('*').eq('author_username', st.session_state.user).order('id', desc=True).execute().data: st.info(f"**{p['dish_name']}**\n{p['comment']}")
    with t2:
        for f in supabase.table('favorites').select('*').eq('username', st.session_state.user).order('id', desc=True).execute().data:
            if f.get('recipe_content'): st.expander("📖 收藏菜谱").markdown(f['recipe_content'])

# ==========================================
# 3. 核心路由与多语言 UI
# ==========================================
if st.session_state.current_page == "首页":
    c_title, c_log, c_set = st.columns([6, 2, 2])
    c_title.markdown(f"<h2 style='margin-top:-10px;'>{t['title']}</h2>", unsafe_allow_html=True)
    if c_log.button(f"👤 {st.session_state.user}" if st.session_state.user else f"👤 {t['login']}", use_container_width=True): st.session_state.current_page = "登录"; st.rerun()
    if c_set.button(f"⚙️ {t['set']}", use_container_width=True): st.session_state.current_page = "设置"; st.rerun()
    st.write("\n\n")
    
    c1, c2 = st.columns(2, gap="large")
    if c1.button(t['m1'], type="primary", use_container_width=True): st.session_state.current_page = "A"; st.rerun()
    if c1.button(t['m2'], type="primary", use_container_width=True): st.session_state.current_page = "C"; st.rerun()
    if c2.button(t['m3'], type="primary", use_container_width=True): st.session_state.current_page = "B"; st.rerun()
    if c2.button(t['m4'], type="primary", use_container_width=True): st.session_state.current_page = "D"; st.rerun()

elif st.session_state.current_page == "登录":
    if st.button(t['back']): st.session_state.current_page = "首页"; st.rerun()
    if st.session_state.user:
        st.success(f"已登录 (Logged in)：{st.session_state.user}")
        if st.button("退出 (Logout)"): st.session_state.user = None; st.rerun()
    else:
        tb1, tb2 = st.tabs(["登录 (Login)", "注册 (Register)"])
        with tb1:
            u, p = st.text_input("用户名"), st.text_input("密码", type="password")
            if st.button("确认"):
                if supabase.table('app_users').select('*').eq('username', u).eq('password', p).execute().data: st.session_state.user = u; st.session_state.current_page = "首页"; st.rerun()
                else: st.error("错误 Error")
        with tb2:
            nu, np = st.text_input("新账号"), st.text_input("新密码", type="password")
            if st.button("提交"):
                if supabase.table('app_users').select('*').eq('username', nu).execute().data: st.error("已占用")
                else: supabase.table('app_users').insert({"username": nu, "password": np}).execute(); st.success("成功 Success")

elif st.session_state.current_page == "设置":
    if st.button(t['back']): st.session_state.current_page = "首页"; st.rerun()
    st.markdown("---")
    
    st.markdown("### 🎨 偏好设置 / Preferences")
    col_t, col_l = st.columns(2)
    with col_t:
        new_th = st.selectbox("界面模板 (Theme)", ["🍎 苹果白 (Apple Light)", "🌌 暗夜黑 (Dark Mode)", "🍃 抹茶绿 (Nature Mint)"], index=["🍎 苹果白 (Apple Light)", "🌌 暗夜黑 (Dark Mode)", "🍃 抹茶绿 (Nature Mint)"].index(st.session_state.theme))
        if new_th != st.session_state.theme: st.session_state.theme = new_th; st.rerun()
    with col_l:
        new_la = st.selectbox("语言 (Language)", ["🇨🇳 简体中文", "🇬🇧 English"], index=["🇨🇳 简体中文", "🇬🇧 English"].index(st.session_state.lang))
        if new_la != st.session_state.lang: st.session_state.lang = new_la; st.rerun()
    
    st.markdown("---")
    st.markdown("### 📖 系统说明书 / User Manual")
    with st.expander("🟢 模块 A：AI 智能后厨 (AI Kitchen)"):
        st.info("**功能介绍：**\n1. 上传冰箱里剩余食材的照片，输入口味要求，AI大厨会自动为你量身定制两套菜谱。\n2. 如果你对饮食禁忌、营养成分有疑问，可以在问答区随时咨询 24 小时在线的 AI 营养师。")
    with st.expander("🔵 模块 B：健康数据管家 (Health Tracker)"):
        st.info("**功能介绍：**\n1. 每天记录你的体重和早、中、晚三餐吃的内容，AI 会自动帮你估算总卡路里并保存。\n2. 连续打卡后，可以在分析报告页查看体重的折线图，并一键生成本周的“AI 饮食诊断书”。")
    with st.expander("🟠 模块 C：美食广场社区 (Community)"):
        st.warning("**功能介绍：**\n1. 你可以在这里发布自己的减脂餐或者欺骗餐，和其他用户互相点赞交流。\n2. 系统会自动统计全站数据，并生成“本周热力榜”，展示最受欢迎的 Top 3 食谱。")
    with st.expander("🟣 模块 D：专属主页 (My Profile)"):
        st.success("**功能介绍：**\n1. 历史发布：统一管理你在社区发过的所有帖子。\n2. 收藏夹：在 AI 后厨生成的满意菜谱，点击收藏后会永久保存在这里，永不丢失。")

else:
    if st.button("← " + t['back']): st.session_state.current_page = "首页"; st.rerun()
    st.markdown("---")
    {"A": m_kitchen, "B": m_health, "C": m_community, "D": m_user}[st.session_state.current_page]()
