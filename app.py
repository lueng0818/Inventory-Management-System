# 輕珠寶設計師專屬庫存管理系統
#
# 專案結構：
# inventory_system/
# ├── app.py
# ├── requirements.txt
# └── database.db (自動建立)

import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 類別表
c.execute('''
CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)''')
# 品項表
c.execute('''
CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)''')
# 細項表
c.execute('''
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)''')
# 銷/進貨表
for tbl in ['進貨','銷售']:
    c.execute(f'''
CREATE TABLE IF NOT EXISTS {tbl} (
    紀錄ID INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項編號 INTEGER,
    細項編號 INTEGER,
    數量 INTEGER,
    單價 REAL,
    總價 REAL,
    日期 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號),
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號),
    FOREIGN KEY(細項編號) REFERENCES 細項(細項編號)
)''')
conn.commit()

# --- 輔助函式 ---
def 查詢(table):
    return pd.read_sql(f'SELECT * FROM {table}', conn)

def 新增(table, cols, vals):
    # 動態偵測資料表欄位，跳過第一欄主鍵
    df = 查詢(table)
    cols_all = df.columns.tolist()
    # 排除主鍵 (第一欄)
    target_cols = cols_all[1:1+len(vals)]
    cols_str = ','.join(target_cols)
    qmarks = ','.join(['?'] * len(vals))
    sql = f'INSERT INTO {table} ({cols_str}) VALUES ({qmarks})'
    try:
        c.execute(sql, vals)
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能已重複建立或外鍵限制")
        st.warning("操作失敗：可能已重複建立或外鍵限制")

def 刪除(table, key_col, key_val):
    c.execute(f'DELETE FROM {table} WHERE {key_col}=?', (key_val,))
    conn.commit()

def 取得對映(table, key, val):
    df = 查詢(table)
    df.columns = df.columns.str.strip()
    # 動態尋找包含關鍵字的欄位名稱
    key_col = next((col for col in df.columns if key in col), None)
    val_col = next((col for col in df.columns if val in col), None)
    # 備援檢查：若使用者看到DF列已重新rename為'編號','名稱'
    if not key_col and '編號' in df.columns:
        key_col = '編號'
    if not val_col and '名稱' in df.columns:
        val_col = '名稱'
    if key_col and val_col:
        return dict(zip(df[val_col], df[key_col]))
    st.warning(f"在 {table} 表中找不到含 '{key}' 或 '{val}' 的欄位 (現有: {df.columns.tolist()})")
    return {}

# --- UI ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])

# 類別管理
if menu == '類別管理':
    st.title('⚙️ 類別管理')
    # 顯示現有類別
    df = 查詢('類別')
    df.columns = df.columns.str.strip()
    st.subheader('現有類別列表')
    st.table(df.rename(columns={'類別編號':'編號','類別名稱':'名稱'})[['編號','名稱']])
    # 新增或刪除類別
    with st.form('form_cat'):
        new_name = st.text_input('新增類別名稱')
        del_id = st.text_input('刪除類別編號')
        submitted = st.form_submit_button('執行')
        if submitted:
            if new_name:
                新增('類別',['類別名稱'],[new_name])
                st.success(f'已新增類別：{new_name}')
            if del_id.isdigit():
                刪除('類別','類別編號',int(del_id))
                st.success(f'已刪除類別編號：{del_id}')
            # 自動刷新或提示
            try:
                st.experimental_rerun()
            except AttributeError:
                st.info('請重新整理頁面以更新資料表')

elif menu == '進貨':
    st.info('請使用全功能版本以進行進貨記錄')
elif menu == '銷售':
    st.info('請使用全功能版本以進行銷售記錄')
elif menu == '儀表板':
    # 儀表板：整合進貨與銷售顯示庫存與收支
    st.title('📊 庫存儀表板')
    df_p = pd.read_sql('SELECT * FROM 進貨', conn)
    df_s = pd.read_sql('SELECT * FROM 銷售', conn)
    # 合併類別、品項、細項名稱
    df_c = 查詢('類別'); df_c.columns = df_c.columns.str.strip()
    df_i = 查詢('品項');   df_i.columns = df_i.columns.str.strip()
    df_su= 查詢('細項');   df_su.columns = df_su.columns.str.strip()
    df_p = df_p.merge(df_c, on='類別編號').merge(df_i, on='品項編號').merge(df_su, on='細項編號')
    df_s = df_s.merge(df_c, on='類別編號').merge(df_i, on='品項編號').merge(df_su, on='細項編號')
    grp_p = df_p.groupby(['類別名稱','品項名稱','細項名稱'], as_index=False).agg(進貨=('數量','sum'), 支出=('總價','sum'))
    grp_s = df_s.groupby(['類別名稱','品項名稱','細項名稱'], as_index=False).agg(銷售=('數量','sum'), 收入=('總價','sum'))
    summary = pd.merge(grp_p, grp_s, on=['類別名稱','品項名稱','細項名稱'], how='outer').fillna(0)
    summary['庫存'] = summary['進貨'] - summary['銷售']
    st.dataframe(summary)
    total_exp = grp_p['支出'].sum(); total_rev = grp_s['收入'].sum()
    st.subheader('💰 財務概況')
    st.metric('總支出', f"{total_exp:.2f}")
    st.metric('總收入', f"{total_rev:.2f}")
    st.metric('淨利', f"{total_rev - total_exp:.2f}")
else:
    st.info('請使用全功能版本以查看儀表板')
    st.info('請使用全功能版本以查看儀表板')

# requirements.txt
# streamlit
# pandas
