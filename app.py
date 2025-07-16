import streamlit as st
st.set_page_config(layout="wide")
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 建表
c.execute('''
CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)
''')
c.execute('''
CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)
''')
c.execute('''
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)
''')
for tbl in ['進貨', '銷售']:
    c.execute(f'''
    CREATE TABLE IF NOT EXISTS {tbl} (
        紀錄ID INTEGER PRIMARY KEY AUTOINCREMENT,
        類別編號 INTEGER,
        品項編號 INTEGER,
        細項編號 INTEGER,
        數量 REAL,
        單價 REAL,
        總價 REAL,
        日期 TEXT,
        FOREIGN KEY(類別編號) REFERENCES 類別(類別編號),
        FOREIGN KEY(品項編號) REFERENCES 品項(品項編號),
        FOREIGN KEY(細項編號) REFERENCES 細項(細項編號)
    )
    ''')
conn.commit()

# --- 輔助函式 ---
def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 取得對映(table: str) -> dict:
    mapping = {
        '類別': ('類別名稱', '類別編號'),
        '品項': ('品項名稱', '品項編號'),
        '細項': ('細項名稱', '細項編號')
    }
    name_col, id_col = mapping.get(table, (None, None))
    if not name_col:
        return {}
    rows = conn.execute(f"SELECT {name_col}, {id_col} FROM {table}").fetchall()
    return {name: idx for name, idx in rows}

def 新增(table: str, cols: list, vals: list):
    placeholders = ','.join(['?'] * len(vals))
    try:
        c.execute(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({placeholders})", vals)
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能重複或外鍵限制")
        return None

def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col} = ?", (key_val,))
    conn.commit()

def 更新(table: str, key_col: str, key_val, col: str, new_val):
    c.execute(f"UPDATE {table} SET {col} = ? WHERE {key_col} = ?", (new_val, key_val))
    conn.commit()

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", ['類別管理','品項管理','細項管理','進貨','銷售','日期查詢','儀表板'])

