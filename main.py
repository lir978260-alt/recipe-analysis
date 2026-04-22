import streamlit as st
import base64
import requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

# ==========================================
# 0. 网页基本设置与全局样式注入 (极致极简)
# ==========================================
st.set_page_config(page_title="AI 健康全生态", page_icon="🍎", layout="centered")

# 强制隐藏顶部工具栏和底部水印，注入苹果风大卡片样式
st.markdown("""
    <style>
    /* 彻底隐藏官方 UI 元素 */
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    #MainMenu {visibility: hidden !important;}

    /* 全局背景与字体 */
    .stApp { background-color: #f5f5f7; }
    
    /* 首页巨型卡片样式 (Apple Style) */
    section[data-testid="stMain"] div.stButton > button {
        height: 240px !important;
        border-radius: 28px !important;
        background-color: #ffffff !important;
        border: 1px solid rgba(0,0,0,0.02) !important;
        box-shadow: 0 8px 24px rgba(0,0,0,0.04) !important;
        transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
        padding: 2rem !important;
    }
    section[data-testid="stMain"] div.stButton > button:hover {
        transform: translateY(-10px) scale(1.02) !important;
        box-shadow: 0 20px 40px rgba(0,0,0,0.08) !important;
        border-color: rgba(0, 113, 227, 0.4) !important;
    }
    section[data-testid="stMain"] div.stButton > button p {
        font-size: 1.5rem !important;
        font-weight: 600 !important;
        color: #1d1d1f !important;
        line-height: 1.4 !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- 状态管理 ---
if 'user' not in st.session_state: st.session_state.user = None
if 'current_page' not in st.session_state: st.session_state.current_page = "首页"
if 'show_settings' not in st.session_state: st.session_state.show_settings = False

# --- 数据库连接 ---
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase = init_connection()
    api_key = st.secrets["ALIYUN_API_KEY"]
except:
    st.error("数据库配置错误")
    st.stop()

# ==========================================
# 1. AI 引擎调用层
# ==========================================
def ask_ai_text(sys_p, usr_p):
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    data = {"model": "qwen-plus", "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}]}
    return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']

def ask_ai_vision(img_bytes, prompt):
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    data = {"model": "qwen-vl-plus", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]}
    return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']

# ==========================================
# 2. 四大核心模块 (8大功能实现)
# ==========================================

# --- 模块 A: AI 后厨 (功能 1&2) ---
def module_ai_kitchen():
    st.subheader("🍳 AI 智能后厨")
    t1, t2 = st.tabs(["📸 功能1: 看图出菜谱", "💬 功能2: 健康问答区"])
    with t1:
        col_u, col_p = st.columns(2)
        with col_u:
            up = st.file_uploader("上传食材照", type=['jpg', 'png'])
            pref = st.text_input("要求？", placeholder="例如：少油、快手菜")
        if up: col_p.image(up)
        if st.button("生成菜谱", type="primary"):
            with st.spinner("AI 大厨思考中..."):
                res = ask_ai_vision(up.getvalue(), f"识别食材，按要求 {pref} 给出菜谱")
                st.session_state['last_rec'] = res
                st.markdown(res)
        if 'last_rec' in st.session_state and st.session_state.user:
            if st.button("⭐️ 收藏此菜谱"):
                supabase.table('favorites').insert({"username": st.session_state.user, "recipe_content": st.session_state['last_rec']}).execute()
                st.success("已存入收藏夹")
    with t2:
        q = st.text_area("提问关于健康或饮食...")
        if st.button("向营养师提问"):
            st.info(ask_ai_text("你是一位专业营养师", q))

# --- 模块 B: 健康管家 (功能 3&4) ---
def module_health_tracker():
    st.subheader("📈 健康数据管家")
    if not st.session_state.user: st.warning("请先登录"); return
    t1, t2 = st.tabs(["📝 功能3: 每日数据打卡", "📊 功能4: AI 营养周报"])
    with t1:
        c1, c2 = st.columns(2)
        d = c1.date_input("日期", value=date.today())
        w = c2.number_input("体重 (kg)", value=60.0)
        cal = c1.number_input("摄入热量 (kcal)", value=1500)
        m = c2.text_area("饮食记录")
        if st.button("提交打卡"):
            supabase.table('diet_logs').insert({"username": st.session_state.user, "log_date": str(d), "weight": w, "calories": cal, "meals_record": m}).execute()
            st.success("打卡成功")
    with t2:
        logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date').execute().data
        if logs:
            df = pd.DataFrame(logs); df['log_date'] = pd.to_datetime(df['log_date']); df.set_index('log_date', inplace=True)
            st.line_chart(df[['weight', 'calories']])
            if st.button("分析近7天趋势"):
                with st.spinner("AI 诊断中..."):
                    logs_str = "\n".join([f"{r['log_date']}: {r['weight']}kg, {r['calories']}kcal" for r in logs[-7:]])
                    st.markdown(ask_ai_text("专业营养师", f"分析这些趋势并给建议: {logs_str}"))
        else: st.info("暂无数据")

# --- 模块 C: 广场社区 (功能 5&6) ---
def module_community():
    st.subheader("🏘️ 美食广场社区")
    t1, t2 = st.tabs(["🔥 功能5: 本周热力榜", "广场 功能6: 交流大厅"])
    with t1:
        top = supabase.table('comments').select('*').order('likes', desc=True).limit(3).execute().data
        cols = st.columns(3)
        for i, p in enumerate(top): cols[i].success(f"🏆 NO.{i+1} {p['user_name']}\n\n{p['dish_name']}")
    with t2:
        if st.session_state.user:
            with st.expander("✍️ 我要分享"):
                tag = st.selectbox("标签", ["#日常", "#减脂", "#神仙菜"])
                dish = st.text_input("标题")
                cont = st.text_area("评价")
                if st.button("发布"):
                    supabase.table('comments').insert({"user_name": st.session_state.user, "author_username": st.session_state.user, "dish_name": dish, "comment": cont, "likes": 0, "liked_by": [], "tag": tag}).execute()
                    st.rerun()
        
        posts = supabase.table('comments').select("*").order('id', desc=True).execute().data
        for r in posts:
            with st.container(border=True):
                st.markdown(f"**{r['user_name']}** `{r['tag']}`")
                st.write(f"### {r['dish_name']}\n{r['comment']}")
                liked = row_liked = r.get('liked_by') or []
                if st.button(f"👍 {r['likes']}", key=f"l_{r['id']}", disabled=(st.session_state.user in liked)):
                    liked.append(st.session_state.user)
                    supabase.table('comments').update({"likes": r['likes']+1, "liked_by": liked}).eq("id", r['id']).execute()
                    st.rerun()

# --- 模块 D: 个人主页 (功能 7&8) ---
def module_user_center():
    st.subheader("👤 我的专属主页")
    if not st.session_state.user: st.warning("请先登录"); return
    t1, t2 = st.tabs(["📜 功能7: 我的历史发布", "⭐ 功能8: 个人收藏夹"])
    with t1:
        mp = supabase.table('comments').select('*').eq('author_username', st.session_state.user).execute().data
        for p in mp: st.info(f"**{p['dish_name']}**\n{p['comment']}")
    with t2:
        favs = supabase.table('favorites').select('*').eq('username', st.session_state.user).execute().data
        for f in favs:
            if f.get('recipe_content'):
                with st.expander("📖 收藏的 AI 菜谱"): st.markdown(f['recipe_content'])
            else: st.write("帖子收藏 ID:", f['post_id'])

# ==========================================
# 3. 侧边栏与导航逻辑
# ==========================================
with st.sidebar:
    st.title("User Center")
    if st.session_state.user:
        st.write(f"Logged in as: **{st.session_state.user}**")
        if st.button("退出系统"): st.session_state.user = None; st.rerun()
    else:
        l, r = st.tabs(["登录", "注册"])
        with l:
            un = st.text_input("用户名")
            pw = st.text_input("密码", type="password")
            if st.button("立即进入"):
                if supabase.table('app_users').select('*').eq('username', un).eq('password', pw).execute().data:
                    st.session_state.user = un; st.rerun()
        with r:
            new_u = st.text_input("新账号")
            new_p = st.text_input("新密码", type="password")
            if st.button("确认注册"):
                supabase.table('app_users').insert({"username": new_u, "password": new_p}).execute()
                st.success("注册成功")
    
    st.markdown("---")
    if st.button("⚙️ 偏好设置"): st.session_state.show_settings = not st.session_state.show_settings; st.rerun()
    if st.session_state.show_settings:
        st.subheader("产品说明书")
        st.write("本站集成 AI 视觉与健康追踪，助你科学饮食。")

# ==========================================
# 4. 主视觉路由
# ==========================================
st.markdown("<h1 style='text-align: center; color: #1d1d1f; margin-bottom: 3rem;'>AI 健康全生态</h1>", unsafe_allow_html=True)

if st.session_state.current_page == "首页":
    c1, c2 = st.columns(2, gap="large")
    with c1:
        if st.button("🍳 AI 智能后厨\n\n看图出菜 · 专家问答"): st.session_state.current_page = "A"; st.rerun()
        if st.button("🏘️ 美食广场社区\n\n热力排行 · 广场互动"): st.session_state.current_page = "C"; st.rerun()
    with c2:
        if st.button("📈 健康数据管家\n\n数据打卡 · AI 周报"): st.session_state.current_page = "B"; st.rerun()
        if st.button("👤 我的专属主页\n\n发布记录 · 收藏中心"): st.session_state.current_page = "D"; st.rerun()
else:
    if st.button("← 返回功能大厅"): st.session_state.current_page = "首页"; st.rerun()
    st.markdown("---")
    if st.session_state.current_page == "A": module_ai_kitchen()
    elif st.session_state.current_page == "B": module_health_tracker()
    elif st.session_state.current_page == "C": module_community()
    elif st.session_state.current_page == "D": module_user_center()
