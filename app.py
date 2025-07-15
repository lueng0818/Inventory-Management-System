import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 類別表
c.execute('''
CREATE TABLE IF NOT EXISTS 類別 (
    類別編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別名稱 TEXT UNIQUE
)
''')
# 品項表
c.execute('''
CREATE TABLE IF NOT EXISTS 品項 (
    品項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    類別編號 INTEGER,
    品項名稱 TEXT,
    FOREIGN KEY(類別編號) REFERENCES 類別(類別編號)
)
''')
# 細項表
c.execute('''
CREATE TABLE IF NOT EXISTS 細項 (
    細項編號 INTEGER PRIMARY KEY AUTOINCREMENT,
    品項編號 INTEGER,
    細項名稱 TEXT,
    FOREIGN KEY(品項編號) REFERENCES 品項(品項編號)
)
''')
# 進/銷 貨表
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
def 查詢(table):
    return pd.read_sql(f"SELECT * FROM {table}", conn)


def 新增(table, cols, vals):
    df = 查詢(table)
    cols_all = df.columns.tolist()
    target = cols_all[1:1+len(vals)]
    q = ','.join(target)
    qm = ','.join(['?'] * len(vals))
    try:
        c.execute(f"INSERT INTO {table} ({q}) VALUES ({qm})", vals)
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning('操作失敗：可能重複或外鍵限制')


def 刪除(table, key, val):
    c.execute(f"DELETE FROM {table} WHERE {key}=?", (val,))
    conn.commit()


def 取得對映(table, key_col=None, val_col=None):
    """
    回傳指定資料表的名稱->編號映射。
    支援 類別、品項、細項 三張表。
    """
    if table == '類別':
        df = 查詢('類別')
        df.columns = df.columns.str.strip()
        return dict(zip(df['類別名稱'], df['類別編號']))
    elif table == '品項':
        df = 查詢('品項')
        df.columns = df.columns.str.strip()
        return dict(zip(df['品項名稱'], df['品項編號']))
    elif table == '細項':
        df = 查詢('細項')
        df.columns = df.columns.str.strip()
        return dict(zip(df['細項名稱'], df['細項編號']))
    else:
        st.warning(f"不支援的表：{table}")
        return {}
        except sqlite3.OperationalError:
            # 若尚未建立類別表或DB異常，回傳空字典
            return {}
    df = 查詢(table)
    df.columns = df.columns.str.strip()
    if key_col not in df.columns or val_col not in df.columns:
        st.warning(f"表 {table} 缺少 {key_col} 或 {val_col} 欄位")
        return {}
    return dict(zip(df[val_col], df[key_col]))


def 批次匯入進貨(df):
    df = df.rename(columns=str.strip)
    df['買入數量'] = df.get('買入數量', 0).fillna(0)
    df['買入單價'] = df.get('買入單價', 0).fillna(0)
    count = 0
    for _, r in df.iterrows():
        if r['買入數量'] <= 0:
            continue
        cat, item, sub = r['類別'], r['品項'], r['細項']
        if pd.isna(cat) or pd.isna(item) or pd.isna(sub):
            continue
        新增('類別', ['類別名稱'], [cat])
        cid = 取得對映('類別', '類別編號', '類別名稱').get(cat)
        新增('品項', ['類別編號', '品項名稱'], [cid, item])
        iid = pd.read_sql(
            'SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?',
            conn, params=(cid, item)
        )['品項編號'].iloc[0]
        新增('細項', ['品項編號', '細項名稱'], [iid, sub])
        sid = pd.read_sql(
            'SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?',
            conn, params=(iid, sub)
        )['細項編號'].iloc[0]
        新增('進貨', ['類別編號', '品項編號', '細項編號', '數量', '單價'],
             [cid, iid, sid, int(r['買入數量']), float(r['買入單價'])])
        count += 1
    return count


def 批次匯入銷售(df):
    df = df.rename(columns=str.strip)
    df['賣出數量'] = df.get('賣出數量', 0).fillna(0)
    df['賣出單價'] = df.get('賣出單價', 0).fillna(0)
    count = 0
    for _, r in df.iterrows():
        if r['賣出數量'] <= 0:
            continue
        cat, item, sub = r['類別'], r['品項'], r['細項']
        if pd.isna(cat) or pd.isna(item) or pd.isna(sub):
            continue
        新增('類別', ['類別名稱'], [cat])
        cid = 取得對映('類別', '類別編號', '類別名稱').get(cat)
        新增('品項', ['類別編號', '品項名稱'], [cid, item])
        iid = pd.read_sql(
            'SELECT 品項編號 FROM 品項 WHERE 類別編號=? AND 品項名稱=?',
           	conn, params=(cid, item)
        )['品項編號'].iloc[0]
        新增('細項', ['品項編號', '細項名稱'], [iid, sub])
        sid = pd.read_sql(
            'SELECT 細項編號 FROM 細項 WHERE 品項編號=? AND 細項名稱=?',
           	conn, params=(iid, sub)
        )['細項編號'].iloc[0]
        新增('銷售', ['類別編號', '品項編號', '細項編號', '數量', '單價'],
             [cid, iid, sid, int(r['賣出數量']), float(r['賣出單價'])])
        count += 1
    return count

# --- UI 分支 ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理', '品項管理', '細項管理', '進貨', '銷售', '儀表板'
])

if menu == '類別管理':
    st.title('⚙️ 類別管理')
    df = 查詢('類別').rename(columns={'類別編號': '編號', '類別名稱': '名稱'})
    st.table(df)
    with st.form('form_cat'):
        new_name = st.text_input('新增類別')
        del_id = st.text_input('刪除編號')
        if st.form_submit_button('執行'):
            if new_name:
                新增('類別', ['類別名稱'], [new_name])
            if del_id.isdigit():
                刪除('類別', '類別編號', int(del_id))
            st.experimental_rerun()

