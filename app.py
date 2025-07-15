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
    cols_all = df.columns.tolist()
    target = cols_all[1:1+len(vals)]
    q = ",".join(target); qm = ",".join(["?"]*len(vals))
    try:
        c.execute(f"INSERT INTO {table} ({q}) VALUES ({qm})", vals)
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("操作失敗：重複或外鍵限制")

def 刪除(table, key, val):
    c.execute(f"DELETE FROM {table} WHERE {key}=?", (val,))
    conn.commit()

def 取得對映(table, key_col, val_col):
    if table == '類別':
        df = pd.read_sql("SELECT 類別編號, 類別名稱 FROM 類別", conn)
        return dict(zip(df['類別名稱'], df['類別編號']))
    df = 查詢(table)
    df.columns = df.columns.str.strip()
    if key_col in df.columns and val_col in df.columns:
        return dict(zip(df[val_col], df[key_col]))
    st.warning(f"{table} 欄位 {key_col} 或 {val_col} 不存在")
    return {}

def 批次匯入進貨(df):
    df = df.rename(columns=str.strip)
    df['買入數量'] = df.get('買入數量',0).fillna(0)
    df['買入單價'] = df.get('買入單價',0).fillna(0)
    cnt=0
    for _,r in df.iterrows():
        if r['買入數量']<=0: continue
        cat,item,sub=r['類別'],r['品項'],r['細項']
        if pd.isna(cat)|pd.isna(item)|pd.isna(sub): continue
        新增('類別',['類別名稱'],[cat])
        cid=取得對映('類別','類別編號','類別名稱')[cat]
        新增('品項',['類別編號','品項名稱'],[cid,item])
        iid=pd.read_sql("SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?",conn,(cid,item))['品項編號'].iloc[0]
        新增('細項',['品項編號','細項名稱'],[iid,sub])
        sid=pd.read_sql("SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?",conn,(iid,sub))['細項編號'].iloc[0]
        新增('進貨',['類別編號','品項編號','細項編號','數量','單價'],[cid,iid,sid,int(r['買入數量']),float(r['買入單價'])])
        cnt+=1
    return cnt

def 批次匯入銷售(df):
    df = df.rename(columns=str.strip)
    df['賣出數量'] = df.get('賣出數量',0).fillna(0)
    df['賣出單價'] = df.get('賣出單價',0).fillna(0)
    cnt=0
    for _,r in df.iterrows():
        if r['賣出數量']<=0: continue
        cat,item,sub=r['類別'],r['品項'],r['細項']
        if pd.isna(cat)|pd.isna(item)|pd.isna(sub): continue
        新增('類別',['類別名稱'],[cat])
        cid=取得對映('類別','類別編號','類別名稱')[cat]
        新增('品項',['類別編號','品項名稱'],[cid,item])
        iid=pd.read_sql("SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?",conn,(cid,item))['品項編號'].iloc[0]
        新增('細項',['品項編號','細項名稱'],[iid,sub])
        sid=pd.read_sql("SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?",conn,(iid,sub))['細項編號'].iloc[0]
        新增('銷售',['類別編號','品項編號','細項編號','數量','單價'],[cid,iid,sid,int(r['賣出數量']),float(r['賣出單價'])])
        cnt+=1
    return cnt

# --- UI 分支 ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單',[
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])

if menu=='類別管理':
    st.title('類別管理'); df=查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('cat'):
        n=st.text_input('新增'); d=st.text_input('刪除編號')
        if st.form_submit_button('執行'):
            if n: 新增('類別',['類別名稱'],[n]); st.success('新增')
            if d.isdigit(): 刪除('類別','類別編號',int(d)); st.success('刪除')
            st.experimental_rerun()

elif menu=='品項管理':
    st.title('品項管理')
    cmap=取得對映('類別','類別編號','類別名稱')
    if not cmap: st.warning('先新增類別')
    else:
        sel=st.selectbox('類別',list(cmap.keys())); cid=cmap[sel]
        df=pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?',conn,(cid,)).rename(columns={'品項編號':'編號','品項名稱':'名稱'})
        st.table(df)
        with st.form('item'):
            n=st.text_input('新增'); d=st.text_input('刪除編號')
            if st.form_submit_button('執行'):
                if n: 新增('品項',['類別編號','品項名稱'],[cid,n]); st.success('新增')
                if d.isdigit(): 刪除('品項','品項編號',int(d)); st.success('刪除')
                st.experimental_rerun()