# --- 類別管理 ---
if menu == '類別管理':
    st.header('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('form_cat'):
        new_cat = st.text_input('新增類別')
        del_cat = st.text_input('刪除編號')
        if st.form_submit_button('執行'):
            if new_cat: 新增('類別',['類別名稱'],[new_cat])
            if del_cat.isdigit(): 刪除('類別','類別編號',int(del_cat))
            st.experimental_rerun()

# --- 品項管理 ---
elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先建立類別')
    else:
        sel_cat = st.selectbox('選擇類別', ['請選擇'] + list(cmap.keys()))
        if sel_cat != '請選擇':
            cid = cmap[sel_cat]
            df = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            st.table(df.rename(columns={'品項編號':'編號','品項名稱':'名稱'}))
            with st.form('form_item'):
                new_item = st.text_input('新增品項')
                del_item = st.text_input('刪除編號')
                if st.form_submit_button('執行'):
                    if new_item: 新增('品項',['類別編號','品項名稱'],[cid,new_item])
                    if del_item.isdigit(): 刪除('品項','品項編號',int(del_item))
                    st.experimental_rerun()

# --- 細項管理 ---
elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先建立類別')
    else:
        sel_cat = st.selectbox('選擇類別', ['請選擇'] + list(cmap.keys()))
        if sel_cat != '請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('選擇品項', ['請選擇'] + list(imap.keys()))
            if sel_item != '請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                submap = dict(zip(subs['細項名稱'], subs['細項編號']))
                sel_action = st.selectbox('操作', ['新增細項','刪除細項'] + list(submap.keys()))
                if sel_action == '新增細項':
                    name = st.text_input('新細項名稱')
                    if st.button('新增細項') and name:
                        新增('細項',['品項編號','細項名稱'],[iid,name])
                        st.experimental_rerun()
                elif sel_action == '刪除細項':
                    dn = st.selectbox('選擇刪除', ['請選擇'] + list(submap.keys()))
                    if dn != '請選擇' and st.button('刪除細項'):
                        刪除('細項','細項編號',submap[dn])
                        st.experimental_rerun()
                else:
                    sid = submap[sel_action]
                    # 初始庫存
                    rec = None
                    if 'init_rec' not in st.session_state:
                        with st.form('save_init'):
                            q = st.number_input('初始數量', min_value=0.0, value=1.0, step=0.1, format='%.1f')
                            p = st.number_input('初始單價', min_value=0.0, value=0.0, step=0.1, format='%.1f')
                            d = st.date_input('初始日期')
                            if st.form_submit_button('儲存初始庫存'):
                                rec = 新增('進貨',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                                         [cid,iid,sid,q,p,q*p,d.strftime('%Y-%m-%d')])
                                st.session_state.init_rec = rec
                                st.success('已儲存初始庫存')
                    if 'init_rec' in st.session_state:
                        rid,oq,op,od = conn.execute('SELECT 紀錄ID,數量,單價,日期 FROM 進貨 WHERE 紀錄ID=?',
                                                    (st.session_state.init_rec,)).fetchone()
                        st.info(f'初始紀錄ID={rid}, 數量={oq}, 單價={op}, 日期={od}')
                        with st.form('edit_init'):
                            nq = st.number_input('修改數量', min_value=0.0, value=oq, step=0.1, format='%.1f')
                            if st.form_submit_button('更新初始數量'):
                                更新('進貨','紀錄ID',rid,'數量',nq)
                                更新('進貨','紀錄ID',rid,'總價',nq*op)
                                st.success('已更新初始數量')

# --- 進貨管理 ---
elif menu == '進貨':
    st.header('➕ 進貨管理')
    tab1,tab2,tab3 = st.tabs(['範例檔下載','手動記錄','編輯/刪除紀錄'])
    # 範例檔
    with tab1:
        st.write('下載進貨範例CSV：')
        sample_csv = """類別名稱,品項名稱,細項名稱,數量,單價,日期
零件類,螺絲,銀珠3mm,10,5.0,2025-07-16"""
        st.download_button('下載進貨範例檔', sample_csv, file_name='purchase_sample.csv', mime='text/csv')
    # 手動記錄
    with tab2:
        cmap = 取得對映('類別')
        sel_cat = st.selectbox('類別', ['請選擇']+list(cmap.keys()))
        if sel_cat != '請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('品項', ['請選擇']+list(imap.keys()))
            if sel_item != '請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                sel_sub = st.selectbox('細項', ['請選擇']+list(smap.keys()))
                if sel_sub != '請選擇':
                    sid = smap[sel_sub]
                    date = st.date_input('日期')
                    qty = st.number_input('數量', min_value=0.0, value=1.0, step=0.1, format='%.1f')
                    price = st.number_input('單價', min_value=0.0, value=0.0, step=0.1, format='%.1f')
                    if st.button('儲存進貨'):
                        新增('進貨',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                             [cid,iid,sid,qty,price,qty*price,date.strftime('%Y-%m-%d')])
                        st.success('已儲存進貨')
    # 編輯/刪除
    with tab3:
        df_all = pd.read_sql(
            "SELECT p.紀錄ID, c.類別名稱, i.品項名稱, s.細項名稱, p.數量, p.單價, p.總價, p.日期 "
            "FROM 進貨 p JOIN 類別 c ON p.類別編號=c.類別編號 "
            "JOIN 品項 i ON p.品項編號=i.品項編號 "
            "JOIN 細項 s ON p.細項編號=s.細項編號", conn)
        st.dataframe(df_all)
        rec_id = st.number_input('紀錄ID', min_value=1, step=1)
        price_row = conn.execute('SELECT 單價, 日期 FROM 進貨 WHERE 紀錄ID=?', (rec_id,)).fetchone()
        old_qty = conn.execute('SELECT 數量 FROM 進貨 WHERE 紀錄ID=?',(rec_id,)).fetchone()[0]
        old_date = None
        if price_row:
            old_date = price_row[1]
        new_qty = st.number_input('新數量', min_value=0.0, value=float(old_qty), step=0.1, format='%.1f')
        new_date = st.date_input('新日期', value=datetime.strptime(old_date, '%Y-%m-%d') if old_date else datetime.now())
        if st.button('更新進貨紀錄'):
            if price_row:
                price = price_row[0]
                更新('進貨','紀錄ID',rec_id,'數量',new_qty)
                更新('進貨','紀錄ID',rec_id,'總價',new_qty*price)
                更新('進貨','紀錄ID',rec_id,'日期', new_date.strftime('%Y-%m-%d'))
                st.success('已更新進貨紀錄')
        if st.button('刪除進貨紀錄'):
            刪除('進貨','紀錄ID',rec_id)
            st.success('已刪除進貨紀錄')

# 銷售管理
elif menu == '銷售':
    st.header('➕ 銷售管理')
    tab1,tab2,tab3 = st.tabs(['範例檔下載','手動記錄','編輯/刪除紀錄'])
    # 範例檔
    with tab1:
        sample_csv = """類別名稱,品項名稱,細項名稱,數量,單價,日期
零件類,螺絲,銀珠3mm,5,8.0,2025-07-16"""
        st.download_button('下載銷售範例檔', sample_csv, file_name='sales_sample.csv', mime='text/csv')
    # 手動記錄
    with tab2:
        cmap = 取得對映('類別')
        sel_cat = st.selectbox('類別', ['請選擇']+list(cmap.keys()))
        if sel_cat != '請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('品項', ['請選擇']+list(imap.keys()))
            if sel_item != '請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                sel_sub = st.selectbox('細項', ['請選擇']+list(smap.keys()))
                if sel_sub != '請選擇':
                    sid = smap[sel_sub]
                    date = st.date_input('日期')
                    qty = st.number_input('數量', min_value=0.0, value=1.0, step=0.1, format='%.1f')
                    price = st.number_input('單價', min_value=0.0, value=0.0, step=0.1, format='%.1f')
                    if st.button('儲存銷售'):
                        新增('銷售',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                             [cid,iid,sid,qty,price,qty*price,date.strftime('%Y-%m-%d')])
                        st.success('已儲存銷售')
    # 編輯/刪除
    with tab3:
        df_all = pd.read_sql(
            "SELECT p.紀錄ID, c.類別名稱, i.品項名稱, s.細項名稱, p.數量, p.單價, p.總價, p.日期 "
            "FROM 銷售 p JOIN 類別 c ON p.類別編號=c.類別編號 "
            "JOIN 品項 i ON p.品項編號=i.品項編號 "
            "JOIN 細項 s ON p.細項編號=s.細項編號", conn)
        st.dataframe(df_all)
        rec_id = st.number_input('紀錄ID', min_value=1, step=1, key='sell_rec')
        price_row = conn.execute('SELECT 單價, 日期 FROM 銷售 WHERE 紀錄ID=?', (rec_id,)).fetchone()
        old_qty = conn.execute('SELECT 數量 FROM 銷售 WHERE 紀錄ID=?', (rec_id,)).fetchone()[0]
        old_date = None
        if price_row:
            old_date = price_row[1]
        new_qty = st.number_input('新數量', min_value=0.0, value=float(old_qty), step=0.1, format='%.1f')
        new_date = st.date_input('新日期', value=datetime.strptime(old_date, '%Y-%m-%d') if old_date else datetime.now())
        if st.button('更新銷售紀錄', key='upd_sell'):
            if price_row:
                price = price_row[0]
                更新('銷售','紀錄ID',rec_id,'數量',new_qty)
                更新('銷售','紀錄ID',rec_id,'總價',new_qty*price)
                更新('銷售','紀錄ID',rec_id,'日期', new_date.strftime('%Y-%m-%d'))
                st.success('已更新銷售紀錄')
elif menu == '銷售':
    st.header('➕ 銷售管理')
    tab1,tab2,tab3 = st.tabs(['範例檔下載','手動記錄','編輯/刪除紀錄'])
    # 範例檔
    with tab1:
        sample_csv = """類別名稱,品項名稱,細項名稱,數量,單價,日期
零件類,螺絲,銀珠3mm,5,8.0,2025-07-16"""
        st.download_button('下載銷售範例檔', sample_csv, file_name='sales_sample.csv', mime='text/csv')
    # 手動記錄
    with tab2:
        cmap = 取得對映('類別')
        sel_cat = st.selectbox('類別', ['請選擇']+list(cmap.keys()))
        if sel_cat != '請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('品項', ['請選擇']+list(imap.keys()))
            if sel_item != '請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                sel_sub = st.selectbox('細項', ['請選擇']+list(smap.keys()))
                if sel_sub != '請選擇':
                    sid = smap[sel_sub]
                    date = st.date_input('日期')
                    qty = st.number_input('數量', min_value=0.0, value=1.0, step=0.1, format='%.1f')
                    price = st.number_input('單價', min_value=0.0, value=0.0, step=0.1, format='%.1f')
                    if st.button('儲存銷售'):
                        新增('銷售',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                             [cid,iid,sid,qty,price,qty*price,date.strftime('%Y-%m-%d')])
                        st.success('已儲存銷售')
    # 編輯/刪除
    with tab3:
        df_all = pd.read_sql(
            "SELECT p.紀錄ID, c.類別名稱, i.品項名稱, s.細項名稱, p.數量, p.單價, p.總價, p.日期 "
            "FROM 銷售 p JOIN 類別 c ON p.類別編號=c.類別編號 "
            "JOIN 品項 i ON p.品項編號=i.品項編號 "
            "JOIN 細項 s ON p.細項編號=s.細項編號", conn)
        st.dataframe(df_all)
        rec_id = st.number_input('紀錄ID', min_value=1, step=1, key='sell_rec')
        new_qty = st.number_input('新數量', min_value=0.0, step=0.1, format='%.1f', key='sell_qty')
        if st.button('更新銷售數量', key='upd_sell'):
            price = conn.execute('SELECT 單價 FROM 銷售 WHERE 紀錄ID=?', (rec_id,)).fetchone()[0]
            更新('銷售','紀錄ID',rec_id,'數量',new_qty)
            更新('銷售','紀錄ID',rec_id,'總價',new_qty*price)
            st.success('已更新銷售')
        if st.button('刪除銷售紀錄', key='del_sell'):
            刪除('銷售','紀錄ID',rec_id)
            st.success('已刪除銷售')

# --- 日期查詢 ---
elif menu == '日期查詢':
    st.header('📅 按日期查詢')
    sd = st.date_input('開始日期')
    ed = st.date_input('結束日期')
    if sd <= ed:
        dfp = pd.read_sql('SELECT * FROM 進貨', conn);
        dfs = pd.read_sql('SELECT * FROM 銷售', conn)
        dfp['日期'] = pd.to_datetime(dfp['日期']); dfs['日期'] = pd.to_datetime(dfs['日期'])
        fp = dfp[(dfp['日期']>=sd)&(dfp['日期']<=ed)]; fs = dfs[(dfs['日期']>=sd)&(dfs['日期']<=ed)]
        dfc = 查詢('類別'); dfi = 查詢('品項'); dfsu = 查詢('細項')
        gp = fp.merge(dfc, on='類別編號').merge(dfi, on='品項編號').merge(dfsu, on='細項編號')
        gs = fs.merge(dfc, on='類別編號').merge(dfi, on='品項編號').merge(dfsu, on='細項編號')
        sp = gp.groupby('類別名稱', as_index=False)['總價'].sum().rename(columns={'總價':'進貨支出'})
        ss = gs.groupby('類別名稱', as_index=False)['總價'].sum().rename(columns={'總價':'銷售收入'})
        summary = pd.merge(sp, ss, on='類別名稱', how='outer').fillna(0)
        st.dataframe(summary, use_container_width=True)
        st.metric('總進貨支出', summary['進貨支出'].sum())
        st.metric('總銷售收入', summary['銷售收入'].sum())

# --- 儀表板 ---
elif menu == '儀表板':
    st.header('📊 庫存儀表板')
    dfp = pd.read_sql('SELECT * FROM 進貨', conn)
    dfs = pd.read_sql('SELECT * FROM 銷售', conn)
    dfc = 查詢('類別'); dfi = 查詢('品項'); dfsu = 查詢('細項')
    merged_p = dfp.merge(dfc, on='類別編號').merge(dfi, on='品項編號').merge(dfsu, on='細項編號')
    merged_s = dfs.merge(dfc, on='類別編號').merge(dfi, on='品項編號').merge(dfsu, on='細項編號')
    sum_p = merged_p.groupby(['類別名稱','品項名稱','細項名稱'], as_index=False).agg(
        進貨數量=('數量','sum'), 進貨支出=('總價','sum')
    )
    sum_s = merged_s.groupby(['類別名稱','品項名稱','細項名稱'], as_index=False).agg(
        銷售數量=('數量','sum'), 銷售收入=('總價','sum')
    )
    summary = pd.merge(sum_p, sum_s, on=['類別名稱','品項名稱','細項名稱'], how='outer').fillna(0)
    summary['庫存數量'] = summary['進貨數量'] - summary['銷售數量']
    summary['平均進貨單價'] = summary.apply(lambda r: r['進貨支出']/r['進貨數量'] if r['進貨數量']>0 else 0, axis=1)
    summary['平均銷售單價'] = summary.apply(lambda r: r['銷售收入']/r['銷售數量'] if r['銷售數量']>0 else 0, axis=1)
    summary['庫存價值'] = summary['庫存數量'] * summary['平均進貨單價']
    # 篩選
    sel_cat = st.selectbox('篩選類別', ['全部'] + summary['類別名稱'].unique().tolist())
    if sel_cat != '全部': summary = summary[summary['類別名稱']==sel_cat]
    sel_item = st.selectbox('篩選品項', ['全部'] + summary['品項名稱'].unique().tolist())
    if sel_item != '全部': summary = summary[summary['品項名稱']==sel_item]
    sel_sub = st.selectbox('篩選細項', ['全部'] + summary['細項名稱'].unique().tolist())
    if sel_sub != '全部': summary = summary[summary['細項名稱']==sel_sub]
    st.dataframe(summary[[
        '類別名稱','品項名稱','細項名稱',
        '進貨數量','平均進貨單價','進貨支出',
        '銷售數量','平均銷售單價','銷售收入',
        '庫存數量','庫存價值'
    ]], use_container_width=True)
    st.metric('總進貨支出', summary['進貨支出'].sum())
    st.metric('總銷售收入', summary['銷售收入'].sum())
    st.metric('總庫存價值', (summary['庫存數量']*summary['平均進貨單價']).sum())
