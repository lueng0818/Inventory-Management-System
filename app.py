import streamlit as st
st.set_page_config(layout="wide")
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 建表
c.execute('''CREATE TABLE IF NOT EXISTS 類別 (類別編號 INTEGER PRIMARY KEY AUTOINCREMENT, 類別名稱 TEXT UNIQUE)''')
c.execute('''CREATE TABLE IF NOT EXISTS 品項 (品項編號 INTEGER PRIMARY KEY AUTOINCREMENT, 類別編號 INTEGER, 品項名稱 TEXT, FOREIGN KEY(類別編號) REFERENCES 類別(類別編號))''')
c.execute('''CREATE TABLE IF NOT EXISTS 細項 (細項編號 INTEGER PRIMARY KEY AUTOINCREMENT, 品項編號 INTEGER, 細項名稱 TEXT, FOREIGN KEY(品項編號) REFERENCES 品項(品項編號))''')
for tbl in ['進貨','銷售']:
    c.execute(f'''CREATE TABLE IF NOT EXISTS {tbl} (紀錄ID INTEGER PRIMARY KEY AUTOINCREMENT, 類別編號 INTEGER, 品項編號 INTEGER, 細項編號 INTEGER, 數量 INTEGER, 單價 REAL, 總價 REAL, 日期 TEXT, FOREIGN KEY(類別編號) REFERENCES 類別(類別編號), FOREIGN KEY(品項編號) REFERENCES 品項(品項編號), FOREIGN KEY(細項編號) REFERENCES 細項(細項編號))''')
conn.commit()

# --- 輔助函式 ---
def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 取得對映(table: str) -> dict:
    mapping = {'類別': ('類別名稱','類別編號'), '品項': ('品項名稱','品項編號'), '細項': ('細項名稱','細項編號')}
    name_col,id_col = mapping.get(table,(None,None))
    if not name_col: return {}
    rows = conn.execute(f"SELECT {name_col},{id_col} FROM {table}").fetchall()
    return {name:idx for name,idx in rows}

def 新增(table:str,cols:list,vals:list):
    placeholders=','.join(['?']*len(vals))
    try:
        c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})",vals)
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能重複或外鍵限制")
        return None

def 刪除(table:str,key_col:str,key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col}=?",(key_val,))
    conn.commit()

def 更新(table:str,key_col:str,key_val,col:str,new_val):
    c.execute(f"UPDATE {table} SET {col}=? WHERE {key_col}=?",(new_val,key_val))
    conn.commit()

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", ['類別管理','品項管理','細項管理','進貨','銷售','日期查詢','儀表板'])

# 類別管理
if menu=='類別管理':
    st.header('⚙️ 類別管理')
    df=查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('form_cat'):
        new=st.text_input('新增類別')
        d=st.text_input('刪除編號')
        if st.form_submit_button('執行'):
            if new: 新增('類別',['類別名稱'],[new])
            if d.isdigit(): 刪除('類別','類別編號',int(d))
            st.experimental_rerun()

# 品項管理
elif menu=='品項管理':
    st.header('⚙️ 品項管理')
    cmap=取得對映('類別')
    if not cmap: st.warning('請先建立類別')
    else:
        sel=st.selectbox('選擇類別',['請選擇']+list(cmap.keys()))
        if sel!='請選擇':
            cid=cmap[sel]
            df=pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',conn,params=(cid,)).rename(columns={'品項編號':'編號','品項名稱':'名稱'})
            st.table(df)
            with st.form('form_item'):
                new=st.text_input('新增品項')
                d=st.text_input('刪除編號')
                if st.form_submit_button('執行'):
                    if new: 新增('品項',['類別編號','品項名稱'],[cid,new])
                    if d.isdigit(): 刪除('品項','品項編號',int(d))
                    st.experimental_rerun()

# 細項管理
elif menu=='細項管理':
    st.header('⚙️ 細項管理')
    cmap=取得對映('類別')
    if not cmap: st.warning('請先建立類別')
    else:
        selc=st.selectbox('選擇類別',['請選擇']+list(cmap.keys()))
        if selc!='請選擇':
            cid=cmap[selc]
            items=pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',conn,params=(cid,))
            imap={r[1]:r[0] for r in items.itertuples(index=False)}
            selp=st.selectbox('選擇品項',['請選擇']+list(imap.keys()))
            if selp!='請選擇':
                iid=imap[selp]
                subs=pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',conn,params=(iid,))
                submap={r[1]:r[0] for r in subs.itertuples(index=False)}
                act=st.selectbox('操作',['新增','刪除']+list(submap.keys()))
                if act=='新增':
                    name=st.text_input('新細項名稱')
                    if st.button('新增細項') and name:
                        新增('細項',['品項編號','細項名稱'],[iid,name]); st.experimental_rerun()
                elif act=='刪除':
                    dn=st.selectbox('選刪',['請選擇']+list(submap.keys()))
                    if dn!='請選擇' and st.button('刪除細項'):
                        刪除('細項','細項編號',submap[dn]);st.experimental_rerun()
                else:
                    sid=submap[act]
                    # 初始庫存表單及更新
                    if 'init_saved' not in st.session_state:
                        with st.form('save_init'):
                            q=st.number_input('初始數量',min_value=0)
                            p=st.number_input('初始單價',min_value=0.0,format='%.2f')
                            d=st.date_input('初始日期')
                            if st.form_submit_button('儲存初始'):
                                rec=新增('進貨',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],[cid,iid,sid,q,p,q*p,d.strftime('%Y-%m-%d')])
                                st.session_state.init_saved=True; st.session_state.init_rec=rec; st.success('已儲存初始庫存')
                    if st.session_state.get('init_saved'):
                        rid,oq,op,od=conn.execute('SELECT 紀錄ID,數量,單價,日期 FROM 進貨 WHERE 紀錄ID=?',(st.session_state.init_rec,)).fetchone()
                        st.info(f'初始: 紀錄ID={rid},數量={oq},單價={op},日期={od}')
                        with st.form('edit_init'):
                            nq=st.number_input('修改數量',min_value=0,value=oq)
                            if st.form_submit_button('更新初始'):
                                更新('進貨','紀錄ID',rid,'數量',nq)
                                更新('進貨','紀錄ID',rid,'總價',nq*op)
                                st.success('已更新初始數量'); st.experimental_rerun()

