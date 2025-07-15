# 輕珠寶設計師專屬庫存管理系統
#
# 專案結構：
# inventory_system/
# ├── app.py
# ├── requirements.txt
# ├── integrated_inventory.csv (可選匯入檔)
# └── database.db (自動建立)

import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- 資料庫設定 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 類別表
c.execute('''
CREATE TABLE IF NOT EXISTS 類別 (
    編號 INTEGER PRIMARY KEY,
    名稱 TEXT UNIQUE
)''')
# 進貨與銷售表 (新增細項欄位)
for tbl in ['進貨', '銷售']:
    c.execute(f'''
    CREATE TABLE IF NOT EXISTS {tbl} (
        編號 INTEGER PRIMARY KEY,
        類別編號 INTEGER,
        品項 TEXT,
        細項 TEXT,
        數量 INTEGER,
        單價 REAL,
        總價 REAL,
        日期 TEXT,
        FOREIGN KEY(類別編號) REFERENCES 類別(編號)
    )
    ''')
# 補貨提醒表
c.execute('''
CREATE TABLE IF NOT EXISTS 補貨提醒 (
    類別編號 INTEGER,
    品項 TEXT,
    細項 TEXT,
    提醒 INTEGER,
    PRIMARY KEY(類別編號, 品項, 細項)
)''')
conn.commit()

# --- 輔助函式 ---
def 取得類別():
    rows = c.execute('SELECT 編號, 名稱 FROM 類別').fetchall()
    return {name: id for id, name in rows}

