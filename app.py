import streamlit as st
import datetime

# --- 網頁基礎設定 ---
# 必須設定為 wide 模式，左右分欄才不會太擠
st.set_page_config(page_title="ER 大夜班提示器", layout="wide")

# 初始化 session_state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

st.title("🚨 急診留觀：智能待辦與交班提示器")

# --- 版面左右分割 (比例 1 : 1.2) ---
col_left, col_right = st.columns([1, 1.2], gap="large")

# ==========================================
# 左半邊：新增待做事項區
# ==========================================
with col_left:
    st.subheader("➕ 新增待做事項")
    
    # 1. 動態床號選擇區
    area = st.selectbox("區域", ["診間", "OBS", "兒科", "FRee (自行輸入)"])
    
    if area == "診間":
        clinic_beds = ["5", "6"] + [str(i) for i in range(11, 26)] + [str(i) for i in range(27, 34)] + ["36", "37", "39"]
        bed_num = st.selectbox("選擇床號", [f"診間 {b}" for b in clinic_beds])
    elif area == "OBS":
        obs_beds = [str(i) for i in range(1, 4)] + [str(i) for i in range(5, 14)] + \
                   [str(i) for i in range(15, 24)] + [str(i) for i in range(25, 34)] + \
                   [str(i) for i in range(35, 40)]
        bed_num = st.selectbox("選擇床號", [f"OBS {b}" for b in obs_beds])
    elif area == "兒科":
        peds_beds = ["501", "502", "503", "505", "506", "507", "508", "509"]
        bed_num = st.selectbox("選擇床號", [f"兒科 {b}" for b in peds_beds])
    else:
        bed_num = st.text_input("輸入名稱/床號", placeholder="例如: 走廊加床 王大明")

    st.markdown("---")
    st.markdown("##### 📌 勾選待做事項")
    
    # 2. 待辦事項勾選區 (使用欄位排列較省空間)
    chk_col1, chk_col2, chk_col3 = st.columns(3)
    selected_tasks = []
    
    with chk_col1:
        if st.checkbox("體溫"): selected_tasks.append("體溫")
        if st.checkbox("血壓"): selected_tasks.append("血壓")
        if st.checkbox("疼痛"): selected_tasks.append("疼痛")
    with chk_col2:
        if st.checkbox("呼吸"): selected_tasks.append("呼吸")
        if st.checkbox("血氧"): selected_tasks.append("血氧")
        if st.checkbox("病解"): selected_tasks.append("病解")
    with chk_col3:
        if st.checkbox("on cath"): selected_tasks.append("on cath")
        if st.checkbox("EKG"): selected_tasks.append("EKG")
        if st.checkbox("其他"): selected_tasks.append("其他")
        
    # 抽血獨立區塊：若勾選則跳出文字輸入框
    st.markdown(" ")
    blood_draw = st.checkbox("💉 抽血")
    blood_tests = ""
    if blood_draw:
        blood_tests = st.text_input("輸入檢驗項目", placeholder="例如: CBC, SMA, Trop-I...")

    st.markdown("---")
    
    # 3. 時間設定與送出
    now = datetime.datetime.now()
    default_time = (now + datetime.timedelta(hours=2)).time()
    target_time_input = st.time_input("設定提醒時間 (24小時制)", value=default_time)

    if st.button("新增提醒", use_container_width=True, type="primary"):
        # 處理抽血字串
        if blood_draw:
            if blood_tests.strip() == "":
                selected_tasks.append("抽血")
            else:
                selected_tasks.append(f"抽血({blood_tests})")

        if not bed_num:
            st.error("⚠️ 請填寫或選擇床號！")
        elif not selected_tasks:
            st.error("⚠️ 請至少勾選一項待做事項！")
        else:
            target_dt = datetime.datetime.combine(now.date(), target_time_input)
            if target_dt < now:
                target_dt += datetime.timedelta(days=1)
                
            task_str = "、".join(selected_tasks) 
            
            # 加入任務清單
            st.session_state.tasks.append({
                "bed": bed_num,
                "task": task_str,
                "target_time": target_dt,
                "status": "pending"
            })
            st.success(f"✅ 已成功新增 {bed_num} 的 【{task_str}】")

# ==========================================
# 右半邊：待辦與超時看板區
# ==========================================
with col_right:
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader("📋 待辦任務看板")
    with header_col2:
        if st.button("🧹 清除已完成", use_container_width=True):
            st.session_state.tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]
            st.rerun()

    now = datetime.datetime.now()
    active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

    if not active_tasks:
        st.info("🎉 目前沒有待辦任務，可以趁機補個紀錄或喝口水！")
    else:
        # 智慧排序：把快要超時或已經超時的任務排在最上面
        sorted_tasks = sorted(
            [(idx, t) for idx, t in enumerate(st.session_state.tasks) if t["status"] == "pending"],
            key=lambda x: x[1]["target_time"]
        )
        
        for original_idx, task in sorted_tasks:
            time_diff = task["target_time"] - now
            is_overdue = time_diff.total_seconds() <= 0

            # 用框線卡片包裝任務，視覺更像 Kanban 看板
            with st.container(border=True):
                task_col1, task_col2 = st.columns([4, 1])
                with task_col1:
                    if is_overdue:
                        st.error(f"🚨 **超時提醒！** 【{task['bed']}】 - {task['task']} (設定時間: {task['target_time'].strftime('%H:%M')})")
                    else:
                        mins_left = int(time_diff.total_seconds() / 60)
                        st.warning(f"⏳ **倒數 {mins_left} 分鐘** 【{task['bed']}】 - {task['task']} (設定時間: {task['target_time'].strftime('%H:%M')})")
                with task_col2:
                    # 點擊完成後直接更新狀態並重整網頁
                    if st.button("✅ 完成", key=f"done_{original_idx}", use_container_width=True):
                        st.session_state.tasks[original_idx]["status"] = "done"
                        st.rerun()
