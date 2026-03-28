import streamlit as st
import datetime
import pandas as pd

# 1. 初始化網頁的暫存記憶 (Session State)，用來記住所有任務
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# 設定網頁標題與排版
st.set_page_config(page_title="ER 大夜班提示器", layout="centered")
st.title("🚨 急診留觀：智能再評估提示器")

# 2. 新增任務的表單區塊
with st.form("add_task_form"):
    st.write("### ➕ 新增評估提醒")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        bed_num = st.text_input("床號", placeholder="例如: 留觀 5")
    with col2:
        task_type = st.selectbox("評估項目", ["疼痛再評估 (給藥後)", "V/S 追蹤", "抽血報告確認", "特殊給藥觀察", "其他"])
    with col3:
        # 預設 120 分鐘 (2小時)，可自由調整
        delay_mins = st.number_input("幾分鐘後提醒？", min_value=1, value=120, step=15)

    submitted = st.form_submit_button("新增提醒", use_container_width=True)
    
    if submitted and bed_num:
        # 計算目標提醒時間
        target_time = datetime.datetime.now() + datetime.timedelta(minutes=delay_mins)
        st.session_state.tasks.append({
            "bed": bed_num,
            "task": task_type,
            "target_time": target_time,
            "status": "pending"
        })
        st.success(f"已新增 {bed_num} 的 {task_type} 提醒！")

st.divider()

# 3. 顯示任務看板 (結合交班前狀態)
st.subheader("📋 待辦與超時看板")

# 取得系統當下時間
now = datetime.datetime.now()
active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

if not active_tasks:
    st.info("🎉 目前沒有待辦任務，喝口水休息一下吧！")
else:
    for idx, task in enumerate(st.session_state.tasks):
        if task["status"] == "done":
            continue # 已完成的任務不顯示

        # 計算時間差
        time_diff = task["target_time"] - now
        is_overdue = time_diff.total_seconds() <= 0

        # UI 顯示邏輯：超時顯示紅色 Error，未超時顯示黃色 Warning
        if is_overdue:
            st.error(f"🚨 **超時提醒！** 【{task['bed']}】 - {task['task']} (原定時間: {task['target_time'].strftime('%H:%M')})")
            if st.button("✅ 標記完成", key=f"done_{idx}"):
                st.session_state.tasks[idx]["status"] = "done"
                st.rerun() # 重新整理網頁畫面
        else:
            mins_left = int(time_diff.total_seconds() / 60)
            st.warning(f"⏳ **倒數 {mins_left} 分鐘** 【{task['bed']}】 - {task['task']} (預計時間: {task['target_time'].strftime('%H:%M')})")
            if st.button("提前完成", key=f"early_{idx}"):
                st.session_state.tasks[idx]["status"] = "done"
                st.rerun()
