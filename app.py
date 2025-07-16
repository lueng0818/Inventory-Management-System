import streamlit as st
st.set_page_config(layout="wide")
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
        數量 REAL,
        單價 REAL,
        總價 REAL,
        日期 TEXT
    )''')
conn.commit()

# --- 輔助函式 ---
def 查詢(table): return pd.read_sql(f"SELECT * FROM {table}",conn)

def 取得對映(table):
    mapping={'類別':('類別名稱','類別編號'),'品項':('品項名稱','品項編號'),'細項':('細項名稱','細項編號')}
    nc,idc=mapping.get(table,(None,None))
    if not nc: return {}
    rows=conn.execute(f"SELECT {nc},{idc} FROM {table}").fetchall()
    return {r[0]:r[1] for r in rows}

def 新增(table,cols,vals):
    c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(vals))})",vals)
    conn.commit(); return c.lastrowid

def 刪除(table,col,val): c.execute(f"DELETE FROM {table} WHERE {col}=?",(val,));conn.commit()

def 更新(table,key,val,col,new): c.execute(f"UPDATE {table} SET {col}=? WHERE {key}=?",(new,val));conn.commit()

# --- UI ---
st.sidebar.title("庫存管理系統")
menu=st.sidebar.radio("功能選單",['類別管理','品項管理','細項管理','進貨','銷售','日期查詢','儀表板'])

# 類別管理
if menu=='類別管理':
    st.header('⚙️ 類別管理')
    df=查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('fc'):
        new=st.text_input('新增');d=st.text_input('刪除ID')
        if st.form_submit_button('執行'):
            if new: 新增('類別',['類別名稱'],[new])
            if d.isdigit(): 刪除('類別','類別編號',int(d))
            st.experimental_rerun()

# 品項管理
elif menu=='品項管理':
    st.header('⚙️ 品項管理')
    cmap=取得對映('類別')
    if not cmap: st.warning('先建立類別')
    else:
        sel=st.selectbox('類別',['請選']+list(cmap.keys()))
        if sel!='請選':
            cid=cmap[sel]
            df=pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',conn,(cid,))
            st.table(df.rename(columns={'品項編號':'ID','品項名稱':'名稱'}))
            with st.form('fi'):
                n=st.text_input('新增');d=st.text_input('刪除ID')
                if st.form_submit_button('確定'):
                    if n: 新增('品項',['類別編號','品項名稱'],[cid,n])
                    if d.isdigit(): 刪除('品項','品項編號',int(d))
                    st.experimental_rerun()

# 細項管理
elif menu=='細項管理':
    st.header('⚙️ 細項管理')
    cmap=取得對映('類別')
    if not cmap: st.warning('先建立類別')
    else:
        sc=st.selectbox('類別',['請選']+list(cmap.keys()))
        if sc!='請選':
            cid=cmap[sc]
            items=pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',conn,(cid,))
            im={r[1]:r[0] for r in items.itertuples(False)}
            si=st.selectbox('品項',['請選']+list(im.keys()))
            if si!='請選':
                iid=im[si]
                subs=pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',conn,(iid,))
                sm={r[1]:r[0] for r in subs.itertuples(False)}
                act=st.selectbox('操作',['新增','刪除']+list(sm.keys()))
                if act=='新增':
                    nm=st.text_input('名稱')
                    if st.button('確定'):
                        新增('細項',['品項編號','細項名稱'],[iid,nm]);st.experimental_rerun()
                elif act=='刪除':
                    dn=st.selectbox('刪除',['請選']+list(sm.keys()))
                    if dn!='請選' and st.button('刪除'):
                        刪除('細項','細項編號',sm[dn]);st.experimental_rerun()

# 進貨管理
elif menu=='進貨':
    st.header('➕ 進貨管理')
    tabs=st.tabs(['批次','手動','編輯'])
    # 編輯
    with tabs[2]:
        df_all=pd.read_sql('''SELECT p.紀錄ID,c.類別名稱,i.品項名稱,s.細項名稱,p.數量,p.單價,p.總價,p.日期
            FROM 進貨 p
            JOIN 類別 c ON p.類別編號=c.類別編號
            JOIN 品項 i ON p.品項編號=i.品項編號
            JOIN 細項 s ON p.細項編號=s.細項編號''',conn)
        st.dataframe(df_all)
        rec=int(st.number_input('ID',1,step=1))
        row=conn.execute('SELECT 數量,單價,日期 FROM 進貨 WHERE 紀錄ID=?',(rec,)).fetchone()
        oq,op,od=row if row else (0.0,0.0,datetime.now().strftime('%Y-%m-%d'))
        nq=st.number_input('新數量',0.0,value=float(oq),step=0.1,format='%.1f')
        ud=st.checkbox('更新日期')
        nd=st.date_input('新日期',value=datetime.strptime(od,'%Y-%m-%d'))
        if st.button('更新進貨'):
            更新('進貨','紀錄ID',rec,'數量',nq)
            更新('進貨','紀錄ID',rec,'總價',nq*op)
            if ud: 更新('進貨','紀錄ID',rec,'日期',nd.strftime('%Y-%m-%d'))
            st.success('已更新')
        if st.button('刪除進貨'):
            刪除('進貨','紀錄ID',rec);st.success('已刪除')

# 銷售管理
elif menu=='銷售':
    st.header('➕ 銷售管理')
    # 同進貨編輯邏輯
    df_all=pd.read_sql(df_all := conn.execute('''SELECT p.紀錄ID,c.類別名稱,i.品項名稱,s.細項名稱,p.數量,p.單價,p.總價,p.日期
            FROM 銷售 p
            JOIN 類別 c ON p.類別編號=c.類別編號
            JOIN 品項 i ON p.品項編號=i.品項編號
            JOIN 細項 s ON p.細項編號=s.細項編號''').fetchdf(), conn)
    st.dataframe(df_all)
    rec=int(st.number_input('ID',1,step=1, key='sr'))
    row=conn.execute('SELECT 數量,單價,日期 FROM 銷售 WHERE 紀錄ID=?',(rec,)).fetchone()
    oq,op,od=row if row else (0.0,0.0,datetime.now().strftime('%Y-%m-%d'))
    nq=st.number_input('新數量',0.0,value=float(oq),step=0.1,format='%.1f', key='sn')
    ud=st.checkbox('更新日期',key='su')
    nd=st.date_input('新日期',value=datetime.strptime(od,'%Y-%m-%d'))
    if st.button('更新銷售', key='btn_upd_sell'):
    更新('銷售', '紀錄ID', rec, '數量', nq)
    更新('銷售', '紀錄ID', rec, '總價', nq * op)
    if ud:
        更新('銷售', '紀錄ID', rec, '日期', nd.strftime('%Y-%m-%d'))
        更新('銷售','紀錄ID',rec,'日期',nd.strftime('%Y-%m-%d'))
    st.success('已更新銷售紀錄'):
    更新('銷售','紀錄ID',rec,'數量',nq)
    更新('銷售','紀錄ID',rec,'總價',nq*op)
    if ud:
        更新('銷售','紀錄ID',rec,'日期',nd.strftime('%Y-%m-%d'))
    st.success('已更新銷售紀錄')
    if st.button('刪除銷售',key='del_s'): 刪除('銷售','紀錄ID',rec);st.success('已刪除')

# 日期查詢
elif menu=='日期查詢':
    st.header('📅 日期查詢')
    sd,ed=st.columns(2)
    col1, col2 = st.columns(2)
    with col1:
        s = st.date_input('起始日期')
    with col2:
        e = st.date_input('結束日期')
    if s>e: st.error('錯誤日期')
    else:
        dfp=pd.read_sql('SELECT * FROM 進貨',conn); dfs=pd.read_sql('SELECT * FROM 銷售',conn)
        dfp['日期'],dfs['日期']=pd.to_datetime(dfp['日期']),pd.to_datetime(dfs['日期'])
        f1, f2 = dfp[(dfp['日期']>=s)&(dfp['日期']<=e)], dfs[(dfs['日期']>=s)&(dfs['日期']<=e)]
        dfn=lambda df,label: df.merge(查詢('類別'),on='類別編號').merge(查詢('品項'),on='品項編號').merge(查詢('細項'),on='細項編號').groupby('類別名稱')['總價'].sum().rename(label).reset_index()
        sp, ss = dfn(f1,'進貨支出'), dfn(f2,'銷售收入')
        sm=pd.merge(sp,ss,on='類別名稱',how='outer').fillna(0)
        st.dataframe(sm); st.metric('支出',sm['進貨支出'].sum()); st.metric('收入',sm['銷售收入'].sum())

# 儀表板
elif menu=='儀表板':
    st.header('📊 儀表板')
    dfp,dfs= pd.read_sql('SELECT * FROM 進貨',conn),pd.read_sql('SELECT * FROM 銷售',conn)
    dfc,dfi,dfs1=查詢('類別'),查詢('品項'),查詢('細項')
    mp=lambda df: df.merge(dfc,on='類別編號').merge(dfi,on='品項編號').merge(dfs1,on='細項編號')
    gp,gs=mp(dfp),mp(dfs)
    sp=gp.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(進貨量=('數量','sum'),支出=('總價','sum'))
    ss=gs.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(銷售量=('數量','sum'),收入=('總價','sum'))
    sum=pd.merge(sp,ss,on=['類別名稱','品項名稱','細項名稱'],how='outer').fillna(0)
    sum['庫存']=sum['進貨量']-sum['銷售量']
    sum['價值']=sum['庫存']*(sum['支出']/sum['進貨量'].replace(0,1))
    # 篩選
    c1,c2,c3=st.columns(3)
    cat=c1.selectbox('類別',['全']+sum['類別名稱'].unique().tolist())
    itm=c2.selectbox('品項',['全']+sum['品項名稱'].unique().tolist())
    sub=c3.selectbox('細項',['全']+sum['細項名稱'].unique().tolist())
    df=sum[(sum['類別名稱']==cat if cat!='全' else True)&(sum['品項名稱']==itm if itm!='全' else True)&(sum['細項名稱']==sub if sub!='全' else True)]
    st.dataframe(df,use_container_width=True);
    st.metric('總支出',df['支出'].sum());st.metric('總收入',df['收入'].sum());st.metric('總價值',df['價值'].sum())
