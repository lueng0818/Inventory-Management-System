# === app.py (1/3) ===
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
        日期 TEXT
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
        '細項': ('細項名稱', '細項編號'),
    }
    name_col, id_col = mapping.get(table, (None, None))
    if not name_col:
        return {}
    rows = conn.execute(f"SELECT {name_col}, {id_col} FROM {table}").fetchall()
    return {name: idx for name, idx in rows}

def 新增(table: str, cols: list, vals: list):
    c.execute(
        f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join(['?']*len(vals))})",
        vals
    )
    conn.commit()
    return c.lastrowid

def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col}=?", (key_val,))
    conn.commit()

def 更新(table: str, key_col: str, key_val, col: str, new_val):
    c.execute(f"UPDATE {table} SET {col}=? WHERE {key_col}=?", (new_val, key_val))
    conn.commit()

# --- 主介面分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", [
    '類別管理','品項管理','細項管理','進貨','銷售','日期查詢','儀表板'
])

# === app.py (2/3) ===

if menu == '類別管理':
    st.header('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('form_cat'):
        new = st.text_input('新增類別')
        d = st.text_input('刪除編號')
        if st.form_submit_button('執行'):
            if new: 新增('類別',['類別名稱'],[new])
            if d.isdigit(): 刪除('類別','類別編號',int(d))
            st.experimental_rerun()

elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先建立類別')
    else:
        sel = st.selectbox('選擇類別',['請選擇']+list(cmap.keys()))
        if sel!='請選擇':
            cid = cmap[sel]
            df = pd.read_sql(
                'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            st.table(df.rename(columns={'品項編號':'編號','品項名稱':'名稱'}))
            with st.form('form_item'):
                new = st.text_input('新增品項')
                d = st.text_input('刪除編號')
                if st.form_submit_button('執行'):
                    if new: 新增('品項',['類別編號','品項名稱'],[cid,new])
                    if d.isdigit(): 刪除('品項','品項編號',int(d))
                    st.experimental_rerun()

elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先建立類別')
    else:
        selc = st.selectbox('選擇類別',['請選擇']+list(cmap.keys()))
        if selc!='請選擇':
            cid = cmap[selc]
            items = pd.read_sql(
                'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            selp = st.selectbox('選擇品項',['請選擇']+list(imap.keys()))
            if selp!='請選擇':
                iid = imap[selp]
                subs = pd.read_sql(
                    'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                    conn, params=(iid,)
                )
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                act = st.selectbox('操作',['新增','刪除']+list(smap.keys()))
                if act=='新增':
                    name = st.text_input('新細項名稱')
                    if st.button('新增細項') and name:
                        新增('細項',['品項編號','細項名稱'],[iid,name])
                        st.experimental_rerun()
                elif act=='刪除':
                    dn = st.selectbox('刪除細項',['請選擇']+list(smap.keys()))
                    if dn!='請選擇' and st.button('刪除細項'):
                        刪除('細項','細項編號',smap[dn])
                        st.experimental_rerun()
                else:
                    sid = smap[act]
                    # 初始庫存設定
                    if 'init_rec' not in st.session_state:
                        with st.form('save_init'):
                            q = st.number_input('初始數量',min_value=0.0,step=0.1,format='%.1f')
                            p = st.number_input('初始單價',min_value=0.0,step=0.1,format='%.1f')
                            d = st.date_input('初始日期')
                            if st.form_submit_button('儲存初始庫存'):
                                rec = 新增(
                                    '進貨',
                                    ['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                                    [cid,iid,sid,q,p,q*p,d.strftime('%Y-%m-%d')]
                                )
                                st.session_state.init_rec = rec
                                st.success('已儲存初始庫存')
                    else:
                        rec = st.session_state.init_rec
                        oq, op, od = conn.execute(
                            'SELECT 數量,單價,日期 FROM 進貨 WHERE 紀錄ID=?',
                            (rec,)
                        ).fetchone()
                        st.info(f'初始紀錄ID={rec}, 數量={oq}, 單價={op}, 日期={od}')
                        with st.form('edit_init'):
                            nq  = st.number_input('修改數量',min_value=0.0,value=oq,step=0.1,format='%.1f')
                            upd = st.checkbox('更新日期')
                            nd  = st.date_input('新日期',value=datetime.strptime(od,'%Y-%m-%d'))
                            if st.form_submit_button('更新初始庫存'):
                                更新('進貨','紀錄ID',rec,'數量',nq)
                                更新('進貨','紀錄ID',rec,'總價',nq*op)
                                if upd:
                                    更新('進貨','紀錄ID',rec,'日期',nd.strftime('%Y-%m-%d'))
                                st.success('已更新初始庫存')
# === app.py (3/3) ===

elif menu == '進貨':
    st.header('➕ 進貨管理')
    tab1, tab2, tab3 = st.tabs(['匯入','手動','編輯'])

    # 批次匯入
    with tab1:
        st.write('上傳 CSV 批次匯入進貨')
        up = st.file_uploader('', type='csv')
        if up:
            df = pd.read_csv(up)
            cmap = 取得對映('類別')
            imap, smap = {}, {}
            for idx, row in df.iterrows():
                cat = row['類別名稱']
                item = row['品項名稱']
                sub  = row['細項名稱']
                try:
                    qty = float(row['數量'])
                    pr  = float(row['單價'])
                except:
                    st.error(f'第{idx+1}列 數量或單價格式錯誤')
                    continue
                date = row['日期']
                cid = cmap.get(cat)
                if cid is None:
                    st.error(f'找不到類別：{cat}')
                    continue
                if (cid, item) not in imap:
                    r = conn.execute(
                        'SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?',
                        (cid, item)
                    ).fetchone()
                    imap[(cid,item)] = r[0] if r else None
                iid = imap[(cid,item)]
                if iid is None:
                    st.error(f'找不到品項：{item}')
                    continue
                if (iid, sub) not in smap:
                    r = conn.execute(
                        'SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?',
                        (iid, sub)
                    ).fetchone()
                    smap[(iid,sub)] = r[0] if r else None
                sid = smap[(iid,sub)]
                if sid is None:
                    st.error(f'找不到細項：{sub}')
                    continue
                total = qty * pr
                新增(
                    '進貨',
                    ['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                    [cid, iid, sid, qty, pr, total, date]
                )
            st.success('批次匯入完成')

    # 手動記錄
    with tab2:
        cmap = 取得對映('類別')
        cat  = st.selectbox('類別', ['請選擇'] + list(cmap.keys()))
        if cat != '請選擇':
            cid = cmap[cat]
            items = pd.read_sql(
                'SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            it = st.selectbox('品項', ['請選擇'] + list(imap.keys()))
            if it != '請選擇':
                iid = imap[it]
                subs = pd.read_sql(
                    'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                    conn, params=(iid,)
                )
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                su = st.selectbox('細項', ['請選擇'] + list(smap.keys()))
                if su != '請選擇':
                    sid = smap[su]
                    date = st.date_input('日期')
                    qty  = st.number_input('數量', min_value=0.0, step=0.1, format='%.1f')
                    pr   = st.number_input('單價', min_value=0.0, step=0.1, format='%.1f')
                    if st.button('儲存進貨'):
                        新增(
                            '進貨',
                            ['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                            [cid, iid, sid, qty, pr, qty*pr, date.strftime('%Y-%m-%d')]
                        )
                        st.success('已儲存進貨')

    # 編輯/刪除
    with tab3:
        df_all = pd.read_sql(
            'SELECT p.紀錄ID, c.類別名稱, i.品項名稱, s.細項名稱, '
            'p.數量, p.單價, p.總價, p.日期 '
            'FROM 進貨 p '
            'JOIN 類別 c ON p.類別編號=c.類別編號 '
            'JOIN 品項 i ON p.品項編號=i.品項編號 '
            'JOIN 細項 s ON p.細項編號=s.細項編號',
            conn
        )
        st.dataframe(df_all)
        rec = int(st.number_input('紀錄ID', min_value=1, step=1))
        row = conn.execute(
            'SELECT 數量, 單價, 日期 FROM 進貨 WHERE 紀錄ID=?', (rec,)
        ).fetchone()
        oq, op, od = row if row else (0.0, 0.0, datetime.now().strftime('%Y-%m-%d'))
        nq  = st.number_input('新數量', min_value=0.0, value=oq, step=0.1, format='%.1f')
        upd = st.checkbox('更新日期')
        nd  = st.date_input('新日期', value=datetime.strptime(od,'%Y-%m-%d'))
        if st.button('更新進貨'):
            更新('進貨','紀錄ID',rec,'數量',nq)
            更新('進貨','紀錄ID',rec,'總價',nq*op)
            if upd:
                更新('進貨','紀錄ID',rec,'日期',nd.strftime('%Y-%m-%d'))
            st.success('已更新進貨紀錄')
        if st.button('刪除進貨'):
            刪除('進貨','紀錄ID',rec)
            st.success('已刪除進貨紀錄')

# 銷售管理、日期查詢、儀表板可按相同邏輯實作，若需要完整段落也可補上。
