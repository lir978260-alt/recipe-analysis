import streamlit as st
import base64, requests, json
import pandas as pd
from datetime import datetime, date, timedelta
from supabase import create_client
import extra_streamlit_components as stx

# ==========================================
# 0. 全局状态与基础自适应配置 (彻底去红化)
# ==========================================
st.set_page_config(page_title="AI Health Ecosystem", page_icon="☁️", layout="wide", initial_sidebar_state="collapsed")

for k in ['user', 'editing_id']:
    if k not in st.session_state: st.session_state[k] = None
if 'current_page' not in st.session_state: st.session_state.current_page = "Home"
if 'lang' not in st.session_state: st.session_state.lang = "🇨🇳 简体中文"

# 恢复默认主题并彻底摒弃红色元素
if 'theme' not in st.session_state: st.session_state.theme = "☁️ 云朵白 (Cloud Light)"

if 'need_set_cookie' not in st.session_state: st.session_state.need_set_cookie = False
if 'need_del_cookie' not in st.session_state: st.session_state.need_del_cookie = False
if 'logout_flag' not in st.session_state: st.session_state.logout_flag = False

cookie_manager = stx.CookieManager(key="cookie_manager")

if st.session_state.need_set_cookie:
    cookie_manager.set("saved_user", st.session_state.user, expires_at=datetime.now() + timedelta(days=30))
    st.session_state.need_set_cookie = False

if st.session_state.need_del_cookie:
    cookie_manager.delete("saved_user")
    st.session_state.need_del_cookie = False

saved_user = cookie_manager.get(cookie="saved_user")
if saved_user and st.session_state.user is None and not st.session_state.logout_flag:
    st.session_state.user = saved_user
    st.rerun()

