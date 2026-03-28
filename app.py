import streamlit as st
import datetime
from datetime import timezone, timedelta
import pandas as pd

# --- 網頁基礎設定 ---
st.set_page_config(page_title="ER 大夜班提示器", layout="wide")

# 強制設定為台灣時區 (UTC+8)
tw_tz = timezone(timedelta(hours=8))

# 初始化 session_state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

st.title("🚨 急診留觀：智能待辦與交班提示器")

# ==========================================
# 建立前台與後台分頁
# ==========================================
tab1, tab2 = st.tabs(["🏥 臨床待辦看板", "📊 後台數據追蹤 (管理員專用)"])

# ------------------------------------------
# 分頁 1：臨床待辦看板 (日常操作區)
# ------------------------------------------
with tab1:
    col_left, col_right = st.columns([1, 1.2], gap="large")

    # --- 左半邊：新增待做事項區 ---
    with col_left:
        st.subheader("➕ 新增待做事項")
        
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
            
        st.markdown(" ")
        blood_draw = st.checkbox("💉 抽血")
        blood_tests = ""
        if blood_draw:
            blood_tests = st.text_input("輸入檢驗項目", placeholder="例如: CBC, SMA, Trop-I...")

        st.markdown("---")
        
        time_str = st.text_input("設定執行時間 (輸入4碼數字，例如: 0312 或 1530)", max_chars=4, placeholder="0312")

        if st.button("新增提醒", use_container_width=True, type="primary"):
            if blood_draw:
                if blood_tests.strip() == "":
                    selected_tasks.append("抽血")
                else:
                    selected_tasks.append(f"抽血({blood_tests})")

            if not bed_num:
                st.error("⚠️ 請填寫或選擇床號！")
            elif not selected_tasks:
                st.error("⚠️ 請至少勾選一項待做事項！")
            elif len(time_str) != 4 or not time_str.isdigit():
                st.error("⚠️ 請輸入4位純數字的時間格式，例如 0312！")
            else:
                try:
                    hour = int(time_str[:2])
                    minute = int(time_str[2:])
                    parsed_time = datetime.time(hour, minute)
                    now_tw = datetime.datetime.now(tw_tz)
                    target_dt = datetime.datetime.combine(now_tw.date(), parsed_time).replace(tzinfo=tw_tz)
                    
                    if target_dt < now_tw - datetime.timedelta(hours=12): 
                        target_dt += datetime.timedelta(days=1)
                        
                    task_str = "、".join(selected_tasks) 
                    
                    st.session_state.tasks.append({
                        "bed": bed_num,
                        "task": task_str,
                        "target_time": target_dt,
                        "status": "pending",
                        "actual_time": None # 新增實際完成時間欄位
                    })
                    st.success(f"✅ 已成功新增 {bed_num} 的 【{task_str}】")
                except ValueError:
                    st.error("⚠️ 時間格式錯誤！請確認小時(00-23)與分鐘(00-59)是否正確。")

    # --- 右半邊：待辦任務看板 ---
    with col_right:
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            st.subheader("📋 待辦任務看板")
        with header_col2:
            # 清除按鈕改為只清除「未完成」的任務，或者您可以保留原本清除已完成的邏輯
            # 這裡為了收集資料，我們建議交班後直接從後台匯出，前台只需專注執行
            pass 

        now_tw = datetime.datetime.now(tw_tz)
        active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

        if not active_tasks:
            st.info("🎉 目前沒有待辦任務！")
        else:
            sorted_tasks = sorted(
                [(idx, t) for idx, t in enumerate(st.session_state.tasks) if t["status"] == "pending"],
                key=lambda x: x[1]["target_time"]
            )
            
            for original_idx, task in sorted_tasks:
                time_diff = task["target_time"] - now_tw
                diff_mins = time_diff.total_seconds() / 60

                with st.container(border=True):
                    task_col1, task_col2 = st.columns([4, 1])
                    
                    with task_col1:
                        if diff_mins > 30:
                            st.markdown(f"⚪ **尚未到期** (剩餘 {int(diff_mins)} 分鐘)<br>【{task['bed']}】 - {task['task']}<br>🕒 設定時間: {task['target_time'].strftime('%H:%M')}", unsafe_allow_html=True)
                        elif 0 < diff_mins <= 30:
                            st.success(f"🟢 **即將執行** (剩餘 {int(diff_mins)} 分鐘)\n\n【{task['bed']}】 - {task['task']}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}")
                        elif -30 <= diff_mins <= 0:
                            st.warning(f"🟡 **已超時** (超時 {int(abs(diff_mins))} 分鐘)\n\n【{task['bed']}】 - {task['task']}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}")
                        else:
                            st.error(f"🔴 **嚴重超時** (超時 {int(abs(diff_mins))} 分鐘)\n\n【{task['bed']}】 - {task['task']}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}")

                    with task_col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        if st.button("✅ 完成", key=f"done_{original_idx}", use_container_width=True):
                            st.session_state.tasks[original_idx]["status"] = "done"
                            # 關鍵更新：記錄按下按鈕的精準時間
                            st.session_state.tasks[original_idx]["actual_time"] = datetime.datetime.now(tw_tz)
                            st.rerun()

