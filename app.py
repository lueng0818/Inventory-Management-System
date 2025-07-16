import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# 建立主表
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
# 建立交易表
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

def 新增(table: str, cols: list, vals: list):
    df = 查詢(table)
    cols_used = df.columns.tolist()[1:1+len(vals)]
    placeholders = ",".join(["?" for _ in vals])
    try:
        c.execute(
            f"INSERT INTO {table} ({','.join(cols_used)}) VALUES ({placeholders})",
            vals
        )
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("操作失敗：可能重複或外鍵限制")

def 刪除(table: str, key_col: str, key_val):
    c.execute(f"DELETE FROM {table} WHERE {key_col}=?", (key_val,))
    conn.commit()

def 取得對映(table: str) -> dict:
    mapping = {
        '類別': ("類別名稱","類別編號"),
        '品項': ("品項名稱","品項編號"),
        '細項': ("細項名稱","細項編號"),
    }
    name_col, id_col = mapping.get(table, (None,None))
    if not name_col:
        return {}
    rows = conn.execute(f"SELECT {name_col},{id_col} FROM {table}").fetchall()
    return {name: idx for name, idx in rows}

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", [
    "類別管理","品項管理","細項管理","進貨","銷售","儀表板"
])

# 類別管理
if menu == "類別管理":
    st.header("⚙️ 類別管理")
    df = 查詢("類別").rename(columns={"類別編號":"編號","類別名稱":"名稱"})
    st.table(df)

    with st.form("form_cat"):
        new_cat = st.text_input("新增類別")
        del_cat = st.text_input("刪除編號")
        if st.form_submit_button("執行"):
            if new_cat:
                新增("類別", ["類別名稱"], [new_cat])
            if del_cat.isdigit():
                刪除("類別", "類別編號", int(del_cat))
            st.experimental_rerun()

# 品項管理
elif menu == "品項管理":
    st.header("⚙️ 品項管理")
    cmap = 取得對映("類別")
    if not cmap:
        st.warning("請先到「類別管理」建立類別")
    else:
        sel = st.selectbox("選擇類別", list(cmap.keys()))
        cid = cmap[sel]
        df = pd.read_sql(
            "SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?",
            conn, params=(cid,)
        ).rename(columns={"品項編號":"編號","品項名稱":"名稱"})
        st.table(df)

        with st.form("form_item"):
            new_item = st.text_input("新增品項")
            del_item = st.text_input("刪除編號")
            if st.form_submit_button("執行"):
                if new_item:
                    新增("品項", ["類別編號","品項名稱"], [cid, new_item])
                if del_item.isdigit():
                    刪除("品項", "品項編號", int(del_item))
                st.experimental_rerun()

# 細項管理
elif menu == "細項管理":
    st.header("⚙️ 細項管理")
    cmap = 取得對映("類別")
    if not cmap:
        st.warning("請先到「類別管理」建立類別")
    else:
        sel = st.selectbox("選擇類別", list(cmap.keys()))
        cid = cmap[sel]
        items = pd.read_sql(
            "SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?",
            conn, params=(cid,)
        )
        imap = dict(zip(items["品項名稱"], items["品項編號"]))
        if not imap:
            st.warning("該類別尚無品項")
        else:
            sel2 = st.selectbox("選擇品項", list(imap.keys()))
            iid = imap[sel2]
            df_s = pd.read_sql(
                "SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?",
                conn, params=(iid,)
            ).rename(columns={"細項編號":"編號","細項名稱":"名稱"})
            st.table(df_s)

            with st.form("form_sub"):
                new_sub = st.text_input("新增細項")
                del_sub = st.text_input("刪除編號")
                if st.form_submit_button("執行"):
                    if new_sub:
                        新增("細項", ["品項編號","細項名稱"], [iid, new_sub])
                    if del_sub.isdigit():
                        刪除("細項", "細項編號", int(del_sub))
                    st.experimental_rerun()

# 進貨管理
elif menu == "進貨":
    st.header("➕ 進貨管理")
    tab1, tab2 = st.tabs(["批次匯入","手動記錄"])
    with tab1:
        st.info("批次匯入請使用下方範例檔案")
    with tab2:
        cat_map = 取得對映("類別")
        if not cat_map:
            st.warning("請先在「類別管理」新增類別")
        else:
            sel_cat = st.selectbox("選擇類別", list(cat_map.keys()))
            cid = cat_map[sel_cat]
            items = pd.read_sql(
                "SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?",
                conn, params=(cid,)
            )
            item_map = dict(zip(items["品項名稱"], items["品項編號"]))
            if not item_map:
                st.warning("該類別尚無品項，請先在「品項管理」新增")
            else:
                sel_item = st.selectbox("選擇品項", list(item_map.keys()))
                iid = item_map[sel_item]
                subs = pd.read_sql(
                    "SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?",
                    conn, params=(iid,)
                )
                sub_map = dict(zip(subs["細```
