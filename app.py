import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# --- 資料庫初始化 ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
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
    cols_all = df.columns.tolist()[1:1+len(vals)]
    q = ",".join(cols_all)
    qm = ",".join(["?"]*len(vals))
    try:
        c.execute(f"INSERT INTO {table} ({q}) VALUES ({qm})", vals)
        conn.commit()
    except sqlite3.IntegrityError:
        st.warning("操作失敗：重複或外鍵限制")

def 刪除(table: str, key: str, val):
    c.execute(f"DELETE FROM {table} WHERE {key}=?", (val,))
    conn.commit()

def 取得對映(table: str) -> dict:
    # 直接用 sqlite3 查詢名稱->編號
    if table == "類別":
        rows = conn.execute("SELECT 類別名稱, 類別編號 FROM 類別").fetchall()
        return {name: cid for name, cid in rows}
    if table == "品項":
        rows = conn.execute("SELECT 品項名稱, 品項編號 FROM 品項").fetchall()
        return {name: pid for name, pid in rows}
    if table == "細項":
        rows = conn.execute("SELECT 細項名稱, 細項編號 FROM 細項").fetchall()
        return {name: sid for name, sid in rows}
    return {}

def 批次匯入進貨(df: pd.DataFrame) -> int:
    df = df.rename(columns=str.strip)
    df["買入數量"] = df.get("買入數量",0).fillna(0)
    df["買入單價"] = df.get("買入單價",0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r["買入數量"]<=0: continue
        cat, item, sub = r["類別"], r["品項"], r["細項"]
        if pd.isna(cat)|pd.isna(item)|pd.isna(sub): continue
        新增("類別", ["類別名稱"], [cat])
        cid = 取得對映("類別")[cat]
        新增("品項", ["類別編號","品項名稱"], [cid,item])
        iid = 取得對映("品項")[item]
        新增("細項", ["品項編號","細項名稱"], [iid,sub])
        sid = 取得對映("細項")[sub]
        新增("進貨", ["類別編號","品項編號","細項編號","數量","單價"],
             [cid,iid,sid,int(r["買入數量"]),float(r["買入單價"])])
        cnt += 1
    return cnt

def 批次匯入銷售(df: pd.DataFrame) -> int:
    df = df.rename(columns=str.strip)
    df["賣出數量"] = df.get("賣出數量",0).fillna(0)
    df["賣出單價"] = df.get("賣出單價",0).fillna(0)
    cnt = 0
    for _, r in df.iterrows():
        if r["賣出數量"]<=0: continue
        cat, item, sub = r["類別"], r["品項"], r["細項"]
        if pd.isna(cat)|pd.isna(item)|pd.isna(sub): continue
        新增("類別", ["類別名稱"], [cat])
        cid = 取得對映("類別")[cat]
        新增("品項", ["類別編號","品項名稱"], [cid,item])
        iid = 取得對映("品項")[item]
        新增("細項", ["品項編號","細項名稱"], [iid,sub])
        sid = 取得對映("細項")[sub]
        新增("銷售", ["類別編號","品項編號","細項編號","數量","單價"],
             [cid,iid,sid,int(r["賣出數量"]),float(r["賣出單價"])])
        cnt += 1
    return cnt

# --- UI 分支 ---
st.sidebar.title("庫存管理系統")
menu = st.sidebar.radio("功能選單", [
    "類別管理","品項管理","細項管理","進貨","銷售","儀表板"
])

if menu == "類別管理":
    st.header("⚙️ 類別管理")
    df = 查詢("類別").rename(columns={"類別編號":"編號","類別名稱":"名稱"})
    st.table(df)
    with st.form("f1"):
        n = st.text_input("新增類別")
        d = st.text_input("刪除編號")
        if st.form_submit_button("執行"):
            if n: 新增("類別",["類別名稱"],[n])
            if d.isdigit(): 刪除("類別","類別編號",int(d))
            st.experimental_rerun()

elif menu == "品項管理":
    st.header("⚙️ 品項管理")
    cmap = 取得對映("類別")
    if not cmap:
        st.warning("先到類別管理新增")
    else:
        sel = st.selectbox("類別",list(cmap.keys()))
        cid = cmap[sel]
        df = pd.read_sql("SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?",conn,(cid,))
        df = df.rename(columns={"品項編號":"編號","品項名稱":"名稱"})
        st.table(df)
        with st.form("f2"):
            ni = st.text_input("新增品項")
            di = st.text_input("刪除編號")
            if st.form_submit_button("執行"):
                if ni: 新增("品項",["類別編號","品項名稱"],[cid,ni])
                if di.isdigit(): 刪除("品項","品項編號",int(di))
                st.experimental_rerun()

elif menu == "細項管理":
    st.header("⚙️ 細項管理")
    cmap = 取得對映("類別")
    if not cmap:
        st.warning("先到類別管理新增")
    else:
        sel = st.selectbox("類別",list(cmap.keys()))
        cid = cmap[sel]
        df_i = pd.read_sql("SELECT 品項編號,品項名稱 FROM 品項 WHERE 類別編號=?",conn,(cid,))
        imap = dict(zip(df_i["品項名稱"],df_i["品項編號"]))
        if not imap:
            st.warning("先新增品項")
        else:
            sel2 = st.selectbox("品項",list(imap.keys()))
            iid = imap[sel2]
            df_s = pd.read_sql("SELECT 細項編號,細項名稱 FROM 細項 WHERE 品項編號=?",conn,(iid,))
            df_s = df_s.rename(columns={"細項編號":"編號","細項名稱":"名稱"})
            st.table(df_s)
            with st.form("f3"):
                ns = st.text_input("新增細項")
                ds = st.text_input("刪除編號")
                if st.form_submit_button("執行"):
                    if ns: 新增("細項",["品項編號","細項名稱"],[iid,ns])
                    if ds.isdigit(): 刪除("細項","細項編號",int(ds))
                    st.experimental_rerun()

elif menu == "進貨":
    st.header("➕ 進貨管理")
    t1,t2 = st.tabs(["批次匯入","手動記錄"])
    with t1:
        sample = pd.DataFrame({"類別":["首飾"],"品項":["項鍊"],"細項":["金屬鍊"],"買入數量":[10],"買入單價":[100.0]})
        btn = sample.to_csv(index=False,encoding="utf-8-sig")
        st.download_button("下載範例",btn,"purchase.csv","text/csv")
        up = st.file_uploader("上傳",type=["csv","xlsx","xls"])
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            c = 批次匯入進貨(df); st.success(f"匯入{c}筆")
    with t2:
        st.info("手動記錄請先設定好主檔")

elif menu == "銷售":
    st.header("➕ 銷售管理")
    t1,t2 = st.tabs(["批次匯入","手動記錄"])
    with t1:
        sample = pd.DataFrame({"類別":["首飾"],"品項":["手鍊"],"細項":["皮革鍊"],"賣出數量":[2],"賣出單價":[150.0]})
        btn = sample.to_csv(index=False,encoding="utf-8-sig")
        st.download_button("下載範例",btn,"sales.csv","text/csv")
        up = st.file_uploader("上傳",type=["csv","xlsx","xls"])
        if up:
            try: df = pd.read_excel(up)
            except: df = pd.read_csv(up)
            c = 批次匯入銷售(df); st.success(f"匯入{c}筆")
    with t2:
        st.info("手動記錄請先設定好主檔")

elif menu == "儀表板":
    st.header("📊 庫存儀表板")
    df_p = pd.read_sql("SELECT * FROM 進貨",conn)
    df_s = pd.read_sql("SELECT * FROM 銷售",conn)
    df_c = 查詢("類別").rename(columns={"類別編號":"類別編號","類別名稱":"類別名稱"})
    df_i = 查詢("品項").rename(columns={"品項編號":"品項編號","品項名稱":"品項名稱"})
    df_su= 查詢("細項").rename(columns={"細項編號":"細項編號","細項名稱":"細項名稱"})
    df_p = df_p.merge(df_c,on="類別編號").merge(df_i,on="品項編號").merge(df_su,on="細項編號")
    df_s = df_s.merge(df_c,on="類別編號").merge(df_i,on="品項編號").merge(df_su,on="細項編號")
    gp = df_p.groupby(["類別名稱","品項名稱","細項名稱"],as_index=False).agg(進貨=("數量","sum"),支出=("總價","sum"))
    gs = df_s.groupby(["類別名稱","品項名稱","細項名稱"],as_index=False).agg(銷售=("數量","sum"),收入=("總價","sum"))
    summary = pd.merge(gp,gs,on=["類別名稱","品項名稱","細項名稱"],how="outer").fillna(0)
    summary["庫存"] = summary["進貨"] - summary["銷售"]
    st.dataframe(summary)
    st.metric("總支出",f"{gp['支出'].sum():.2f}")
    st.metric("總收入",f"{gs['收入'].sum():.2f}")
    st.metric("淨利",f"{gs['收入'].sum()-gp['支出'].sum():.2f}")
