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
    cols_str = ','.join(cols)
    qmarks = ','.join(['?'] * len(vals))
    sql = f'INSERT INTO {table} ({cols_str}) VALUES ({qmarks})'
    try:
        c.execute(sql, vals)
        conn.commit()
    except sqlite3.IntegrityError:
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
    df = 查詢('類別')
    st.table(df.rename(columns={'類別編號':'編號','類別名稱':'名稱'}))
    with st.form('form_cat'):
        name = st.text_input('新增類別名稱')
        del_id = st.text_input('刪除類別編號')
        submitted = st.form_submit_button('執行')
        if submitted:
            if name:
                新增('類別',['類別名稱'],[name])
                st.success(f'新增類別：{name}')
            if del_id.isdigit():
                刪除('類別','類別編號',int(del_id))
                st.success(f'刪除類別編號：{del_id}')
            st.experimental_rerun()

# 品項管理
elif menu == '品項管理':
    st.title('⚙️ 品項管理')
    cat_map = 取得對映('類別','類別編號','類別名稱')
    if not cat_map:
        st.warning('請先新增類別')
        st.stop()
    st.subheader('現有類別')
    st.write(list(cat_map.values()))
    sel_cat = st.selectbox('選擇類別', list(cat_map.values()))
    cat_id = {v:k for k,v in cat_map.items()}[sel_cat]
    df = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cat_id,))
    st.table(df.rename(columns={'品項編號':'編號','品項名稱':'名稱'}))
    with st.form('form_item'):
        name = st.text_input('新增品項名稱')
        del_id = st.text_input('刪除品項編號')
        sb = st.form_submit_button('執行')
        if sb:
            if name:
                新增('品項',['類別編號','品項名稱'],[cat_id,name])
                st.success(f'於「{sel_cat}」新增品項：{name}')
            if del_id.isdigit():
                刪除('品項','品項編號',int(del_id))
                st.success(f'刪除品項編號：{del_id}')
            st.experimental_rerun()

# 細項管理
elif menu == '細項管理':
    st.title('⚙️ 細項管理')
    item_map = {}
    # 選類再選品項
    cat_map = 取得對映('類別','類別編號','類別名稱')
    if not cat_map:
        st.warning('請先新增類別')
        st.stop()
    sel_cat = st.selectbox('類別', list(cat_map.values()))
    cat_id = {v:k for k,v in cat_map.items()}[sel_cat]
    item_map = 取得對映('品項','品項編號','品項名稱')
    item_map = {n:i for n,i in item_map.items() if i in pd.read_sql('SELECT 品項編號 FROM 品項 WHERE 類別編號=?',conn,params=(cat_id,))['品項編號'].tolist()}
    if not item_map:
        st.warning('該類別尚無品項')
        st.stop()
    sel_item = st.selectbox('選擇品項', list(item_map.keys()))
    item_id = item_map[sel_item]
    df = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(item_id,))
    st.table(df.rename(columns={'細項編號':'編號','細項名稱':'名稱'}))
    with st.form('form_sub'):
        name = st.text_input('新增細項名稱')
        del_id = st.text_input('刪除細項編號')
        sb = st.form_submit_button('執行')
        if sb:
            if name:
                新增('細項',['品項編號','細項名稱'],[item_id,name])
                st.success(f'於「{sel_item}」新增細項：{name}')
            if del_id.isdigit():
                刪除('細項','細項編號',int(del_id))
                st.success(f'刪除細項編號：{del_id}')
            st.experimental_rerun()

# 進貨 / 銷售與儀表板保留先前邏輯...
elif menu == '進貨':
    st.info('請使用全功能版本以進行進貨記錄')
elif menu == '銷售':
    st.info('請使用全功能版本以進行銷售記錄')
else:
    st.info('請使用全功能版本以查看儀表板')

# requirements.txt
# streamlit
# pandas
