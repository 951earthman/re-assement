import streamlit as st
import streamlit.components.v1 as components
import datetime
from datetime import timezone, timedelta
import pandas as pd
import json
import os
import uuid

# --- 網頁基礎設定 ---
st.set_page_config(page_title="🚨 ER 提示器", layout="wide", initial_sidebar_state="expanded")
tw_tz = timezone(timedelta(hours=8))
DATA_FILE = "er_tasks_data.json"

# ==========================================
# 側邊欄：保護聲明與著作權
# ==========================================
with st.sidebar:
    st.header("⚖️ 系統保護聲明")
    st.warning("⚠️ **免責聲明**\n\n本系統僅供臨床交班與待辦事項輔助提醒，**並非正式醫療紀錄（HIS）系統**。所有醫療處置、給藥時間與醫囑變更，請一律以醫院主系統與醫師正式醫囑為準。")
    st.info("💡 **資料隱私**\n\n本系統為便利交班之輔助工具，請盡量以「床號」代替病患全名，切勿輸入身分證字號等敏感個資，以符合 HIPAA 及相關隱私法規。")
    st.markdown("---")
    st.markdown("##### 👨‍⚕️ 系統資訊")
    st.markdown("© 2026 Developed by **護理師 吳智弘** \n*(Hualien Tzu Chi ER)*")
    st.caption("All Rights Reserved. 僅供單位內部輔助使用，未經授權請勿作商業用途。")

# ==========================================
# 醫院 ISO 常規時間對照表 (24小時制)
# ==========================================
ISO_SCHEDULE = {
    "Q2H": [1, 3, 5, 7, 9, 11, 13, 15, 17, 19, 21, 23],
    "Q4H": [1, 5, 9, 13, 17, 21],
    "Q6H": [5, 11, 17, 23],
    "Q8H": [5, 13, 21],
    "BIDAC": [7, 17],
    "QIDAC": [7, 11, 17, 21]
}

def get_next_iso_time(base_time, freq):
    if freq not in ISO_SCHEDULE:
        return base_time + datetime.timedelta(hours=2)
    hours = ISO_SCHEDULE[freq]
    current_hour = base_time.hour
    next_hour = None
    add_days = 0
    for h in hours:
        if h > current_hour:
            next_hour = h
            break
    if next_hour is None:
        next_hour = hours[0]
        add_days = 1
    next_time = base_time.replace(hour=next_hour, minute=0, second=0, microsecond=0)
    next_time += datetime.timedelta(days=add_days)
    return next_time

# ==========================================
# 床位與分區設定字典
# ==========================================
BED_MAP = {
    "第三診間區": ["5", "6", "39"] + [str(i) for i in range(27, 34)],
    "第二診間區": [str(i) for i in range(16, 21)] + ["36", "37", "38"],
    "第一診間區": [str(i) for i in range(11, 16) if i != 14] + [str(i) for i in range(21, 26) if i != 24],
    "OBS 1": [str(i) for i in range(1, 11) if i != 4] + ["35", "36", "37", "38"],
    "OBS 2": [str(i) for i in range(11, 24) if i != 14],
    "OBS 3": [str(i) for i in range(25, 34)] + ["39"],
    "兒科": ["501", "502", "503", "505", "506", "507", "508", "509"],
    "FRee (自行輸入)": []
}

# ==========================================
# 資料庫 (JSON 讀寫功能)
# ==========================================
def load_tasks():
    if not os.path.exists(DATA_FILE): return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for d in data:
                d['target_time'] = datetime.datetime.fromisoformat(d['target_time'])
                if d.get('actual_time'):
                    d['actual_time'] = datetime.datetime.fromisoformat(d['actual_time'])
                if 'freq' not in d: d['freq'] = '單次'
                if 'area' not in d: d['area'] = '舊版資料'
                # 相容舊資料，預設次數邏輯
                if 'freq_total' not in d: d['freq_total'] = 99
                if 'freq_current' not in d: d['freq_current'] = 1
            return data
    except:
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

st.session_state.tasks = load_tasks()

# ==========================================
# 前台介面開始
# ==========================================
title_col, sync_col = st.columns([4, 1])
with title_col:
    st.title("🚨 急診留觀：智能待辦與交班提示器")
with sync_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 同步最新資料", use_container_width=True):
        st.rerun()

tab1, tab_dash, tab2, tab3 = st.tabs(["🏥 臨床待辦看板", "👁️ 單位總覽儀表板", "📝 歷史紀錄 (完成/取消)", "📊 後台數據追蹤 (管理員)"])

# ------------------------------------------
# 分頁 1：臨床待辦看板
# ------------------------------------------
with tab1:
    col_left, col_right = st.columns([1, 1.2], gap="large")

    with col_left:
        st.subheader("➕ 新增待做事項")
        
        area = st.selectbox("選擇分區", list(BED_MAP.keys()))
        if area == "FRee (自行輸入)":
            bed_num = st.text_input("輸入名稱/床號", placeholder="例如: 走廊 王大明")
            full_bed_name = f"【FRee】{bed_num}" if bed_num else ""
        else:
            bed_select = st.selectbox("選擇床號", BED_MAP[area])
            full_bed_name = f"【{area}】{bed_select}床"

        st.markdown("---")
        st.markdown("##### 📌 勾選常規待做事項")
        
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
            if st.checkbox("🩸 測血糖"): selected_tasks.append("測血糖")
            other_check = st.checkbox("其他")
            
        st.markdown(" ")
        
        remove_old_cath = False
        old_cath_location = ""
        if on_cath_check:
            remove_old_cath = st.checkbox("🔄 是否移除原 cath？")
            if remove_old_cath:
                old_cath_location = st.text_input("輸入原 cath 位置", placeholder="例如: 左手背...")

        other_text = ""
        if other_check:
            other_text = st.text_input("輸入其他待做事項", placeholder="例如: 紀錄 I/O...")
            
        blood_draw = st.checkbox("💉 抽血")
        blood_tests = ""
        if blood_draw:
            blood_tests = st.text_input("輸入檢驗項目", placeholder="例如: CBC, SMA...")

        wound_care = st.checkbox("🩹 傷口護理")
        wound_details = ""
        if wound_care:
            wound_details = st.text_input("輸入換藥部位與方式", placeholder="例如: 右小腿擦傷 CD...")

        # --- 特殊檢查與排程專區 ---
        st.markdown("---")
        st.markdown("##### 🔬 特殊檢查與排程")
        
        exam_col1, exam_col2 = st.columns(2)
        with exam_col1:
            radio_exam = st.checkbox("☢️ 放射科檢查")
            radio_items = []
            if radio
