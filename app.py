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

# --- 新增了第二個分頁：全觀儀表板 ---
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
            if radio_exam:
                radio_items = st.multiselect("選擇放射科項目", ["X光", "CT", "MRI"])
                
        with exam_col2:
            endo_exam = st.checkbox("🩺 內視鏡/超音波")
            endo_items = []
            endo_scheduled = False
            if endo_exam:
                endo_items = st.multiselect("選擇檢查項目", ["胃鏡", "大腸鏡", "腹部超音波", "腎臟超音波"])
                endo_scheduled = st.checkbox("✅ 已完成排程", key="endo_sch")

        st.markdown("---")
        
        freq_option = st.selectbox("🔄 執行頻率 (常規醫囑)", ["單次", "Q2H", "Q4H", "Q6H", "Q8H", "BIDAC", "QIDAC"])
        time_str = st.text_input("設定首次執行時間 (輸入4碼，例如: 0312)", max_chars=4, placeholder="0312")

        if st.button("新增提醒", use_container_width=True, type="primary"):
            if on_cath_check:
                if remove_old_cath and old_cath_location.strip():
                    selected_tasks.append(f"on cath(移除舊:{old_cath_location})")
                else:
                    selected_tasks.append("on cath")

            if other_check and other_text.strip(): selected_tasks.append(f"其他({other_text})")
            elif other_check: selected_tasks.append("其他")
            
            if blood_draw and blood_tests.strip(): selected_tasks.append(f"抽血({blood_tests})")
            elif blood_draw: selected_tasks.append("抽血")
                    
            if wound_care and wound_details.strip(): selected_tasks.append(f"傷口護理({wound_details})")
            elif wound_care: selected_tasks.append("傷口護理")

            if radio_exam:
                if radio_items: selected_tasks.append(f"放射科檢查({','.join(radio_items)})")
                else: selected_tasks.append("放射科檢查")
                    
            if endo_exam:
                sch_str = "已排程" if endo_scheduled else "未排程"
                if endo_items: selected_tasks.append(f"消化內視鏡({','.join(endo_items)} - {sch_str})")
                else: selected_tasks.append(f"消化內視鏡({sch_str})")

            if not full_bed_name.strip() or full_bed_name == "【FRee】":
                st.error("⚠️ 請填寫或選擇床號！")
            elif not selected_tasks:
                st.error("⚠️ 請至少勾選一項待做事項！")
            elif len(time_str) != 4 or not time_str.isdigit():
                st.error("⚠️ 請輸入4位純數字的時間格式！")
            else:
                try:
                    hour, minute = int(time_str[:2]), int(time_str[2:])
                    parsed_time = datetime.time(hour, minute)
                    now_tw = datetime.datetime.now(tw_tz)
                    target_dt = datetime.datetime.combine(now_tw.date(), parsed_time).replace(tzinfo=tw_tz)
                    if target_dt < now_tw - datetime.timedelta(hours=12): 
                        target_dt += datetime.timedelta(days=1)
                        
                    task_str = "、".join(selected_tasks) 
                    
                    current_tasks = load_tasks()
                    current_tasks.append({
                        "id": str(uuid.uuid4()),
                        "area": area,
                        "bed": full_bed_name,
                        "task": task_str,
                        "target_time": target_dt,
                        "status": "pending",
                        "actual_time": None,
                        "freq": freq_option
                    })
                    save_tasks(current_tasks)
                    st.toast(f"✅ 已成功新增 {full_bed_name} 的待辦事項！")
                    st.rerun()
                except ValueError:
                    st.error("⚠️ 時間格式錯誤！")

    with col_right:
        st.subheader("📋 待辦任務看板")
        
        filt_col1, filt_col2 = st.columns(2)
        with filt_col1:
            zone_options = ["全區顯示", "🏥 診間全區", "🛏️ OBS全區"] + list(BED_MAP.keys())
            filter_zone = st.selectbox("📍 依區域過濾", zone_options)
        with filt_col2:
            all_filter_options = [
                "體溫", "血壓", "疼痛", "EKG", "呼吸", "血氧", "病解", "NG", "on cath", 
                "Foley", "測血糖", "抽血", "傷口護理", "放射科檢查", "消化內視鏡", "其他"
            ]
            filter_tasks = st.multiselect("🩺 依項目過濾", all_filter_options, placeholder="顯示全部項目")

        now_tw = datetime.datetime.now(tw_tz)
        active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

        if filter_zone == "🏥 診間全區":
            active_tasks = [t for t in active_tasks if "診間" in t.get('area', '')]
        elif filter_zone == "🛏️ OBS全區":
            active_tasks = [t for t in active_tasks if "OBS" in t.get('area', '')]
        elif filter_zone != "全區顯示":
            active_tasks = [t for t in active_tasks if t.get('area') == filter_zone]

        if filter_tasks:
            active_tasks = [t for t in active_tasks if any(kw in t['task'] for kw in filter_tasks)]

        has_alert = any((t["target_time"] - now_tw).total_seconds() / 60 <= 30 for t in active_tasks)

        if not active_tasks:
            st.info("🎉 目前此條件下無待辦任務！")
        else:
            sorted_tasks = sorted(active_tasks, key=lambda x: x["target_time"])
            
            for task in sorted_tasks:
                time_diff = task["target_time"] - now_tw
                diff_mins = time_diff.total_seconds() / 60
                freq_badge = f" 🔁 **{task['freq']}**" if task['freq'] != "單次" else ""

                with st.container(border=True):
                    task_col1, task_col2 = st.columns([3.5, 1.5])
                    
                    with task_col1:
                        display_text = f"📍 **{task['bed']}** - {task['task']}{freq_badge}\n\n🕒 設定: {task['target_time'].strftime('%H:%M')}"
                        
                        if diff_mins > 30:
                            st.markdown(f"⚪ **尚未到期** (剩餘 {int(diff_mins)} 分)<br>📍 **{task['bed']}** - {task['task']}{freq_badge}<br>🕒 設定: {task['target_time'].strftime('%H:%M')}", unsafe_allow_html=True)
                        elif 0 < diff_mins <= 30:
                            st.success(f"🟢 **即將執行** (剩餘 {int(diff_mins)} 分)\n\n{display_text}")
                        elif -30 <= diff_mins <= 0:
                            st.warning(f"🟡 **已超時** (超時 {int(abs(diff_mins))} 分)\n\n{display_text}")
                        else:
                            st.error(f"🔴 **嚴重超時** (超時 {int(abs(diff_mins))} 分)\n\n{display_text}")

                    with task_col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        cancel_key = f"confirm_cancel_{task['id']}"
                        
                        if not st.session_state.get(cancel_key, False):
                            if st.button("✅ 完成", key=f"done_{task['id']}", use_container_width=True):
                                current_tasks = load_tasks()
                                for t in current_tasks:
                                    if t['id'] == task['id']:
                                        t['status'] = 'done'
                                        t['actual_time'] = datetime.datetime.now(tw_tz)
                                        if t['freq'] in ISO_SCHEDULE:
                                            next_time = get_next_iso_time(t['target_time'], t['freq'])
                                            current_tasks.append({
                                                "id": str(uuid.uuid4()),
                                                "area": t.get('area'),
                                                "bed": t['bed'], "task": t['task'], "target_time": next_time,
                                                "status": "pending", "actual_time": None, "freq": t['freq']
                                            })
                                save_tasks(current_tasks)
                                st.toast("✅ 任務已完成！")
                                st.rerun()
                                
                            if st.button("❌ 取消", key=f"init_cancel_{task['id']}", use_container_width=True):
                                st.session_state[cancel_key] = True
                                st.rerun()
                        
                        else:
                            st.error("確定取消此醫囑？")
                            if st.button("⭕ 確定", key=f"yes_cancel_{task['id']}", use_container_width=True):
                                current_tasks = load_tasks()
                                for t in current_tasks:
                                    if t['id'] == task['id']:
                                        t['status'] = 'cancelled'
                                        t['actual_time'] = datetime.datetime.now(tw_tz)
                                save_tasks(current_tasks)
                                st.session_state[cancel_key] = False
                                st.toast("🚫 已取消此醫囑！")
                                st.rerun()
                                
                            if st.button("返回", key=f"no_cancel_{task['id']}", use_container_width=True):
                                st.session_state[cancel_key] = False
                                st.rerun()

        if has_alert:
            components.html("""
            <script>
                const parentDoc = window.parent.document;
                if (!window.parent.flashInterval) {
                    let isFlashing = false;
                    window.parent.flashInterval = setInterval(() => {
                        parentDoc.title = isFlashing ? "⚠️【超時警告】ER 提示器" : "🚨 ER 提示器";
                        isFlashing = !isFlashing;
                    }, 1000);
                }
            </script>
            """, height=0, width=0)
        else:
            components.html("""
            <script>
                if (window.parent.flashInterval) {
                    clearInterval(window.parent.flashInterval);
                    window.parent.flashInterval = null;
                }
                window.parent.document.title = "🚨 ER 提示器";
            </script>
            """, height=0, width=0)