def 新增類別(name):
    try:
        c.execute('INSERT INTO 類別 (名稱) VALUES (?)', (name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def 新增進貨(cat_id, item, subitem, qty, price, date=None):
    total = qty * price
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        'INSERT INTO 進貨 (類別編號, 品項, 細項, 數量, 單價, 總價, 日期) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (cat_id, item, subitem, qty, price, total, date)
    )
    conn.commit()

def 新增銷售(cat_id, item, subitem, qty, price, date=None):
    total = qty * price
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute(
        'INSERT INTO 銷售 (類別編號, 品項, 細項, 數量, 單價, 總價, 日期) VALUES (?, ?, ?, ?, ?, ?, ?)',
        (cat_id, item, subitem, qty, price, total, date)
    )
    conn.commit()

def 設定提醒(cat_id, item, subitem, flag):
    c.execute(
        'REPLACE INTO 補貨提醒 (類別編號, 品項, 細項, 提醒) VALUES (?, ?, ?, ?)',
        (cat_id, item, subitem, 1 if flag else 0)
    )
    conn.commit()

# --- 自動匯入整合 CSV ---
IMPORT_PATH = 'integrated_inventory.csv'
if os.path.exists(IMPORT_PATH):
    df_imp = pd.read_csv(IMPORT_PATH)
    for idx, row in df_imp.iterrows():
        cat = row.get('類別') or row.get('Category')
        item = row.get('品項') or row.get('Item')
        subitem = row.get('細項') or ''
        if pd.isna(cat) or pd.isna(item):
            continue
        新增類別(cat)
        cats = 取得類別()
        cid = cats.get(cat)
        start_qty = int(row.get('起始數量', 0)) if pd.notna(row.get('起始數量')) else 0
        price_raw = row.get('起始單價') or row.get('單價') or 0
        try:
            price = float(str(price_raw).replace('NT$', '').replace(',', ''))
        except:
            price = 0.0
        if start_qty > 0:
            新增進貨(cid, item, subitem, start_qty, price, row.get('日期'))
        dec = int(row.get('減少', 0)) if pd.notna(row.get('減少')) else 0
        if dec > 0:
            新增銷售(cid, item, subitem, dec, price, row.get('日期'))
        remind = bool(row.get('需補貨提醒', False))
        設定提醒(cid, item, subitem, remind)

# --- Streamlit 應用 ---
st.sidebar.title('庫存管理系統')
選單 = st.sidebar.radio('功能選單', ['儀表板', '類別管理', '新增進貨', '新增銷售', '檢視紀錄', '匯入/匯出'])

if 選單 == '匯入/匯出':
    st.title('📥 匯入 / 匯出')
    up = st.file_uploader('上傳 integrated_inventory.csv', type='csv')
    if up:
        with open(IMPORT_PATH, 'wb') as f:
            f.write(up.getbuffer())
        st.success('檔案已儲存，請重新啟動匯入')
    if st.button('匯出當前庫存'):
        df_p = pd.read_sql('SELECT * FROM 進貨', conn)
        df_s = pd.read_sql('SELECT * FROM 銷售', conn)
        df_r = pd.read_sql('SELECT * FROM 補貨提醒', conn)
        df = df_p.merge(df_s, on=['類別編號', '品項', '細項'], how='outer', suffixes=('_進貨', '_銷售'))
        df = df.merge(df_r, on=['類別編號', '品項', '細項'], how='left')
        df.to_csv('exported_inventory.csv', index=False)
        st.download_button('下載 exported_inventory.csv', 'exported_inventory.csv', 'text/csv')

elif 選單 == '儀表板':
    st.title('📊 庫存儀表板')
    df_p = pd.read_sql('SELECT 類別編號, 品項, 細項, SUM(數量) AS 進貨數量, SUM(總價) AS 支出 FROM 進貨 GROUP BY 類別編號, 品項, 細項', conn)
    df_s = pd.read_sql('SELECT 類別編號, 品項, 細項, SUM(數量) AS 銷售數量, SUM(總價) AS 收入 FROM 銷售 GROUP BY 類別編號, 品項, 細項', conn)
    df_p.columns = ['類別編號', '品項', '細項', '進貨數量', '支出']
    df_s.columns = ['類別編號', '品項', '細項', '銷售數量', '收入']
    summary = df_p.merge(df_s, on=['類別編號', '品項', '細項'], how='outer').fillna(0)
    summary['庫存'] = summary['進貨數量'] - summary['銷售數量']
    cats = {v: k for k, v in 取得類別().items()}
    summary['類別'] = summary['類別編號'].map(cats)
    st.dataframe(summary[['類別', '品項', '細項', '進貨數量', '銷售數量', '庫存']])
    total_exp = summary['支出'].sum()
    total_rev = summary['收入'].sum()
    st.subheader('💰 財務概況')
    st.metric('總支出', f"{total_exp:.2f}")
    st.metric('總收入', f"{total_rev:.2f}")
    st.metric('淨利潤', f"{total_rev - total_exp:.2f}")
    rems = pd.read_sql('SELECT * FROM 補貨提醒 WHERE 提醒=1', conn)
    if not rems.empty:
        st.subheader('⚠️ 需補貨清單')
        for _, r in rems.iterrows():
            cat_name = {v: k for k, v in 取得類別().items()}.get(r['類別編號'], '')
            st.warning(f"{cat_name} / {r['品項']} / {r['細項']} 需補貨")

elif 選單 == '類別管理':
    st.title('⚙️ 類別管理')
    with st.form('f_cat'):
        n = st.text_input('新增類別名稱')
        if st.form_submit_button('新增') and n:
            新增類別(n)
            st.success(f"已新增：{n}")
    st.table(pd.DataFrame(取得類別().items(), columns=['類別', '編號']))

elif 選單 == '新增進貨':
    st.title('➕ 新增進貨')
    cats = 取得類別()
    with st.form('f_p'):
        cat_sel = st.selectbox('類別', list(cats.keys()))
        item = st.text_input('品項名稱')
        sub = st.text_input('細項說明')
        q = st.number_input('數量', min_value=1, value=1)
        p = st.number_input('單價', min_value=0.0, format='%.2f')
        if st.form_submit_button('儲存'):
            新增進貨(cats[cat_sel], item, sub, q, p)
            st.success('已記錄進貨')

elif 選單 == '新增銷售':
    st.title('➕ 新增銷售')
    cats = 取得類別()
    with st.form('f_s'):
        cat_sel = st.selectbox('類別', list(cats.keys()))
        item = st.text_input('品項名稱')
        sub = st.text_input('細項說明')
        q = st.number_input('數量', min_value=1, value=1)
        p = st.number_input('單價', min_value=0.0, format='%.2f')
        if st.form_submit_button('儲存'):
            新增銷售(cats[cat_sel], item, sub, q, p)
            st.success('已記錄銷售')

elif 選單 == '檢視紀錄':
    st.title('📚 檢視所有紀錄')
    df_p = pd.read_sql('SELECT * FROM 進貨 ORDER BY 日期 DESC', conn)
    df_s = pd.read_sql('SELECT * FROM 銷售 ORDER BY 日期 DESC', conn)
    df_c = pd.read_sql('SELECT 編號, 名稱 FROM 類別', conn)
    df_p = df_p.merge(df_c, left_on='類別編號', right_on='編號', how='left')
    df_s = df_s.merge(df_c, left_on='類別編號', right_on='編號', how='left')
    st.subheader('進貨紀錄')
    st.dataframe(
        df_p[['編號_x', '日期', '名稱', '品項', '細項', '數量', '單價']]
        .rename(columns={'編號_x': '編號', '名稱': '類別'})
    )
    st.subheader('銷售紀錄')
    st.dataframe(
        df_s[['編號_x', '日期', '名稱', '品項', '細項', '數量', '單價']]
        .rename(columns={'編號_x': '編號', '名稱': '類別'})
    )

# requirements.txt
# streamlit
# pandas
