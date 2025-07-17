import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

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

# --- 輔助函式 ---
def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 新增(table: str, cols: list, vals: list) -> int:
    df = 查詢(table)
    cols_used = df.columns.tolist()[1:1+len(vals)]
    placeholders = ",".join(["?"] * len(vals))
    try:
        c.execute(
            f"INSERT INTO {table} ({','.join(cols_used)}) VALUES ({placeholders})",
            vals
        )
        conn.commit()
        new_id = c.lastrowid
        st.session_state['last_action'] = {
            'type':'新增', 'table':table,
            'pk_col': cols_used[0], 'pk_val': new_id
        }
        return new_id
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能重複或外鍵限制")
        return None

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
    if not name_col:
        return {}
    rows = conn.execute(f"SELECT {name_col},{id_col} FROM {table}").fetchall()
    return {name: idx for name, idx in rows}

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])

# 類別管理
if menu == '類別管理':
    st.header('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    st.download_button(
        '下載類別 CSV',
        df.to_csv(index=False, encoding='utf-8-sig'),
        'categories.csv',
        'text/csv'
    )
    with st.form('form_cat'):
        new_cat = st.text_input('新增類別', key='cat_new')
        del_cat = st.text_input('刪除編號', key='cat_del')
        confirm_del = st.checkbox(f'確認刪除類別編號 {del_cat}?') if del_cat.isdigit() else False
        if st.form_submit_button('執行'):
            if new_cat:
                新增('類別',['類別名稱'],[new_cat])
            if del_cat.isdigit() and confirm_del:
                刪除('類別','類別編號',int(del_cat))
            st.session_state['cat_new']=''
            st.session_state['cat_del']=''
            if hasattr(st,'experimental_rerun'):
                st.experimental_rerun()

# 品項管理
elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先新增類別')
    else:
        sel = st.selectbox('選擇類別', list(cmap.keys()))
        cid = cmap[sel]
        df = pd.read_sql(
            'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
            conn, params=(cid,)
        ).rename(columns={'品項編號':'編號','品項名稱':'名稱'})
        st.table(df)
        st.download_button(
            '下載品項 CSV',
            df.to_csv(index=False, encoding='utf-8-sig'),
            f'items_cat{cid}.csv',
            'text/csv'
        )
        with st.form('form_item'):
            new_item = st.text_input('新增品項', key='item_new')
            del_item = st.text_input('刪除編號', key='item_del')
            confirm_item = st.checkbox(f'確認刪除品項編號 {del_item}?') if del_item.isdigit() else False
            if st.form_submit_button('執行'):
                if new_item:
                    新增('品項',['類別編號','品項名稱'],[cid,new_item])
                if del_item.isdigit() and confirm_item:
                    刪除('品項','品項編號',int(del_item))
                st.session_state['item_new']=''
                st.session_state['item_del']=''
                if hasattr(st,'experimental_rerun'):
                    st.experimental_rerun()

# 細項管理
elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先新增類別')
    else:
        sel = st.selectbox('選擇類別', list(cmap.keys()))
        cid = cmap[sel]
        df_i = pd.read_sql(
            'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
            conn, params=(cid,)
        )
        imap = dict(zip(df_i['品項名稱'], df_i['品項編號']))
        if not imap:
            st.warning('該類別尚無品項')
        else:
            sel2 = st.selectbox('選擇品項', list(imap.keys()))
            iid = imap[sel2]
            df_s = pd.read_sql(
                'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                conn, params=(iid,)
            ).rename(columns={'細項編號':'編號','細項名稱':'名稱'})
            st.table(df_s)
            st.download_button(
                '下載細項 CSV',
                df_s.to_csv(index=False, encoding='utf-8-sig'),
                f'subs_item{iid}.csv',
                'text/csv'
            )
            with st.form('form_sub'):
                new_sub = st.text_input('新增細項', key='sub_new')
                del_sub = st.text_input('刪除編號', key='sub_del')
                confirm_sub = st.checkbox(f'確認刪除細項編號 {del_sub}?') if del_sub.isdigit() else False
                if st.form_submit_button('執行'):
                    if new_sub:
                        新增('細項',['品項編號','細項名稱'],[iid,new_sub])
                    if del_sub.isdigit() and confirm_sub:
                        刪除('細項','細項編號',int(del_sub))
                    st.session_state['sub_new']=''
                    st.session_state['sub_del']=''
                    if hasattr(st,'experimental_rerun'):
                        st.experimental_rerun()

# 進貨管理
elif menu == '進貨':
    st.header('➕ 進貨管理')
    tab1, tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        df = 查詢('進貨')
        st.download_button(
            '下載所有進貨記錄 CSV',
            df.to_csv(index=False, encoding='utf-8-sig'),
            'purchases.csv',
            'text/csv'
        )
    with tab2:
        # 你的手動記錄邏輯保持不變
        pass

# 銷售管理
elif menu == '銷售':
    st.header('➕ 銷售管理')
    tab1, tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        df = 查詢('銷售')
        st.download_button(
            '下載所有銷售記錄 CSV',
            df.to_csv(index=False, encoding='utf-8-sig'),
            'sales.csv',
            'text/csv'
        )
    with tab2:
        # 你的手動記錄邏輯保持不變
        pass

# 儀表板
elif menu == '儀表板':
    st.header('📊 庫存儀表板')
    df_p  = pd.read_sql('SELECT * FROM 進貨', conn)
    df_s  = pd.read_sql('SELECT * FROM 銷售', conn)
    df_c  = 查詢('類別')
    df_i  = 查詢('品項')
    df_su = 查詢('細項')
    gp = (df_p
          .merge(df_c, on='類別編號')
          .merge(df_i, on='品項編號')
          .merge(df_su, on='細項編號')
          .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
          .agg(進貨=('數量','sum'),支出=('總價','sum')))
    gs = (df_s
          .merge(df_c, on='類別編號')
          .merge(df_i, on='品項編號')
          .merge(df_su, on='細項編號')
          .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
          .agg(銷售=('數量','sum'),收入=('總價','sum')))
    summary = pd.merge(gp, gs,
                       on=['類別名稱','品項名稱','細項名稱'],
                       how='outer').fillna(0)
    summary['庫存'] = summary['進貨'] - summary['銷售']
    st.dataframe(summary)
    st.download_button(
        '下載庫存摘要 CSV',
        summary.to_csv(index=False, encoding='utf-8-sig'),
        'summary.csv',
        'text/csv'
    )
    st.metric('總支出', f"{gp['支出'].sum():.2f}")
    st.metric('總收入', f"{gs['收入'].sum():.2f}")
    st.metric('淨利',   f"{gs['收入'].sum()-gp['支出'].sum():.2f}")
