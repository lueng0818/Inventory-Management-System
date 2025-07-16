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
    rows = conn.execute(f"SELECT {name_col}, {id_col} FROM {table}").fetchall() if name_col else []
    return {name: idx for name, idx in rows}

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", ['類別管理', '品項管理', '細項管理', '進貨', '銷售', '儀表板'])

# 類別管理
if menu == '類別管理':
    st.header('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
    st.table(df)
    with st.form('form_cat'):
        new_cat = st.text_input('新增類別')
        del_cat = st.text_input('刪除類別編號')
        if st.form_submit_button('執行'):
            if new_cat:
                新增('類別',['類別名稱'],[new_cat])
            if del_cat.isdigit():
                刪除('類別','類別編號',int(del_cat))
            st.experimental_rerun()

# 品項管理
elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先到「類別管理」建立類別')
    else:
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()))
        if sel_cat!='請選擇':
            cid = cmap[sel_cat]
            df = pd.read_sql('SELECT 品項編號,細項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,)).rename(columns={'品項編號':'編號','品項名稱':'名稱'})
            st.table(df)
            with st.form('form_item'):
                new_item = st.text_input('新增品項')
                del_item = st.text_input('刪除品項編號')
                if st.form_submit_button('執行'):
                    if new_item:
                        新增('品項',['類別編號','品項名稱'],[cid,new_item])
                    if del_item.isdigit():
                        刪除('品項','品項編號',int(del_item))
                    st.experimental_rerun()

# 細項管理
elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    cmap = 取得對映('類別')
    if not cmap:
        st.warning('請先到「類別管理」建立類別')
    else:
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()))
        if sel_cat!='請選擇':
            cid = cmap[sel_cat]
            items = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap = dict(zip(items['品項名稱'],items['品項編號']))
            sel_item = st.selectbox('選擇品項', ['請選擇']+list(imap.keys()))
            if sel_item!='請選擇':
                iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                sub_map = dict(zip(subs['細項名稱'],subs['細項編號']))
                st.table(subs.rename(columns={'細項編號':'編號','細項名稱':'名稱'}))
                sel_sub = st.selectbox('選擇細項或新增', ['新增細項']+list(sub_map.keys()))
                if sel_sub=='新增細項':
                    with st.form('form_new_sub'):
                        new_name = st.text_input('細項名稱')
                        if st.form_submit_button('新增') and new_name:
                            新增('細項',['品項編號','細項名稱'],[iid,new_name])
                            st.experimental_rerun()
                else:
                    sid = sub_map[sel_sub]
                    with st.form('form_edit_sub'):
                        st.write(f'編輯細項：{sel_sub}')
                        qty_str = st.text_input('初始數量 (留空不設定)')
                        price_str = st.text_input('初始單價 (留空不設定)')
                        date_str = st.text_input('初始日期 YYYY-MM-DD (留空=今日)')
                        del_confirm = st.checkbox('刪除此細項')
                        if st.form_submit_button('執行'):
                            if del_confirm:
                                刪除('細項','細項編號',sid)
                                st.success(f'已刪除細項：{sel_sub}')
                                st.experimental_rerun()
                            qty = int(qty_str) if qty_str.isdigit() else None
                            try:
                                price = float(price_str) if price_str else None
                            except:
                                price = None
                            if date_str:
                                try:
                                    date = datetime.strptime(date_str,'%Y-%m-%d').strftime('%Y-%m-%d')
                                except:
                                    st.warning('日期格式錯誤，使用今日')
                                    date = datetime.now().strftime('%Y-%m-%d')
                            else:
                                date = datetime.now().strftime('%Y-%m-%d')
                            if qty is not None or price is not None:
                                use_qty = qty or 0
                                use_price = price or 0.0
                                total = use_qty*use_price
                                新增('進貨',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],[cid,iid,sid,use_qty,use_price,total,date])
                                st.success('初始庫存已儲存')

# 進貨與銷售
elif menu in ['進貨','銷售']:
    title = '進貨' if menu=='進貨' else '銷售'
    st.header(f'➕ {title}管理')
    tab1,tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        st.info('批次匯入請使用範例檔')
    with tab2:
        cmap = 取得對映('類別')
        sel_cat = st.selectbox('選擇類別', ['請選擇']+list(cmap.keys()))
        if sel_cat!='請選擇':
            cid=cmap[sel_cat]
            items=pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap=dict(zip(items['品項名稱'],items['品項編號']))
            sel_item=st.selectbox('選擇品項', ['請選擇']+list(imap.keys()))
            if sel_item!='請選擇':
                iid=imap[sel_item]
                subs=pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap=dict(zip(subs['細項名稱'],subs['細項編號']))
                sel_sub=st.selectbox('選擇細項', ['請選擇']+list(smap.keys()))
                if sel_sub!='請選擇':
                    sid=smap[sel_sub]
                    use_today=st.checkbox('自動帶入今日日期',value=True)
                    date=datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期').strftime('%Y-%m-%d')
                    qty=st.number_input('數量',min_value=1,value=1)
                    price=st.number_input('單價',min_value=0.0,format='%.2f')
                    if st.button(f'儲存{title}'):
                        total=qty*price
                        新增(menu,['類別編號','品項編號','細項編號','數量','單價','總價','日期'],[cid,iid,sid,qty,price,total,date])
                        st.success(f'{title}記錄已儲存')

# 儀表板
elif menu=='儀表板':
    st.header('📊 庫存儀表板')
    df_p=pd.read_sql('SELECT * FROM 進貨',conn)
    df_s=pd.read_sql('SELECT * FROM 銷售',conn)
    df_c=查詢('類別')
    df_i=查詢('品項')
    df_su=查詢('細項')
    gp=(df_p.merge(df_c,on='類別編號').merge(df_i,on='品項編號').merge(df_su,on='細項編號')
         .groupby(['類別名稱','品項名稱','細項名稱'],as_index=False)
         .agg(進貨=('數量','sum'),支出=('總價','sum')))
    gs=(df_s.merge(df_c,on='類別編號').merge(df_i,on='品項編號').merge(df_su,on='細項編號')
         .groupby(['類別名稱','品項名稱','細項名稱'],as_index=False)
         .agg(銷售=('數量','sum'),收入=('總價','sum')))
    summary=pd.merge(gp,gs,on=['類別名稱','品項名稱','細項名稱'],how='outer').fillna(0)
    summary['庫存']=summary['進貨']-summary['銷售']
    st.dataframe(summary,use_container_width=True)
    st.metric('總支出',f"{gp['支出'].sum():.2f}")
    st.metric('總收入',f"{gs['收入'].sum():.2f}")
    st.metric('淨利',f"{gs['收入'].sum()-gp['支出'].sum():.2f}")
