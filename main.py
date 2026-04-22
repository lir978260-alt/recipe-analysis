import streamlit as st
import base64
import requests
import pandas as pd
from datetime import datetime, date
from supabase import create_client, Client

# --- 1. 网页基本设置 ---
st.set_page_config(page_title="AI 智能食谱与健康社区", page_icon="🥗", layout="wide")
st.title("🥗 AI 智能食谱与健康社区 (V2.0)")

# --- 2. 初始化全局状态 ---
if 'user' not in st.session_state:
    st.session_state.user = None

@st.cache_resource
def init_connection():
    return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])

try:
    supabase: Client = init_connection()
    db_connected = True
except Exception:
    db_connected = False

# --- 3. 侧边栏：用户中心 ---
with st.sidebar:
    st.header("🔐 用户中心")
    if st.session_state.user:
        st.success(f"👤 欢迎回来：{st.session_state.user}")
        if st.button("退出登录"):
            st.session_state.user = None
            st.rerun()
    else:
        tab_login, tab_reg = st.tabs(["快速登录", "注册新号"])
        with tab_login:
            log_name = st.text_input("用户名", key="log_name")
            log_pwd = st.text_input("密码", type="password", key="log_pwd")
            if st.button("登录系统", type="primary", use_container_width=True):
                res = supabase.table('app_users').select('*').eq('username', log_name).eq('password', log_pwd).execute()
                if res.data:
                    st.session_state.user = log_name
                    st.rerun()
                else:
                    st.error("❌ 账号或密码错误！")
        with tab_reg:
            reg_name = st.text_input("设置用户名", key="reg_name")
            reg_pwd = st.text_input("设置密码", type="password", key="reg_pwd")
            if st.button("立即注册", use_container_width=True):
                exist = supabase.table('app_users').select('*').eq('username', reg_name).execute()
                if exist.data:
                    st.error("⚠️ 用户名已被注册！")
                else:
                    supabase.table('app_users').insert({"username": reg_name, "password": reg_pwd}).execute()
                    st.success("✅ 注册成功！请切换到【快速登录】页登录。")

    st.markdown("---")
    try:
        api_key = st.secrets["ALIYUN_API_KEY"]
        st.success("✅ AI 引擎全功率运行中")
    except Exception:
        api_key = ""
        st.error("⚠️ AI 秘钥缺失")

# --- 4. AI 引擎函数 ---
def ask_ai_text(system_prompt, user_prompt, key):
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = {"model": "qwen-plus", "messages": [{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}]}
    try:
        return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ AI 开小差了: {str(e)}"

def ask_ai_vision(image_bytes, user_prompt, key):
    base64_image = base64.b64encode(image_bytes).decode('utf-8')
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    headers = {'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'}
    data = {"model": "qwen-vl-plus", "messages": [{"role": "user", "content": [{"type": "text", "text": user_prompt}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}]}]}
    try:
        return requests.post(url, headers=headers, json=data).json()['choices'][0]['message']['content']
    except Exception as e:
        return f"❌ 视觉系统错误: {str(e)}"

# --- 5. 核心界面划分 ---
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📸 看图出菜谱", "💬 健康问答区", "📈 饮食与体重追踪", "🏘️ 互动社区", "👤 我的主页"])

# ==========================================
# Tab 1: 看图出菜谱 (+ 收藏功能)
# ==========================================
with tab1:
    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded_file = st.file_uploader("上传食材照片", type=['jpg', 'jpeg', 'png'])
        user_preference = st.text_input("有什么特殊要求吗？", placeholder="例如：我想吃辣的")
    with col2:
        if uploaded_file: st.image(uploaded_file, use_container_width=True)

    if st.button("🍳 开始生成专属菜谱", type="primary"):
        if not uploaded_file:
            st.warning("请先上传一张食材照片！")
        else:
            with st.spinner("👨‍🍳 AI 厨师正在思考..."):
                prompt = f"识别图片食材，根据要求：【{user_preference}】，给出 2 种菜谱。包含：菜名、营养、步骤。"
                result = ask_ai_vision(uploaded_file.getvalue(), prompt, api_key)
                st.session_state['last_recipe'] = result # 暂存下来用于收藏
                st.markdown(result)
                
    if 'last_recipe' in st.session_state and st.session_state.user:
        if st.button("⭐️ 保存这篇食谱到我的主页"):
            supabase.table('favorites').insert({"username": st.session_state.user, "recipe_name": "AI 智能菜谱", "recipe_content": st.session_state['last_recipe']}).execute()
            st.success("✅ 收藏成功！去【👤 我的主页】查看吧！")

