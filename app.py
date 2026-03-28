import streamlit as st
import datetime
from datetime import timezone, timedelta
import pandas as pd
import json
import os
import uuid

# --- 網頁基礎設定 ---
st.set_page_config(page_title="ER 大夜班提示器", layout="wide")

# 強制設定為台灣時區 (UTC+8)
tw_tz = timezone(timedelta(hours=8))
DATA_FILE = "er_tasks_data.json"

# ==========================================
# 共用資料庫 (JSON 讀寫功能)
# ==========================================
def load_tasks():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for d in data:
                d['target_time'] = datetime.datetime.fromisoformat(d['target_time'])
                if d.get('actual_time'):
                    d['actual_time'] = datetime.datetime.fromisoformat(d['actual_time'])
            return data
    except Exception as e:
        return []

def save_tasks(tasks):
    safe_tasks = []
    for t in tasks:
        task_dict = t.copy()
        task_dict['target_time'] = t['target_time'].isoformat()
        if t.get('actual_time'):
            task_dict['actual_time'] = t['actual_time'].isoformat()
        safe_tasks.append(task_dict)
        
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(safe_tasks, f, ensure_ascii=False, indent=2)

# 確保每次畫面互動時，狀態都是最新的
st.session_state.tasks = load_tasks()

# ==========================================
# 前台介面開始
# ==========================================
title_col, sync_col = st.columns([4, 1])
with title_col:
    st.title("🚨 急診留觀：智能待辦與交班提示器")
with sync_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 點我同步最新資料", use_container_width=True):
        st.rerun()

tab1, tab2 = st.tabs(["🏥 臨床待辦看板", "📊 後台數據追蹤 (管理員專用)"])

# ------------------------------------------
# 分頁 1：臨床待辦看板
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
            if st.checkbox("EKG"): selected_tasks.append("EKG")
        with chk_col2:
            if st.checkbox("呼吸"): selected_tasks.append("呼吸")
            if st.checkbox("血氧"): selected_tasks.append("血氧")
            if st.checkbox("病解"): selected_tasks.append("病解")
            if st.checkbox("NG"): selected_tasks.append("NG")
        with chk_col3:
            on_cath_check = st.checkbox("on cath")
            if st.checkbox("Foley"): selected_tasks.append("Foley")
            other_check = st.checkbox("其他")
            
        st.markdown(" ")
        
        remove_old_cath = False
        old_cath_location = ""
        if on_cath_check:
            remove_old_cath = st.checkbox("🔄 是否移除原 cath？")
            if remove_old_cath:
                old_cath_location = st.text_input("輸入原 cath 位置", placeholder="例如: 左手背、右前臂...")

        other_text = ""
        if other_check:
            other_text = st.text_input("輸入其他待做事項", placeholder="例如: 觀察過敏反應、紀錄 I/O...")
            
        blood_draw = st.checkbox("💉 抽血")
        blood_tests = ""
        if blood_draw:
            blood_tests = st.text_input("輸入檢驗項目", placeholder="例如: CBC, SMA, Trop-I...")

        wound_care = st.checkbox("🩹 傷口護理")
        wound_details = ""
        if wound_care:
            wound_details = st.text_input("輸入換藥部位與方式", placeholder="例如: 右小腿擦傷，CD...")

        st.markdown("---")
        
        time_str = st.text_input("設定執行時間 (輸入4碼數字，例如: 0312 或 1530)", max_chars=4, placeholder="0312")

        if st.button("新增提醒", use_container_width=True, type="primary"):
            if on_cath_check:
                if remove_old_cath:
                    if old_cath_location.strip() == "":
                        selected_tasks.append("on cath (需移除原cath)")
                    else:
                        selected_tasks.append(f"on cath (移除原cath: {old_cath_location})")
                else:
                    selected_tasks.append("on cath")

            if other_check:
                if other_text.strip() == "":
                    selected_tasks.append("其他")
                else:
                    selected_tasks.append(f"其他({other_text})")
            
            if blood_draw:
                if blood_tests.strip() == "":
                    selected_tasks.append("抽血")
                else:
                    selected_tasks.append(f"抽血({blood_tests})")
                    
            if wound_care:
                if wound_details.strip() == "":
                    selected_tasks.append("傷口護理")
                else:
                    selected_tasks.append(f"傷口護理({wound_details})")

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
                    
                    # 寫入資料庫
                    current_tasks = load_tasks()
                    current_tasks.append({
                        "id": str(uuid.uuid4()),
                        "bed": bed_num,
                        "task": task_str,
                        "target_time": target_dt,
                        "status": "pending",
                        "actual_time": None
                    })
                    save_tasks(current_tasks)
                    
                    # 使用 toast 顯示成功訊息 (會飄浮在畫面上，不會因為重整而消失)
                    st.toast(f"✅ 已成功新增 {bed_num} 的待辦事項！")
                    # 強制重新整理網頁，讓右邊看板立刻更新
                    st.rerun()
                    
                except ValueError:
                    st.error("⚠️ 時間格式錯誤！請確認小時(00-23)與分鐘(00-59)是否正確。")

    # --- 右半邊：待辦任務看板 ---
    with col_right:
        header_col1, header_col2 = st.columns([3, 1])
        with header_col1:
            st.subheader("📋 待辦任務看板")
        with header_col2:
            pass 

        now_tw = datetime.datetime.now(tw_tz)
        active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

        if not active_tasks:
            st.info("🎉 目前沒有待辦任務！如果別台電腦有新增，請點擊上方「🔄 同步最新資料」。")
        else:
            sorted_tasks = sorted(
                [(t) for t in st.session_state.tasks if t["status"] == "pending"],
                key=lambda x: x["target_time"]
            )
            
            for task in sorted_tasks:
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
                        if st.button("✅ 完成", key=f"done_{task['id']}", use_container_width=True):
                            current_tasks = load_tasks()
                            for t in current_tasks:
                                if t['id'] == task['id']:
                                    t['status'] = 'done'
                                    t['actual_time'] = datetime.datetime.now(tw_tz)
                            save_tasks(current_tasks)
                            st.toast("✅ 任務已完成！")
                            st.rerun()

