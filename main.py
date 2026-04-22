import streamlit as st
import base64
import requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

# ==========================================
# 0. 网页基本设置与隐藏全局水印
# ==========================================
st.set_page_config(page_title="AI 健康全生态", page_icon="🍎", layout="centered")

# 全局隐藏顶部工具栏和底部官方水印
st.markdown("""
    <style>
    header {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #fcfcfd; }
    </style>
""", unsafe_allow_html=True)

# 状态管理
if 'user' not in st.session_state: st.session_state.user = None
if 'current_page' not in st.session_state: st.session_state.current_page = "首页"

# 数据库连接
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
# 2. 四大核心模块函数 (全功能打通)
# ==========================================
def module_ai_kitchen():
    st.subheader("🍳 AI 智能后厨")
    t1, t2 = st.tabs(["📸 看图出菜谱", "💬 营养师问答"])
    with t1:
        col_u, col_p = st.columns(2)
        with col_u:
            up = st.file_uploader("上传食材照", type=['jpg', 'png'])
            pref = st.text_input("要求？", placeholder="例如：少油、快手菜")
        if up: col_p.image(up)
        if st.button("生成菜谱"): # 正常小按钮
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

def module_health_tracker():
    st.subheader("📈 健康数据管家")
    if not st.session_state.user: st.warning("⚠️ 请先返回首页登录"); return
    t1, t2 = st.tabs(["📝 每日数据打卡", "📊 AI 营养周报"])
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

def module_community():
    st.subheader("🏘️ 美食广场社区")
    t1, t2 = st.tabs(["🔥 本周热力榜", "💬 交流大厅"])
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
                st.markdown(f"**{r['user_