# ------------------------------------------
# 分頁 2 (新增)：全觀儀表板 (Leader 上帝視角)
# ------------------------------------------
with tab_dash:
    st.subheader("👁️ ER 全單位待辦戰情中心")
    now_tw = datetime.datetime.now(tw_tz)
    
    dash_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]
    
    if not dash_tasks:
        st.success("🎉 目前全單位沒有任何待辦任務，系統清空，完美交班！")
    else:
        # 計算戰力指標
        total_active = len(dash_tasks)
        overdue_cnt = sum(1 for t in dash_tasks if (t['target_time'] - now_tw).total_seconds() / 60 <= 0)
        warning_cnt = sum(1 for t in dash_tasks if 0 < (t['target_time'] - now_tw).total_seconds() / 60 <= 30)
        safe_cnt = total_active - overdue_cnt - warning_cnt
        
        # 1. 頂部四大指標
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🏥 總待辦任務", f"{total_active} 件")
        m2.metric("🚨 已超時 (需優先處理)", f"{overdue_cnt} 件")
        m3.metric("🟢 30分內即將到期", f"{warning_cnt} 件")
        m4.metric("⚪ 尚未到期 (>30分)", f"{safe_cnt} 件")
        
        st.markdown("---")
        
        dash_col1, dash_col2 = st.columns(2)
        
        # 2. 區域塞車排行 (長條圖)
        with dash_col1:
            st.markdown("##### 📍 各區域待辦數量分佈")
            area_counts = {}
            for t in dash_tasks:
                a = t.get('area', '未知區')
                area_counts[a] = area_counts.get(a, 0) + 1
            
            if area_counts:
                df_area = pd.DataFrame(list(area_counts.items()), columns=['區域', '任務數']).set_index('區域')
                st.bar_chart(df_area)

        # 3. 處置熱點排行 (長條圖)
        with dash_col2:
            st.markdown("##### 🩺 待辦處置熱點統計")
            # 統計關鍵字出現次數
            keywords = ["抽血", "測血糖", "EKG", "on cath", "傷口護理", "放射科", "內視鏡", "Foley", "NG"]
            kw_counts = {kw: 0 for kw in keywords}
            
            for t in dash_tasks:
                for kw in keywords:
                    if kw in t['task']:
                        kw_counts[kw] += 1
                        
            # 過濾掉 0 的項目
            active_kw_counts = {k: v for k, v in kw_counts.items() if v > 0}
            
            if active_kw_counts:
                df_kw = pd.DataFrame(list(active_kw_counts.items()), columns=['處置項目', '數量']).set_index('處置項目')
                st.bar_chart(df_kw)
            else:
                st.info("目前無特殊處置項目待辦。")