# ------------------------------------------
# 分頁 2：後台數據追蹤與匯出 (密碼保護)
# ------------------------------------------
with tab2:
    st.subheader("🔒 管理員專區")
    
    # 建立密碼輸入框
    admin_pw = st.text_input("請輸入管理員密碼以解鎖後台：", type="password")
    
    if admin_pw == "ALEX":
        st.success("解鎖成功！歡迎進入數據追蹤後台。")
        st.markdown("---")
        
        done_tasks = [t for t in st.session_state.tasks if t["status"] == "done"]
        
        if not done_tasks:
            st.info("目前尚無已完成的任務紀錄。")
        else:
            total_done = len(done_tasks)
            
            on_time_count = 0
            for t in done_tasks:
                diff_mins = (t["actual_time"] - t["target_time"]).total_seconds() / 60
                if diff_mins <= 60:
                    on_time_count += 1
                    
            overdue_count = total_done - on_time_count
            on_time_rate = round((on_time_count / total_done) * 100, 1) if total_done > 0 else 0

            met_col1, met_col2, met_col3, met_col4 = st.columns(4)
            met_col1.metric("總完成任務數", f"{total_done} 件")
            met_col2.metric("✅ 達標完成 (含1小時內)", f"{on_time_count} 件")
            met_col3.metric("🚨 嚴重超時 (>1小時)", f"{overdue_count} 件")
            met_col4.metric("🏆 任務達標率", f"{on_time_rate} %")
            
            st.markdown("---")
            
            df_data = []
            for t in done_tasks:
                target_str = t['target_time'].strftime('%Y-%m-%d %H:%M')
                actual_str = t['actual_time'].strftime('%Y-%m-%d %H:%M:%S')
                diff_mins = round((t['actual_time'] - t['target_time']).total_seconds() / 60, 1)
                is_on_time = "是" if diff_mins <= 60 else "否(超時>1hr)"
                
                df_data.append({
                    "床號": t['bed'],
                    "待做事項": t['task'],
                    "目標時間": target_str,
                    "實際完成時間": actual_str,
                    "是否達標": is_on_time,
                    "時間差(分)": diff_mins 
                })
                
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True)
            
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                csv = df.to_csv(index=False).encode('utf-8-sig')
                current_date_str = datetime.datetime.now(tw_tz).strftime("%Y%m%d_%H%M")
                st.download_button(
                    label="📥 下載今日執行紀錄 (CSV 檔)",
                    data=csv,
                    file_name=f"ER_NightShift_Log_{current_date_str}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
            with col_btn2:
                if st.button("🗑️ 清空所有歷史資料 (交班後使用)", type="primary", use_container_width=True):
                    save_tasks([])
                    st.toast("🗑️ 資料已全部清空！準備迎接下一班！")
                    st.rerun()

    elif admin_pw != "":
        st.error("❌ 密碼錯誤！請重新輸入。")
