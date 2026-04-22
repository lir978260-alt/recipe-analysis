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

# 全局隐藏顶部工具栏和底部官方水印 (更精准的隐藏，防误伤)
st.markdown("""
    <style>
    header[data-testid="stHeader"] {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    .stApp { background-color: #fcfcfd; }
    </style>
""", unsafe_allow_html=True)

# 状态管理
if 'user' not in st.session_state: st.session_state.user = None
if 'current_page' not in st.session_state: st.session_state.current_page = "首页"
if 'editing_id' not in st.session_state: st.session_state.editing_id = None

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
    try:
        return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']
    except:
        return "0"

def ask_ai_vision(img_bytes, prompt):
    b64 = base64.b64encode(img_bytes).decode('utf-8')
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    data = {"model": "qwen-vl-plus", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}]}]}
    try:
        return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']
    except:
        return "AI 视觉错误"

# ==========================================
# 2. 四大核心模块函数 (无省略，完整版)
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
        if st.button("生成菜谱"): 
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
    
    t1, t2 = st.tabs(["📝 数据录入与管理", "📊 营养分析报告"])
    with t1:
        with st.form("diet_form", clear_on_submit=True):
            st.write("### 📅 今日打卡" if not st.session_state.editing_id else "### ✏️ 修改记录")
            c1, c2 = st.columns(2)
            d = c1.date_input("选择日期", value=date.today())
            w = c2.number_input("体重 (kg)", value=60.0, step=0.1)
            
            st.write("---")
            b = st.text_input("🍳 早餐记录", placeholder="例如：燕麦片一碗，蓝莓一小把")
            l = st.text_input("🍱 午餐记录", placeholder="例如：香煎三文鱼，西兰花，半碗糙米饭")
            dn = st.text_input("🌙 晚餐记录", placeholder="例如：西红柿鸡蛋面，少量青菜")
            
            submit_label = "🚀 提交并让 AI 计算热量" if not st.session_state.editing_id else "💾 保存修改"
            submitted = st.form_submit_button(submit_label, type="primary")
            
            if submitted:
                with st.spinner("AI 正在根据您的食谱估算热量..."):
                    prompt = f"请根据以下三餐描述，估算总摄入卡路里：早餐：{b}；午餐：{l}；晚餐：{dn}。请仅返回一个纯数字整数，不要包含任何单位或其他文字。"
                    cal_res = ask_ai_text("你是一个营养计算器", prompt)
                    try:
                        final_cal = int(''.join(filter(str.isdigit, cal_res)))
                    except:
                        final_cal = 0
                    
                    data_payload = {
                        "username": st.session_state.user,
                        "log_date": str(d),
                        "weight": w,
                        "calories": final_cal,
                        "breakfast": b,
                        "lunch": l,
                        "dinner": dn
                    }
                    
                    if st.session_state.editing_id:
                        supabase.table('diet_logs').update(data_payload).eq('id', st.session_state.editing_id).execute()
                        st.session_state.editing_id = None
                        st.success("修改成功！")
                    else:
                        supabase.table('diet_logs').insert(data_payload).execute()
                        st.success(f"打卡成功！AI 估算今日总摄入：{final_cal} kcal")
                    st.rerun()

        st.write("---")
        st.write("### 📂 历史记录管理")
        logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date', desc=True).execute().data
        
        if not logs:
            st.info("暂无记录，快去上方打卡吧！")
        else:
            for record in logs:
                with st.expander(f"📅 {record['log_date']} | 体重: {record['weight']}kg | 热量: {record['calories']}kcal"):
                    st.write(f"**早：** {record.get('breakfast', '无')}")
                    st.write(f"**午：** {record.get('lunch', '无')}")
                    st.write(f"**晚：** {record.get('dinner', '无')}")
                    
                    col_edit, col_del = st.columns([1, 1])
                    if col_edit.button("修改此记录", key=f"edit_{record['id']}"):
                        st.session_state.editing_id = record['id']
                        st.rerun()
                    
                    if col_del.button("删除此记录", key=f"del_{record['id']}"):
                        supabase.table('diet_logs').delete().eq('id', record['id']).execute()
                        st.success("记录已删除")
                        st.rerun()

    with tab2:
        logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date').execute().data
        if logs:
            df = pd.DataFrame(logs); df['log_date'] = pd.to_datetime(df['log_date']); df.set_index('log_date', inplace=True)
            st.line_chart(df[['weight', 'calories']])
        else:
            st.info("暂无数据进行报表分析")

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
                st.markdown(f"**🧑‍🍳 {r['user_name']}** ｜ 🏷️ {r['tag']}")
                st.write(f"### {r['dish_name']}\n{r['comment']}")
                liked = row_liked = r.get('liked_by') or []
                if st.button(f"👍 {r['likes']}", key=f"l_{r['id']}", disabled=(st.session_state.user in liked)):
                    liked.append(st.session_state.user)
                    supabase.table('comments').update({"likes": r['likes']+1, "liked_by": liked}).eq("id", r['id']).execute()
                    st.rerun()

def module_user_center():
    st.subheader("👤 我的专属主页")
    if not st.session_state.user: st.warning("⚠️ 请先返回首页登录"); return
    t1, t2 = st.tabs(["📜 我的历史
