import streamlit as st
import streamlit.components.v1 as components
import datetime
from datetime import timezone, timedelta
import pandas as pd
import json
import os
import uuid

# --- 網頁基礎設定 ---
# 將 initial_sidebar_state 設為 collapsed，讓 iPad 打開時預設收合左側欄
st.set_page_config(page_title="🚨 ER 提示器", layout="wide", initial_sidebar_state="collapsed")
tw_tz = timezone(timedelta(hours=8))
DATA_FILE = "er_tasks_data.json"

# ==========================================
# 側邊欄：保護聲明與著作權 (加入摺疊功能)
# ==========================================
with st.sidebar:
    st.header("⚖️ 系統資訊")
    
    # 用 expander 將長篇幅的聲明收合起來
    with st.expander("📝 展開查看保護與隱私聲明", expanded=False):
        st.warning("⚠️ **免責聲明**\n\n本系統僅供臨床交班與待辦事項輔助提醒，**並非正式醫療紀錄（HIS）系統**。所有醫療處置、給藥時間與醫囑變更，請一律以醫院主系統與醫師正式醫囑為準。")
        st.info("💡 **資料隱私**\n\n本系統為便利交班之輔助工具，請盡量以「床號」代替病患全名，切勿輸入身分證字號等敏感個資，以符合 HIPAA 及相關隱私法規。")
    
    st.markdown("---")
    st.markdown("##### 👨‍⚕️ 開發者資訊")
    st.markdown("© 2026 Developed by **護理師 吳智弘** \n*(花蓮慈濟醫學中心 急診部)*")
    st.caption("All Rights Reserved.\n僅供單位內部輔助使用，未經授權請勿作商業用途。")

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
    if freq not in ISO_SCHEDULE: return base_time + datetime.timedelta(hours=2)
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
                if d.get('actual_time'): d['actual_time'] = datetime.datetime.fromisoformat(d['actual_time'])
                if 'freq' not in d: d['freq'] = '單次'
                if 'area' not in d: d['area'] = '舊版資料'
                if 'reason' not in d: d['reason'] = ""
            return data
    except: return []

def save_tasks(tasks):
    safe_tasks = []
    for t in tasks:
        task_dict = t.copy()
        task_dict['target_time'] = t['target_time'].isoformat()
        if t.get('actual_time'): task_dict['actual_time'] = t['actual_time'].isoformat()
        safe_tasks.append(task_dict)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(safe_tasks, f, ensure_ascii=False, indent=2)

st.session_state.tasks = load_tasks()