# ==========================================
# 1. 双语字典引擎 (i18n)
# ==========================================
i18n = {
    "🇨🇳 简体中文": {
        "sys_lang": "简体中文", "title": "AI 健康全生态", "login": "登录", "set": "设置", "back": "返回大厅",
        "m1": "☁️ AI 智能后厨\n\n看图出菜 · 专家问答", "m2": "🏘️ 美食广场社区\n\n热力排行 · 广场互动",
        "m3": "📈 健康数据管家\n\n数据打卡 · AI 周报", "m4": "👤 我的专属主页\n\n发布记录 · 收藏中心",
        "k_t": "☁️ AI 智能后厨", "k_t1": "📸 看图出菜谱", "k_t2": "💬 营养师问答", "up": "上传食材照片",
        "req": "口味要求 (可选)", "gen": "生成菜谱", "fav": "⭐️ 收藏此篇", "ask": "向营养师提问",
        "up_opt": "上传参考图片 (可选)", "think": "数据传输中...",
        "h_t": "📈 健康数据管家", "h_t1": "📝 数据录入", "h_t2": "📊 分析报告", "d": "选择日期", "w": "体重 (kg)",
        "b": "早餐记录", "l": "午餐记录", "dn": "晚餐记录", "sub": "提交并计算热量", "del": "删除", "edit": "修改",
        "c_t": "🏘️ 美食广场社区", "c_t1": "🔥 热力榜", "c_t2": "💬 交流大厅", "pub": "✨ 发布动态", "like": "赞",
        "tag": "选择标签", "title_in": "输入标题", "desc_in": "输入内容", "log_req": "⚠️ 请先登录",
        "u_t": "👤 我的主页", "u_t1": "📜 历史发布", "u_t2": "⭐ 收藏夹",
        "err": "账号或密码错误", "suc": "操作成功", "out": "退出登录", "reg": "注册新号", "no_data": "暂无数据",
        "id_in": "输入账号", "pwd_in": "输入密码", "new_id": "设置新账号", "new_pwd": "设置新密码", "confirm": "确认",
        "unfav": "🤍 取消收藏", "del_post": "🗑️ 删除此贴", "reply": "💬 回复", "reply_ph": "写下回复...", "send": "发送",
        # 新增推荐榜单词汇
        "rec_dish": "🍲 推荐神仙菜品", "rec_btn": "👍 推荐/投票", "rec_ph": "输入你想推荐的菜名...", 
        "voted": "⚠️ 你已经给这道菜投过票啦！", "votes": "票"
    },
    "🇬🇧 English": {
        "sys_lang": "English", "title": "AI Health Ecosystem", "login": "Login", "set": "Settings", "back": "Back to Home",
        "m1": "☁️ AI Kitchen\n\nRecipes & Q&A", "m2": "🏘️ Community\n\nTrending & Social",
        "m3": "📈 Health Tracker\n\nDaily Log & AI Report", "m4": "👤 My Profile\n\nHistory & Favs",
        "k_t": "☁️ AI Kitchen", "k_t1": "📸 Image to Recipe", "k_t2": "💬 Dietitian Q&A", "up": "Upload Ingredients",
        "req": "Preferences (Optional)", "gen": "Generate Recipe", "fav": "⭐️ Save Recipe", "ask": "Ask Dietitian",
        "up_opt": "Upload Image (Optional)", "think": "Transmitting data...",
        "h_t": "📈 Health Tracker", "h_t1": "📝 Data Entry", "h_t2": "📊 Analytics", "d": "Date", "w": "Weight (kg)",
        "b": "Breakfast Log", "l": "Lunch Log", "dn": "Dinner Log", "sub": "Submit & Calc Calories", "del": "Delete", "edit": "Edit",
        "c_t": "🏘️ Community Square", "c_t1": "🔥 Trending", "c_t2": "💬 Discussion", "pub": "✨ Publish", "like": "Like",
        "tag": "Select Tag", "title_in": "Enter Title", "desc_in": "Enter Details", "log_req": "⚠️ Please login first",
        "u_t": "👤 My Profile", "u_t1": "📜 My Posts", "u_t2": "⭐ Favorites",
        "err": "Invalid credentials", "suc": "Success", "out": "Logout", "reg": "Register", "no_data": "No data available",
        "id_in": "Enter ID", "pwd_in": "Enter Password", "new_id": "Create ID", "new_pwd": "Create Password", "confirm": "Confirm",
        "unfav": "🤍 Unfavorite", "del_post": "🗑️ Delete Post", "reply": "💬 Reply", "reply_ph": "Write a reply...", "send": "Send",
        # 新增推荐榜单词汇
        "rec_dish": "🍲 Recommend a Dish", "rec_btn": "👍 Vote/Suggest", "rec_ph": "Enter dish name...", 
        "voted": "⚠️ You already voted for this dish!", "votes": "votes"
    }
}
t = i18n[st.session_state.lang]

@st.cache_resource
def init_db(): return create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_KEY"])
try: supabase, api_key = init_db(), st.secrets["ALIYUN_API_KEY"]
except: st.error("Database connection failed."); st.stop()

# ==========================================
# 2. 自适应 CSS 引擎与色彩管理
# ==========================================
theme_colors = {
    "☁️ 云朵白 (Cloud Light)": {"bg": "#fcfcfd", "card": "#ffffff", "text": "#1d1d1f"},
    "🌌 暗夜黑 (Dark Mode)": {"bg": "#1c1c1e", "card": "#2c2c2e", "text": "#f5f5f7"},
    "🍃 抹茶绿 (Nature Mint)": {"bg": "#f4fbf6", "card": "#ffffff", "text": "#2d3a33"},
    "🌊 海洋蓝 (Ocean Blue)": {"bg": "#f4f9ff", "card": "#ffffff", "text": "#0a2540"}
}
c = theme_colors[st.session_state.theme]

