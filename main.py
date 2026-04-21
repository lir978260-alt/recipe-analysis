import streamlit as st
import base64
import requests
from supabase import create_client, Client

# --- 网页基本设置 ---
st.set_page_config(page_title="AI 智能食谱与健康管理师", page_icon="🥗", layout="wide")
st.title("🥗 AI 智能食谱与健康社区 (Beta)")

# --- 数据库初始化连接 ---
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

# --- 侧边栏：全局状态 ---
with st.sidebar:
    st.header("⚙️ 系统状态")
    try:
        api_key = st.secrets["ALIYUN_API_KEY"]
        st.success("✅ AI 引擎已全功率运行！")
    except Exception:
        api_key = ""
        st.error("⚠️ 云端保密柜未配置 API Key。")
        st.stop()
        
    if db_connected:
        st.success("✅ 社区数据库已连接上线！")
    else:
        st.error("⚠️ 数据库连接失败，请检查 Secrets 配置。")
        
    st.markdown("---")
    st.write("📌 提示：这是一个基于大模型的全栈营养管理应用。")

# --- 通用 AI 调用函数 (处理纯文本) ---
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

# --- 视觉 AI 调用函数 (处理图片) ---
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

# --- 核心界面划分 ---
tab1, tab2, tab3, tab4 = st.tabs(["📸 功能1: 看图出菜谱", "💬 功能2: 健康问答区", "⚖️ 功能3: 三餐热量精算", "🏘️ 功能4: 美食交流社区"])

# ==========================================
# 需求 1: 分析食材出菜谱
# ==========================================
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

# ==========================================
# 需求 2: AI 健康问答区
# ==========================================
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

# ==========================================
# 需求 3: 基于身体数据的三餐热量分析
# ==========================================
with tab3:
    st.subheader("📊 每日摄入精准测算与目标建议")

    st.markdown("#### 1. 完善你的身体档案")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        gender = st.selectbox("性别", ["男", "女"])
    with c2:
        height = st.number_input("身高 (cm)", value=170, step=1)
    with c3:
        weight = st.number_input("体重 (kg)", value=65.0, step=0.1)
    with c4:
        goal = st.selectbox("核心目标", ["减脂减肥", "增肌塑形", "维持现状", "改善三高"])

    st.markdown("#### 2. 记录你今天的三餐")
    meals_input = st.text_area("请详细描述你的三餐", height=150)

    if st.button("🔬 生成深度营养分析报告", type="primary"):
        if len(meals_input) < 5:
            st.warning("请多写一点你吃的东西！")
        else:
            with st.spinner("🧮 正在拆解五大营养素，计算热量差..."):
                system_prompt = "你是一个专业营养管理师。请根据用户的身体数据和饮食记录，提供一份专业的报告。包含：1. 估算总热量。2. 五大营养素比例。3. 饮食缺点及明天建议。"
                user_prompt = f"我的档案：性别{gender}，身高{height}cm，体重{weight}kg，目标是{goal}。我今天吃了这些：{meals_input}。"
                report = ask_ai_text(system_prompt, user_prompt, api_key)
                st.success("报告已生成！")
                st.markdown(report)

# ==========================================
# 需求 4: 美食交流社区 (动态数据库支持)
# ==========================================
with tab4:
    st.subheader("🏘️ 美食交流社区 - 发现身边的神仙食谱")

    if not db_connected:
        st.warning("等待数据库连接中...")
    else:
        # 1. 顶部发布区
        with st.expander("✍️ 点击发布我的美食推荐 / 评价", expanded=True):
            user_name = st.text_input("你的昵称", placeholder="例如：减脂小达人")
            dish_name = st.text_input("推荐菜品 / 讨论话题", placeholder="例如：空气炸锅版无油鸡腿")
            comment = st.text_area("你的评价或心得", placeholder="这道菜绝了，热量低还解馋！强烈推荐大家试试。")
            
            if st.button("🚀 发布内容", type="primary"):
                if user_name and dish_name and comment:
                    # 将数据写入数据库
                    supabase.table('comments').insert({
                        "user_name": user_name, 
                        "dish_name": dish_name, 
                        "comment": comment, 
                        "likes": 0
                    }).execute()
                    st.success("发布成功！快去下方看看吧。")
                    st.rerun() # 自动刷新网页显示最新留言
                else:
                    st.warning("⚠️ 昵称、菜品和评价都必须填写哦！")

        st.markdown("---")
        
        # 2. 下方展示区与互动区
        st.markdown("### 🌟 社区最新动态")
        
        try:
            # 按照时间倒序拉取所有留言
            response = supabase.table('comments').select("*").order('id', desc=True).execute()
            comments_data = response.data

            if not comments_data:
                st.info("目前还没有人发布推荐，快来抢沙发吧！")
            else:
                for row in comments_data:
                    with st.container():
                        st.markdown(f"**🧑‍🍳 {row['user_name']}** 推荐了：***《{row['dish_name']}》***")
                        st.write(f"💬 {row['comment']}")
                        
                        # 点赞按钮
                        col1, col2 = st.columns([1, 10])
                        with col1:
                            if st.button(f"👍 赞 ({row['likes']})", key=f"like_{row['id']}"):
                                new_likes = row['likes'] + 1
                                supabase.table('comments').update({"likes": new_likes}).eq("id", row['id']).execute()
                                st.rerun()
                        st.markdown("---")
        except Exception as e:
            st.error(f"无法读取社区数据: {e}")
