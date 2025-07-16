import streamlit as st
st.set_page_config(layout="wide")
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 建立主表
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
# 建立交易表
for tbl in ['進貨', '銷售']:
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
    )
    ''')
conn.commit()

# --- 輔助函式 ---
def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 更新(table: str, key_col: str, key_val, col: str, new_val):
    """
    更新單一欄位值
    """
    c.execute(f"UPDATE {table} SET {col} = ? WHERE {key_col} = ?", (new_val, key_val))
    conn.commit()

def 新增(table: str, cols: list, vals: list):

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", [
    '類別管理', '品項管理', '細項管理', '進貨', '銷售', '日期查詢', '儀表板'
])

# 類別管理
if menu == '類別管理':
    st.header('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('form_cat'):
        new_cat = st.text_input('新增類別')
        del_cat = st.text_input('刪除類別編號')
        if st.form_submit_button('執行'):
            if new_cat: 新增('類別',['類別名稱'],[new_cat])
            if del_cat.isdigit(): 刪除('類別','類別編號',int(del_cat))
            st.experimental_rerun()

# 品項管理
elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先建立類別')
    else:
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()))
        if sel_cat!='請選擇':
            cid = cmap[sel_cat]
            df = pd.read_sql(
                'SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,)
            ).rename(columns={'品項編號':'編號','品項名稱':'名稱'})
            st.table(df)
            with st.form('form_item'):
                new_item = st.text_input('新增品項')
                del_item = st.text_input('刪除品項編號')
                if st.form_submit_button('執行'):
                    if new_item: 新增('品項',['類別編號','品項名稱'],[cid,new_item])
                    if del_item.isdigit(): 刪除('品項','品項編號',int(del_item))
                    st.experimental_rerun()

# 細項管理
elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先建立類別')
    else:
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()))
        if sel_cat!='請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql(
                'SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,)
            )
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('選擇品項', ['請選擇']+list(imap.keys()))
            if sel_item!='請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql(
                    'SELECT 細項編號, 細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,)
                )
                sub_map = dict(zip(subs['細項名稱'], subs['細項編號']))
                actions = ['新增細項','刪除細項'] + list(sub_map.keys())
                sel_action = st.selectbox('操作：', actions)
                if sel_action=='新增細項':
                    with st.form('form_new'):
                        name = st.text_input('新細項名稱')
                        if st.form_submit_button('新增') and name:
                            新增('細項',['品項編號','細項名稱'],[iid,name]); st.experimental_rerun()
                elif sel_action=='刪除細項':
                    del_name = st.selectbox('選擇刪除', ['請選擇']+list(sub_map.keys()))
                    if del_name!='請選擇' and st.button('確認刪除'):
                        刪除('細項','細項編號', sub_map[del_name]); st.success(f'已刪除細項：{del_name}'); st.experimental_rerun()
                else:
                    sid = sub_map[sel_action]
                    with st.form('form_init'):
                        qty = st.text_input('初始數量')
                        price = st.text_input('初始單價')
                        date_str = st.text_input('初始日期 YYYY-MM-DD')
                        if st.form_submit_button('儲存初始庫存'):
                            q = int(qty) if qty.isdigit() else 0
                            p = float(price) if price.replace('.','',1).isdigit() else 0.0
                            try:
                                d = datetime.strptime(date_str,'%Y-%m-%d').strftime('%Y-%m-%d') if date_str else datetime.now().strftime('%Y-%m-%d')
                            except:
                                d = datetime.now().strftime('%Y-%m-%d')
                            新增('進貨',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],[cid,iid,sid,q,p,q*p,d])
                            st.success('初始庫存已儲存')
                            st.table(pd.DataFrame([{'細項名稱': sel_action, '數量': q, '單價': p, '日期': d}]))

# 進貨管理
elif menu=='進貨':
    st.header('➕ 進貨管理')
    tab1, tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        st.info('批次匯入請使用範例檔')
    with tab2:
        cmap = 取得對映('類別')
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()))
        if sel_cat!='請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('選擇品項', ['請選擇']+list(imap.keys()))
            if sel_item!='請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號, 細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                sel_sub = st.selectbox('選擇細項', ['請選擇']+ list(smap.keys()))
                if sel_sub!='請選擇':
                    sid = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期', value=True)
                    date = datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期').strftime('%Y-%m-%d')
                    qty = st.number_input('數量', min_value=1, value=1)
                    price = st.number_input('單價', min_value=0.0, format='%.2f')
                    if st.button('儲存進貨'):
                        total = qty * price
                        新增('進貨', ['類別編號','品項編號','細項編號','數量','單價','總價','日期'], [cid,iid,sid,qty,price,total,date])
                        st.success(f'進貨記錄已儲存：{date}')

# 銷售管理
elif menu=='銷售':
    st.header('➕ 銷售管理')
    tab1, tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        st.info('批次匯入請使用範例檔')
    with tab2:
        cmap = 取得對映('類別')
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()), key='sell_cat')
        if sel_cat!='請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            sel_item = st.selectbox('選擇品項', ['請選擇']+ list(imap.keys()), key='sell_item')
            if sel_item!='請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號, 細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                sel_sub = st.selectbox('選擇細項', ['請選擇']+ list(smap.keys()), key='sell_sub')
                if sel_sub!='請選擇':
                    sid = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期', value=True, key='sell_today')
                    date = datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期').strftime('%Y-%m-%d')
                    qty = st.number_input('數量', min_value=1, value=1, key='sell_qty')
                    price = st.number_input('單價', min_value=0.0, format='%.2f', key='sell_price')
                    if st.button('儲存銷售'):
                        total = qty * price
                        新增('銷售', ['類別編號','品項編號','細項編號','數量','單價','總價','日期'], [cid,iid,sid,qty,price,total,date])
                        st.success(f'銷售記錄已儲存：{date}')

# 日期查詢
elif menu == '日期查詢':
    st.header('📅 按日期查詢')
    col1, col2 = st.columns(2)
    with col1:
        start = st.date_input('開始日期')
    with col2:
        end = st.date_input('結束日期')
    if start > end:
        st.error('開始日期不可晚於結束日期')
    else:
        df_p = pd.read_sql('SELECT * FROM 進貨', conn)
        df_s = pd.read_sql('SELECT * FROM 銷售', conn)
        df_p['日期'] = pd.to_datetime(df_p['日期'])
        df_s['日期'] = pd.to_datetime(df_s['日期'])
        mask_p = (df_p['日期'] >= pd.to_datetime(start)) & (df_p['日期'] <= pd.to_datetime(end))
        mask_s = (df_s['日期'] >= pd.to_datetime(start)) & (df_s['日期'] <= pd.to_datetime(end))
        sel_p = df_p.loc[mask_p]
        sel_s = df_s.loc[mask_s]
        df_c = 查詢('類別'); df_i = 查詢('品項'); df_su = 查詢('細項')
        sel_p = sel_p.merge(df_c, on='類別編號').merge(df_i, on='品項編號').merge(df_su, on='細項編號')
        sel_s = sel_s.merge(df_c, on='類別編號').merge(df_i, on='品項編號').merge(df_su, on='細項編號')
        gp = sel_p.groupby('類別名稱', as_index=False)['總價'].sum().rename(columns={'總價':'進貨支出'})
        gs = sel_s.groupby('類別名稱', as_index=False)['總價'].sum().rename(columns={'總價':'銷售收入'})
        summary_date = pd.merge(gp, gs, on='類別名稱', how='outer').fillna(0)
        st.subheader(f'{start} 至 {end} 各類別統計')
        st.dataframe(summary_date, use_container_width=True)
        total_p = sel_p['總價'].sum()
        total_s = sel_s['總價'].sum()
        st.metric('所選期間總進貨支出', f"{total_p:.2f}")
        st.metric('所選期間總銷售收入', f"{total_s:.2f}")

# 儀表板
elif menu=='儀表板':
    st.header('📊 庫存儀表板')
    st.set_page_config(layout="wide")
    # 讀取資料
    df_p = pd.read_sql('SELECT * FROM 進貨', conn)
    df_s = pd.read_sql('SELECT * FROM 銷售', conn)
    df_c = 查詢('類別')
    df_i = 查詢('品項')
    df_su = 查詢('細項')
    # 彙總進貨
    gp = (
        df_p.merge(df_c, on='類別編號')
            .merge(df_i, on='品項編號')
            .merge(df_su, on='細項編號')
            .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
            .agg(
                進貨數量=('數量','sum'),
                進貨支出=('總價','sum')
            )
    )
    # 彙總銷售
    gs = (
        df_s.merge(df_c, on='類別編號')
            .merge(df_i, on='品項編號')
            .merge(df_su, on='細項編號')
            .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
            .agg(
                銷售數量=('數量','sum'),
                銷售收入=('總價','sum')
            )
    )
    # 合併並計算庫存＆價格
    summary = pd.merge(gp, gs, on=['類別名稱','品項名稱','細項名稱'], how='outer').fillna(0)
    summary['庫存數量'] = summary['進貨數量'] - summary['銷售數量']
    summary['平均進貨單價'] = summary.apply(
        lambda row: row['進貨支出']/row['進貨數量'] if row['進貨數量']>0 else 0, axis=1
    )
    summary['平均銷售單價'] = summary.apply(
        lambda row: row['銷售收入']/row['銷售數量'] if row['銷售數量']>0 else 0, axis=1
    )
    summary['庫存價值'] = summary['庫存數量'] * summary['平均進貨單價']
    # 篩選
    cats = ['全部'] + summary['類別名稱'].unique().tolist()
    sel_cat = st.selectbox('篩選類別', cats)
    if sel_cat != '全部': summary = summary[summary['類別名稱']==sel_cat]
    items = ['全部'] + summary['品項名稱'].unique().tolist()
    sel_item = st.selectbox('篩選品項', items)
    if sel_item != '全部': summary = summary[summary['品項名稱']==sel_item]
    subs = ['全部'] + summary['細項名稱'].unique().tolist()
    sel_sub = st.selectbox('篩選細項', subs)
    if sel_sub != '全部': summary = summary[summary['細項名稱']==sel_sub]
    # 顯示 DataFrame：進貨數量、平均進貨單價、進貨支出、銷售數量、平均銷售單價、銷售收入、庫存數量、庫存價值
    st.dataframe(
        summary[[
            '類別名稱','品項名稱','細項名稱',
            '進貨數量','平均進貨單價','進貨支出',
            '銷售數量','平均銷售單價','銷售收入',
            '庫存數量','庫存價值'
        ]], use_container_width=True
    )
    # 全局指標
    st.metric('總進貨支出', f"{summary['進貨支出'].sum():.2f}")
    st.metric('總銷售收入', f"{summary['銷售收入'].sum():.2f}")
    st.metric('總庫存價值', f"{summary['庫存價值'].sum():.2f}")