st.markdown(f"""
    <style>
    header[data-testid="stHeader"], footer {{visibility: hidden !important;}}
    .stApp, .stApp > header {{ background-color: {c['bg']} !important; }}
    h1, h2, h3, h4, h5, h6, p, span, label, div[data-testid="stMarkdownContainer"] {{ color: {c['text']} !important; }}
    
    .block-container {{
        max-width: 1200px !important;
        padding-top: 2rem !important;
        padding-bottom: 2rem !important;
    }}
    
    div[data-testid="stButton"] > button {{ color: {c['text']} !important; border-color: rgba(150,150,150,0.3) !important; }}
    div[data-testid="stButton"] > button:disabled {{
        background-color: transparent !important; opacity: 0.4 !important; border: 1px solid rgba(150,150,150,0.2) !important;
    }}
    
    section[data-testid="stMain"] div.stButton > button[kind="primary"] {{
        min-height: 180px !important; 
        height: auto !important;
        padding: 1.5rem !important;
        border-radius: 24px !important; 
        background-color: {c['card']} !important;
        border: 1px solid rgba(0,0,0,0.06) !important; 
        box-shadow: 0 4px 12px rgba(0,0,0,0.03) !important;
        transition: all 0.3s ease-in-out !important; 
        width: 100% !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"]:hover {{
        transform: translateY(-6px) scale(1.01) !important; box-shadow: 0 12px 24px rgba(0,0,0,0.08) !important;
    }}
    section[data-testid="stMain"] div.stButton > button[kind="primary"] p {{
        font-size: clamp(1.1rem, 2vw, 1.4rem) !important; 
        font-weight: 600 !important; 
        line-height: 1.5 !important;
        white-space: pre-wrap !important; 
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 3. 流式 AI 引擎调用层
# ==========================================
def ask_ai_stream(sys_p, usr_p, img=None):
    usr_p += f"\n\n[CRITICAL INSTRUCTION: You must strictly output your entire response in {t['sys_lang']}! Do not use any other language.]"
    model = "qwen-vl-plus" if img else "qwen-plus"
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    h = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    
    msg_content = [{"type": "text", "text": usr_p}]
    if img:
        b64 = base64.b64encode(img).decode('utf-8')
        msg_content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}})
        
    data = {
        "model": model, 
        "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": msg_content}],
        "stream": True
    }
    
    try: 
        res = requests.post(url, headers=h, json=data, timeout=90, stream=True)
        for line in res.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                if line_str.startswith('data: ') and line_str != 'data: [DONE]':
                    try:
                        chunk = json.loads(line_str[6:])
                        delta = chunk['choices'][0]['delta'].get('content', '')
                        if delta:
                            yield delta
                    except: pass
    except Exception as e: 
        yield f"\n\nAI Network Error: {str(e)}"

def ask_ai_sync(sys_p, usr_p):
    model = "qwen-plus"
    url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
    h = {'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'}
    data = {"model": model, "messages": [{"role": "system", "content": sys_p}, {"role": "user", "content": usr_p}]}
    try: 
        res = requests.post(url, headers=h, json=data, timeout=30)
        return res.json()['choices'][0]['message']['content']
    except: return "0"

# ==========================================
# 4. 核心模块函数
# ==========================================
def m_kitchen():
    st.subheader(t['k_t'])
    t1, t2 = st.tabs([t['k_t1'], t['k_t2']])
    with t1:
        c1, c2 = st.columns(2)
        up, pref = c1.file_uploader(t['up'], type=['jpg', 'png'], key="f1"), c1.text_input(t['req'])
        if up: c2.image(up, use_column_width=True)
        if st.button(t['gen']) and up:
            with st.spinner(t['think']):
                res = st.write_stream(ask_ai_stream("You are a Master Chef.", f"Identify the ingredients and generate a highly professional recipe. Requirements: {pref}", up.getvalue()))
                st.session_state['l_rec'] = res
        if st.session_state.get('l_rec') and st.session_state.user and st.button(t['fav']):
            try:
                supabase.table('favorites').insert({"username": st.session_state.user, "recipe_content": st.session_state['l_rec']}).execute()
                st.success(t['suc'])
            except Exception as e: st.error(f"DB Error: {e}")
    with t2:
        up_nutri = st.file_uploader(t['up_opt'], type=['jpg', 'png'], key="f2")
        if up_nutri: st.image(up_nutri, use_column_width=True)
        q = st.text_area(t['ask'])
        if st.button(t['confirm']) and q:
            with st.spinner(t['think']):
                st.write_stream(ask_ai_stream("You are a highly professional Dietitian.", q, up_nutri.getvalue() if up_nutri else None))

def m_health():
    if not st.session_state.user: 
        st.session_state.current_page = "Login"; st.rerun()
        
    st.subheader(t['h_t'])
    t1, t2 = st.tabs([t['h_t1'], t['h_t2']])
    with t1:
        with st.form("d_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            d, w = c1.date_input(t['d'], date.today()), c2.number_input(t['w'], 60.0, step=0.1)
            b, l, dn = st.text_input(t['b']), st.text_input(t['l']), st.text_input(t['dn'])
            if st.form_submit_button(t['sub'], type="primary"):
                cal = int(''.join(filter(str.isdigit, ask_ai_sync("Nutrition Calculator", f"Estimate total calories. Return ONLY an integer: Breakfast:{b} Lunch:{l} Dinner:{dn}"))) or 0)
                payload = {"username": st.session_state.user, "log_date": str(d), "weight": w, "calories": cal, "breakfast": b, "lunch": l, "dinner": dn}
                try:
                    if st.session_state.editing_id: supabase.table('diet_logs').update(payload).eq('id', st.session_state.editing_id).execute(); st.session_state.editing_id = None
                    else: supabase.table('diet_logs').insert(payload).execute()
                    st.rerun()
                except Exception as e: st.error(f"DB Error: {e}")
                    
        for r in supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date', desc=True).execute().data:
            with st.expander(f"{r['log_date']} | {r['weight']}kg | {r['calories']}kcal"):
                st.write(f"{t['b']}:{r.get('breakfast','')} {t['l']}:{r.get('lunch','')} {t['dn']}:{r.get('dinner','')}")
                ce, cd = st.columns(2)
                if ce.button(t['edit'], key=f"e_{r['id']}"): st.session_state.editing_id = r['id']; st.rerun()
                if cd.button(t['del'], key=f"d_{r['id']}"): 
                    try: supabase.table('diet_logs').delete().eq('id', r['id']).execute(); st.rerun()
                    except Exception as e: st.error(f"DB Error: {e}")
    with t2:
        logs = supabase.table('diet_logs').select('*').eq('username', st.session_state.user).order('log_date').execute().data
        if logs: 
            df = pd.DataFrame(logs); df['log_date'] = pd.to_datetime(df['log_date']); df.set_index('log_date', inplace=True)
            st.line_chart(df[['weight', 'calories']])
        else: st.info(t['no_data'])

def m_community():
    st.subheader(t['c_t'])
    t1, t2 = st.tabs([t['c_t1'], t['c_t2']])
    
    # 【核心重构】：菜品推荐排行榜功能
    with t1:
        # 展示排名前5的神仙菜品
        top_dishes = supabase.table('dish_ranking').select('*').order('votes', desc=True).limit(5).execute().data
        if top_dishes:
            for i, d in enumerate(top_dishes): 
                st.success(f"🏆 NO.{i+1} **{d['dish_name']}** —— {d['votes']} {t['votes']}")
        else:
            st.info(t['no_data'])
            
        st.markdown("---")
        st.markdown(f"#### {t['rec_dish']}")
        
        # 推荐菜品交互逻辑
        if st.session_state.user:
            c_input, c_btn = st.columns([3, 1])
            new_dish = c_input.text_input("hidden_label", label_visibility="collapsed", placeholder=t['rec_ph'])
            if c_btn.button(t['rec_btn'], use_container_width=True) and new_dish:
                dish_clean = new_dish.strip()
                if dish_clean:
                    try:
                        # 检查菜品是否已存在
                        exist = supabase.table('dish_ranking').select('*').eq('dish_name', dish_clean).execute().data
                        if exist:
                            record = exist[0]
                            voters = record.get('voted_by', [])
                            if not isinstance(voters, list): voters = []
                            # 查重防止重复投票
                            if st.session_state.user in voters:
                                st.warning(t['voted'])
                            else:
                                voters.append(st.session_state.user)
                                supabase.table('dish_ranking').update({"votes": record['votes'] + 1, "voted_by": voters}).eq('id', record['id']).execute()
                                st.rerun()
                        else:
                            # 插入新菜品
                            supabase.table('dish_ranking').insert({"dish_name": dish_clean, "votes": 1, "voted_by": [st.session_state.user]}).execute()
                            st.rerun()
                    except Exception as e:
                        st.error(f"DB Error: {e}")
        else:
            st.info(t['log_req'])

    # 交流大厅保持原样，互不影响
    with t2:
        if st.session_state.user:
            with st.expander(t['pub']):
                tag, dish, cont = st.selectbox(t['tag'], ["#Daily", "#Diet", "#Yummy"] if t['sys_lang']=="English" else ["#日常", "#减脂", "#神仙菜"]), st.text_input(t['title_in']), st.text_area(t['desc_in'])
                if st.button(t['confirm']) and dish:
                    try:
                        supabase.table('comments').insert({"user_name": st.session_state.user, "author_username": st.session_state.user, "dish_name": dish, "comment": cont, "likes": 0, "liked_by": [], "tag": tag, "replies": []}).execute()
                        st.rerun()
                    except Exception as e: st.error(f"Publish Failed: {str(e)}")
        else: st.info(t['log_req'])

        for r in supabase.table('comments').select("*").order('id', desc=True).execute().data:
            with st.container(border=True):
                st.write(f"**{r['user_name']}** | 🏷️ {r['tag']}\n### {r['dish_name']}\n{r['comment']}")
                
                lk = r.get('liked_by')
                if not isinstance(lk, list): lk = [] 
                has_liked = (st.session_state.user in lk) if st.session_state.user else False
                if st.button(f"{t['like']} ({r.get('likes', 0)})", key=f"l_{r['id']}", disabled=(not st.session_state.user or has_liked)):
                    lk.append(st.session_state.user)
                    try:
                        supabase.table('comments').update({"likes": int(r.get('likes', 0))+1, "liked_by": lk}).eq("id", r['id']).execute()
                        st.rerun()
                    except: pass
                
                reps = r.get('replies')
                if not isinstance(reps, list): reps = []
                if len(reps) > 0:
                    st.markdown("---")
                    for rep in reps: st.caption(f"💬 **{rep.get('u', 'User')}**: {rep.get('t', '')}")
                
                if st.session_state.user:
                    with st.expander(t['reply']):
                        rep_text = st.text_input(t['reply_ph'], key=f"rt_{r['id']}")
                        if st.button(t['send'], key=f"rs_{r['id']}") and rep_text:
                            reps.append({"u": st.session_state.user, "t": rep_text})
                            try:
                                supabase.table('comments').update({"replies": reps}).eq("id", r['id']).execute()
                                st.rerun()
                            except Exception as e: st.error(f"Reply Failed: {e}")

def m_user():
    if not st.session_state.user: 
        st.session_state.current_page = "Login"; st.rerun()
        
    st.subheader(t['u_t'])
    t1, t2 = st.tabs([t['u_t1'], t['u_t2']])
    
    with t1:
        my_posts = supabase.table('comments').select('*').eq('author_username', st.session_state.user).order('id', desc=True).execute().data
        if not my_posts: st.info(t['no_data'])
        for p in my_posts: 
            with st.container(border=True):
                st.info(f"**{p['dish_name']}**\n{p['comment']}")
                if st.button(t['del_post'], key=f"dp_{p['id']}"):
                    try:
                        supabase.table('comments').delete().eq('id', p['id']).execute()
                        st.rerun()
                    except Exception as e: st.error(f"Delete Failed: {e}")
                    
    with t2:
        favs = supabase.table('favorites').select('*').eq('username', st.session_state.user).order('id', desc=True).execute().data
        if not favs: st.info(t['no_data'])
        for f in favs:
            with st.container(border=True):
                if f.get('recipe_content'): 
                    with st.expander(t['fav']): st.markdown(f['recipe_content'])
                if st.button(t['unfav'], key=f"uf_{f['id']}"):
                    try:
                        supabase.table('favorites').delete().eq('id', f['id']).execute()
                        st.rerun()
                    except Exception as e: st.error(f"Unfavorite Failed: {e}")

# ==========================================
# 5. 路由导航与设置界面
# ==========================================
if st.session_state.current_page == "Home":
    c_title, c_log, c_set = st.columns([8, 2, 2])
    c_title.markdown(f"<h2 style='margin-top:-10px;'>{t['title']}</h2>", unsafe_allow_html=True)
    if c_log.button(f"👤 {st.session_state.user}" if st.session_state.user else f"👤 {t['login']}", use_container_width=True): st.session_state.current_page = "Login"; st.rerun()
    if c_set.button(f"⚙️ {t['set']}", use_container_width=True): st.session_state.current_page = "Settings"; st.rerun()
    st.write("\n\n")
    
    c1, c2 = st.columns(2, gap="medium")
    if c1.button(t['m1'], type="primary", use_container_width=True): st.session_state.current_page = "A"; st.rerun()
    if c1.button(t['m2'], type="primary", use_container_width=True): st.session_state.current_page = "C"; st.rerun()
    if c2.button(t['m3'], type="primary", use_container_width=True): st.session_state.current_page = "B"; st.rerun()
    if c2.button(t['m4'], type="primary", use_container_width=True): st.session_state.current_page = "D"; st.rerun()

elif st.session_state.current_page == "Login":
    if st.button(t['back']): st.session_state.current_page = "Home"; st.rerun()
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.user:
            st.success(f"{t['suc']}：{st.session_state.user}")
            if st.button(t['out'], use_container_width=True): 
                st.session_state.user = None
                st.session_state.need_del_cookie = True
                st.session_state.logout_flag = True
                st.rerun()
        else:
            tb1, tb2 = st.tabs([t['login'], t['reg']])
            with tb1:
                u, p = st.text_input(t['id_in']), st.text_input(t['pwd_in'], type="password")
                if st.button(t['confirm'], key="btn_login", use_container_width=True):
                    try:
                        if supabase.table('app_users').select('*').eq('username', u).eq('password', p).execute().data: 
                            st.session_state.user = u
                            st.session_state.need_set_cookie = True
                            st.session_state.logout_flag = False
                            st.session_state.current_page = "Home"
                            st.rerun()
                        else: st.error(t['err'])
                    except Exception as e: st.error(f"DB Error: {e}")
            with tb2:
                nu, np = st.text_input(t['new_id']), st.text_input(t['new_pwd'], type="password")
                if st.button(t['confirm'], key="btn_reg", use_container_width=True):
                    try:
                        if supabase.table('app_users').select('*').eq('username', nu).execute().data: st.error(t['err'])
                        else: supabase.table('app_users').insert({"username": nu, "password": np}).execute(); st.success(t['suc'])
                    except Exception as e: st.error(f"DB Error: {e}")

elif st.session_state.current_page == "Settings":
    if st.button(t['back']): st.session_state.current_page = "Home"; st.rerun()
    st.markdown("---")
    
    st.markdown(f"### ⚙️ {'Preferences' if t['sys_lang']=='English' else '偏好设置'}")
    col_t, col_l = st.columns(2)
    
    theme_opts = list(theme_colors.keys())
    with col_t:
        new_th = st.selectbox("Theme / 主题", theme_opts, index=theme_opts.index(st.session_state.theme))
        if new_th != st.session_state.theme: st.session_state.theme = new_th; st.rerun()
        
    with col_l:
        new_la = st.selectbox("Language / 语言", ["🇨🇳 简体中文", "🇬🇧 English"], index=["🇨🇳 简体中文", "🇬🇧 English"].index(st.session_state.lang))
        if new_la != st.session_state.lang: st.session_state.lang = new_la; st.rerun()

else:
    if st.button("← " + t['back']): st.session_state.current_page = "Home"; st.rerun()
    st.markdown("---")
    {"A": m_kitchen, "B": m_health, "C": m_community, "D": m_user}[st.session_state.current_page]()
