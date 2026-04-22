import streamlit as st
import base64
import requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

# ==========================================
# 0. 网页基本设置与全局状态初始化
# ==========================================
st.set_page_config(page_title="AI 健康社区", page_icon="🍎", layout="centered")

# 初始化用户登录状态
if 'user' not in st.session_state:
    st.session_state.user = None
# 初始化网页排版偏好
if 'layout_style' not in st.session_state:
    st.session_state.layout_style = "📱 卡片网格版 (推荐)"
# 初始化当前页面路由
if 'current_page' not in st.session_state:
    st.session_state.current_page = "首页"
# 初始化设置面板的隐藏/显示状态
if 'show_settings' not in st.session_state:
    st.session_state.show_settings = False

# 数据库静默连接
@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
try:
    supabase = init_connection()
    api_key = st.secrets["ALIYUN_API_KEY"]
except Exception:
    st.error("系统维护中，请联系管理员配置云端秘钥。")
    st.stop()

# ==========================================
# 1. 侧边栏：纯净版用户中心 & 隐藏式设置
# ==========================================
with st.sidebar:
    st.header("👤 个人中心")
    if st.session_state.user:
        st.success(f"欢迎，{st.session_state.user}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        st.info("登录后解锁完整生态")
        tab_login, tab_reg = st.tabs(["登录", "注册"])
        with tab_login:
            log_name = st.text_input("用户名", key="log_name")
            log_pwd = st.text_input("密码", type="password", key="log_pwd")
            if st.button("登录", type="primary", use_container_width=True):
                if supabase.table('app_users').select('*').eq('username', log_name).eq('password', log_pwd).execute().data:
                    st.session_state.user = log_name
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        with tab_reg:
            reg_name = st.text_input("设置用户名", key="reg_name")
            reg_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
            if st.button("注册", use_container_width=True):
                if supabase.table('app_users').select('*').eq('username', reg_name).execute().data:
                    st.error("用户名已被占用")
                else:
                    supabase.table('app_users').insert({"username": reg_name, "password": reg_pwd}).execute()
                    st.success("注册成功！")

    st.markdown("---")
    
    # 隐藏式设置按钮
    if st.button("⚙️ 显示/隐藏 偏好设置", use_container_width=True):
        st.session_state.show_settings = not st.session_state.show_settings
        st.rerun()
        
    if st.session_state.show_settings:
        st.markdown("### 偏好设置")
        new_style = st.selectbox("🖥️ 网页排版模式", ["📱 卡片网格版 (推荐)", "📑 传统标签页版"])
        if new_style != st.session_state.layout_style:
            st.session_state.layout_style = new_style
            st.session_state.current_page = "首页" 
            st.rerun()
            
        st.markdown("### 📖 产品说明书")
        st.info("""
        **探索四大生态：**
        * **AI 后厨**：拍照识图生成专属菜谱，或向 AI 提问。
        * **健康管家**：记录每日三餐与体重，生成 AI 营养周报。
        * **美食广场**：浏览热门动态，给喜欢的食谱点赞。
        * **我的主页**：管理你的发布记录与个人收藏夹。
        """)

# ==========================================
# 2. 团队开发模块区 (4人分工区域)
# ==========================================
def ask_ai(prompt, is_vision=False, image_bytes=None):
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    if is_vision:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        data = {"model": "qwen-vl-plus", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]}
    else:
        data = {"model": "qwen-plus", "messages": [{"role": "user", "content": prompt}]}
    return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']

# 👨‍💻 同学 A
def module_ai_kitchen():
    st.header("🍳 AI 智能后厨")
    st.write("📸 小功能 1：看图出菜谱 | 💬 小功能 2：营养师问答")
    st.info("同学 A：在此处粘贴你的代码")

# 👨‍💻 同学 B
def module_health_tracker():
    st.header("📈 健康管家")
    st.write("📝 小功能 1：每日打卡 | 📊 小功能 2：AI 营养周报")
    if not st.session_state.user: st.warning("请先登录！"); return
    st.info("同学 B：在此处粘贴你的代码")

# 👨‍💻 同学 C
def module_community():
    st.header("🏘️ 美食广场")
    st.write("🔥 小功能 1：热力排行 | ✍️ 小功能 2：标签发帖")
    if not st.session_state.user: st.warning("请先登录！"); return
    st.info("同学 C：在此处粘贴你的代码")

# 👨‍💻 同学 D
def module_user_center():
    st.header("👤 我的主页")
    st.write("⭐️ 小功能 1：我的收藏 | 📜 小功能 2：我的发布")
    if not st.session_state.user: st.warning("请先登录！"); return
    st.info("同学 D：在此处粘贴你的代码")

# ==========================================
# 3. 前端 UI 核心路由系统 (Apple Style 视觉注入)
# ==========================================
st.markdown("<h1 style='text-align: center; color: #1d1d1f; font-weight: 700; margin-bottom: 2rem;'>AI 健康全生态</h1>", unsafe_allow_html=True)

if st.session_state.layout_style == "📱 卡片网格版 (推荐)":
    
    if st.session_state.current_page == "首页":
        # 【修复版黑科技】仅在首页主屏幕注入卡片 CSS，绝不干扰侧边栏
        st.markdown("""
        <style>
        section[data-testid="stMain"] div[data-testid="stButton"] > button {
            height: 220px !important;
            border-radius: 24px !important;
            background-color: #ffffff !important;
            border: 1px solid rgba(0,0,0,0.04) !important;
            box-shadow: 0 10px 30px rgba(0,0,0,0.06) !important;
            transition: all 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
            align-items: center !important;
        }
        section[data-testid="stMain"] div[data-testid="stButton"] > button:hover {
            transform: translateY(-8px) scale(1.02) !important;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1) !important;
            border-color: rgba(0, 113, 227, 0.3) !important;
        }
        section[data-testid="stMain"] div[data-testid="stButton"] > button p {
            font-size: 1.4rem !important;
            font-weight: 600 !important;
            color: #1d1d1f !important;
            line-height: 1.6 !important;
        }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2 = st.columns(2, gap="large")
        with col1:
            if st.button("🍳 AI 智能后厨\n\n看图做菜 · 健康答疑", use_container_width=True):
                st.session_state.current_page = "模块A"
                st.rerun()
            if st.button("🏘️ 美食广场社区\n\n查看热门 · 分享食谱", use_container_width=True):
                st.session_state.current_page = "模块C"
                st.rerun()
                
        with col2:
            if st.button("📈 健康数据管家\n\n每日打卡 · AI周报", use_container_width=True):
                st.session_state.current_page = "模块B"
                st.rerun()
            if st.button("👤 我的专属主页\n\n收藏夹 · 历史记录", use_container_width=True):
                st.session_state.current_page = "模块D"
                st.rerun()
                
    else:
        if st.button("← 返回功能大厅"):
            st.session_state.current_page = "首页"
            st.rerun()
        st.markdown("---")
        
        # 路由分发
        if st.session_state.current_page == "模块A": module_ai_kitchen()
        elif st.session_state.current_page == "模块B": module_health_tracker()
        elif st.session_state.current_page == "模块C": module_community()
        elif st.session_state.current_page == "模块D": module_user_center()

else:
    # 传统标签页模式
    t1, t2, t3, t4 = st.tabs(["🍳 AI 后厨", "📈 健康管家", "🏘️ 美食社区", "👤 我的主页"])
    with t1: module_ai_kitchen()
    with t2: module_health_tracker()
    with t3: module_community()
    with t4: module_user_center()
