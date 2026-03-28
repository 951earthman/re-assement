import streamlit as st
import datetime

# 初始化 session_state，用來記住所有任務
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

st.set_page_config(page_title="ER 大夜班提示器", layout="centered")
st.title("🚨 急診留觀：智能再評估提示器")

st.write("### ➕ 新增評估提醒")

# --- 1. 動態床號選擇區 ---
col1, col2 = st.columns([1, 2])

with col1:
    area = st.selectbox("區域", ["診間", "OBS", "兒科", "FRee (自行輸入)"])

with col2:
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

# --- 2. 評估項目與指定時間設定 ---
task_options = ["體溫", "呼吸", "血壓", "血氧", "疼痛", "病解", "抽血報告", "其他"]
task_type = st.multiselect("評估項目 (可複選)", task_options, default=["血壓", "疼痛"])

# 取得現在時間，並預設提醒時間為 2 小時後
now = datetime.datetime.now()
default_time = (now + datetime.timedelta(hours=2)).time()

# 改用 st.time_input 讓使用者直接選擇或輸入時間 (24小時制)
target_time_input = st.time_input("設定提醒時間 (24小時制)", value=default_time)

# --- 3. 送出按鈕與邏輯 ---
if st.button("新增提醒", use_container_width=True, type="primary"):
    if not bed_num:
        st.error("⚠️ 請填寫或選擇床號！")
    elif not task_type:
        st.error("⚠️ 請至少選擇一項評估項目！")
    else:
        # 將今天的日期與輸入的時間結合
        target_dt = datetime.datetime.combine(now.date(), target_time_input)
        
        # 智慧判斷：如果設定的時間比「現在」還要早，代表是要設定到「明天」
        # （例如現在是 23:00，設定 02:00，就會自動加一天）
        if target_dt < now:
            target_dt += datetime.timedelta(days=1)
            
        task_str = "、".join(task_type) 
        
        st.session_state.tasks.append({
            "bed": bed_num,
            "task": task_str,
            "target_time": target_dt,
            "status": "pending"
        })
        st.success(f"✅ 已成功新增 {bed_num} 的 【{task_str}】 提醒！預計時間：{target_dt.strftime('%H:%M')}")

st.divider()

# --- 4. 顯示任務看板與清除功能 ---
col_title, col_btn = st.columns([3, 1])
with col_title:
    st.subheader("📋 待辦與超時看板")
with col_btn:
    # 增加一鍵清除已完成任務的按鈕
    if st.button("🧹 清除已完成", use_container_width=True):
        st.session_state.tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]
        st.rerun()

now = datetime.datetime.now()
active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

if not active_tasks:
    st.info("🎉 目前沒有待辦任務！")
else:
    for idx, task in enumerate(st.session_state.tasks):
        if task["status"] == "done":
            continue

        time_diff = task["target_time"] - now
        is_overdue = time_diff.total_seconds() <= 0

        if is_overdue:
            st.error(f"🚨 **超時提醒！** 【{task['bed']}】 - {task['task']} (設定時間: {task['target_time'].strftime('%H:%M')})")
            if st.button("✅ 標記完成", key=f"done_{idx}"):
                st.session_state.tasks[idx]["status"] = "done"
                st.rerun()
        else:
            mins_left = int(time_diff.total_seconds() / 60)
            st.warning(f"⏳ **倒數 {mins_left} 分鐘** 【{task['bed']}】 - {task['task']} (設定時間: {task['target_time'].strftime('%H:%M')})")
            if st.button("提前完成", key=f"early_{idx}"):
                st.session_state.tasks[idx]["status"] = "done"
                st.rerun()
