# 輕珠寶設計師專屬庫存管理系統
#
# 專案結構：
# inventory_system/
# ├── app.py
# ├── requirements.txt
# └── database.db (自動建立)

import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 類別表
c.execute('''
CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)''')
# 品項表
c.execute('''
CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)''')
# 細項表
c.execute('''
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)''')
# 銷/進貨表
for tbl in ['進貨','銷售']:
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
)''')
conn.commit()

# --- 輔助函式 ---
def 查詢(table):
    return pd.read_sql(f'SELECT * FROM {table}', conn)

def 新增(table, cols, vals):
    # 動態偵測資料表欄位，跳過第一欄主鍵
    df = 查詢(table)
    cols_all = df.columns.tolist()
    # 排除主鍵 (第一欄)
    target_cols = cols_all[1:1+len(vals)]
    cols_str = ','.join(target_cols)
    qmarks = ','.join(['?'] * len(vals))
    sql = f'INSERT INTO {table} ({cols_str}) VALUES ({qmarks})'
    try:
        c.execute(sql, vals)
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能已重複建立或外鍵限制")
        st.warning("操作失敗：可能已重複建立或外鍵限制")

def 刪除(table, key_col, key_val):
    c.execute(f'DELETE FROM {table} WHERE {key_col}=?', (key_val,))
    conn.commit()

def 取得對映(table, key, val):
    df = 查詢(table)
    df.columns = df.columns.str.strip()
    # 動態尋找包含關鍵字的欄位名稱
    key_col = next((col for col in df.columns if key in col), None)
    val_col = next((col for col in df.columns if val in col), None)
    # 備援檢查：若使用者看到DF列已重新rename為'編號','名稱'
    if not key_col and '編號' in df.columns:
        key_col = '編號'
    if not val_col and '名稱' in df.columns:
        val_col = '名稱'
    if key_col and val_col:
        return dict(zip(df[val_col], df[key_col]))
    st.warning(f"在 {table} 表中找不到含 '{key}' 或 '{val}' 的欄位 (現有: {df.columns.tolist()})")
    return {}

# --- UI ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板','批次匯入買賣進出表'
])

# 類別管理
if menu == '類別管理':
    st.title('⚙️ 類別管理')
    df = 查詢('類別')
    df.columns = df.columns.str.strip()
    st.subheader('現有類別列表')
    st.table(df.rename(columns={'類別編號':'編號','類別名稱':'名稱'})[['編號','名稱']])
    with st.form('form_cat'):
        new_name = st.text_input('新增類別名稱')
        del_id = st.text_input('刪除類別編號')
        submitted = st.form_submit_button('執行')
        if submitted:
            if new_name:
                新增('類別',['類別名稱'],[new_name])
                st.success(f'已新增類別：{new_name}')
            if del_id.isdigit():
                刪除('類別','類別編號',int(del_id))
                st.success(f'已刪除類別編號：{del_id}')
            try:
                st.experimental_rerun()
            except AttributeError:
                st.info('請重新整理頁面以更新資料表')

# 品項管理
elif menu == '品項管理':
    st.title('⚙️ 品項管理')
    cat_map = 取得對映('類別','類別編號','類別名稱')
    if not cat_map:
        st.warning('請先新增類別')
    else:
        st.subheader('現有類別')
        st.write(list(cat_map.keys()))
        sel_cat = st.selectbox('選擇類別', list(cat_map.keys()))
        cat_id = cat_map[sel_cat]
        st.info(f'您選擇的類別：{sel_cat} (編號: {cat_id})')
        df_items = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cat_id,))
        df_items.columns = df_items.columns.str.strip()
        st.subheader(f'「{sel_cat}」下現有品項')
        st.table(df_items.rename(columns={'品項編號':'編號','品項名稱':'名稱'})[['編號','名稱']])
        with st.form('form_item'):
            new_item = st.text_input('新增品項名稱')
            del_item_id = st.text_input('刪除品項編號')
            submit_item = st.form_submit_button('執行')
            if submit_item:
                if new_item:
                    新增('品項',['類別編號','品項名稱'],[cat_id,new_item])
                    st.success(f'於「{sel_cat}」新增品項：{new_item}')
                if del_item_id.isdigit():
                    刪除('品項','品項編號',int(del_item_id))
                    st.success(f'已刪除品項編號：{del_item_id}')
                try:
                    st.experimental_rerun()
                except AttributeError:
                    st.info('請重新整理頁面以更新列表')

# 細項管理
elif menu == '細項管理':
    st.title('⚙️ 細項管理')
    cat_map = 取得對映('類別','類別編號','類別名稱')
    if not cat_map:
        st.warning('請先新增類別')
    else:
        st.subheader('現有類別')
        st.write(list(cat_map.keys()))
        sel_cat = st.selectbox('選擇類別', list(cat_map.keys()))
        cat_id = cat_map[sel_cat]
        st.info(f'您選擇的類別：{sel_cat} (編號: {cat_id})')
        df_items = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cat_id,))
        df_items.columns = df_items.columns.str.strip()
        item_map = {row['品項名稱']: row['品項編號'] for _, row in df_items.iterrows()}
        if not item_map:
            st.warning('該類別尚無品項')
        else:
            sel_item = st.selectbox('選擇品項', list(item_map.keys()))
            item_id = item_map[sel_item]
            st.subheader(f'「{sel_item}」下現有細項')
            df_sub = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(item_id,))
            df_sub.columns = df_sub.columns.str.strip()
            st.table(df_sub.rename(columns={'細項編號':'編號','細項名稱':'名稱'})[['編號','名稱']])
            with st.form('form_sub'):
                new_sub = st.text_input('新增細項名稱')
                del_sub_id = st.text_input('刪除細項編號')
                submit_sub = st.form_submit_button('執行')
                if submit_sub:
                    if new_sub:
                        新增('細項',['品項編號','細項名稱'],[item_id,new_sub])
                        st.success(f'於「{sel_item}」新增細項：{new_sub}')
                    if del_sub_id.isdigit():
                        刪除('細項','細項編號',int(del_sub_id))
                        st.success(f'已刪除細項編號：{del_sub_id}')
                    try:
                        st.experimental_rerun()
                    except AttributeError:
                        st.info('請重新整理頁面以更新列表')

# 進貨
elif menu == '進貨':
    st.title('➕ 批次或手動新增進貨')
    tab1, tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        uploaded = st.file_uploader('上傳買賣進出表 Excel/CSV (批次進貨)', type=['xlsx','xls','csv'])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
            except Exception:
                try:
                    df = pd.read_csv(uploaded)
                except Exception:
                    st.warning('無法讀取檔案，請確認為 Excel 或 CSV')
                    st.stop()
            df = df.rename(columns=lambda x: x.strip())
            df['買入數量'] = df.get('買入 數量', df.get('買入數量', 0)).fillna(0)
            df['買入單價'] = df.get('買入 單價', df.get('買入單價', 0)).fillna(0)
            count = 0
            for _, row in df.iterrows():
                if row['買入數量'] > 0:
                    cat, item, sub = row.get('類別'), row.get('品項'), row.get('細項')
                    if pd.isna(cat) or pd.isna(item) or pd.isna(sub): continue
                    新增('類別',['類別名稱'],[cat])
                    cat_map = 取得對映('類別','類別編號','類別名稱')
                    cid = cat_map.get(cat)
                    新增('品項',['類別編號','品項名稱'],[cid,item])
                    df_i = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=? AND 品項名稱=?', conn, params=(cid,item))
                    iid = df_i['品項編號'].iloc[0]
                    新增('細項',['品項編號','細項名稱'],[iid,sub])
                    df_su = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=? AND 細項名稱=?', conn, params=(iid,sub))
                    sid = df_su['細項編號'].iloc[0]
                    新增('進貨',['類別編號','品項編號','細項編號','數量','單價'],[cid,iid,sid,int(row['買入數量']),float(row['買入單價'])])
                    count += 1
            st.success(f'批次匯入進貨完成，共 {count} 筆')
    with tab2:
        # 手動記錄
        cat_map = 取得對映('類別','類別編號','類別名稱')
        if not cat_map:
            st.warning('請先在類別管理新增類別')
            st.stop()
        cat_name = st.selectbox('類別', list(cat_map.keys()))
        cid = cat_map[cat_name]
        df_items = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
        df_items.columns = df_items.columns.str.strip()
        item_map = {row['品項名稱']:row['品項編號'] for _,row in df_items.iterrows()}
        if not item_map:
            st.warning('請先在品項管理新增品項')
            st.stop()
        item_name = st.selectbox('品項', list(item_map.keys()))
        iid = item_map[item_name]
        df_sub = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
        df_sub.columns = df_sub.columns.str.strip()
        sub_map = {row['細項名稱']:row['細項編號'] for _,row in df_sub.iterrows()}
        if not sub_map:
            st.warning('請先在細項管理新增細項')
            st.stop()
        sub_name = st.selectbox('細項', list(sub_map.keys()))
        sid = sub_map[sub_name]
        qty = st.number_input('數量', min_value=1, value=1)
        price = st.number_input('單價', min_value=0.0, format='%.2f')
        if st.button('儲存進貨'):
            新增('進貨',['類別編號','品項編號','細項編號','數量','單價'],[cid,iid,sid,qty,price])
            st.success('已記錄進貨')
elif menu == '銷售':
    st.info('請使用全功能版本以進行銷售記錄')

# 儀表板
elif menu == '儀表板':
    st.title('📊 庫存儀表板')
    # ... existing 儀表板 code ...

# 批次匯入買賣進出表
elif menu == '批次匯入買賣進出表':
    st.title('📥 批次匯入買賣進出表')
    uploaded = st.file_uploader('上傳買賣進出 Excel 檔', type=['xlsx','xls'])
    if uploaded:
        # 嘗試以 Excel 讀取，若失敗請用 CSV 重傳
        try:
            df = pd.read_excel(uploaded)
        except Exception:
            try:
                df = pd.read_csv(uploaded)
            except Exception:
                st.warning('無法讀取檔案，請確認為 Excel 或 CSV')
                st.stop()
        # 預處理欄位
        df = df.rename(columns=lambda x: x.strip())
        # 清理並提取必要欄位
        df['買入數量'] = df.get('買入 數量', df.get('買入數量', 0)).fillna(0)
        df['買入單價'] = df.get('買入 單價', df.get('買入單價', 0)).fillna(0)
        df['賣出數量'] = df.get('賣出 數量', df.get('賣出數量', 0)).fillna(0)
        df['賣出單價'] = df.get('賣出 單價', df.get('賣出單價', 0)).fillna(0)
        # 依行匯入
        count_buy = 0
        count_sell = 0
        for _, row in df.iterrows():
            cat = row.get('類別')
            item = row.get('品項')
            sub = row.get('細項')
            if pd.isna(cat) or pd.isna(item) or pd.isna(sub):
                continue
            # 建立對映
            新增('類別',['類別名稱'],[cat])
            cat_map = 取得對映('類別','類別編號','類別名稱')
            cid = cat_map.get(cat)
            新增('品項',['類別編號','品項名稱'],[cid, item])
            item_map = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=? AND 品項名稱=?', conn, params=(cid, item))
            iid = item_map['品項編號'].iloc[0]
            新增('細項',['品項編號','細項名稱'],[iid, sub])
            sub_map = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=? AND 細項名稱=?', conn, params=(iid, sub))
            sid = sub_map['細項編號'].iloc[0]
            # 匯入買入
            if row['買入數量'] > 0:
                新增('進貨',['類別編號','品項編號','細項編號','數量','單價'],[cid,iid,sid,int(row['買入數量']),float(row['買入單價'])])
                count_buy += 1
            # 匯入賣出
            if row['賣出數量'] > 0:
                新增('銷售',['類別編號','品項編號','細項編號','數量','單價'],[cid,iid,sid,int(row['賣出數量']),float(row['賣出單價'])])
                count_sell += 1
        st.success(f'批次匯入完成：買入 {count_buy} 筆，賣出 {count_sell} 筆')