elif menu=='細項管理':
    st.title('細項管理')
    cmap=取得對映('類別','類別編號','類別名稱')
    if not cmap: st.warning('先新增類別')
    else:
        sel=st.selectbox('類別',list(cmap.keys())); cid=cmap[sel]
        df_i=pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?',conn,(cid,))
        df_i.columns=df_i.columns.str.strip()
        imap={r['品項名稱']:r['品項編號'] for _,r in df_i.iterrows()}
        if not imap: st.warning('先新增品項')
        else:
            sel2=st.selectbox('品項',list(imap.keys())); iid=imap[sel2]
            df_s=pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?',conn,(iid,)).rename(columns={'細項編號':'編號','細項名稱':'名稱'})
            st.table(df_s)
            with st.form('sub'):
                n=st.text_input('新增'); d=st.text_input('刪除編號')
                if st.form_submit_button('執行'):
                    if n: 新增('細項',['品項編號','細項名稱'],[iid,n]); st.success('新增')
                    if d.isdigit(): 刪除('細項','細項編號',int(d)); st.success('刪除')
                    st.experimental_rerun()

elif menu=='進貨':
    st.title('進貨')
    t1,t2=st.tabs(['批次','手動'])
    with t1:
        sample=pd.DataFrame({'類別':['首飾'],'品項':['項鍊'],'細項':['金屬鍊'],'買入數量':[10],'買入單價':[100.0]})
        btn=sample.to_csv(index=False,encoding='utf-8-sig')
        st.download_button('下載範例',btn,'purchase.csv','text/csv')
        upl=st.file_uploader('上傳',type=['csv','xlsx','xls'])
        if upl:
            try: df=pd.read_excel(upl)
            except: df=pd.read_csv(upl)
            c=批次匯入進貨(df); st.success(f'匯入{c}筆')
    with t2:
        st.info('手動記錄同前')

elif menu=='銷售':
    st.title('銷售')
    t1,t2=st.tabs(['批次','手動'])
    with t1:
        sample=pd.DataFrame({'類別':['首飾'],'品項':['手鍊'],'細項':['皮革鍊'],'賣出數量':[2],'賣出單價':[150.0]})
        btn=sample.to_csv(index=False,encoding='utf-8-sig')
        st.download_button('下載範例',btn,'sales.csv','text/csv')
        upl=st.file_uploader('上傳',type=['csv','xlsx','xls'])
        if upl:
            try: df=pd.read_excel(upl)
            except: df=pd.read_csv(upl)
            c=批次匯入銷售(df); st.success(f'匯入{c}筆')
    with t2:
        st.info('手動記錄同前')

elif menu=='儀表板':
    st.title('儀表板')
    df_p=pd.read_sql('SELECT * FROM 進貨',conn)
    df_s=pd.read_sql('SELECT * FROM 銷售',conn)
    df_c=查詢('類別').rename(columns={'類別編號':'類別編號','類別名稱':'類別名稱'})
    df_i=查詢('品項').rename(columns={'品項編號':'品項編號','品項名稱':'品項名稱'})
    df_su=查詢('細項').rename(columns={'細項編號':'細項編號','細項名稱':'細項名稱'})
    df_p=df_p.merge(df_c,on='類別編號').merge(df_i,on='品項編號').merge(df_su,on='細項編號')
    df_s=df_s.merge(df_c,on='類別編號').merge(df_i,on='品項編號').merge(df_su,on='細項編號')
    gp=df_p.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(進貨=('數量','sum'),支出=('總價','sum'))
    gs=df_s.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(銷售=('數量','sum'),收入=('總價','sum'))
    summary=pd.merge(gp,gs,on=['類別名稱','品項名稱','細項名稱'],how='outer').fillna(0)
    summary['庫存']=summary['進貨']-summary['銷售']
    st.dataframe(summary)
    st.metric('總支出',f"{gp['支出'].sum():.2f}"); st.metric('總收入',f"{gs['收入'].sum():.2f}"); st.metric('淨利',f"{gs['收入'].sum()-gp['支出'].sum():.2f}")