# ==========================================
# 前台介面開始
# ==========================================
title_col, sync_col = st.columns([4, 1])
with title_col: st.title("🚨 急診留觀：智能待辦與交班提示器")
with sync_col:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔄 同步最新資料", use_container_width=True): st.rerun()

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
        chk_col1, chk_col2, chk_col3 = st.columns(3)
        selected_tasks = []
        with chk_col1:
            for i in ["體溫", "血壓", "疼痛", "EKG"]:
                if st.checkbox(i): selected_tasks.append(i)
        with chk_col2:
            for i in ["呼吸", "血氧", "病解", "NG"]:
                if st.checkbox(i): selected_tasks.append(i)
        with chk_col3:
            on_cath_check = st.checkbox("on cath")
            if st.checkbox("Foley"): selected_tasks.append("Foley")
            if st.checkbox("🩸 測血糖"): selected_tasks.append("測血糖")
            other_check = st.checkbox("其他")
            
        st.markdown(" ")
        remove_old_cath, old_cath_location = False, ""
        if on_cath_check:
            remove_old_cath = st.checkbox("🔄 是否移除原 cath？")
            if remove_old_cath: old_cath_location = st.text_input("輸入原 cath 位置")

        other_text = st.text_input("輸入其他待做事項") if other_check else ""
        blood_draw = st.checkbox("💉 抽血")
        blood_tests = st.text_input("輸入檢驗項目") if blood_draw else ""
        wound_care = st.checkbox("🩹 傷口護理")
        wound_details = st.text_input("輸入換藥部位與方式") if wound_care else ""

        st.markdown("---")
        exam_col1, exam_col2 = st.columns(2)
        with exam_col1:
            radio_exam = st.checkbox("☢️ 放射科檢查")
            radio_items = st.multiselect("選擇放射科項目", ["X光", "CT", "MRI"]) if radio_exam else []
        with exam_col2:
            endo_exam = st.checkbox("🩺 內視鏡/超音波")
            endo_items = st.multiselect("選擇檢查項目", ["胃鏡", "大腸鏡", "腹部超音波", "腎臟超音波"]) if endo_exam else []
            endo_scheduled = st.checkbox("✅ 已完成排程") if endo_exam else False

        st.markdown("---")
        freq_option = st.selectbox("🔄 執行頻率", ["單次", "Q2H", "Q4H", "Q6H", "Q8H", "BIDAC", "QIDAC"])
        freq_count_limit = 99
        if freq_option != "單次":
            freq_count_limit = st.number_input("設定執行總次數 (持續性醫囑保留 99)", min_value=1, value=99)
        time_str = st.text_input("設定首次執行時間 (4碼)", max_chars=4, placeholder="0312")

        if st.button("新增提醒", use_container_width=True, type="primary"):
            if on_cath_check: selected_tasks.append(f"on cath(移除舊:{old_cath_location})" if remove_old_cath else "on cath")
            if other_check: selected_tasks.append(f"其他({other_text})")
            if blood_draw: selected_tasks.append(f"抽血({blood_tests})")
            if wound_care: selected_tasks.append(f"傷口護理({wound_details})")
            if radio_exam: selected_tasks.append(f"放射科檢查({','.join(radio_items)})" if radio_items else "放射科檢查")
            if endo_exam: selected_tasks.append(f"消化內視鏡({','.join(endo_items)} - {'已排' if endo_scheduled else '未排'})" if endo_items else f"消化內視鏡({'已排' if endo_scheduled else '未排'})")

            if not full_bed_name.strip() or full_bed_name == "【FRee】": st.error("⚠️ 請填寫或選擇床號！")
            elif not selected_tasks: st.error("⚠️ 請至少勾選一項待做事項！")
            elif len(time_str) != 4 or not time_str.isdigit(): st.error("⚠️ 請輸入4位純數字的時間格式！")
            else:
                try:
                    hour, minute = int(time_str[:2]), int(time_str[2:])
                    parsed_time = datetime.time(hour, minute)
                    now_tw = datetime.datetime.now(tw_tz)
                    target_dt = datetime.datetime.combine(now_tw.date(), parsed_time).replace(tzinfo=tw_tz)
                    if target_dt < now_tw - datetime.timedelta(hours=12): target_dt += datetime.timedelta(days=1)
                        
                    current_tasks = load_tasks()
                    current_tasks.append({
                        "id": str(uuid.uuid4()), "area": area, "bed": full_bed_name, "task": "、".join(selected_tasks),
                        "target_time": target_dt, "status": "pending", "actual_time": None, "reason": "",
                        "freq": freq_option, "freq_total": freq_count_limit, "freq_current": 1
                    })
                    save_tasks(current_tasks); st.toast(f"✅ 已新增 {full_bed_name}！"); st.rerun()
                except ValueError: st.error("⚠️ 時間格式錯誤！")

    with col_right:
        st.subheader("📋 待辦任務看板")
        filt_col1, filt_col2 = st.columns(2)
        with filt_col1: filter_zone = st.selectbox("📍 依區域過濾", ["全區顯示", "🏥 診間全區", "🛏️ OBS全區"] + list(BED_MAP.keys()))
        with filt_col2: filter_task = st.selectbox("🩺 依項目過濾", ["全部顯示", "體溫", "血壓", "疼痛", "EKG", "呼吸", "血氧", "病解", "NG", "on cath", "Foley", "測血糖", "抽血", "傷口護理", "放射科檢查", "消化內視鏡", "其他"])

        now_tw = datetime.datetime.now(tw_tz)
        active_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]

        if filter_zone == "🏥 診間全區": active_tasks = [t for t in active_tasks if "診間" in t.get('area', '')]
        elif filter_zone == "🛏️ OBS全區": active_tasks = [t for t in active_tasks if "OBS" in t.get('area', '')]
        elif filter_zone != "全區顯示": active_tasks = [t for t in active_tasks if t.get('area') == filter_zone]
        if filter_task != "全部顯示": active_tasks = [t for t in active_tasks if filter_task in t['task']]

        has_alert = any((t["target_time"] - now_tw).total_seconds() / 60 <= 30 for t in active_tasks)

        if not active_tasks: st.info("🎉 目前此條件下無待辦任務！")
        else:
            for task in sorted(active_tasks, key=lambda x: x["target_time"]):
                time_diff = task["target_time"] - now_tw
                diff_mins = time_diff.total_seconds() / 60
                
                freq_badge = ""
                if task['freq'] != "單次":
                    progress_str = f" ({task.get('freq_current', 1)}/{task.get('freq_total', 99)})" if task.get('freq_total', 99) != 99 else " (持續)"
                    freq_badge = f" 🔁 **{task['freq']}{progress_str}**"

                with st.container(border=True):
                    task_col1, task_col2 = st.columns([3.5, 1.5])
                    
                    with task_col1:
                        display_text = f"📍 **{task['bed']}** - {task['task']}{freq_badge}\n\n🕒 設定時間: {task['target_time'].strftime('%H:%M')}"
                        
                        if diff_mins > 30:
                            st.markdown(f"⚪ **尚未到期** (距離執行還有 {int(diff_mins)} 分)<br>📍 **{task['bed']}** - {task['task']}{freq_badge}<br>🕒 設定時間: {task['target_time'].strftime('%H:%M')}", unsafe_allow_html=True)
                        elif 0 <= diff_mins <= 30:
                            st.success(f"🟢 **可開始執行** (提前 {int(diff_mins)} 分內)\n\n{display_text}")
                        elif -60 <= diff_mins < 0:
                            grace_left = 60 - int(abs(diff_mins))
                            st.warning(f"🟡 **執行區間內** (距超時剩 {grace_left} 分)\n\n{display_text}")
                        else:
                            overdue_mins = int(abs(diff_mins)) - 60
                            st.error(f"🔴 **嚴重超時** (超過合格範圍 {overdue_mins} 分)\n\n{display_text}")

                    with task_col2:
                        st.markdown("<br>", unsafe_allow_html=True)
                        cancel_key = f"confirm_cancel_{task['id']}"
                        reason_key = f"require_reason_{task['id']}"
                        
                        if st.session_state.get(reason_key, False):
                            st.warning("⚠️ 執行時間異常，請選擇原因：")
                            reason_opt = st.selectbox("異常原因", ["1.依照醫囑延後、提前", "2.病人不在位置上", "3.遺漏執行完成登錄", "4.因忙碌忘記執行", "5.其他 (自行輸入)"], key=f"sel_{task['id']}")
                            other_r = st.text_input("輸入其他原因", key=f"txt_{task['id']}") if "5.其他" in reason_opt else ""
                            
                            sub_c1, sub_c2 = st.columns(2)
                            if sub_c1.button("送出", key=f"sub_{task['id']}", type="primary"):
                                final_reason = other_r if "5.其他" in reason_opt else reason_opt
                                current_tasks = load_tasks()
                                for t in current_tasks:
                                    if t['id'] == task['id']:
                                        t['status'], t['actual_time'], t['reason'] = 'done', datetime.datetime.now(tw_tz), final_reason
                                        if t['freq'] in ISO_SCHEDULE and t.get('freq_current', 1) < t.get('freq_total', 99):
                                            current_tasks.append({
                                                "id": str(uuid.uuid4()), "area": t.get('area'), "bed": t['bed'], "task": t['task'], 
                                                "target_time": get_next_iso_time(t['target_time'], t['freq']), "status": "pending", 
                                                "actual_time": None, "reason": "", "freq": t['freq'], 
                                                "freq_total": t['freq_total'], "freq_current": t['freq_current'] + 1
                                            })
                                save_tasks(current_tasks)
                                st.session_state[reason_key] = False
                                st.toast("✅ 已記錄原因並完成！"); st.rerun()
                                
                            if sub_c2.button("取消", key=f"back_{task['id']}"):
                                st.session_state[reason_key] = False; st.rerun()

                        elif st.session_state.get(cancel_key, False):
                            st.error("確定取消此醫囑？")
                            if st.button("⭕ 確定", key=f"yes_cancel_{task['id']}", use_container_width=True):
                                current_tasks = load_tasks()
                                for t in current_tasks:
                                    if t['id'] == task['id']: t['status'], t['actual_time'] = 'cancelled', datetime.datetime.now(tw_tz)
                                save_tasks(current_tasks); st.session_state[cancel_key] = False; st.toast("🚫 已取消此醫囑！"); st.rerun()
                            if st.button("返回", key=f"no_cancel_{task['id']}", use_container_width=True):
                                st.session_state[cancel_key] = False; st.rerun()

                        else:
                            if st.button("✅ 完成", key=f"done_{task['id']}", use_container_width=True):
                                if diff_mins < -60 or diff_mins > 30:
                                    st.session_state[reason_key] = True
                                    st.rerun()
                                else:
                                    current_tasks = load_tasks()
                                    for t in current_tasks:
                                        if t['id'] == task['id']:
                                            t['status'], t['actual_time'] = 'done', datetime.datetime.now(tw_tz)
                                            if t['freq'] in ISO_SCHEDULE and t.get('freq_current', 1) < t.get('freq_total', 99):
                                                current_tasks.append({
                                                    "id": str(uuid.uuid4()), "area": t.get('area'), "bed": t['bed'], "task": t['task'], 
                                                    "target_time": get_next_iso_time(t['target_time'], t['freq']), "status": "pending", 
                                                    "actual_time": None, "reason": "", "freq": t['freq'], 
                                                    "freq_total": t['freq_total'], "freq_current": t['freq_current'] + 1
                                                })
                                    save_tasks(current_tasks); st.toast("✅ 任務已完成！"); st.rerun()
                                
                            if st.button("❌ 取消醫囑", key=f"init_cancel_{task['id']}", use_container_width=True):
                                st.session_state[cancel_key] = True; st.rerun()

        if has_alert:
            components.html("""
            <script>
                const parentDoc = window.parent.document;
                if (!window.parent.flashInterval) {
                    let isFlashing = false;
                    window.parent.flashInterval = setInterval(() => {
                        parentDoc.title = isFlashing ? "⚠️【即將到期/超時】ER 提示器" : "🚨 ER 提示器";
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
# 分頁 2：全觀儀表板
# ------------------------------------------
with tab_dash:
    st.subheader("👁️ ER 全單位待辦戰情中心")
    now_tw = datetime.datetime.now(tw_tz)
    dash_tasks = [t for t in st.session_state.tasks if t["status"] == "pending"]
    
    if not dash_tasks: st.success("🎉 目前全單位沒有任何待辦任務，系統清空，完美交班！")
    else:
        total_active = len(dash_tasks)
        overdue_cnt = sum(1 for t in dash_tasks if (t['target_time'] - now_tw).total_seconds() / 60 < -60)
        warning_cnt = sum(1 for t in dash_tasks if -60 <= (t['target_time'] - now_tw).total_seconds() / 60 <= 30)
        safe_cnt = total_active - overdue_cnt - warning_cnt
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("🏥 總待辦", f"{total_active} 件")
        m2.metric("🚨 嚴重超時 (>1hr)", f"{overdue_cnt} 件")
        m3.metric("🟢/🟡 執行區間內", f"{warning_cnt} 件")
        m4.metric("⚪ 尚未到期 (>30分)", f"{safe_cnt} 件")
        st.markdown("---")
        dash_col1, dash_col2 = st.columns(2)
        with dash_col1:
            st.markdown("##### 📍 區域待辦數")
            area_counts = {}
            for t in dash_tasks: area_counts[t.get('area', '未知區')] = area_counts.get(t.get('area', '未知區'), 0) + 1
            if area_counts: st.bar_chart(pd.DataFrame(list(area_counts.items()), columns=['區域', '任務數']).set_index('區域'))

        with dash_col2:
            st.markdown("##### 🩺 處置熱點")
            kw_counts = {kw: 0 for kw in ["抽血", "測血糖", "EKG", "on cath", "傷口護理", "放射科", "內視鏡", "Foley", "NG"]}
            for t in dash_tasks:
                for kw in kw_counts.keys():
                    if kw in t['task']: kw_counts[kw] += 1
            active_kw = {k: v for k, v in kw_counts.items() if v > 0}
            if active_kw: st.bar_chart(pd.DataFrame(list(active_kw.items()), columns=['處置項目', '數量']).set_index('處置項目'))
            else: st.info("無特殊處置。")

# ------------------------------------------
# 分頁 3：歷史紀錄 (完成與取消區)
# ------------------------------------------
with tab2:
    st.subheader("📝 歷史紀錄 (點錯可隨時復原)")
    history_tasks = sorted([t for t in st.session_state.tasks if t["status"] in ["done", "cancelled"]], key=lambda x: x["actual_time"], reverse=True)
    
    if not history_tasks: st.info("目前尚無歷史紀錄。")
    else:
        for task in history_tasks:
            with st.container(border=True):
                col1, col2 = st.columns([5, 1])
                with col1:
                    freq_badge = f" 🔁 **{task['freq']} ({task.get('freq_current', 1)}/{task.get('freq_total', 99)})**" if task['freq'] != "單次" else ""
                    if task["status"] == "done":
                        st.success(f"✔️ **{task['bed']}** 已完成：{task['task']}{freq_badge}\n\n🕒 原設定: {task['target_time'].strftime('%H:%M')} ｜ 實際操作: {task['actual_time'].strftime('%H:%M')}")
                    else:
                        st.error(f"🚫 **{task['bed']}** **已取消醫囑**：{task['task']}{freq_badge}\n\n🕒 原設定: {task['target_time'].strftime('%H:%M')} ｜ 實際操作: {task['actual_time'].strftime('%H:%M')}")
                    
                    if task.get('reason'):
                        st.caption(f"💡 異常原因：{task['reason']}")
                        
                with col2:
                    st.markdown("<br>", unsafe_allow_html=True)
                    if st.button("↩️ 復原", key=f"undo_{task['id']}", use_container_width=True):
                        current_tasks = load_tasks()
                        for t in current_tasks:
                            if t['id'] == task['id']: t['status'], t['actual_time'], t['reason'] = 'pending', None, ""
                        save_tasks(current_tasks); st.toast("↩️ 醫囑已復原！"); st.rerun()

# ------------------------------------------
# 分頁 4：後台數據追蹤與匯出
# ------------------------------------------
with tab3:
    st.subheader("🔒 管理員專區")
    admin_pw = st.text_input("請輸入管理員密碼以解鎖後台：", type="password")
    if admin_pw == "6155":
        st.markdown("---")
        done_tasks = [t for t in st.session_state.tasks if t["status"] == "done"]
        cancelled_tasks = [t for t in st.session_state.tasks if t["status"] == "cancelled"]
        
        total_done = len(done_tasks)
        on_time_count = sum(1 for t in done_tasks if -30 <= (t["actual_time"] - t["target_time"]).total_seconds() / 60 <= 60)
        on_time_rate = round((on_time_count / total_done) * 100, 1) if total_done > 0 else 0

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("總完成 (不含取消)", f"{total_done} 件")
        m2.metric("✅ 達標 (-30~+60分)", f"{on_time_count} 件")
        m3.metric("🚨 異常執行時間", f"{total_done - on_time_count} 件")
        m4.metric("🏆 達標率", f"{on_time_rate} %")
        
        df_data = []
        for t in (done_tasks + cancelled_tasks):
            diff_mins = round((t['actual_time'] - t['target_time']).total_seconds() / 60, 1)
            status_str = "已取消 (DC)" if t['status'] == 'cancelled' else ("是" if -30 <= diff_mins <= 60 else "否")
            df_data.append({
                "狀態": "完成" if t['status'] == 'done' else "取消",
                "床號": t['bed'], "待做事項": t['task'], "頻率": t['freq'],
                "目標時間": t['target_time'].strftime('%Y-%m-%d %H:%M'),
                "實際操作時間": t['actual_time'].strftime('%Y-%m-%d %H:%M:%S'),
                "是否達標": status_str, "時間差(分)": diff_mins if t['status'] == 'done' else "",
                "異常原因": t.get('reason', '') 
            })
            
        df = pd.DataFrame(df_data)
        st.dataframe(df, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            st.download_button("📥 下載 CSV 完整紀錄", data=df.to_csv(index=False).encode('utf-8-sig'), file_name=f"ER_Log_{datetime.datetime.now(tw_tz).strftime('%Y%m%d_%H%M')}.csv", mime="text/csv", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ 清空歷史資料 (交班使用)", type="primary", use_container_width=True):
                save_tasks([]); st.toast("🗑️ 資料已清空！"); st.rerun()
    elif admin_pw != "": st.error("❌ 密碼錯誤！")