# ------------------------------------------
# 分頁 3：歷史紀錄 (完成與取消區)
# ------------------------------------------
with tab2:
    st.subheader("📝 歷史紀錄 (點錯可隨時復原)")
    history_tasks = [t for t in st.session_state.tasks if t["status"] in ["done", "cancelled"]]
    
    if not history_tasks:
        st.info("目前尚無歷史紀錄。")
    else:
        history_tasks = sorted(history_tasks, key=lambda x: x["actual_time"], reverse=True)
        for task in history_tasks:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    freq_badge = f" 🔁 **{task['freq']}**" if task['freq'] != "單次" else ""
                    if task["status"] == "done":
                        st.success(f"✔️ **{task['bed']}** 已完成：{task['task']}{freq_badge}\n\n🕒 原設定: {task['target_time'].strftime('%H:%M')} ｜ 實際操作: {task['actual_time'].strftime('%H:%M')}")
                    else:
                        st.error(f"🚫 **{task['bed']}** **已取消醫囑**：{task['task']}{freq_badge}\n\n🕒 原設定: {task['target_time'].strftime('%H:%M')} ｜ 實際操作: {task['actual_time'].strftime('%H:%M')}")
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("↩️ 復原", key=f"undo_{task['id']}", use_container_width=True):
                        current_tasks = load_tasks()
                        for t in current_tasks:
                            if t['id'] == task['id']:
                                t['status'] = 'pending'
                                t['actual_time'] = None
                        save_tasks(current_tasks)
                        st.toast("↩️ 醫囑已復原至待辦清單！")
                        st.rerun()

