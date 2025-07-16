import streamlit as st
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

def 新增(table: str, cols: list, vals: list):
    cols_str = ",".join(cols)
    placeholders = ",".join(["?" for _ in vals])
    try:
        c.execute(f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders})", vals)
        conn.commit()
        return c.lastrowid
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能重複或外鍵限制")
        return None

def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col} = ?", (key_val,))
    conn.commit()

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

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", [
    '類別管理', '品項管理', '細項管理', '進貨', '銷售', '儀表板'
])

if menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先到「類別管理」建立類別')
    else:
        cat_opts = ['請選擇'] + list(cmap.keys())
        sel_cat = st.selectbox('選擇類別', cat_opts)
        if sel_cat != '請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql(
                'SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            item_map = dict(zip(items['品項名稱'], items['品項編號']))
            item_opts = ['請選擇'] + list(item_map.keys())
            sel_item = st.selectbox('選擇品項', item_opts)
            if sel_item != '請選擇':
                iid = item_map[sel_item]
                subs = pd.read_sql(
                    'SELECT 細項編號, 細項名稱 FROM 細項 WHERE 品項編號=?',
                    conn, params=(iid,)
                )
                st.table(subs.rename(columns={'細項編號':'編號','細項名稱':'名稱'}))
                with st.form('form_sub'):
                    new_sub = st.text_input('新增細項')
                    del_sub = st.text_input('刪除編號')
                    init_qty = st.number_input('初始數量', min_value=0, value=0)
                    init_date = st.date_input('初始日期', value=datetime.now())
                    if st.form_submit_button('執行'):
                        # 新增細項
                        new_id = None
                        if new_sub:
                            new_id = 新增('細項', ['品項編號','細項名稱'], [iid, new_sub])
                        # 刪除細項
                        if del_sub.isdigit():
                            刪除('細項', '細項編號', int(del_sub))
                        # 初始庫存紀錄
                        if init_qty > 0 and new_id:
                            total = 0.0
                            新增('進貨', ['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                                  [cid, iid, new_id, init_qty, 0.0, total, init_date.strftime('%Y-%m-%d')])
                        st.experimental_rerun()

else:
    # 其他功能保持不變，請參考先前版本
    pass
