import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime, date

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 建類別、品項、細項三個主檔
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
# 建進貨/銷售表
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

# 查詢整張表
def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

# 通用新增
def 新增(table: str, cols: list, vals: list) -> int:
    df = 查詢(table)
    cols_used = df.columns.tolist()[1:1+len(vals)]
    ph = ",".join(["?"] * len(vals))
    c.execute(
        f"INSERT INTO {table} ({','.join(cols_used)}) VALUES ({ph})",
        vals
    )
    conn.commit()
    return c.lastrowid

# 通用刪除
def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col}=?", (key_val,))
    conn.commit()

# 取得名稱→編號對映
def 取得對映(table: str) -> dict:
    mapping = {
        '類別': ('類別名稱','類別編號'),
        '品項': ('品項名稱','品項編號'),
        '細項': ('細項名稱','細項編號'),
    }
    nc, ic = mapping.get(table, (None,None))
    rows = conn.execute(f"SELECT {nc},{ic} FROM {table}").fetchall()
    return {r[0]:r[1] for r in rows}

# 批次主檔匯入：類別/品項/細項
def 批次匯入主檔(df: pd.DataFrame):
    df = df.rename(columns=str.strip)
    for _, r in df.iterrows():
        cat = r.get('類別'); item = r.get('品項'); sub = r.get('細項')
        if pd.notna(cat): 新增('類別',['類別名稱'],[cat])
        if pd.notna(item):
            cid = 取得對映('類別')[r['類別']]
            新增('品項',['類別編號','品項名稱'],[cid,item])
        if pd.notna(sub):
            iid = 取得對映('品項')[r['品項']]
            新增('細項',['品項編號','細項名稱'],[iid,sub])

# 批次匯入進貨/銷售（同先前）…
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])

if menu == '類別管理':
    st.header('⚙️ 類別管理')
    tab1, tab2 = st.tabs(['批次匯入','單筆管理'])

    with tab1:
        sample = pd.DataFrame({'類別':['示例A'],'品項':[''],'細項':['']})
        st.download_button(
            '下載批次匯入範例',
            sample[['類別']].to_csv(index=False,encoding='utf-8-sig'),
            'cat_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_cat')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            批次匯入主檔(df)
            st.success('批次匯入類別完成')

    with tab2:
        df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
        st.table(df)
        st.download_button(
            '下載類別 CSV',
            df.to_csv(index=False,encoding='utf-8-sig'),
            'categories.csv','text/csv'
        )
        with st.form('form_cat'):
            newc = st.text_input('新增類別', key='cat_new')
            delc = st.text_input('刪除編號', key='cat_del')
            confirm = st.checkbox(f'確認刪除 類別 {delc}?') if delc.isdigit() else False
            if st.form_submit_button('執行'):
                if newc: 新增('類別',['類別名稱'],[newc])
                if delc.isdigit() and confirm: 刪除('類別','類別編號',int(delc))
                st.session_state['cat_new']=''; st.session_state['cat_del']=''
                st.experimental_rerun()
elif menu == '品項管理':
    st.header('⚙️ 品項管理')
    tab1, tab2 = st.tabs(['批次匯入','單筆管理'])

    with tab1:
        sample = pd.DataFrame({'類別':['示例A'],'品項':['示例X'],'細項':['']})
        st.download_button(
            '下載品項批次範例',
            sample[['類別','品項']].to_csv(index=False,encoding='utf-8-sig'),
            'item_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_item')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            批次匯入主檔(df)
            st.success('批次匯入品項完成')

    with tab2:
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
            st.download_button(
                '下載此類品項 CSV',
                df.to_csv(index=False,encoding='utf-8-sig'),
                f'items_{cid}.csv','text/csv'
            )
            with st.form('form_item'):
                newi = st.text_input('新增品項', key='item_new')
                deli = st.text_input('刪除編號', key='item_del')
                confirm = st.checkbox(f'確認刪除 品項 {deli}?') if deli.isdigit() else False
                if st.form_submit_button('執行'):
                    if newi: 新增('品項',['類別編號','品項名稱'],[cid,newi])
                    if deli.isdigit() and confirm: 刪除('品項','品項編號',int(deli))
                    st.session_state['item_new']=''; st.session_state['item_del']=''
                    st.experimental_rerun()
elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    tab1, tab2 = st.tabs(['批次匯入','單筆管理'])

    with tab1:
        sample = pd.DataFrame({
            '類別':['示例A'],'品項':['示例X'],'細項':['示例α']
        })
        st.download_button(
            '下載細項批次範例',
            sample[['類別','品項','細項']].to_csv(index=False,encoding='utf-8-sig'),
            'sub_template.csv','text/csv'
        )
        up=st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_sub')
        if up:
            try: df=pd.read_excel(up)
            except: df=pd.read_csv(up)
            批次匯入主檔(df)
            st.success('批次匯入細項完成')

    with tab2:
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
                st.download_button(
                    '下載此品項細項 CSV',
                    df_s.to_csv(index=False,encoding='utf-8-sig'),
                    f'subs_{iid}.csv','text/csv'
                )
                with st.form('form_sub'):
                    new_s = st.text_input('新增細項', key='sub_new')
                    del_s = st.text_input('刪除編號', key='sub_del')
                    confirm = st.checkbox(f'確認刪除 細項 {del_s}?') if del_s.isdigit() else False
                    if st.form_submit_button('執行'):
                        if new_s: 新增('細項',['品項編號','細項名稱'],[iid,new_s])
                        if del_s.isdigit() and confirm: 刪除('細項','細項編號',int(del_s))
                        st.session_state['sub_new']=''; st.session_state['sub_del']=''
                        st.experimental_rerun()
elif menu == '進貨':
    st.header('➕ 進貨管理')
    tab1,tab2,tab3,tab4=st.tabs(['批次匯入','查詢/匯出','手動記錄','編輯紀錄'])

    # 批次匯入
    with tab1:
        sample = pd.DataFrame({
            '類別':['示例A'],'品項':['示例X'],'細項':['示例α'],
            '買入數量':[10],'買入單價':[100.0],'日期':['2025-07-17']
        })
        st.download_button(
            '下載進貨批次範例',
            sample.to_csv(index=False,encoding='utf-8-sig'),
            'purchase_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_p')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            cnt = 批次匯入進貨(df)
            st.success(f'批次匯入 {cnt} 筆進貨記錄')

    # 查詢 / 匯出
    with tab2:
        df = 查詢('進貨')
        col1, col2 = st.columns(2)
        with col1:
            d1 = st.date_input('起始日期', value=date.today().replace(day=1), key='p_start')
        with col2:
            d2 = st.date_input('結束日期', value=date.today(), key='p_end')
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df_f = df[(df['日期']>=pd.to_datetime(d1)) & (df['日期']<=pd.to_datetime(d2))]
        st.dataframe(df_f)
        st.download_button(
            '匯出進貨 CSV',
            df_f.to_csv(index=False,encoding='utf-8-sig'),
            'purchases_filtered.csv','text/csv'
        )

    # 手動記錄
    with tab3:
        cat_map = 取得對映('類別')
        if not cat_map: st.warning('請先新增類別')
        else:
            sel_cat = st.selectbox('類別', list(cat_map.keys()), key='p_cat')
            cid     = cat_map[sel_cat]
            items   = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap    = dict(zip(items['品項名稱'], items['品項編號']))
            if not imap: st.warning('該類別無品項')
            else:
                sel_item = st.selectbox('品項', list(imap.keys()), key='p_item')
                iid       = imap[sel_item]
                subs      = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap      = dict(zip(subs['細項名稱'], subs['細項編號']))
                if not smap: st.warning('該品項無細項')
                else:
                    sel_sub = st.selectbox('細項', list(smap.keys()), key='p_sub')
                    sid     = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期', value=True, key='p_today')
                    date_str  = datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期', key='p_date').strftime('%Y-%m-%d')
                    qty       = st.number_input('數量', min_value=1, value=1, key='p_qty')
                    price     = st.number_input('單價', min_value=0.0, format='%.2f', key='p_price')
                    if st.button('儲存進貨', key='p_save'):
                        新增('進貨',['類別編號','品項編號','細項編號','數量','單價','日期'],
                             [cid,iid,sid,qty,price,date_str])
                        st.success(f'進貨記錄已儲存：{date_str}')
   # === 編輯 & 刪除 ===
    with tab4:
        sql_p = '''
        SELECT P.紀錄ID, C.類別名稱, I.品項名稱, S.細項名稱,
               P.數量, P.單價, P.總價, P.日期
        FROM 進貨 P
        JOIN 類別 C ON P.類別編號=C.類別編號
        JOIN 品項 I ON P.品項編號=I.品項編號
        JOIN 細項 S ON P.細項編號=S.細項編號
        '''
        dfp = pd.read_sql(sql_p, conn)
        if dfp.empty:
            st.warning('目前無進貨紀錄')
        else:
            st.dataframe(dfp)
            # 準備描述→ID 對映
            desc_map = {
                f"{r['紀錄ID']}: {r['類別名稱']}/{r['品項名稱']}/{r['細項名稱']}":
                r['紀錄ID']
                for _, r in dfp.iterrows()
            }
            # 單筆更新
            sel = st.selectbox('選擇進貨紀錄', list(desc_map.keys()), key='edit_p_sel')
            rid = desc_map[sel]
            row = dfp[dfp['紀錄ID'] == rid].iloc[0]
            date_new = st.date_input('日期', value=pd.to_datetime(row['日期']).date(), key='edit_p_date')
            qty_new  = st.number_input('數量', min_value=1, value=int(row['數量']), key='edit_p_qty')
            price_new= st.number_input('單價', min_value=0.0, format='%.2f', value=float(row['單價']), key='edit_p_price')
            if st.button('更新進貨', key='edit_p_save'):
                total = qty_new * price_new
                c.execute(
                    'UPDATE 進貨 SET 數量=?, 單價=?, 總價=?, 日期=? WHERE 紀錄ID=?',
                    (qty_new, price_new, total, date_new.strftime('%Y-%m-%d'), rid)
                )
                conn.commit()
                st.success('進貨記錄更新成功')

            # 批次刪除
            to_del = st.multiselect('批次刪除進貨', list(desc_map.keys()), key='batch_p')
            confirm = st.checkbox('確認刪除以上所選進貨紀錄？', key='batch_p_confirm')
            if to_del and confirm and st.button('刪除所選進貨', key='del_p_batch'):
                for d in to_del:
                    c.execute('DELETE FROM 進貨 WHERE 紀錄ID=?', (desc_map[d],))
                conn.commit()
                st.success(f'已刪除 {len(to_del)} 筆進貨')
                st.experimental_rerun()

            # 刪除所有
            confirm_all = st.checkbox('確認刪除所有進貨紀錄？', key='del_all_p_confirm')
            if confirm_all and st.button('刪除所有進貨', key='del_all_p'):
                c.execute('DELETE FROM 進貨')
                conn.commit()
                st.success('已刪除所有進貨紀錄')
                st.experimental_rerun()

            
