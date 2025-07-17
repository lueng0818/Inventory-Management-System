import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)
""")
for tbl in ['進貨','銷售']:
    c.execute(f"""
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
    )
    """)
conn.commit()

def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 新增(table: str, cols: list, vals: list) -> int:
    df = 查詢(table)
    cols_used = df.columns.tolist()[1:1+len(vals)]
    placeholders = ",".join(["?"] * len(vals))
    c.execute(
        f"INSERT INTO {table} ({','.join(cols_used)}) VALUES ({placeholders})",
        vals
    )
    conn.commit()
    return c.lastrowid

def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col}=?", (key_val,))
    conn.commit()

def 取得對映(table: str) -> dict:
    mapping = {
        '類別': ('類別名稱','類別編號'),
        '品項': ('品項名稱','品項編號'),
        '細項': ('細項名稱','細項編號'),
    }
    name_col, id_col = mapping.get(table, (None,None))
    rows = conn.execute(f"SELECT {name_col},{id_col} FROM {table}").fetchall()
    return {name:idx for name,idx in rows}

# 批次匯入進貨
def 批次匯入進貨(df: pd.DataFrame) -> int:
    df = df.rename(columns=str.strip)
    df['買入數量'] = df.get('買入數量',0).fillna(0)
    df['買入單價'] = df.get('買入單價',0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r['買入數量'] <= 0: continue
        cat,item,sub = r['類別'], r['品項'], r['細項']
        if pd.isna(cat)|pd.isna(item)|pd.isna(sub): continue
        新增('類別',['類別名稱'],[cat])
        cid = 取得對映('類別')[cat]
        新增('品項',['類別編號','品項名稱'],[cid,item])
        iid = 取得對映('品項')[item]
        新增('細項',['品項編號','細項名稱'],[iid,sub])
        sid = 取得對映('細項')[sub]
        新增('進貨',
             ['類別編號','品項編號','細項編號','數量','單價','日期'],
             [cid,iid,sid,int(r['買入數量']),float(r['買入單價']), r.get('日期')]
        )
        cnt += 1
    return cnt

# 批次匯入銷售
def 批次匯入銷售(df: pd.DataFrame) -> int:
    df = df.rename(columns=str.strip)
    df['賣出數量'] = df.get('賣出數量',0).fillna(0)
    df['賣出單價'] = df.get('賣出單價',0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r['賣出數量'] <= 0: continue
        cat,item,sub = r['類別'], r['品項'], r['細項']
        if pd.isna(cat)|pd.isna(item)|pd.isna(sub): continue
        新增('類別',['類別名稱'],[cat])
        cid = 取得對映('類別')[cat]
        新增('品項',['類別編號','品項名稱'],[cid,item])
        iid = 取得對映('品項')[item]
        新增('細項',['品項編號','細項名稱'],[iid,sub])
        sid = 取得對映('細項')[sub]
        新增('銷售',
             ['類別編號','品項編號','細項編號','數量','單價','日期'],
             [cid,iid,sid,int(r['賣出數量']),float(r['賣出單價']), r.get('日期')]
        )
        cnt += 1
    return cnt
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])

# 類別管理
if menu == '類別管理':
    st.header('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    st.download_button('下載類別 CSV', df.to_csv(index=False,encoding='utf-8-sig'),
                       'categories.csv','text/csv')
    with st.form('form_cat'):
        new_cat = st.text_input('新增類別', key='cat_new')
        del_cat = st.text_input('刪除編號', key='cat_del')
        confirm = st.checkbox(f'確認刪除 類別 {del_cat}?') if del_cat.isdigit() else False
        if st.form_submit_button('執行'):
            if new_cat: 新增('類別',['類別名稱'],[new_cat])
            if del_cat.isdigit() and confirm: 刪除('類別','類別編號',int(del_cat))
            st.session_state['cat_new']=''; st.session_state['cat_del']=''
            st.experimental_rerun()

# 品項管理
elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先新增類別')
    else:
        sel = st.selectbox('類別', list(cmap.keys()))
        cid = cmap[sel]
        df = pd.read_sql(
            'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
            conn, params=(cid,)
        ).rename(columns={'品項編號':'編號','品項名稱':'名稱'})
        st.table(df)
        st.download_button('下載品項 CSV', df.to_csv(index=False,encoding='utf-8-sig'),
                           f'items_{cid}.csv','text/csv')
        with st.form('form_item'):
            new_item = st.text_input('新增品項', key='item_new')
            del_item = st.text_input('刪除編號', key='item_del')
            confirm = st.checkbox(f'確認刪除 品項 {del_item}?') if del_item.isdigit() else False
            if st.form_submit_button('執行'):
                if new_item: 新增('品項',['類別編號','品項名稱'],[cid,new_item])
                if del_item.isdigit() and confirm: 刪除('品項','品項編號',int(del_item))
                st.session_state['item_new']=''; st.session_state['item_del']=''
                st.experimental_rerun()

# 細項管理
elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先新增類別')
    else:
        sel = st.selectbox('類別', list(cmap.keys()))
        cid = cmap[sel]
        df_i = pd.read_sql(
            'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
            conn, params=(cid,)
        )
        imap = dict(zip(df_i['品項名稱'], df_i['品項編號']))
        if not imap:
            st.warning('該類別無品項')
        else:
            sel2 = st.selectbox('品項', list(imap.keys()))
            iid = imap[sel2]
            df_s = pd.read_sql(
                'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                conn, params=(iid,)
            ).rename(columns={'細項編號':'編號','細項名稱':'名稱'})
            st.table(df_s)
            st.download_button('下載細項 CSV', df_s.to_csv(index=False,encoding='utf-8-sig'),
                               f'subs_{iid}.csv','text/csv')
            with st.form('form_sub'):
                new_sub = st.text_input('新增細項', key='sub_new')
                del_sub = st.text_input('刪除編號', key='sub_del')
                confirm = st.checkbox(f'確認刪除 細項 {del_sub}?') if del_sub.isdigit() else False
                if st.form_submit_button('執行'):
                    if new_sub: 新增('細項',['品項編號','細項名稱'],[iid,new_sub])
                    if del_sub.isdigit() and confirm: 刪除('細項','細項編號',int(del_sub))
                    st.session_state['sub_new']=''; st.session_state['sub_del']=''
                    st.experimental_rerun()
# === 進貨管理 ===
elif menu == '進貨':
    st.header('➕ 進貨管理')
    tab1, tab2, tab3 = st.tabs(['批次匯入','查詢/匯出','手動記錄'])
    # 批次匯入
    with tab1:
        sample = pd.DataFrame({
            '類別':['首飾'],'品項':['項鍊'],'細項':['金屬鍊'],
            '買入數量':[10],'買入單價':[100.0]
        })
        csv = sample.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載進貨範例', csv, 'purchase_template.csv','text/csv')
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_p')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            cnt = 批次匯入進貨(df)
            st.success(f'批次匯入 {cnt} 筆進貨記錄')
    # 查詢/匯出
    with tab2:
        df = 查詢('進貨')
        col1, col2 = st.columns(2)
        with col1:
            d1 = st.date_input('起始日期', value=date.today().replace(day=1), key='p_start')
        with col2:
            d2 = st.date_input('結束日期', value=date.today(), key='p_end')
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df_f = df[(df['日期']>=pd.to_datetime(d1))&(df['日期']<=pd.to_datetime(d2))]
        st.dataframe(df_f)
        st.download_button('匯出進貨 CSV', df_f.to_csv(index=False,encoding='utf-8-sig'),
                           'purchases_filtered.csv','text/csv')
    # 手動記錄
    with tab3:
        cat_map = 取得對映('類別')
        if not cat_map: st.warning('請先新增類別')
        else:
            sel_cat = st.selectbox('類別',list(cat_map.keys()),key='p_cat')
            cid = cat_map[sel_cat]
            items = pd.read_sql(
                'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            if not imap: st.warning('該類別無品項')
            else:
                sel_item = st.selectbox('品項',list(imap.keys()),key='p_item')
                iid = imap[sel_item]
                subs = pd.read_sql(
                    'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                    conn, params=(iid,)
                )
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                if not smap: st.warning('該品項無細項')
                else:
                    sel_sub = st.selectbox('細項',list(smap.keys()),key='p_sub')
                    sid = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期',value=True,key='p_today')
                    date_str = datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期',key='p_date').strftime('%Y-%m-%d')
                    qty = st.number_input('數量',min_value=1,value=1,key='p_qty')
                    price = st.number_input('單價',min_value=0.0,format='%.2f',key='p_price')
                    if st.button('儲存進貨',key='p_save'):
                        新增('進貨',['類別編號','品項編號','細項編號','數量','單價','日期'],
                             [cid,iid,sid,qty,price,date_str])
                        st.success(f'進貨記錄已儲存：{date_str}')

# === 銷售管理 ===
elif menu == '銷售':
    st.header('➕ 銷售管理')
    tab1, tab2, tab3 = st.tabs(['批次匯入','查詢/匯出','手動記錄'])
    # 批次匯入
    with tab1:
        sample = pd.DataFrame({
            '類別':['首飾'],'品項':['手鍊'],'細項':['皮革鍊'],
            '賣出數量':[2],'賣出單價':[150.0]
        })
        csv = sample.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載銷售範例', csv, 'sales_template.csv','text/csv')
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_s')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            cnt = 批次匯入銷售(df)
            st.success(f'批次匯入 {cnt} 筆銷售記錄')
    # 查詢/匯出
    with tab2:
        df = 查詢('銷售')
        col1, col2 = st.columns(2)
        with col1:
            d1 = st.date_input('起始日期', value=date.today().replace(day=1), key='s_start')
        with col2:
            d2 = st.date_input('結束日期', value=date.today(), key='s_end')
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df_f = df[(df['日期']>=pd.to_datetime(d1))&(df['日期']<=pd.to_datetime(d2))]
        st.dataframe(df_f)
        st.download_button('匯出銷售 CSV', df_f.to_csv(index=False,encoding='utf-8-sig'),
                           'sales_filtered.csv','text/csv')
    # 手動記錄
    with tab3:
        cat_map = 取得對映('類別')
        if not cat_map: st.warning('請先新增類別')
        else:
            sel_cat = st.selectbox('類別',list(cat_map.keys()),key='s_cat')
            cid = cat_map[sel_cat]
            items = pd.read_sql(
                'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            imap = dict(zip(items['品項名稱'],items['品項編號']))
            if not imap: st.warning('該類別無品項')
            else:
                sel_item = st.selectbox('品項',list(imap.keys()),key='s_item')
                iid = imap[sel_item]
                subs = pd.read_sql(
                    'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                    conn, params=(iid,)
                )
                smap = dict(zip(subs['細項名稱'],subs['細項編號']))
                if not smap: st.warning('該品項無細項')
                else:
                    sel_sub = st.selectbox('細項',list(smap.keys()),key='s_sub')
                    sid = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期',value=True,key='s_today')
                    date_str = datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期',key='s_date').strftime('%Y-%m-%d')
                    qty = st.number_input('數量',min_value=1,value=1,key='s_qty')
                    price = st.number_input('單價',min_value=0.0,format='%.2f',key='s_price')
                    if st.button('儲存銷售',key='s_save'):
                        新增('銷售',['類別編號','品項編號','細項編號','數量','單價','日期'],
                             [cid,iid,sid,qty,price,date_str])
                        st.success(f'銷售記錄已儲存：{date_str}')
elif menu == '儀表板':
    st.header('📊 庫存儀表板')
    df_p = pd.read_sql('SELECT * FROM 進貨', conn)
    df_s = pd.read_sql('SELECT * FROM 銷售', conn)
    df_c = 查詢('類別')
    df_i = 查詢('品項')
    df_su= 查詢('細項')

    gp = (df_p.merge(df_c, on='類別編號')
               .merge(df_i, on='品項編號')
               .merge(df_su,on='細項編號')
               .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
               .agg(進貨=('數量','sum'),支出=('總價','sum')))

    gs = (df_s.merge(df_c, on='類別編號')
               .merge(df_i, on='品項編號')
               .merge(df_su,on='細項編號')
               .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
               .agg(銷售=('數量','sum'),收入=('總價','sum')))

    summary = pd.merge(gp, gs,
                       on=['類別名稱','品項名稱','細項名稱'],
                       how='outer').fillna(0)
    summary['庫存'] = summary['進貨'] - summary['銷售']

    st.dataframe(summary)
    st.download_button('下載庫存摘要 CSV',
                       summary.to_csv(index=False, encoding='utf-8-sig'),
                       'summary.csv','text/csv')
    st.metric('總支出', f"{gp['支出'].sum():.2f}")
    st.metric('總收入', f"{gs['收入'].sum():.2f}")
    st.metric('淨利',   f"{gs['收入'].sum()-gp['支出'].sum():.2f}")
