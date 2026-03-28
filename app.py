import streamlit as st
import datetime
from datetime import timezone, timedelta

# --- 網頁基礎設定 ---
st.set_page_config(page_title="ER 大夜班提示器", layout="wide")

# 強制設定為台灣時區 (UTC+8)
tw_tz = timezone(timedelta(hours=8))

# 初始化 session_state
if 'tasks' not in st.session_state:
    st.session_state.tasks = []

# 初始化時間輸入框的預設記憶（避免勾選選單時時間被重置）
if 'target_time_input' not in st.session_state:
    st.session_state.target_time_input = datetime.datetime.now(tw_tz).time()

st.title("🚨 急診留觀：智能待辦與交班提示器")

# --- 版面左右分割 ---
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
    
    # 3. 時間設定與送出 (綁定 key 來鎖定記憶，不會亂跳)
    st.time_input("設定執行時間 (24小時制)", key="target_time_input")

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
        else:
            now_tw = datetime.datetime.now(tw_tz)
            # 抓取鎖定住的使用者輸入時間
            target_dt = datetime.datetime.combine(now_tw.date(), st.session_state.target_time_input).replace(tzinfo=tw_tz)
            
            # 跨日邏輯判定
            if target_dt < now_tw - datetime.timedelta(hours=12): 
                # 如果設定的時間比現在早超過12小時，通常代表是設定給「明天」的
                target_dt += datetime.timedelta(days=1)
                
            task_str = "、".join(selected_tasks) 
            
            st.session_state.tasks.append({
                "bed": bed_num,
                "task": task_str,
                "target_time": target_dt,
                "status": "pending"
            })
            st.success(f"✅ 已成功新增 {bed_num} 的 【{task_str}】")

# ==========================================
# 右半邊：待辦與四段變色看板區
# ==========================================
with col_right:
    header_col1, header_col2 = st.columns([3, 1])
    with header_col1:
        st.subheader("📋 待辦任務看板")
    with header_col2:
        if st.button("🧹 清除紀錄", use_container_width=True):
            st.session_state.tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]
            st.rerun()

    now_tw = datetime.datetime.now(tw_tz)
    active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

    if not active_tasks:
        st.info("🎉 目前沒有待辦任務！")
    else:
        # 依照時間排序，最緊急的在最上面
        sorted_tasks = sorted(
            [(idx, t) for idx, t in enumerate(st.session_state.tasks) if t["status"] == "pending"],
            key=lambda x: x[1]["target_time"]
        )
        
        for original_idx, task in sorted_tasks:
            time_diff = task["target_time"] - now_tw
            diff_mins = time_diff.total_seconds() / 60

            # 用框線卡片包裝任務
            with st.container(border=True):
                task_col1, task_col2 = st.columns([4, 1])
                
                with task_col1:
                    # 【四段變色邏輯】
                    if diff_mins > 30:
                        # 1. 超過半小時：沒有底色
                        st.markdown(f"⚪ **尚未到期** (剩餘 {int(diff_mins)} 分鐘)<br>【{task['bed']}】 - {task['task']}<br>🕒 設定時間: {task['target_time'].strftime('%H:%M')}", unsafe_allow_html=True)
                    
                    elif 0 < diff_mins <= 30:
                        # 2. 進入半小時內：綠色底色
                        st.success(f"🟢 **即將執行** (剩餘 {int(diff_mins)} 分鐘)\n\n【{task['bed']}】 - {task['task']}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}")
                    
                    elif -30 <= diff_mins <= 0:
                        # 3. 超時半小時以內：黃色底色
                        st.warning(f"🟡 **已超時** (超時 {int(abs(diff_mins))} 分鐘)\n\n【{task['bed']}】 - {task['task']}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}")
                    
                    else:
                        # 4. 超時超過半小時：紅色底色
                        st.error(f"🔴 **嚴重超時** (超時 {int(abs(diff_mins))} 分鐘)\n\n【{task['bed']}】 - {task['task']}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}")

                with task_col2:
                    st.markdown("<br>", unsafe_allow_html=True) # 微調按鈕高度
                    if st.button("✅ 完成", key=f"done_{original_idx}", use_container_width=True):
                        st.session_state.tasks[original_idx]["status"] = "done"
                        st.rerun()

    # --- 已完成任務紀錄區塊 ---
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander("📜 已完成任務紀錄 (點擊展開查看)"):
        done_tasks = [t for t in st.session_state.tasks if t["status"] == "done"]
        if not done_tasks:
            st.caption("目前尚無已完成的紀錄。")
        else:
            for t in done_tasks:
                st.success(f"✔️ 【{t['bed']}】已完成：{t['task']} (原設定: {t['target_time'].strftime('%H:%M')})")