elif menu == '銷售':
    st.header('➕ 銷售管理')
    tab1,tab2,tab3,tab4=st.tabs(['批次匯入','查詢/匯出','手動記錄','編輯紀錄'])

    # 批次匯入
    with tab1:
        sample = pd.DataFrame({
            '類別':['示例A'],'品項':['示例X'],'細項':['示例α'],
            '賣出數量':[2],'賣出單價':[150.0],'日期':['2025-07-17']
        })
        st.download_button(
            '下載銷售批次範例',
            sample.to_csv(index=False,encoding='utf-8-sig'),
            'sales_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_s')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            cnt = 批次匯入銷售(df)
            st.success(f'批次匯入 {cnt} 筆銷售記錄')

    # 查詢 / 匯出
    with tab2:
        df = 查詢('銷售')
        col1, col2 = st.columns(2)
        with col1:
            d1 = st.date_input('起始日期', value=date.today().replace(day=1), key='s_start')
        with col2:
            d2 = st.date_input('結束日期', value=date.today(), key='s_end')
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df_f = df[(df['日期']>=pd.to_datetime(d1)) & (df['日期']<=pd.to_datetime(d2))]
        st.dataframe(df_f)
        st.download_button(
            '匯出銷售 CSV',
            df_f.to_csv(index=False,encoding='utf-8-sig'),
            'sales_filtered.csv','text/csv'
        )

    # 手動記錄
    with tab3:
        cat_map = 取得對映('類別')
        if not cat_map: st.warning('請先新增類別')
        else:
            sel_cat = st.selectbox('類別', list(cat_map.keys()), key='s_cat')
            cid     = cat_map[sel_cat]
            items   = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
            imap    = dict(zip(items['品項名稱'], items['品項編號']))
            if not imap: st.warning('該類別無品項')
            else:
                sel_item = st.selectbox('品項', list(imap.keys()), key='s_item')
                iid       = imap[sel_item]
                subs      = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
                smap      = dict(zip(subs['細項名稱'], subs['細項編號']))
                if not smap: st.warning('該品項無細項')
                else:
                    sel_sub = st.selectbox('細項', list(smap.keys()), key='s_sub')
                    sid     = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期', value=True, key='s_today')
                    date_str  = datetime.now().strftime('%Y-%m-%d') if use_today else st.date_input('選擇日期', key='s_date').strftime('%Y-%m-%d')
                    qty       = st.number_input('數量', min_value=1, value=1, key='s_qty')
                    price     = st.number_input('單價', min_value=0.0, format='%.2f', key='s_price')
                    if st.button('儲存銷售', key='s_save'):
                        新增('銷售',['類別編號','品項編號','細項編號','數量','單價','日期'],
                             [cid,iid,sid,qty,price,date_str])
                        st.success(f'銷售記錄已儲存：{date_str}')
                        