# ==========================================
# Tab 2: 健康问答区
# ==========================================
with tab2:
    question = st.text_area("你想问什么健康问题？", height=100)
    if st.button("💡 提交问题"):
        if question:
            with st.spinner("正在查阅文献..."):
                ans = ask_ai_text("你是一位专业的注册营养师（RD）。", question, api_key)
                st.markdown(ans)

# ==========================================
# Tab 3: 饮食与体重追踪
# ==========================================
with tab3:
    if not st.session_state.user:
        st.warning("⚠️ 追踪记录和生成周报功能需要登录后使用！")
    else:
        c1, c2 = st.columns([1, 2])
        with c1:
            st.subheader("📝 今日打卡")
            log_date = st.date_input("日期", value=date.today())
            weight = st.number_input("今日空腹体重 (kg)", value=60.0, step=0.1)
            calories = st.number_input("今日总摄入预估 (千卡)", value=1500, step=50)
            meals = st.text_area("三餐记录(可选)", placeholder="例如：早：水煮蛋；中：沙拉...")
            if st.button("✅ 记录今日数据", type="primary"):
                existing = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).eq('log_date', str(log_date)).execute()
                if existing.data:
                    supabase.table('diet_logs').update({"weight": weight, "calories": calories, "meals_record": meals}).eq('id', existing.data[0]['id']).execute()
                else:
                    supabase.table('diet_logs').insert({"username": st.session_state.user, "log_date": str(log_date), "weight": weight, "calories": calories, "meals_record": meals}).execute()
                st.success("记录成功！")

        with c2:
            st.subheader("📊 我的趋势")
            logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date').execute().data
            if logs:
                df = pd.DataFrame(logs)
                df['log_date'] = pd.to_datetime(df['log_date'])
                df.set_index('log_date', inplace=True)
                
                tab_w, tab_c = st.tabs(["📉 体重曲线", "🔥 热量曲线"])
                with tab_w: st.line_chart(df['weight'], color="#FF4B4B")
                with tab_c: st.line_chart(df['calories'], color="#0068C9")
            else:
                st.info("暂无数据，快去左侧打卡吧！")

        st.markdown("---")
        st.subheader("🤖 AI 营养师周报")
        if st.button("生成近期饮食『红黑榜』诊断书"):
            if len(logs) < 3:
                st.warning("数据太少啦，至少需要打卡 3 天才能生成精准报告哦！")
            else:
                with st.spinner("AI 正在深度分析你最近的饮食结构和体重变化..."):
                    logs_str = "\n".join([f"日期:{r['log_date']}, 体重:{r['weight']}kg, 摄入:{r['calories']}kcal, 饮食:{r['meals_record']}" for r in logs[-7:]])
                    prompt = f"你是严厉但专业的AI营养师。这是用户最近几天的数据：\n{logs_str}\n请给出一份周报，包含：1.体重与热量趋势分析。2.饮食红黑榜。3.下周实操建议。语气活泼犀利。"
                    report = ask_ai_text("你是一个顶尖营养师", prompt, api_key)
                    st.markdown(report)