# ------------------------------------------
# 分頁 4：後台數據追蹤與匯出
# ------------------------------------------
with tab3:
    st.subheader("🔒 管理員專區")
    admin_pw = st.text_input("請輸入管理員密碼以解鎖後台：", type="password")
    
    if admin_pw == "ALEX":
        st.success("解鎖成功！")
        st.markdown("---")
        
        done_tasks = [t for t in st.session_state.tasks if t["status"] == "done"]
        cancelled_tasks = [t for t in st.session_state.tasks if t["status"] == "cancelled"]
        
        total_done = len(done_tasks)
        total_cancelled = len(cancelled_tasks)
        on_time_count = sum(1 for t in done_tasks if (t["actual_time"] - t["target_time"]).total_seconds() / 60 <= 60)
        overdue_count = total_done - on_time_count
        on_time_rate = round((on_time_count / total_done) * 100, 1) if total_done > 0 else 0

        met_col1, met_col2, met_col3, met_col4 = st.columns(4)
        met_col1.metric("總完成 (不含取消)", f"{total_done} 件")
        met_col2.metric("✅ 達標 (含1小時)", f"{on_time_count} 件")
        met_col3.metric("🚨 嚴重超時", f"{overdue_count} 件")
        met_col4.metric("🏆 達標率", f"{on_time_rate} %")
        
        df_data = []
        for t in (done_tasks + cancelled_tasks):
            diff_mins = round((t['actual_time'] - t['target_time']).total_seconds() / 60, 1)
            
            if t['status'] == 'cancelled':
                status_str = "已取消 (DC)"
            else:
                status_str = "是" if diff_mins <= 60 else "否"
                
            df_data.append({
                "狀態": "完成" if t['status'] == 'done' else "取消",
                "床號": t['bed'], "待做事項": t['task'], "頻率": t['freq'],
                "目標時間": t['target_time'].strftime('%Y-%m-%d %H:%M'),
                "實際操作時間": t['actual_time'].strftime('%Y-%m-%d %H:%M:%S'),
                "是否達標": status_str, "時間差(分)": diff_mins if t['status'] == 'done' else ""
            })
            
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載 CSV 完整紀錄", data=csv, file_name=f"ER_Log_{datetime.datetime.now(tw_tz).strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ 清空歷史資料 (交班使用)", type="primary", use_container_width=True):
                save_tasks([])
                st.toast("🗑️ 資料已清空！")
                st.rerun()
    elif admin_pw != "":
        st.error("❌ 密碼錯誤！")