elif menu == '品項管理':
    st.title('⚙️ 品項管理')
    cat_map = 取得對映('類別', '類別編號', '類別名稱')
    if not cat_map:
        st.warning('先新增類別')
    else:
        sel_cat = st.selectbox('類別', list(cat_map.keys()))
        cid = cat_map[sel_cat]
        df = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
        df = df.rename(columns={'品項編號': '編號', '品項名稱': '名稱'})
        st.table(df)
        with st.form('form_item'):
            new_item = st.text_input('新增品項')
            del_item = st.text_input('刪除編號')
            if st.form_submit_button('執行'):
                if new_item:
                    新增('品項', ['類別編號', '品項名稱'], [cid, new_item])
                if del_item.isdigit():
                    刪除('品項', '品項編號', int(del_item))
                st.experimental_rerun()

elif menu == '細項管理':
    st.title('⚙️ 細項管理')
    cat_map = 取得對映('類別', '類別編號', '類別名稱')
    if not cat_map:
        st.warning('先新增類別')
    else:
        sel_cat = st.selectbox('類別', list(cat_map.keys()))
        cid = cat_map[sel_cat]
        df_i = pd.read_sql('SELECT * FROM 品項 WHERE 類別編號=?', conn, params=(cid,))
        df_i.columns = df_i.columns.str.strip()
        item_map = {r['品項名稱']: r['品項編號'] for _, r in df_i.iterrows()}
        if not item_map:
            st.warning('先新增品項')
        else:
            sel_item = st.selectbox('品項', list(item_map.keys()))
            iid = item_map[sel_item]
            df_su = pd.read_sql('SELECT * FROM 細項 WHERE 品項編號=?', conn, params=(iid,))
            df_su = df_su.rename(columns={'細項編號': '編號', '細項名稱': '名稱'})
            st.table(df_su)
            with st.form('form_sub'):
                new_sub = st.text_input('新增細項')
                del_sub = st.text_input('刪除編號')
                if st.form_submit_button('執行'):
                    if new_sub:
                        新增('細項', ['品項編號', '細項名稱'], [iid, new_sub])
                    if del_sub.isdigit():
                        刪除('細項', '細項編號', int(del_sub))
                    st.experimental_rerun()

elif menu == '進貨':
    st.title('➕ 批次匯入 / 手動記錄進貨')
    tab1, tab2 = st.tabs(['批次匯入', '手動記錄'])
    with tab1:
        sample = pd.DataFrame({
            '類別': ['首飾'], '品項': ['項鍊'], '細項': ['金屬鍊'],
            '買入數量': [10], '買入單價': [100.0]
        })
        csv = sample.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載進貨範例', csv, 'purchase.csv', 'text/csv')
        uploaded = st.file_uploader('上傳檔案', type=['csv', 'xlsx', 'xls'])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
            except:
                df = pd.read_csv(uploaded)
            cnt = 批次匯入進貨(df)
            st.success(f'批次匯入 {cnt} 筆進貨記錄')
    with tab2:
        st.info('手動記錄請使用下拉選單')

elif menu == '銷售':
    st.title('➕ 批次匯入 / 手動記錄銷售')
    tab1, tab2 = st.tabs(['批次匯入', '手動記錄'])
    with tab1:
        sample = pd.DataFrame({
            '類別': ['首飾'], '品項': ['手鍊'], '細項': ['皮革鍊'],
            '賣出數量': [2], '賣出單價': [150.0]
        })
        csv = sample.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載銷售範例', csv, 'sales.csv', 'text/csv')
        uploaded = st.file_uploader('上傳檔案', type=['csv', 'xlsx', 'xls'])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
            except:
                df = pd.read_csv(uploaded)
            cnt = 批次匯入銷售(df)
            st.success(f'批次匯入 {cnt} 筆銷售記錄')
    with tab2:
        st.info('手動記錄請使用下拉選單')

elif menu == '儀表板':
    st.title('📊 庫存儀表板')
    df_p = pd.read_sql('SELECT * FROM 進貨', conn)
    df_s = pd.read_sql('SELECT * FROM 銷售', conn)
    df_c = 查詢('類別').rename(columns={'類別編號':'類別編號','類別名稱':'類別名稱'})
    df_i = 查詢('品項').rename(columns={'品項編號':'品項編號','品項名稱':'品項名稱'})
    df_su = 查詢('細項').rename(columns={'細項編號':'細項編號','細項名稱':'細項名稱'})
    df_p = df_p.merge(df_c, on='類別編號').merge(df_i, on='品項編號').merge(df_su, on='細項編號')
    df_s = df_s.merge(df_c, on='類別編號').merge(df_i, on='品項編號').merge(df_su, on='細項編號')
    gp = df_p.groupby(['類別名稱','品項名稱','細項名稱'], as_index=False).agg(進貨=('數量','sum'),支出=('總價','sum'))
    gs = df_s.groupby(['類別名稱','品項名稱','細項名稱'], as_index=False).agg(銷售=('數量','sum'),收入=('總價','sum'))
    summary = pd.merge(gp, gs, on=['類別名稱','品項名稱','細項名稱'], how='outer').fillna(0)
    summary['庫存'] = summary['進貨'] - summary['銷售']
    st.dataframe(summary)
    st.metric('總支出', f"{gp['支出'].sum():.2f}")
    st.metric('總收入', f"{gs['收入'].sum():.2f}")
    st.metric('淨利', f"{gs['收入'].sum()-gp['支出'].sum():.2f}")