# 進貨管理
elif menu=='進貨':
    st.header('➕ 進貨管理')
    tabs=st.tabs(['手動','編輯'])
    with tabs[0]:
        st.write('手動新增進貨...')
    with tabs[1]:
        df=pd.read_sql('SELECT * FROM 進貨',conn);st.dataframe(df)
        rid=st.number_input('紀錄ID',min_value=1,step=1);nq=st.number_input('新數量',min_value=0,step=1)
        if st.button('更新進貨'): 
            price=conn.execute('SELECT 單價 FROM 進貨 WHERE 紀錄ID=?',(rid,)).fetchone()[0]
            更新('進貨','紀錄ID',rid,'數量',nq); 更新('進貨','紀錄ID',rid,'總價',nq*price)
            st.success('已更新進貨'); st.experimental_rerun()

# 銷售管理
elif menu=='銷售':
    st.header('➕ 銷售管理')
    tabs=st.tabs(['手動','編輯'])
    with tabs[1]:
        df=pd.read_sql('SELECT * FROM 銷售',conn);st.dataframe(df)
        rid=st.number_input('紀錄ID',min_value=1,step=1,key='sr');nq=st.number_input('新數量',min_value=0,step=1,key='sq')
        if st.button('更新銷售'): 
            price=conn.execute('SELECT 單價 FROM 銷售 WHERE 紀錄ID=?',(rid,)).fetchone()[0]
            更新('銷售','紀錄ID',rid,'數量',nq); 更新('銷售','紀錄ID',rid,'總價',nq*price)
            st.success('已更新銷售'); st.experimental_rerun()

# 日期查詢
elif menu=='日期查詢':
    st.header('📅 按日期查詢')
    sd=st.date_input('起'); ed=st.date_input('迄')
    if sd<=ed:
        dfp=pd.read_sql('SELECT * FROM 進貨',conn); dfs=pd.read_sql('SELECT * FROM 銷售',conn)
        dfp['日期']=pd.to_datetime(dfp['日期']); dfs['日期']=pd.to_datetime(dfs['日期'])
        fp=dfp[(dfp['日期']>=sd)&(dfp['日期']<=ed)]; fs=dfs[(dfs['日期']>=sd)&(dfs['日期']<=ed)]
        dfc=查詢('類別'); dfi=查詢('品項'); dfsu=查詢('細項')
        gp=fp.merge(dfc,on='類別編號').merge(dfi,on='品項編號').merge(dfsu,on='細項編號')
        gs=fs.merge(dfc,on='類別編號').merge(dfi,on='品項編號').merge(dfsu,on='細項編號')
        sp=gp.groupby('類別名稱')['總價'].sum().reset_index(name='進貨支出')
        ss=gs.groupby('類別名稱')['總價'].sum().reset_index(name='銷售收入')
        s=pd.merge(sp,ss,on='類別名稱',how='outer').fillna(0)
        st.dataframe(s); st.metric('進貨',s['進貨支出'].sum()); st.metric('銷售',s['銷售收入'].sum())

# 儀表板
elif menu=='儀表板':
    st.header('📊 庫存儀表板')
    dfp=pd.read_sql('SELECT * FROM 進貨',conn); dfs=pd.read_sql('SELECT * FROM 銷售',conn)
    dfc=查詢('類別'); dfi=查詢('品項'); dfsu=查詢('細項')
    gp=dfp.merge(dfc,on='類別編號').merge(dfi,on='品項編號').merge(dfsu,on='細項編號')
    gs=dfs.merge(dfc,on='類別編號').merge(dfi,on='品項編號').merge(dfsu,on='細項編號')
    sum_p=gp.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(進貨數量=('數量','sum'),進貨支出=('總價','sum'))
    sum_s=gs.groupby([...],as_index=False).agg(銷售數量=('數量','sum'),銷售收入=('總價','sum'))
    df=pd.merge(sum_p,sum_s,on=['類別名稱','品項名稱','細項名稱'],how='outer').fillna(0)
    df['庫存']=df['進貨數量']-df['銷售數量']
    df['平均進貨單價']=df.apply(lambda r:r['進貨支出']/r['進貨數量'] if r['進貨數量']>0 else 0,axis=1)
    df['平均銷售單價']=df.apply(lambda r:r['銷售收入']/r['銷售數量'] if r['銷售數量']>0 else 0,axis=1)
    st.dataframe(df,use_container_width=True)
    st.metric('進貨',df['進貨支出'].sum()); st.metric('銷售',df['銷售收入'].sum()); st.metric('庫存價值',(df['庫存']*df['平均進貨單價']).sum())
