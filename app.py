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
c.execute('''CREATE TABLE IF NOT EXISTS 類別 (
    編號 INTEGER PRIMARY KEY,
    名稱 TEXT UNIQUE
)''')
# 進貨及銷售表
for tbl in ['進貨','銷售']:
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS {tbl} (
            編號 INTEGER PRIMARY KEY,
            品項 TEXT,
            類別編號 INTEGER,
            數量 INTEGER,
            單價 REAL,
            總價 REAL,
            日期 TEXT,
            FOREIGN KEY(類別編號) REFERENCES 類別(編號)
        )''')
# 補貨提醒表
c.execute('''CREATE TABLE IF NOT EXISTS 補貨提醒 (
    品項 TEXT PRIMARY KEY,
    提醒 INTEGER
)''')
conn.commit()

# --- 輔助函式 ---
def 取得類別():
    rows = c.execute('SELECT 編號,名稱 FROM 類別').fetchall()
    return {name: id for id, name in rows}

def 新增類別(name):
    try:
        c.execute('INSERT INTO 類別 (名稱) VALUES (?)',(name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def 新增進貨(item,cat_id,qty,price,date=None):
    total = qty * price
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO 進貨 (品項,類別編號,數量,單價,總價,日期) VALUES (?,?,?,?,?,?)',
              (item,cat_id,qty,price,total,date))
    conn.commit()

def 新增銷售(item,cat_id,qty,price,date=None):
    total = qty * price
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO 銷售 (品項,類別編號,數量,單價,總價,日期) VALUES (?,?,?,?,?,?)',
              (item,cat_id,qty,price,total,date))
    conn.commit()

def 設定提醒(item,flag):
    c.execute('REPLACE INTO 補貨提醒 (品項,提醒) VALUES (?,?)',(item,1 if flag else 0))
    conn.commit()

# --- 自動匯入整合 CSV ---
IMPORT_PATH = 'integrated_inventory.csv'
if os.path.exists(IMPORT_PATH):
    df_imp = pd.read_csv(IMPORT_PATH)
    for _, row in df_imp.iterrows():
        cat = row['Category']
        新增類別(cat)
        cats = 取得類別()
        cid = cats[cat]
        # 初始進貨
        start_qty = int(row.get('起始數量',0)) if pd.notna(row.get('起始數量')) else 0
        unit_price = float(str(row.get('起始單價','0')).replace('NT$','').replace(',',''))
        if start_qty>0:
            新增進貨(row['品項'],cid,start_qty,unit_price,row.get('日期'))
        # 減少視為銷售
        dec = int(row.get('減少',0)) if pd.notna(row.get('減少')) else 0
        if dec>0:
            新增銷售(row['品項'],cid,dec,unit_price,row.get('日期'))
        # 設定補貨提醒
        remind_flag = bool(row.get('需補貨提醒'))
        設定提醒(row['品項'],remind_flag)

# --- Streamlit 應用 ---
st.sidebar.title("庫存管理系統")
頁面 = st.sidebar.radio("功能選單", ["儀表板","類別管理","新增進貨","新增銷售","檢視紀錄","匯入/匯出"])

if 頁面 == '匯入/匯出':
    st.title('📥 匯入 / 匯出')
    if os.path.exists(IMPORT_PATH):
        st.success(f"找到匯入檔：{IMPORT_PATH}")
    上傳 = st.file_uploader('上傳 integrated_inventory.csv',type='csv')
    if 上傳:
        with open(IMPORT_PATH,'wb') as f: f.write(上傳.getbuffer())
        st.success('檔案已儲存，請重新啟動匯入')
    if st.button('匯出當前庫存為 CSV'):
        df_p = pd.read_sql('SELECT 品項,類別編號,數量,單價,總價,日期 FROM 進貨',conn)
        df_s = pd.read_sql('SELECT 品項,類別編號,數量,單價,總價,日期 FROM 銷售',conn)
        df_r = pd.read_sql('SELECT * FROM 補貨提醒',conn)
        df = df_p.merge(df_s, on='品項', how='outer', suffixes=('_進貨','_銷售')).merge(df_r,on='品項',how='left')
        df.to_csv('exported_inventory.csv',index=False)
        st.download_button('下載 exported_inventory.csv','exported_inventory.csv','text/csv')

elif 頁面 == "儀表板":
    st.title("📊 庫存儀表板")
    df_p = pd.read_sql('SELECT 品項,類別編號,SUM(數量) as 進貨數量,SUM(總價) as 支出 FROM 進貨 GROUP BY 品項,類別編號',conn)
    df_s = pd.read_sql('SELECT 品項,類別編號,SUM(數量) as 銷售數量,SUM(總價) as 收入 FROM 銷售 GROUP BY 品項,類別編號',conn)
    cats = {v:k for k,v in 取得類別().items()}
    summary = df_p.merge(df_s,on=['品項','類別編號'],how='outer').fillna(0)
    summary['庫存'] = summary['進貨數量'] - summary['銷售數量']
    summary['類別'] = summary['類別編號'].map(cats)
    st.dataframe(summary[['品項','類別','進貨數量','銷售數量','庫存']])
    # 財務概況
    total_exp = summary['支出'].sum()
    total_rev = summary['收入'].sum()
    st.subheader('💰 財務概況')
    st.metric('總支出',f"{total_exp:.2f}")
    st.metric('總收入',f"{total_rev:.2f}")
    st.metric('淨利潤',f"{total_rev-total_exp:.2f}")
    # 補貨提醒
    rems = pd.read_sql('SELECT 品項 FROM 補貨提醒 WHERE 提醒=1',conn)
    if not rems.empty:
        st.subheader('⚠️ 需補貨清單')
        for itm in rems['品項']:
            st.warning(f"{itm} 需補貨")

elif 頁面 == "類別管理":
    st.title("⚙️ 類別管理")
    with st.form("form_cat"):
        名稱 = st.text_input('新增類別名稱')
        if st.form_submit_button('新增') and 名稱:
            新增類別(名稱)
            st.success(f"已新增：{名稱}")
    st.table(pd.DataFrame(取得類別().items(),columns=['類別','編號']))

elif 頁面 == "新增進貨":
    st.title("➕ 新增進貨")
    cats = 取得類別()
    with st.form('form_p'):
        品項 = st.text_input('品項名稱')
        類別選 = st.selectbox('類別',list(cats.keys()))
        數量 = st.number_input('數量',min_value=1,value=1)
        單價 = st.number_input('單價',min_value=0.0,format='%.2f')
        if st.form_submit_button('儲存'):
            新增進貨(品項,cats[類別選],數量,單價)
            st.success('已記錄進貨')

elif 頁面 == "新增銷售":
    st.title("➕ 新增銷售")
    cats = 取得類別()
    with st.form('form_s'):
        品項 = st.text_input('品項名稱')
        類別選 = st.selectbox('類別',list(cats.keys()))
        數量 = st.number_input('數量',min_value=1,value=1)
        單價 = st.number_input('單價',min_value=0.0,format='%.2f')
        if st.form_submit_button('儲存'):
            新增銷售(品項,cats[類別選],數量,單價)
            st.success('已記錄銷售')

else:  # 檢視紀錄
    st.title("📚 檢視所有紀錄")
    dfp = pd.read_sql('SELECT 編號,日期,品項 as 品項,類別.名稱 as 類別,數量 as 數量,單價 as 單價 FROM 進貨 p JOIN 類別 ON p.類別編號=類別.編號 ORDER BY 日期 DESC',conn)
    dfs = pd.read_sql('SELECT 編號,日期,品項 as 品項,類別.名稱 as 類別,數量 as 數量,單價 as 單價 FROM 銷售 s JOIN 類別 ON s.類別編號=類別.編號 ORDER BY 日期 DESC',conn)
    st.subheader('進貨紀錄'); st.dataframe(dfp)
    st.subheader('銷售紀錄'); st.dataframe(dfs)

# requirements.txt:
# streamlit
# pandas
