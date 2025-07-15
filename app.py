import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute('''
CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)''')
c.execute('''
CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)''')
c.execute('''
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)''')
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
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 新增(table, cols, vals):
    df = 查詢(table)
    target = df.columns.tolist()[1:1+len(vals)]
    q = ",".join(target)
    qm = ",".join(["?"]*len(vals))
    try:
        c.execute(f"INSERT INTO {table} ({q}) VALUES ({qm})", vals)
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("操作失敗：重複或外鍵限制")

def 刪除(table, key, val):
    c.execute(f"DELETE FROM {table} WHERE {key}=?", (val,))
    conn.commit()

def 取得對映(table, key_col, val_col):
    # 類別專用
    if table == '類別':
        try:
            rows = conn.execute('SELECT 類別編號, 類別名稱 FROM 類別').fetchall()
            return {name: cid for cid, name in rows}
        except Exception:
            st.warning('類別查詢失敗')
            return {}
    # 通用
    df = 查詢(table)
    df.columns = df.columns.str.strip()
    if key_col not in df.columns or val_col not in df.columns:
        st.warning(f"{table} 欄位 {key_col} 或 {val_col} 不存在")
        return {}
    return dict(zip(df[val_col], df[key_col]))

def 批次匯入進貨(df):
    df = df.rename(columns=str.strip)
    df['買入數量'] = df.get('買入數量', 0).fillna(0)
    df['買入單價'] = df.get('買入單價', 0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r['買入數量'] <= 0: continue
        cat, item, sub = r['類別'], r['品項'], r['細項']
        if pd.isna(cat) or pd.isna(item) or pd.isna(sub): continue
        新增('類別', ['類別名稱'], [cat])
        cid = 取得對映('類別','類別編號','類別名稱').get(cat)
        新增('品項', ['類別編號','品項名稱'], [cid,item])
        iid = pd.read_sql(
            'SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?',
            conn, params=(cid,item)
        )['品項編號'].iloc[0]
        新增('細項', ['品項編號','細項名稱'], [iid,sub])
        sid = pd.read_sql(
            'SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?',
            conn, params=(iid,sub)
        )['細項編號'].iloc[0]
        新增('進貨', ['類別編號','品項編號','細項編號','數量','單價'],
             [cid,iid,sid,int(r['買入數量']), float(r['買入單價'])])
        cnt += 1
    return cnt

def 批次匯入銷售(df):
    df = df.rename(columns=str.strip)
    df['賣出數量'] = df.get('賣出數量', 0).fillna(0)
    df['賣出單價'] = df.get('賣出單價', 0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r['賣出數量'] <= 0: continue
        cat, item, sub = r['類別'], r['品項'], r['細項']
        if pd.isna(cat) or pd.isna(item) or pd.isna(sub): continue
        新增('類別', ['類別名稱'], [cat])
        cid = 取得對映('類別','類別編號','類別名稱').get(cat)
        新增('品項', ['類別編號','品項名稱'], [cid,item])
        iid = pd.read_sql(
            'SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?',
            conn, params=(cid,item)
        )['品項編號'].iloc[0]
        新增('細項', ['品項編號','細項名稱'], [iid,sub])
        sid = pd.read_sql(
            'SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?',
            conn, params=(iid,sub)
        )['細項編號'].iloc[0]
        新增('銷售', ['類別編號','品項編號','細項編號','數量','單價'],
             [cid,iid,sid,int(r['賣出數量']), float(r['賣出單價'])])
        cnt += 1
    return cnt

# --- UI 分支 ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])

if menu == '類別管理':
    st.title('類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('cat'):
        n = st.text_input('新增類別')
        d = st.text_input('刪除編號')
        if st.form_submit_button('執行'):
            if n: 新增('類別',['類別名稱'],[n])
            if d.isdigit(): 刪除('類別','類別編號',int(d))
            st.experimental_rerun()

elif menu == '品項管理':
    st.title('品項管理')
    cmap = 取得對映('類別','類別編號','類別名稱')
    if not cmap:
        st.warning('先新增類別')
    else:
        sel = st.selectbox('類別', list(cmap.keys()))
        cid = cmap[sel]
        df = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號 = ?', conn, params=(cid,))
        df = df.rename(columns={'品項編號':'編號','品項名稱':'名稱'})
        st.table(df)
        with st.form('item'):
            n = st.text_input('新增品項')
            d = st.text_input('刪除編號')
            if st.form_submit_button('執行'):
                if n: 新增('品項',['類別編號','品項名稱'],[cid,n])
                if d.isdigit(): 刪除('品項','品項編號',int(d))
                st.experimental_rerun()

elif menu == '細項管理':
    st.title('細項管理')
    cmap = 取得對映('類別','類別編號','類別名稱')
    if not cmap:
        st.warning('先新增類別')
    else:
        sel = st.selectbox('類別', list(cmap.keys()))
        cid = cmap[sel]
        df_i = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號 = ?', conn, params=(cid,))
        df_i.columns = df_i.columns.str.strip()
        mapping = {r['品項名稱']:r['品項編號'] for _,r in df_i.iterrows()}
        if not mapping:
            st.warning('先新增品項')
        else:
            sel2 = st.selectbox('品項', list(mapping.keys()))
            iid = mapping[sel2]
            df_s = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號 = ?', conn, params=(iid,))
            df_s = df_s.rename(columns={'細項編號':'編號','細項名稱':'名稱'})
            st.table(df_s)
            with st.form('sub'):
                n = st.text_input('新增細項')
                d = st.text_input('刪除編號')
                if st.form_submit_button('執行'):
                    if n: 新增('細項',['品項編號','細項名稱'],[iid,n])
                    if d.isdigit(): 刪除('細項','細項編號',int(d))
                    st.experimental_rerun()

elif menu == '進貨':
    st.title('進貨')
    # ... 進貨邏輯如前 ...

elif menu == '銷售':
    st.title('銷售')
    # ... 銷售邏輯如前 ...

elif menu == '儀表板':
    st.title('儀表板')
    # ... 儀表板如前 ...
