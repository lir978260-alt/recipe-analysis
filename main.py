import streamlit as st
import base64
import requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

# ==========================================
# 0. 网页基本设置与全局状态初始化
# ==========================================
st.set_page_config(page_title="AI 智能食谱与健康社区", page_icon="🥗", layout="centered")

# 初始化用户登录状态
if 'user' not in st.session_state:
    st.session_state.user = None
# 初始化网页排版偏好 (默认使用卡片网格布局)
if 'layout_style' not in st.session_state:
    st.session_state.layout_style = "📱 卡片网格版 (推荐)"
# 初始化当前页面路由 (针对卡片布局)
if 'current_page' not in st.session_state:
    st.session_state.current_page = "首页"

# 数据库静默连接 (不向用户显示连接状态)
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
# 1. 侧边栏：纯净版用户中心 & 系统设置
# ==========================================
with st.sidebar:
    st.header("👤 个人中心")
    if st.session_state.user:
        st.success(f"欢迎您，{st.session_state.user}")
        if st.button("🚪 退出登录", use_container_width=True):
            st.session_state.user = None
            st.rerun()
    else:
        st.info("登录后解锁完整功能")
        tab_login, tab_reg = st.tabs(["登录", "注册"])
        with tab_login:
            log_name = st.text_input("用户名", key="log_name")
            log_pwd = st.text_input("密码", type="password", key="log_pwd")
            if st.button("登录系统", type="primary", use_container_width=True):
                if supabase.table('app_users').select('*').eq('username', log_name).eq('password', log_pwd).execute().data:
                    st.session_state.user = log_name
                    st.rerun()
                else:
                    st.error("账号或密码错误")
        with tab_reg:
            reg_name = st.text_input("设置用户名", key="reg_name")
            reg_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
            if st.button("立即注册", use_container_width=True):
                if supabase.table('app_users').select('*').eq('username', reg_name).execute().data:
                    st.error("用户名已被占用")
                else:
                    supabase.table('app_users').insert({"username": reg_name, "password": reg_pwd}).execute()
                    st.success("注册成功，请登录！")

    st.markdown("---")
    st.header("⚙️ 系统设置")
    
    # 【UI核心】排版切换设置
    new_style = st.selectbox("🖥️ 网页排版模式", ["📱 卡片网格版 (推荐)", "📑 传统标签页版"])
    if new_style != st.session_state.layout_style:
        st.session_state.layout_style = new_style
        st.session_state.current_page = "首页" # 切换排版时强制回首页
        st.rerun()
        
    # 【UI核心】系统说明书
    with st.expander("📖 网站使用说明书"):
        st.markdown("""
        **欢迎来到 AI 健康社区！**
        * **功能A [AI 后厨]**：上传冰箱食材照片，AI 会教你做菜；或者直接向 AI 提问健康问题。
        * **功能B [健康管家]**：每天记录体重和吃了什么，累计 3 天可生成私人 AI 营养报告。
        * **功能C [美食广场]**：分享你的减脂餐，给别人的食谱点赞。
        * **功能D [我的主页]**：查看自己发过的帖子和收藏的神仙菜谱。
        * *提示：如果觉得卡片排版不习惯，可以在上方设置中切换为标签页模式。*
        """)

# ==========================================
# 2. 团队开发模块区 (4人分工区域)
# ==========================================
def ask_ai(prompt, is_vision=False, image_bytes=None):
    # (通用AI调用接口，队员直接调用，无需修改)
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    if is_vision:
        base64_image = base64.b64encode(image_bytes).decode('utf-8')
        data = {"model": "qwen-vl-plus", "messages": [{"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]}
    else:
        data = {"model": "qwen-plus", "messages": [{"role": "user", "content": prompt}]}
    return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']

# 👨‍💻 同学 A 的战场：AI 后厨
def module_ai_kitchen():
    st.header("🍳 AI 智能后厨")
    st.write("📸 小功能 1：看图出菜谱 | 💬 小功能 2：营养师问答")
    # --- 同学A的代码写在下面 ---
    file = st.file_uploader("上传食材照片找灵感")
    if file and st.button("生成菜谱"):
        st.info("这里是预留给 A 同学写 AI 视觉代码的地方")

# 👨‍💻 同学 B 的战场：健康管家
def module_health_tracker():
    st.header("📈 健康管家")
    st.write("📝 小功能 1：每日打卡 | 📊 小功能 2：AI 营养周报")
    if not st.session_state.user: st.warning("请先登录！"); return
    # --- 同学B的代码写在下面 ---
    st.info("这里是预留给 B 同学写数据库录入和图表绘制代码的地方")

# 👨‍💻 同学 C 的战场：美食社区
def module_community():
    st.header("🏘️ 美食广场")
    st.write("🔥 小功能 1：热力排行 | ✍️ 小功能 2：标签发帖")
    if not st.session_state.user: st.warning("请先登录！"); return
    # --- 同学C的代码写在下面 ---
    st.info("这里是预留给 C 同学写读取社区留言板和点赞逻辑的地方")

# 👨‍💻 同学 D 的战场：个人中心
def module_user_center():
    st.header("👤 我的主页")
    st.write("⭐️ 小功能 1：我的收藏 | 📜 小功能 2：我的发布")
    if not st.session_state.user: st.warning("请先登录！"); return
    # --- 同学D的代码写在下面 ---
    st.info("这里是预留给 D 同学写查自己发过什么帖子的代码的地方")


# ==========================================
# 3. 前端 UI 核心路由系统 (根据设置渲染界面)
# ==========================================
st.title("🥗 AI 智能食谱与健康社区")

if st.session_state.layout_style == "📱 卡片网格版 (推荐)":
    # --- 网格布局模式 ---
    if st.session_state.current_page == "首页":
        st.markdown("### 请选择你需要的功能")
        st.write("") # 留白
        
        # 绘制 2x2 的矩形卡片
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🍳 AI 智能后厨\n\n(看图做菜 / 健康答疑)", use_container_width=True):
                st.session_state.current_page = "模块A"
                st.rerun()
            st.write("") # 留白
            if st.button("🏘️ 美食广场社区\n\n(查看热门 / 分享食谱)", use_container_width=True):
                st.session_state.current_page = "模块C"
                st.rerun()
                
        with col2:
            if st.button("📈 健康数据管家\n\n(每日打卡 / AI周报)", use_container_width=True):
                st.session_state.current_page = "模块B"
                st.rerun()
            st.write("") # 留白
            if st.button("👤 我的专属主页\n\n(收藏夹 / 历史记录)", use_container_width=True):
                st.session_state.current_page = "模块D"
                st.rerun()
                
    else:
        # 进入具体功能页面，提供【返回主页】按钮
        if st.button("🔙 返回功能大厅"):
            st.session_state.current_page = "首页"
            st.rerun()
        st.markdown("---")
        
        # 根据当前页面路由，调用对应同学写的模块代码
        if st.session_state.current_page == "模块A": module_ai_kitchen()
        elif st.session_state.current_page == "模块B": module_health_tracker()
        elif st.session_state.current_page == "模块C": module_community()
        elif st.session_state.current_page == "模块D": module_user_center()

else:
    # --- 传统标签页模式 (兼容老习惯) ---
    t1, t2, t3, t4 = st.tabs(["🍳 AI 后厨", "📈 健康管家", "🏘️ 美食社区", "👤 我的主页"])
    with t1: module_ai_kitchen()
    with t2: module_health_tracker()
    with t3: module_community()
    with t4: module_user_center()