# ==========================================
# Tab 4: 互动社区
# ==========================================
with tab4:
    if st.session_state.user is None:
        st.warning("⚠️ 登录后解锁发帖、点赞与收藏功能！")
    
    st.markdown("### 🔥 本周最热榜")
    top_posts = supabase.table('comments').select('*').order('likes', desc=True).limit(3).execute().data
    if top_posts:
        cols = st.columns(3)
        medals = ["🥇", "🥈", "🥉"]
        for idx, col in enumerate(cols):
            if idx < len(top_posts):
                with col:
                    st.info(f"{medals[idx]} **{top_posts[idx]['user_name']}**\n\n《{top_posts[idx]['dish_name']}》\n\n👍 {top_posts[idx]['likes']} 赞")
    
    st.markdown("---")

    if st.session_state.user:
        with st.expander("✍️ 发布新动态", expanded=False):
            tag_choice = st.selectbox("选择标签", ["#日常分享", "#减脂期神仙菜", "#宿舍党快手菜", "#欺骗餐警报"])
            dish_name = st.text_input("菜品 / 标题")
            comment = st.text_area("内容")
            if st.button("🚀 马上发布"):
                if dish_name and comment:
                    supabase.table('comments').insert({"user_name": st.session_state.user, "author_username": st.session_state.user, "dish_name": dish_name, "comment": comment, "likes": 0, "liked_by": [], "tag": tag_choice}).execute()
                    st.success("发布成功！")
                    st.rerun()

    st.markdown("### 🌟 最新动态")
    filter_tag = st.radio("筛选板块", ["全部", "#日常分享", "#减脂期神仙菜", "#宿舍党快手菜", "#欺骗餐警报"], horizontal=True)
    
    query = supabase.table('comments').select("*").order('id', desc=True)
    if filter_tag != "全部":
        query = query.eq('tag', filter_tag)
        
    comments_data = query.execute().data

    for row in comments_data:
        with st.container(border=True):
            st.markdown(f"**🧑‍🍳 {row['user_name']}** `{row.get('tag', '#日常分享')}`\n### {row['dish_name']}")
            st.write(f"{row['comment']}")
            
            c1, c2, c3 = st.columns([2, 2, 8])
            liked_by_list = row.get('liked_by') or []
            has_liked = st.session_state.user in liked_by_list if st.session_state.user else False
            
            with c1:
                if st.button(f"💖 已赞({row['likes']})" if has_liked else f"👍 赞({row['likes']})", key=f"lk_{row['id']}", disabled=(not st.session_state.user or has_liked)):
                    new_likes = row['likes'] + 1
                    liked_by_list.append(st.session_state.user)
                    supabase.table('comments').update({"likes": new_likes, "liked_by": liked_by_list}).eq("id", row['id']).execute()
                    st.rerun()
                    
            with c2:
                if st.session_state.user:
                    is_fav = supabase.table('favorites').select('id').eq('username', st.session_state.user).eq('post_id', row['id']).execute().data
                    if st.button("⭐️ 已收藏" if is_fav else "⭐ 收藏", key=f"fv_{row['id']}", disabled=bool(is_fav)):
                        supabase.table('favorites').insert({"username": st.session_state.user, "post_id": row['id']}).execute()
                        st.rerun()

# ==========================================
# Tab 5: 个人主页
# ==========================================
with tab5:
    if not st.session_state.user:
        st.warning("⚠️ 登录后即可查看个人主页！")
    else:
        st.header(f"👑 {st.session_state.user} 的主页")
        t_mine, t_fav = st.tabs(["✍️ 我发布的", "⭐️ 我的收藏"])
        
        with t_mine:
            my_posts = supabase.table('comments').select('*').eq('author_username', st.session_state.user).order('id', desc=True).execute().data
            if my_posts:
                for p in my_posts:
                    st.info(f"**《{p['dish_name']}》** | 👍 {p['likes']} 赞 \n\n {p['comment']}")
            else:
                st.write("还没发布过动态哦~")
                
        with t_fav:
            favs = supabase.table('favorites').select('*').eq('username', st.session_state.user).order('id', desc=True).execute().data
            if favs:
                for f in favs:
                    if f.get('post_id'):
                        post = supabase.table('comments').select('dish_name', 'user_name').eq('id', f['post_id']).execute().data
                        if post:
                            st.success(f"📌 收藏了 **{post[0]['user_name']}** 的帖子：**《{post[0]['dish_name']}》**")
                    elif f.get('recipe_content'):
                        with st.expander(f"📖 收藏的AI菜谱 (保存于 {f['created_at'][:10]})"):
                            st.markdown(f['recipe_content'])
            else:
                st.write("收藏夹空空如也~去社区逛逛吧！")
