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
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 類別表
c.execute('''CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)''')
# 品項表
c.execute('''CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)''')
# 細項表
c.execute('''CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)''')
# 進貨
elif menu == '進貨':
    st.title('➕ 批次匯入 / 手動記錄進貨')
    tab1, tab2 = st.tabs(['批次匯入','手動記錄'])
    with tab1:
        uploaded = st.file_uploader('上傳 Excel/CSV', type=['xlsx','xls','csv'])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
            except:
                df = pd.read_csv(uploaded)
            count = 批次匯入進貨(df)
            st.success(f'批次匯入 {count} 筆進貨記錄')
    with tab2:
        cat_map = 取得對映('類別','類別編號','類別名稱')
        if not cat_map:
            st.warning('請先新增類別')
        else:
            sel_cat = st.selectbox('類別', list(cat_map.keys()))
            cid = cat_map[sel_cat]
            df_i = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            df_i.columns = df_i.columns.str.strip()
            item_map = {r['品項名稱']:r['品項編號'] for _,r in df_i.iterrows()}
            if not item_map:
                st.warning('請先新增品項')
            else:
                sel_item = st.selectbox('品項', list(item_map.keys()))
                iid = item_map[sel_item]
                df_sub = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                df_sub.columns = df_sub.columns.str.strip()
                sub_map = {r['細項名稱']:r['細項編號'] for _,r in df_sub.iterrows()}
                if not sub_map:
                    st.warning('請先新增細項')
                else:
                    sel_sub = st.selectbox('細項', list(sub_map.keys()))
                    sid = sub_map[sel_sub]
                    qty = st.number_input('數量', 1)
                    price = st.number_input('單價', 0.0, format='%.2f')
                    if st.button('儲存進貨'):
                        新增('進貨', ['類別編號','品項編號','細項編號','數量','單價'], [cid,iid,sid,qty,price])
                        st.success('進貨記錄完成')

# 銷售
elif menu == '銷售':
    st.title('➕ 批次匯入 / 手動記錄銷售')
    # 批次匯入銷售函式
    def 批次匯入銷售(df_sales):
        df_sales.columns = df_sales.columns.str.strip()
        df_sales['賣出數量'] = df_sales.get('賣出數量', 0).fillna(0)
        df_sales['賣出單價'] = df_sales.get('賣出單價', 0).fillna(0)
        count_s = 0
        for _, row in df_sales.iterrows():
            if row['賣出數量'] <= 0:
                continue
            cat, item, sub = row['類別'], row['品項'], row['細項']
            if pd.isna(cat) or pd.isna(item) or pd.isna(sub):
                continue
            新增('類別',['類別名稱'],[cat])
            cat_map = 取得對映('類別','類別編號','類別名稱')
            cid = cat_map.get(cat)
            新增('品項',['類別編號','品項名稱'],[cid,item])
            df_i2 = pd.read_sql('SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?', conn, params=(cid,item))
            iid2 = df_i2['品項編號'].iloc[0]
            新增('細項',['品項編號','細項名稱'],[iid2,sub])
            df_su2 = pd.read_sql('SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?', conn, params=(iid2,sub))
            sid2 = df_su2['細項編號'].iloc[0]
            新增('銷售', ['類別編號','品項編號','細項編號','數量','單價'], [cid,iid2,sid2,int(row['賣出數量']), float(row['賣出單價'])])
            count_s += 1
        return count_s

    tab_s1, tab_s2 = st.tabs(['批次匯入','手動記錄'])
    with tab_s1:
        up_s = st.file_uploader('上傳銷售 Excel/CSV', type=['xlsx','xls','csv'])
        if up_s:
            try:
                df_sls = pd.read_excel(up_s)
            except:
                df_sls = pd.read_csv(up_s)
            cs = 批次匯入銷售(df_sls)
            st.success(f'批次匯入 {cs} 筆銷售記錄')
    with tab_s2:
        cat_map2 = 取得對映('類別','類別編號','類別名稱')
        if not cat_map2:
            st.warning('請先新增類別')
        else:
            sel_cat2 = st.selectbox('類別', list(cat_map2.keys()))
            cid2 = cat_map2[sel_cat2]
            df_i3 = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cid2,))
            df_i3.columns = df_i3.columns.str.strip()
            item_map2 = {r['品項名稱']:r['品項編號'] for _,r in df_i3.iterrows()}
            if not item_map2:
                st.warning('請先新增品項')
            else:
                sel_item2 = st.selectbox('品項', list(item_map2.keys()))
                iid3 = item_map2[sel_item2]
                df_sub3 = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(iid3,))
                df_sub3.columns = df_sub3.columns.str.strip()
                sub_map2 = {r['細項名稱']:r['細項編號'] for _,r in df_sub3.iterrows()}
                if not sub_map2:
                    st.warning('請先新增細項')
                else:
                    sel_sub2 = st.selectbox('細項', list(sub_map2.keys()))
                    sid3 = sub_map2[sel_sub2]
                    qty2 = st.number_input('數量', 1)
                    price2 = st.number_input('單價', 0.0, format='%.2f')
                    if st.button('儲存銷售'):
                        新增('銷售', ['類別編號','品項編號','細項編號','數量','單價'], [cid2,iid3,sid3,qty2,price2])
                        st.success('銷售記錄完成')

# 儀表板
elif menu == '儀表板':
    st.title('📊 庫存儀表板')
    # ... remain unchanged ...

elif menu == '銷售':
    st.title('➕ 批次匯入 / 手動記錄銷售')
    st.info('實作同進貨模組')

# 儀表板
elif menu == '儀表板':
    st.title('📊 庫存儀表板')
    df_p=pd.read_sql('SELECT * FROM 進貨',conn)
    df_s=pd.read_sql('SELECT * FROM 銷售',conn)
    df_c=查詢('類別');df_c.columns=df_c.columns.str.strip();df_c=df_c.rename(columns={'編號':'類別編號','名稱':'類別名稱'})
    df_i=查詢('品項');df_i.columns=df_i.columns.str.strip();df_i=df_i.rename(columns={'編號':'品項編號','名稱':'品項名稱'})
    df_su=查詢('細項');df_su.columns=df_su.columns.str.strip();df_su=df_su.rename(columns={'編號':'細項編號','名稱':'細項名稱'})
    df_p=df_p.merge(df_c,on='類別編號',how='left').merge(df_i,on='品項編號',how='left').merge(df_su,on='細項編號',how='left')
    df_s=df_s.merge(df_c,on='類別編號',how='left').merge(df_i,on='品項編號',how='left').merge(df_su,on='細項編號',how='left')
    grp_p=df_p.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(進貨=('數量','sum'),支出=('總價','sum'))
    grp_s=df_s.groupby(['類別名稱','品項名稱','細項名稱'],as_index=False).agg(銷售=('數量','sum'),收入=('總價','sum'))
    summary=pd.merge(grp_p,grp_s,on=['類別名稱','品項名稱','細項名稱'],how='outer').fillna(0)
    summary['庫存']=summary['進貨']-summary['銷售']
    st.dataframe(summary)
    exp=grp_p['支出'].sum();rev=grp_s['收入'].sum()
    st.subheader('💰 財務概況');st.metric('總支出',f"{exp:.2f}");st.metric('總收入',f"{rev:.2f}");st.metric('淨利',f"{rev-exp:.2f}")
