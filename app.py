import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
for tbl in ['類別','品項','細項','進貨','銷售']:
    # tables ensure
    pass
# 建表略，請參考先前版本中初始化代碼

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

# --- UI ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", ['細項管理','其他功能...'])

if menu == '細項管理':
    st.header('⚙️ 細項管理')
    # 類別選擇
    cat_map = 取得對映('類別')
    cat_opts = ['請選擇'] + list(cat_map.keys())
    sel_cat = st.selectbox('選擇類別', cat_opts)
    if sel_cat != '請選擇':
        cid = cat_map[sel_cat]
        # 品項選擇
        items = pd.read_sql('SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
        item_map = dict(zip(items['品項名稱'], items['品項編號']))
        item_opts = ['請選擇'] + list(item_map.keys())
        sel_item = st.selectbox('選擇品項', item_opts)
        if sel_item != '請選擇':
            iid = item_map[sel_item]
            # 細項清單
            subs = pd.read_sql('SELECT 細項編號, 細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
            sub_map = dict(zip(subs['細項名稱'], subs['細項編號']))
            st.table(subs.rename(columns={'細項編號':'編號','細項名稱':'名稱'}))
            sub_opts = ['新增細項'] + list(sub_map.keys())
            sel_sub = st.selectbox('選擇細項或新增', sub_opts)
            if sel_sub == '新增細項':
                # 新增細項表單
                with st.form('form_new_sub'):
                    new_name = st.text_input('細項名稱')
                    if st.form_submit_button('新增細項') and new_name:
                        新增('細項',['品項編號','細項名稱'],[iid,new_name])
                        st.experimental_rerun()
            else:
                sid = sub_map[sel_sub]
                # 編輯初始庫存
                with st.form('form_init'):
                    qty_str = st.text_input('初始數量 (留空不設定)')
                    price_str = st.text_input('初始單價 (留空不設定)')
                    date_str = st.text_input('初始日期 YYYY-MM-DD (留空使用今天)')
                    if st.form_submit_button('儲存初始庫存'):
                        # 解析欄位
                        qty = int(qty_str) if qty_str.isdigit() else None
                        try:
                            price = float(price_str) if price_str else None
                        except:
                            price = None
                        if date_str:
                            try:
                                dt = datetime.strptime(date_str, '%Y-%m-%d')
                                date = dt.strftime('%Y-%m-%d')
                            except:
                                st.warning('日期格式錯誤')
                                date = datetime.now().strftime('%Y-%m-%d')
                        else:
                            date = datetime.now().strftime('%Y-%m-%d')
                        # 插入進貨記錄
                        if qty is not None or price is not None:
                            use_qty = qty if qty is not None else 0
                            use_price = price if price is not None else 0.0
                            total = use_qty * use_price
                            新增('進貨',['類別編號','品項編號','細項編號','數量','單價','總價','日期'],
                                  [cid,iid,sid,use_qty,use_price,total,date])
                            st.success('初始庫存已儲存')

else:
    st.write('其他功能請參考先前版本')
