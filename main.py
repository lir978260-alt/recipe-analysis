import streamlit as st
import base64
import requests
from supabase import create_client, Client

# --- 1. 网页基本设置 ---
st.set_page_config(page_title="AI 智能食谱与健康管理师", page_icon="🥗", layout="wide")
st.title("🥗 AI 智能食谱与健康社区 (Beta)")

# --- 2. 初始化全局登录状态 (Session 记忆) ---
if 'user' not in st.session_state:
    st.session_state.user = None

# --- 3. 数据库初始化连接 ---
@st.cache_resource
def init_connection():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

try:
    supabase: Client = init_connection()
    db_connected = True
except Exception:
    db_connected = False

# --- 4. 侧边栏：用户中心与系统状态 ---
with st.sidebar:
    st.header("🔐 用户中心")
    
    # 如果已经登录，显示欢迎语和退出按钮
    if st.session_state.user:
        st.success(f"👤 欢迎回来：{st.session_state.user}")
        if st.button("退出登录"):
            st.session_state.user = None
            st.rerun()
    # 如果未登录，显示登录和注册选项卡
    else:
        tab_login, tab_reg = st.tabs(["快速登录", "注册新号"])
        
        with tab_login:
            log_name = st.text_input("用户名", key="log_name")
            log_pwd = st.text_input("密码", type="password", key="log_pwd")
            if st.button("登录系统", type="primary", use_container_width=True):
                if log_name and log_pwd:
                    # 去数据库比对账号密码
                    res = supabase.table('app_users').select('*').eq('username', log_name).eq('password', log_pwd).execute()
                    if res.data:
                        st.session_state.user = log_name
                        st.rerun()
                    else:
                        st.error("❌ 账号或密码错误！")
                else:
                    st.warning("请输入账号和密码")
                    
        with tab_reg:
            reg_name = st.text_input("设置用户名", key="reg_name")
            reg_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
            if st.button("立即注册", use_container_width=True):
                if reg_name and reg_pwd:
                    # 检查用户名是否被占用
                    exist = supabase.table('app_users').select('*').eq('username', reg_name).execute()
                    if exist.data:
                        st.error("⚠️ 该用户名已被注册，换一个吧！")
                    else:
                        # 写入新用户
                        supabase.table('app_users').insert({"username": reg_name, "password": reg_pwd}).execute()
                        st.success("✅ 注册成功！请切换到【快速登录】页进行登录。")
                else:
                    st.warning("请输入想要设置的账号和密码")

    st.markdown("---")
    st.header("⚙️ 系统状态")
    try:
        api_key = st.secrets["ALIYUN_API_KEY"]
        st.success("✅ AI 引擎已全功率运行！")
    except Exception:
        api_key = ""
        st.error("⚠️ 云端保密柜未配置 API Key。")
        st.stop()

