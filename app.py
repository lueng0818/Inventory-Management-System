# -*- coding: utf-8 -*-
import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime, date

# --- 頁面設定 & 品牌風格 ---
st.set_page_config(
    page_title="Tru-Mi 庫存管理系統",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)
st.image(
    "https://sites.google.com/view/trumi-jewelry/_/rsrc/1688543987023/home/trumi-logo.png",
    width=180
)
st.markdown("#### Tru-Mi 找·金工 － 用首飾收藏故事，靜靜陪你走過每段重要時光")
st.markdown("""
<style>
  .sidebar .sidebar-content { 
    background: linear-gradient(180deg, #b76e79, #f7e4d1);
  }
  .reportview-container { background-color: #fcfbf9; }
</style>
""", unsafe_allow_html=True)

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()

# 主檔：類別、品項、細項（含 系列、圖片 欄位）
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
    系列 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)
""")
c.execute("""
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    圖片 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)
""")
# 確保「圖片」欄位存在
cols = [r[1] for r in conn.execute("PRAGMA table_info(細項)").fetchall()]
if '圖片' not in cols:
    c.execute("ALTER TABLE 細項 ADD COLUMN 圖片 TEXT")
# 進貨 / 銷售 紀錄表
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

# 預設熱銷四大類（僅首次執行）
if pd.read_sql("SELECT * FROM 類別", conn).empty:
    for cat in ["項鍊","耳環","戒指","手鍊"]:
        try: c.execute("INSERT INTO 類別 (類別名稱) VALUES (?)", (cat,))
        except sqlite3.IntegrityError: pass
    conn.commit()

# --- 共用函式 ---
def 查詢(table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {table}", conn)

def 新增(table: str, cols: list, vals: list) -> int:
    df = 查詢(table)
    cols_used = df.columns.tolist()[1:1+len(vals)]
    ph = ",".join(["?"]*len(vals))
    c.execute(f"INSERT INTO {table} ({','.join(cols_used)}) VALUES ({ph})", vals)
    conn.commit()
    return c.lastrowid

def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col}=?", (key_val,))
    conn.commit()

def 取得對映(table: str) -> dict:
    mapping = {
        '類別': ('類別名稱','類別編號'),
        '品項': ('品項名稱','品項編號'),
        '細項': ('細項名稱','細項編號'),
    }
    nc, ic = mapping[table]
    rows = conn.execute(f"SELECT {nc},{ic} FROM {table}").fetchall()
    return {r[0]: r[1] for r in rows}

# 批次匯入主檔
def 批次匯入主檔(df: pd.DataFrame):
    df = df.rename(columns=str.strip)
    for _, r in df.iterrows():
        cat, itm, sub = r.get('類別'), r.get('品項'), r.get('細項')
        if pd.notna(cat): 新增('類別',['類別名稱'],[cat])
        if pd.notna(itm):
            cid = 取得對映('類別')[cat]
            新增('品項',['類別編號','品項名稱'],[cid,itm])
        if pd.notna(sub):
            iid = 取得對映('品項')[itm]
            新增('細項',['品項編號','細項名稱'],[iid,sub])

# 批次匯入進貨
def 批次匯入進貨(df: pd.DataFrame) -> int:
    df = df.rename(columns=str.strip)
    df['買入數量'] = df.get('買入數量',0).fillna(0)
    df['買入單價'] = df.get('買入單價',0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r['買入數量'] <= 0: continue
        新增('類別',['類別名稱'],[r['類別']])
        cid = 取得對映('類別')[r['類別']]
        新增('品項',['類別編號','品項名稱'],[cid,r['品項']])
        iid = 取得對映('品項')[r['品項']]
        新增('細項',['品項編號','細項名稱'],[iid,r['細項']])
        sid = 取得對映('細項')[r['細項']]
        ds = r.get('日期') or datetime.now().strftime('%Y-%m-%d')
        新增('進貨',['類別編號','品項編號','細項編號','數量','單價','日期'],
             [cid,iid,sid,int(r['買入數量']),float(r['買入單價']), ds])
        cnt += 1
    return cnt

# 批次匯入銷售
def 批次匯入銷售(df: pd.DataFrame) -> int:
    df = df.rename(columns=str.strip)
    df['賣出數量'] = df.get('賣出數量',0).fillna(0)
    df['賣出單價'] = df.get('賣出單價',0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r['賣出數量'] <= 0: continue
        新增('類別',['類別名稱'],[r['類別']])
        cid = 取得對映('類別')[r['類別']]
        新增('品項',['類別編號','品項名稱'],[cid,r['品項']])
        iid = 取得對映('品項')[r['品項']]
        新增('細項',['品項編號','細項名稱'],[iid,r['細項']])
        sid = 取得對映('細項')[r['細項']]
        ds = r.get('日期') or datetime.now().strftime('%Y-%m-%d')
        新增('銷售',['類別編號','品項編號','細項編號','數量','單價','日期'],
             [cid,iid,sid,int(r['賣出數量']),float(r['賣出單價']), ds])
        cnt += 1
    return cnt

# --- 側邊欄：官網連結 + 系統選單 ---
site_base = "https://sites.google.com/view/trumi-jewelry"
links = {
    "首頁":          f"{site_base}/首頁",
    "熱銷推薦":      f"{site_base}/%E7%86%B1%E9%8A%B7%E6%8E%A8%E8%96%A6",
    "主題系列":      f"{site_base}/%E4%B8%BB%E9%A1%8C%E7%B3%BB%E5%88%97",
    "婚戒物語":      f"{site_base}/%E5%A9%9A%E6%88%92%E7%89%A9%E8%AA%9E",
    "寶寶禮物":      f"{site_base}/%E5%AF%B6%E5%AF%B6%E7%A6%AE%E7%89%A9",
    "專屬訂製":      f"{site_base}/%E5%B0%88%E5%B1%AC%E8%A8%82%E8%A3%BD",
    "首飾保養":      f"{site_base}/%E9%A6%96%E9%A3%BA%E4%BF%9D%E9%A4%8A",
    "訂購提醒":      f"{site_base}/%E8%A8%82%E8%B3%BC%E6%8F%90%E9%86%92",
    "LINE線上客服": f"{site_base}/line線上客服",
}

for name, url in links.items():
    st.sidebar.markdown(
        f'<a href="{url}" target="_blank" style="text-decoration:none; color:#000;">• {name}</a>',
        unsafe_allow_html=True
    )

# 分隔線
st.sidebar.markdown("---")

# 再提供「進入庫存系統」按鈕，點擊後才顯示管理介面
if not st.sidebar.button("🔧 進入庫存系統"):
    st.stop()

# 接著才是系統功能選單
menu = st.sidebar.radio("系統功能", [
    '類別管理','品項管理','細項管理','進貨','銷售','儀表板'
])


if menu == '類別管理':
    st.header('⚙️ 類別管理')
    tab1, tab2 = st.tabs(['批次匯入','單筆管理'])

    with tab1:
        sample = pd.DataFrame({'類別':['示例A'],'品項':[''],'細項':['']})
        st.download_button('下載類別批次範例',
            sample[['類別']].to_csv(index=False,encoding='utf-8-sig'),
            'cat_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_cat')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            批次匯入主檔(df); st.success('批次匯入類別完成')

    with tab2:
        df = 查詢('類別').rename(columns={'類別編號':'編號','類別名稱':'名稱'})
        st.table(df)
        st.download_button('下載類別 CSV',
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

    # 批次匯入（保持不变）
    with tab1:
        sample = pd.DataFrame({'類別':['示例A'],'品項':['示例X'],'細項':['']})
        st.download_button('下載品項批次範例',
            sample[['類別','品項']].to_csv(index=False,encoding='utf-8-sig'),
            'item_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_item')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            批次匯入主檔(df)
            st.success('批次匯入品項完成')

    # 單筆管理
    with tab2:
        cmap = 取得對映('類別')
        if not cmap:
            st.warning('請先新增類別')
            st.stop()

        sel = st.radio('選擇類別', list(cmap.keys()), index=0, key='item_cat_radio')
        cid = cmap[sel]

        # 嘗試同時讀取 系列 欄位，若出錯則補空白
        try:
            df = pd.read_sql(
                'SELECT 品項編號, 品項名稱, 系列 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
        except Exception:
            df = pd.read_sql(
                'SELECT 品項編號, 品項名稱 FROM 品項 WHERE 類別編號=?',
                conn, params=(cid,)
            )
            df['系列'] = ''

        df = df.rename(columns={'品項編號':'編號','品項名稱':'名稱'})
        st.table(df)

        # 系列编辑
        series_map = dict(zip(df['名稱'], df['系列'].fillna('')))
        sel_item = st.selectbox('編輯品項', list(series_map.keys()), key='series_sel')
        new_series = st.text_input('主題系列', value=series_map[sel_item], key='series_new')
        if st.button('更新系列', key='series_save'):
            iid = df[df['名稱']==sel_item]['編號'].iloc[0]
            c.execute('UPDATE 品項 SET 系列=? WHERE 品項編號=?', (new_series, iid))
            conn.commit()
            st.success('系列已更新')
            st.experimental_rerun()

        # 下載與單筆 CRUD
        st.download_button('下載品項 CSV',
            df.to_csv(index=False, encoding='utf-8-sig'),
            f'items_{cid}.csv','text/csv'
        )
        with st.form('form_item'):
            newi = st.text_input('新增品項', key='item_new')
            deli = st.text_input('刪除編號', key='item_del')
            confirm = st.checkbox(f'確認刪除 品項 {deli}?') if deli.isdigit() else False
            if st.form_submit_button('執行'):
                if newi:
                    新增('品項',['類別編號','品項名稱'],[cid,newi])
                if deli.isdigit() and confirm:
                    刪除('品項','品項編號',int(deli))
                st.experimental_rerun()

elif menu == '細項管理':
    st.header('⚙️ 細項管理')
    tab1, tab2 = st.tabs(['批次匯入','單筆管理'])

    with tab1:
        sample = pd.DataFrame({'類別':['示例A'],'品項':['示例X'],'細項':['示例α']})
        st.download_button('下載細項批次範例',
            sample[['類別','品項','細項']].to_csv(index=False,encoding='utf-8-sig'),
            'sub_template.csv','text/csv'
        )
        up = st.file_uploader('上傳 CSV/Excel', type=['csv','xlsx','xls'], key='up_sub')
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            批次匯入主檔(df); st.success('批次匯入細項完成')

    with tab2:
        cmap = 取得對映('類別')
        if not cmap: st.warning('請先新增類別')
        else:
            sel = st.selectbox('類別', list(cmap.keys())); cid = cmap[sel]
            df_i = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                               conn, params=(cid,))
            imap = dict(zip(df_i['品項名稱'], df_i['品項編號']))
            if not imap: st.warning('該類別無品項')
            else:
                sel2 = st.selectbox('品項', list(imap.keys())); iid = imap[sel2]
                try:
                    df_s = pd.read_sql(
                        'SELECT 細項編號,細項名稱,圖片 FROM 細項 WHERE 品項編號=?',
                        conn, params=(iid,)
                    )
                except:
                    df_s = pd.read_sql(
                        'SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                        conn, params=(iid,)
                    )
                df_s = df_s.rename(columns={'細項編號':'編號','細項名稱':'名稱'})
                st.table(df_s)
                sid_map = dict(zip(df_s['名稱'], df_s['編號']))
                sel_sub = st.selectbox('細項', list(sid_map.keys()), key='img_sel'); sid = sid_map[sel_sub]
                img_path = df_s[df_s['編號']==sid].get('圖片', pd.Series()).iloc[0] if '圖片' in df_s.columns else None
                if img_path and os.path.exists(img_path): st.image(img_path, width=100)
                img = st.file_uploader('上傳細項圖片', type=['png','jpg'], key='img_up')
                if img:
                    os.makedirs('images', exist_ok=True)
                    path = f"images/sub_{sid}.png"
                    with open(path, "wb") as f: f.write(img.getbuffer())
                    c.execute('UPDATE 細項 SET 圖片=? WHERE 細項編號=?', (path, sid))
                    conn.commit(); st.success('圖片已儲存'); st.experimental_rerun()
                st.download_button('下載細項 CSV',
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
    tab1, tab2, tab3, tab4 = st.tabs(['批次匯入','查詢/匯出','手動記錄','編輯/刪除'])

    # 批次匯入
    with tab1:
        sample = pd.DataFrame({
            '類別':['示例A'], '品項':['示例X'], '細項':['示例α'],
            '買入數量':[10], '買入單價':[100.0],
            '日期':[date.today().strftime('%Y-%m-%d')]
        })
        st.download_button(
            '下載進貨批次範例',
            sample.to_csv(index=False, encoding='utf-8-sig'),
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
        d1 = st.date_input('起始日期', date.today().replace(day=1), key='p_start')
        d2 = st.date_input('結束日期', date.today(), key='p_end')
        df['日期'] = pd.to_datetime(df['日期'], errors='coerce')
        df_f = df[(df['日期']>=pd.to_datetime(d1)) & (df['日期']<=pd.to_datetime(d2))]
        st.dataframe(df_f)
        st.download_button(
            '匯出進貨 CSV',
            df_f.to_csv(index=False, encoding='utf-8-sig'),
            'purchases_filtered.csv','text/csv'
        )

    # 手動記錄
    with tab3:
        cat_map = 取得對映('類別')
        if not cat_map:
            st.warning('請先新增類別')
        else:
            sel_cat = st.selectbox('類別', list(cat_map.keys()), key='p_cat'); cid = cat_map[sel_cat]
            items = pd.read_sql('SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?',
                                conn, params=(cid,))
            imap = dict(zip(items['品項名稱'], items['品項編號']))
            if not imap:
                st.warning('該類別無品項')
            else:
                sel_item = st.selectbox('品項', list(imap.keys()), key='p_item'); iid = imap[sel_item]
                subs = pd.read_sql('SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?',
                                   conn, params=(iid,))
                smap = dict(zip(subs['細項名稱'], subs['細項編號']))
                if not smap:
                    st.warning('該品項無細項')
                else:
                    sel_sub = st.selectbox('細項', list(smap.keys()), key='p_sub'); sid = smap[sel_sub]
                    use_today = st.checkbox('自動帶入今日日期', value=True, key='p_today')
                    date_str = (datetime.now().strftime('%Y-%m-%d')
                                if use_today
                                else st.date_input('選擇日期', key='p_date').strftime('%Y-%m-%d'))
                    qty = st.number_input('數量', min_value=1, value=1, key='p_qty')
                    price = st.number_input('單價', min_value=0.0, format='%.2f', key='p_price')
                    if st.button('儲存進貨', key='p_save'):
                        新增('進貨',
                             ['類別編號','品項編號','細項編號','數量','單價','日期'],
                             [cid,iid,sid,qty,price,date_str]
                        )
                        st.success(f'進貨記錄已儲存：{date_str}')

    # 編輯 / 刪除
    with tab4:
        sql = '''
        SELECT P.紀錄ID, C.類別名稱, I.品項名稱, S.細項名稱,
               P.數量, P.單價, P.總價, P.日期
        FROM 進貨 P
        JOIN 類別 C ON P.類別編號=C.類別編號
        JOIN 品項 I ON P.品項編號=I.品項編號
        JOIN 細項 S ON P.細項編號=S.細項編號
        '''
        dfp = pd.read_sql(sql, conn)
        if dfp.empty:
            st.warning('目前無進貨紀錄')
        else:
            st.dataframe(dfp)
            desc_map = {
                f"{r['紀錄ID']}: {r['類別名稱']}/{r['品項名稱']}/{r['細項名稱']}": r['紀錄ID']
                for _, r in dfp.iterrows()
            }
            sel = st.selectbox('選擇紀錄', list(desc_map.keys()), key='edit_p_sel'); rid = desc_map[sel]
            row = dfp[dfp['紀錄ID']==rid].iloc[0]
            date_new = st.date_input('日期', value=pd.to_datetime(row['日期']).date(), key='edit_p_date')
            qty_new = st.number_input('數量', min_value=1, value=int(row['數量']), key='edit_p_qty')
            price_new = st.number_input('單價', min_value=0.0, format='%.2f', value=float(row['單價']), key='edit_p_price')
            if st.button('更新進貨', key='edit_p_save'):
                total = qty_new * price_new
                c.execute(
                    'UPDATE 進貨 SET 數量=?, 單價=?, 總價=?, 日期=? WHERE 紀錄ID=?',
                    (qty_new, price_new, total, date_new.strftime('%Y-%m-%d'), rid)
                )
                conn.commit(); st.success('進貨記錄更新成功')

            to_del = st.multiselect('批次刪除進貨', list(desc_map.keys()), key='batch_p')
            confirm = st.checkbox('確認刪除所選進貨？', key='batch_p_confirm')
            if to_del and confirm and st.button('刪除所選進貨', key='del_p_batch'):
                for d in to_del: c.execute('DELETE FROM 進貨 WHERE 紀錄ID=?', (desc_map[d],))
                conn.commit(); st.success(f'刪除 {len(to_del)} 筆進貨'); st.experimental_rerun()

            confirm_all = st.checkbox('確認刪除所有進貨？', key='del_all_p_confirm')
            if confirm_all and st.button('刪除所有進貨', key='del_all_p'):
                c.execute('DELETE FROM 進貨'); conn.commit()
                st.success('已刪除所有進貨紀錄'); st.experimental_rerun()

elif menu == '銷售':
    st.header('➕ 銷售管理')
    tab1, tab2, tab3, tab4 = st.tabs(['批次匯入','查詢/匯出','手動記錄','編輯/刪除'])

    # 批次匯入、查詢/匯出、手動記錄 同進貨，略…

    # 編輯 / 刪除
    with tab4:
        sql = '''
        SELECT P.紀錄ID, C.類別名稱, I.品項名稱, S.細項名稱,
               P.數量, P.單價, P.總價, P.日期
        FROM 銷售 P
        JOIN 類別 C ON P.類別編號=C.類別編號
        JOIN 品項 I ON P.品項編號=I.品項編號
        JOIN 細項 S ON P.細項編號=S.細項編號
        '''
        dfs = pd.read_sql(sql, conn)
        if dfs.empty:
            st.warning('目前無銷售紀錄')
        else:
            st.dataframe(dfs)
            desc_map_s = {
                f"{r['紀錄ID']}: {r['類別名稱']}/{r['品項名稱']}/{r['細項名稱']}": r['紀錄ID']
                for _, r in dfs.iterrows()
            }
            sel_s = st.selectbox('選擇紀錄', list(desc_map_s.keys()), key='edit_s_sel'); rid_s = desc_map_s[sel_s]
            row_s = dfs[dfs['紀錄ID']==rid_s].iloc[0]
            date_new_s = st.date_input('日期', value=pd.to_datetime(row_s['日期']).date(), key='edit_s_date')
            qty_new_s  = st.number_input('數量', min_value=1, value=int(row_s['數量']), key='edit_s_qty')
            price_new_s= st.number_input('單價', min_value=0.0, format='%.2f', value=float(row_s['單價']), key='edit_s_price')
            if st.button('更新銷售', key='edit_s_save'):
                total_s = qty_new_s * price_new_s
                c.execute(
                    'UPDATE 銷售 SET 數量=?, 單價=?, 總價=?, 日期=? WHERE 紀錄ID=?',
                    (qty_new_s, price_new_s, total_s, date_new_s.strftime('%Y-%m-%d'), rid_s)
                )
                conn.commit(); st.success('銷售記錄更新成功')

            to_del_s = st.multiselect('批次刪除銷售', list(desc_map_s.keys()), key='batch_s')
            confirm_s= st.checkbox('確認刪除所選？', key='batch_s_confirm')
            if to_del_s and confirm_s and st.button('刪除所選銷售', key='del_s_batch'):
                for d in to_del_s: c.execute('DELETE FROM 銷售 WHERE 紀錄ID=?', (desc_map_s[d],))
                conn.commit(); st.success(f'刪除 {len(to_del_s)} 筆銷售'); st.experimental_rerun()

            confirm_all_s = st.checkbox('確認刪除所有銷售？', key='del_all_s_confirm')
            if confirm_all_s and st.button('刪除所有銷售', key='del_all_s'):
                c.execute('DELETE FROM 銷售'); conn.commit()
                st.success('已刪除所有銷售紀錄'); st.experimental_rerun()

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
           .agg(進貨=('數量','sum'), 支出=('總價','sum')))

    gs = (df_s.merge(df_c, on='類別編號')
           .merge(df_i, on='品項編號')
           .merge(df_su, on='細項編號')
           .groupby(['類別名稱','品項名稱','細項名稱'], as_index=False)
           .agg(銷售=('數量','sum'), 收入=('總價','sum')))

    summary = pd.merge(gp, gs,
                       on=['類別名稱','品項名稱','細項名稱'],
                       how='outer').fillna(0)
    summary['庫存'] = summary['進貨'] - summary['銷售']

    threshold = st.number_input('低庫存警戒量', min_value=0, value=5)
    low_stock = summary[summary['庫存'] < threshold]
    if not low_stock.empty:
        st.warning('以下品項庫存低於警戒量')
        st.table(low_stock)

    st.dataframe(summary)
    st.download_button(
        '下載庫存摘要 CSV',
        summary.to_csv(index=False, encoding='utf-8-sig'),
        'summary.csv','text/csv'
    )

    total_spent = gp['支出'].sum()
    total_rev   = gs['收入'].sum()
    st.metric('總支出', f"{total_spent:.2f}")
    st.metric('總收入', f"{total_rev:.2f}")
    st.metric('淨利',   f"{total_rev - total_spent:.2f}")