# ------------------------------------------
# 分頁 2：後台數據追蹤與匯出 (研究/品管用)
# ------------------------------------------
with tab2:
    st.subheader("📈 執行成效追蹤後台")
    
    done_tasks = [t for t in st.session_state.tasks if t["status"] == "done"]
    
    if not done_tasks:
        st.info("目前尚無已完成的任務紀錄。")
    else:
        # 1. 計算數據指標
        total_done = len(done_tasks)
        on_time_count = sum(1 for t in done_tasks if t["actual_time"] <= t["target_time"])
        overdue_count = total_done - on_time_count
        on_time_rate = round((on_time_count / total_done) * 100, 1)

        # 顯示儀表板
        met_col1, met_col2, met_col3, met_col4 = st.columns(4)
        met_col1.metric("總完成任務數", f"{total_done} 件")
        met_col2.metric("✅ 準時完成", f"{on_time_count} 件")
        met_col3.metric("🚨 超時完成", f"{overdue_count} 件")
        met_col4.metric("🏆 準時達成率", f"{on_time_rate} %")
        
        st.markdown("---")
        
        # 2. 準備匯出成 Excel 可讀的 CSV 格式
        df_data = []
        for t in done_tasks:
            target_str = t['target_time'].strftime('%Y-%m-%d %H:%M')
            actual_str = t['actual_time'].strftime('%Y-%m-%d %H:%M:%S')
            is_on_time = "是" if t['actual_time'] <= t['target_time'] else "否"
            
            # 計算提早或延遲的具體分鐘數
            diff_mins = round((t['actual_time'] - t['target_time']).total_seconds() / 60, 1)
            
            df_data.append({
                "床號": t['bed'],
                "待做事項": t['task'],
                "目標時間": target_str,
                "實際完成時間": actual_str,
                "是否準時": is_on_time,
                "時間差(分鐘)": diff_mins # 負數代表提早，正數代表延遲
            })
            
        df = pd.DataFrame(df_data)
        
        # 在網頁上預覽表格
        st.dataframe(df, use_container_width=True)
        
        # 3. 匯出按鈕 (utf-8-sig 確保 Excel 繁體中文不亂碼)
        csv = df.to_csv(index=False).encode('utf-8-sig')
        current_date_str = datetime.datetime.now(tw_tz).strftime("%Y%m%d_%H%M")
        
        st.download_button(
            label="📥 下載今日執行紀錄 (CSV 檔)",
            data=csv,
            file_name=f"ER_NightShift_Log_{current_date_str}.csv",
            mime="text/csv",
            type="primary"
        )
        
        st.markdown("*(💡 提示：建議在早上 08:00 交班前點擊下載，若網頁長時間關閉或重新整理，暫存紀錄可能會被清空)*")