# --- 5. 通用 AI 调用函数 ---
def ask_ai_text(system_prompt, user_prompt, key):
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = {
        "model": "qwen-plus",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ AI 开小差了: {str(e)}"

def ask_ai_vision(image_bytes, user_prompt, key):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = {
        "model": "qwen-vl-plus",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": user_prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
    }
    try:
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ 视觉系统错误: {str(e)}"

# --- 6. 核心界面划分 ---
tab1, tab2, tab3, tab4 = st.tabs(["📸 功能1: 看图出菜谱", "💬 功能2: 健康问答区", "⚖️ 功能3: 三餐热量精算", "🏘️ 功能4: 美食交流社区"])

with tab1:
    st.subheader("冰箱里有什么？拍张照，AI 帮你做大餐！")
    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded_file = st.file_uploader("上传食材照片", type=['jpg', 'jpeg', 'png'])
        user_preference = st.text_input("有什么特殊要求吗？", placeholder="例如：我想吃辣的")
    with col2:
        if uploaded_file:
            st.image(uploaded_file, caption="待处理食材", use_container_width=True)

    if st.button("🍳 开始生成专属菜谱", type="primary"):
        if not uploaded_file:
            st.warning("请先上传一张食材照片！")
        else:
            with st.spinner("👨‍🍳 AI 厨师正在识别食材并构思菜谱..."):
                prompt = f"你是一个顶尖的营养大厨。请先识别这张图片里的主要食材。然后，根据用户的额外要求：【{user_preference}】，给出 2 种你可以用这些食材做出的菜谱。菜谱需要包含：菜名、营养亮点、简单步骤。"
                image_bytes = uploaded_file.getvalue()
                result = ask_ai_vision(image_bytes, prompt, api_key)
                st.success("菜谱生成完毕！")
                st.markdown(result)

with tab2:
    st.subheader("👩‍⚕️ 你的私人营养学专家 24 小时在线")
    question = st.text_area("你想问什么？", height=100)
    if st.button("💡 提交问题"):
        if not question:
            st.warning("你还没输入问题呢！")
        else:
            with st.spinner("正在查阅最新的健康营养文献..."):
                system_prompt = "你是一位专业的注册营养师（RD）。请用通俗易懂、科学严谨的语气回答用户的健康饮食问题。不要给出绝对的医疗诊断，但要给出有实操性的饮食建议。"
                answer = ask_ai_text(system_prompt, question, api_key)
                st.info("专家解答：")
                st.markdown(answer)

with tab3:
    st.subheader("📊 每日摄入精准测算与目标建议")
    st.markdown("#### 1. 完善你的身体档案")
    c1, c2, c3, c4 = st.columns(4)
    with c1: gender = st.selectbox("性别", ["男", "女"])
    with c2: height = st.number_input("身高 (cm)", value=170, step=1)
    with c3: weight = st.number_input("体重 (kg)", value=65.0, step=0.1)
    with c4: goal = st.selectbox("核心目标", ["减脂减肥", "增肌塑形", "维持现状", "改善三高"])

    st.markdown("#### 2. 记录你今天的三餐")
    meals_input = st.text_area("请详细描述你的三餐", height=150)

    if st.button("🔬 生成深度营养分析报告", type="primary"):
        if len(meals_input) < 5:
            st.warning("请多写一点你吃的东西！")
        else:
            with st.spinner("🧮 正在拆解五大营养素，计算热量差..."):
                system_prompt = "你是一个专业营养管理师。请根据用户的身体数据和饮食记录，提供一份专业的报告。"
                user_prompt = f"我的档案：性别{gender}，身高{height}cm，体重{weight}kg，目标是{goal}。我今天吃了这些：{meals_input}。"
                report = ask_ai_text(system_prompt, user_prompt, api_key)
                st.success("报告已生成！")
                st.markdown(report)

# ==========================================
# 功能 4: 美食交流社区 (动态账号系统验证)
# ==========================================
with tab4:
    st.subheader("🏘️ 美食交流社区 - 发现身边的神仙食谱")

    if not db_connected:
        st.warning("等待数据库连接中...")
    else:
        # --- 强制登录验证 ---
        if st.session_state.user is None:
            st.info("💡 请先在屏幕左侧边栏【🔐 用户中心】登录或注册账号，即可解锁发布功能！")
        else:
            with st.expander("✍️ 发布我的美食推荐 / 评价", expanded=True):
                # 账号系统生效：自动锁定发帖人为当前登录用户
                st.text_input("当前发布身份", value=st.session_state.user, disabled=True)
                dish_name = st.text_input("推荐菜品", placeholder="例如：空气炸锅版无油鸡腿")
                comment = st.text_area("你的评价", placeholder="这道菜绝了，热量低还解馋！")
                
                if st.button("🚀 发布内容", type="primary"):
                    if dish_name and comment:
                        supabase.table('comments').insert({
                            "user_name": st.session_state.user, 
                            "author_username": st.session_state.user, # 关联用户表
                            "dish_name": dish_name, 
                            "comment": comment, 
                            "likes": 0
                        }).execute()
                        st.success("发布成功！快去下方看看吧。")
                        st.rerun()
                    else:
                        st.warning("⚠️ 菜品和评价都必须填写哦！")

        st.markdown("---")
        st.markdown("### 🌟 社区最新动态 (所有人可见)")
        
        try:
            # 拉取留言数据
            response = supabase.table('comments').select("*").order('id', desc=True).execute()
            comments_data = response.data

            if not comments_data:
                st.info("目前还没有人发布推荐，快来抢沙发吧！")
            else:
                for row in comments_data:
                    with st.container():
                        st.markdown(f"**🧑‍🍳 {row['user_name']}** 推荐了：***《{row['dish_name']}》***")
                        st.write(f"💬 {row['comment']}")
                        
                        col1, col2 = st.columns([2, 10])
                        with col1:
                            if st.button(f"👍 赞 ({row['likes']})", key=f"like_{row['id']}"):
                                new_likes = row['likes'] + 1
                                supabase.table('comments').update({"likes": new_likes}).eq("id", row['id']).execute()
                                st.rerun()
                        st.markdown("---")
        except Exception as e:
            st.error(f"无法读取社区数据: {e}")
