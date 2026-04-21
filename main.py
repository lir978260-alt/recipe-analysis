import streamlit as st
import base64
import requests

# --- 网页基本设置 ---
st.set_page_config(page_title="AI 智能食谱与健康管理师", page_icon="🥗", layout="wide")
st.title("🥗 AI 智能食谱与健康社区 (Beta)")

# --- 侧边栏：全局配置 ---
with st.sidebar:
    st.header("⚙️ 系统配置")
    api_key = st.text_input("🔑 阿里云 API Key:", type="password")
    if not api_key:
        st.warning("⚠️ 请输入 API Key 以激活所有 AI 功能")
    st.markdown("---")
    st.write("📌 提示：社区交流与个人档案存储功能正在开发中 (Phase 2)...")

# --- 通用 AI 调用函数 (处理纯文本) ---
def ask_ai_text(system_prompt, user_prompt, key):
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = {
        "model": "qwen-plus", # 文本处理用通义千问 Plus
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
        "model": "qwen-vl-plus", # 图像识别专用模型
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
tab1, tab2, tab3 = st.tabs(["📸 功能1: 看图出菜谱", "💬 功能2: 健康问答区", "⚖️ 功能3: 三餐热量精算"])

# ==========================================
# 需求 1: 分析食材出菜谱
# ==========================================
with tab1:
    st.subheader("冰箱里有什么？拍张照，AI 帮你做大餐！")
    col1, col2 = st.columns([1, 1])

    with col1:
        uploaded_file = st.file_uploader("上传食材照片", type=['jpg', 'jpeg', 'png'])
        user_preference = st.text_input("有什么特殊要求吗？（例如：要清淡点、川菜口味、不吃香菜）", placeholder="例如：我想吃辣的")

    with col2:
        if uploaded_file:
            st.image(uploaded_file, caption="待处理食材", use_container_width=True)

    if st.button("🍳 开始生成专属菜谱", type="primary"):
        if not api_key:
            st.error("请先在左侧侧边栏填入 API Key！")
        elif not uploaded_file:
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
    question = st.text_area("你想问什么？（例如：熬夜后吃什么能快速恢复？喝黑咖啡真的能减肥吗？）", height=100)

    if st.button("💡 提交问题"):
        if not api_key:
            st.error("请先在左侧侧边栏填入 API Key！")
        elif not question:
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

    # 建立用户档案
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
    meals_input = st.text_area("请尽可能详细地描述（例如：早餐吃了两个水煮蛋和一杯燕麦奶；午餐吃了黄焖鸡米饭；晚餐吃了一根香蕉）", height=150)

    if st.button("🔬 生成深度营养分析报告", type="primary"):
        if not api_key:
            st.error("请先在左侧侧边栏填入 API Key！")
        elif len(meals_input) < 5:
            st.warning("请多写一点你吃的东西，不然 AI 没法算哦！")
        else:
            with st.spinner("🧮 正在拆解五大营养素，计算热量差..."):
                system_prompt = "你是一个专业营养管理师。请根据用户的身体数据和饮食记录，提供一份专业的报告。报告必须包含：1. 估算今天吃下的总热量（大卡）。2. 估算五大营养素（碳水、蛋白质、脂肪、维生素/矿物质、膳食纤维）的摄入比例。3. 基于用户的身体数据和【目标】，指出今天饮食的缺点，并给出明天怎么吃的具体建议。"
                user_prompt = f"我的档案：性别{gender}，身高{height}cm，体重{weight}kg，目标是{goal}。我今天吃了这些：{meals_input}。"

                report = ask_ai_text(system_prompt, user_prompt, api_key)
                st.success("报告已生成！")
                st.markdown(report)
