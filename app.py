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

# --- 資料庫設定 ---
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
# 進貨、銷售表
for tbl in ['進貨','銷售']:
    c.execute(f'''
    CREATE TABLE IF NOT EXISTS {tbl} (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
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
# 補貨提醒表
c.execute('''
CREATE TABLE IF NOT EXISTS 補貨提醒 (
    細項編號 INTEGER PRIMARY KEY,
    提醒 INTEGER,
    FOREIGN KEY(細項編號) REFERENCES 細項(細項編號)
)''')
conn.commit()

# --- 輔助函式 ---
def 查询表(table):
    return pd.read_sql(f'SELECT * FROM {table}', conn)

def 新增類別(name):
    try:
        c.execute('INSERT INTO 類別 (類別名稱) VALUES (?)',(name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass

def 新增品項(cat_id, name):
    c.execute('INSERT INTO 品項 (類別編號, 品項名稱) VALUES (?,?)',(cat_id,name))
    conn.commit()

def 新增細項(item_id, name):
    c.execute('INSERT INTO 細項 (品項編號, 細項名稱) VALUES (?,?)',(item_id,name))
    conn.commit()

def get_categories():
    df = 查询表('類別')
    df.columns = df.columns.str.strip()
    if '類別名稱' in df.columns and '類別編號' in df.columns:
        return dict(zip(df['類別名稱'], df['類別編號']))
    return {}

def get_items(cat_id):
    df = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cat_id,))
    df.columns = df.columns.str.strip()
    if '品項名稱' in df.columns and '品項編號' in df.columns:
        return dict(zip(df['品項名稱'], df['品項編號']))
    return {}

def get_subitems(item_id):
    df = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(item_id,))
    df.columns = df.columns.str.strip()
    if '細項名稱' in df.columns and '細項編號' in df.columns:
        return dict(zip(df['細項名稱'], df['細項編號']))
    return {}

def 新增進貨(cat_id,item_id,sub_id,qty,price):
    total = qty*price
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO 進貨 (類別編號,品項編號,細項編號,數量,單價,總價,日期) VALUES (?,?,?,?,?,?,?)',
              (cat_id,item_id,sub_id,qty,price,total,date))
    conn.commit()

def 新增銷售(cat_id,item_id,sub_id,qty,price):
    total = qty*price
    date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO 銷售 (類別編號,品項編號,細項編號,數量,單價,總價,日期) VALUES (?,?,?,?,?,?,?)',
              (cat_id,item_id,sub_id,qty,price,total,date))
    conn.commit()

def 設定提醒(sub_id,flag):
    c.execute('REPLACE INTO 補貨提醒 (細項編號,提醒) VALUES (?,?)',(sub_id,1 if flag else 0))
    conn.commit()

# --- Streamlit UI ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', ['類別管理','品項管理','細項管理','進貨','銷售','儀表板'])

if menu=='類別管理':
    st.title('⚙️ 類別管理')
    df = 查询表('類別')
    st.table(df)
    name=st.text_input('新增類別')
    if st.button('新增類別') and name:
        新增類別(name); st.experimental_rerun()

elif menu=='品項管理':
    st.title('⚙️ 品項管理')
    cats = get_categories()
    if not cats:
        st.warning('請先至「類別管理」新增至少一個類別')
        st.stop()
    cat = st.selectbox('選擇類別', list(cats.keys()))
    df = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cats[cat],))
    st.table(df)
    name = st.text_input('新增品項')
    if st.button('新增品項') and name:
        新增品項(cats[cat], name)
        st.experimental_rerun()

elif menu=='細項管理':
    st.title('⚙️ 細項管理')
    cats=get_categories(); cat=st.selectbox('類別',list(cats.keys()))
    items=get_items(cats[cat]); item=st.selectbox('品項',list(items.keys()))
    df = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(items[item],))
    st.table(df)
    name=st.text_input('新增細項')
    if st.button('新增細項') and name:
        新增細項(items[item],name); st.experimental_rerun()

elif menu=='進貨':
    st.title('➕ 新增進貨')
    # 選擇類別並取得ID
    cat_items = list(get_categories().items())
    if not cat_items:
        st.warning('請先新增類別')
        st.stop()
    cat_name, cat_id = st.selectbox('類別', cat_items, format_func=lambda x: x[0])
    # 選擇品項並取得ID
    item_items = list(get_items(cat_id).items())
    if not item_items:
        st.warning('該分類尚無品項，請先新增品項')
        st.stop()
    item_name, item_id = st.selectbox('品項', item_items, format_func=lambda x: x[0])
    # 選擇細項並取得ID
    sub_items = list(get_subitems(item_id).items())
    if not sub_items:
        st.warning('該品項尚無細項，請先新增細項')
        st.stop()
    sub_name, sub_id = st.selectbox('細項', sub_items, format_func=lambda x: x[0])
    # 數量與單價
    qty = st.number_input('數量', 1)
    price = st.number_input('單價', 0.0, format='%.2f')
    if st.button('記錄進貨'):
        新增進貨(cat_id, item_id, sub_id, qty, price)
        st.success('完成')

elif menu=='銷售':
    st.title('➕ 新增銷售')
    cat_items = list(get_categories().items())
    if not cat_items:
        st.warning('請先新增類別')
        st.stop()
    cat_name, cat_id = st.selectbox('類別', cat_items, format_func=lambda x: x[0])
    item_items = list(get_items(cat_id).items())
    if not item_items:
        st.warning('該分類尚無品項，請先新增品項')
        st.stop()
    item_name, item_id = st.selectbox('品項', item_items, format_func=lambda x: x[0])
    sub_items = list(get_subitems(item_id).items())
    if not sub_items:
        st.warning('該品項尚無細項，請先新增細項')
        st.stop()
    sub_name, sub_id = st.selectbox('細項', sub_items, format_func=lambda x: x[0])
    qty = st.number_input('數量', 1)
    price = st.number_input('單價', 0.0, format='%.2f')
    if st.button('記錄銷售'):
        新增銷售(cat_id, item_id, sub_id, qty, price)
        st.success('完成')

else:
    st.title('➕ 新增銷售')
    cats=get_categories(); cat=st.selectbox('類別',list(cats.keys()))
    items=get_items(cats[cat]); item=st.selectbox('品項',list(items.keys()))
    subs=get_subitems(items[item]); sub=st.selectbox('細項',list(subs.keys()))
    qty=st.number_input('數量',1); price=st.number_input('單價',0.0,format='%.2f')
    if st.button('記錄銷售'):
        新增銷售(cats[cat],items[item],subs[sub],qty,price); st.success('完成')

else:
    st.title('📊 庫存儀表板')
    df_p=pd.read_sql('SELECT * FROM 進貨',conn)
    df_s=pd.read_sql('SELECT * FROM 銷售',conn)
    df_c=pd.read_sql('SELECT * FROM 類別',conn)
    df_i=pd.read_sql('SELECT * FROM 品項',conn)
    df_su=pd.read_sql('SELECT * FROM 細項',conn)
    df_p=df_p.merge(df_c,on='類別編號').merge(df_i,on='品項編號').merge(df_su,on='細項編號')
    df_s=df_s.merge(df_c,on='類別編號').merge(df_i,on='品項編號').merge(df_su,on='細項編號')
    grp_p=df_p.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(進貨=('數量','sum'))
    grp_s=df_s.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(銷售=('數量','sum'))
    summary=grp_p.merge(grp_s,on=['類別名稱','品項名稱','細項名稱'],how='outer').fillna(0)
    summary['庫存']=summary['進貨']-summary['銷售']
    st.dataframe(summary)
    total_exp=df_p['總價'].sum(); total_rev=df_s['總價'].sum()
    st.subheader('💰 財務概況'); st.metric('總支出',f"{total_exp:.2f}"); st.metric('總收入',f"{total_rev:.2f}"); st.metric('淨利',f"{total_rev-total_exp:.2f}")