# === 編輯 & 刪除 ===
    with tab4:
        sql_s = '''
        SELECT P.紀錄ID, C.類別名稱, I.品項名稱, S.細項名稱,
               P.數量, P.單價, P.總價, P.日期
        FROM 銷售 P
        JOIN 類別 C ON P.類別編號=C.類別編號
        JOIN 品項 I ON P.品項編號=I.品項編號
        JOIN 細項 S ON P.細項編號=S.細項編號
        '''
        dfs = pd.read_sql(sql_s, conn)
        if dfs.empty:
            st.warning('目前無銷售紀錄')
        else:
            st.dataframe(dfs)
            desc_map_s = {
                f"{r['紀錄ID']}: {r['類別名稱']}/{r['品項名稱']}/{r['細項名稱']}":
                r['紀錄ID']
                for _, r in dfs.iterrows()
            }
            sel_s = st.selectbox('選擇銷售紀錄', list(desc_map_s.keys()), key='edit_s_sel')
            rid_s = desc_map_s[sel_s]
            row_s = dfs[dfs['紀錄ID'] == rid_s].iloc[0]
            date_new_s = st.date_input('日期', value=pd.to_datetime(row_s['日期']).date(), key='edit_s_date')
            qty_new_s  = st.number_input('數量', min_value=1,  value=int(row_s['數量']), key='edit_s_qty')
            price_new_s= st.number_input('單價', min_value=0.0, format='%.2f', value=float(row_s['單價']), key='edit_s_price')
            if st.button('更新銷售', key='edit_s_save'):
                total_s = qty_new_s * price_new_s
                c.execute(
                    'UPDATE 銷售 SET 數量=?, 單價=?, 總價=?, 日期=? WHERE 紀錄ID=?',
                    (qty_new_s, price_new_s, total_s, date_new_s.strftime('%Y-%m-%d'), rid_s)
                )
                conn.commit()
                st.success('銷售記錄更新成功')

            # 批次刪除
            to_del_s = st.multiselect('批次刪除銷售', list(desc_map_s.keys()), key='batch_s')
            confirm_s= st.checkbox('確認刪除以上所選銷售紀錄？', key='batch_s_confirm')
            if to_del_s and confirm_s and st.button('刪除所選銷售', key='del_s_batch'):
                for d in to_del_s:
                    c.execute('DELETE FROM 銷售 WHERE 紀錄ID=?', (desc_map_s[d],))
                conn.commit()
                st.success(f'已刪除 {len(to_del_s)} 筆銷售')
                st.experimental_rerun()

            # 刪除所有
            confirm_all_s = st.checkbox('確認刪除所有銷售紀錄？', key='del_all_s_confirm')
            if confirm_all_s and st.button('刪除所有銷售', key='del_all_s'):
                c.execute('DELETE FROM 鷷取' if False else '銷售')
                conn.commit()
                st.success('已刪除所有銷售紀錄')
                st.experimental_rerun()


elif menu == '儀表板':
    st.header('📊 庫存儀表板')
    df_p  = pd.read_sql('SELECT * FROM 進貨', conn)
    df_s  = pd.read_sql('SELECT * FROM 銷售', conn)
    df_c  = 查詢('類別')
    df_i  = 查詢('品項')
    df_su = 查詢('細項')

    gp = (df_p.merge(df_c, on='類別編號')
               .merge(df_i, on='品項編號')
               .merge(df_su, on='細項編號')
               .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
               .agg(進貨=('數量','sum'),支出=('總價','sum')))

    gs = (df_s.merge(df_c, on='類別編號')
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
        summary.to_csv(index=False,encoding='utf-8-sig'),
        'summary.csv','text/csv'
    )
    # 正確的 f-string 語法
    st.metric('總支出', f"{gp['支出'].sum():.2f}")
    st.metric('總收入', f"{gs['收入'].sum():.2f}")
    st.metric('淨利',   f"{gs['收入'].sum() - gp['支出'].sum():.2f}")

