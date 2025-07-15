# Inventory Management System for Light Jewelry Designers
#
# Repository Structure:
# inventory_system/
# ├── app.py
# ├── requirements.txt
# ├── integrated_inventory.csv (optional import file)
# └── database.db (auto-generated)

import streamlit as st
import sqlite3
import pandas as pd
import os
from datetime import datetime

# --- Database Setup ---
conn = sqlite3.connect('database.db', check_same_thread=False)
c = conn.cursor()
# Categories
c.execute('''CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE
)''')
# Purchases and Sales
for tbl in ['purchases','sales']:
    c.execute(f'''
        CREATE TABLE IF NOT EXISTS {tbl} (
            id INTEGER PRIMARY KEY,
            item_name TEXT,
            category_id INTEGER,
            quantity INTEGER,
            unit_price REAL,
            total_price REAL,
            date TEXT,
            FOREIGN KEY(category_id) REFERENCES categories(id)
        )''')
# Reminder Settings
c.execute('''CREATE TABLE IF NOT EXISTS reminders (
    item_name TEXT PRIMARY KEY,
    remind INTEGER
)''')
conn.commit()

# --- Helper Functions ---
def get_categories():
    rows = c.execute('SELECT id,name FROM categories').fetchall()
    return {name: id for id, name in rows}

def add_category(name):
    try:
        c.execute('INSERT INTO categories (name) VALUES (?)',(name,))
        conn.commit()
    except sqlite3.IntegrityError:
        pass  # already exists


def add_purchase(item,cat_id,qty,price,date=None):
    total = qty*price
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO purchases (item_name,category_id,quantity,unit_price,total_price,date) VALUES (?,?,?,?,?,?)',
              (item,cat_id,qty,price,total,date))
    conn.commit()

def add_sale(item,cat_id,qty,price,date=None):
    total = qty*price
    date = date or datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    c.execute('INSERT INTO sales (item_name,category_id,quantity,unit_price,total_price,date) VALUES (?,?,?,?,?,?)',
              (item,cat_id,qty,price,total,date))
    conn.commit()

def set_reminder(item,flag):
    c.execute('REPLACE INTO reminders (item_name,remind) VALUES (?,?)',(item,1 if flag else 0))
    conn.commit()

# --- Auto-Import Integrated CSV ---
IMPORT_PATH = 'integrated_inventory.csv'
if os.path.exists(IMPORT_PATH):
    df_imp = pd.read_csv(IMPORT_PATH)
    cats = get_categories()
    for _, row in df_imp.iterrows():
        cat = row['Category']
        add_category(cat)
        cats = get_categories()
        cid = cats[cat]
        # 初始庫存
        start_qty = int(row.get('起始數量',0)) if pd.notna(row.get('起始數量')) else 0
        unit_price = float(str(row.get('起始單價','0')).replace('NT$','').replace(',',''))
        if start_qty>0:
            add_purchase(row['品項'],cid,start_qty,unit_price,row.get('日期'))
        # 減少視為銷售
        dec = int(row.get('減少',0)) if pd.notna(row.get('減少')) else 0
        if dec>0:
            add_sale(row['品項'],cid,dec,unit_price,row.get('日期'))
        # 設定提醒
        remind_flag = bool(row.get('需補貨提醒'))
        set_reminder(row['品項'],remind_flag)

# --- Streamlit App ---
st.sidebar.title("Inventory Management")
page = st.sidebar.radio("Navigate", ["Dashboard","Manage Categories","Add Purchase","Add Sale","View Records","Import/Export"])

if page == 'Import/Export':
    st.title('📥 Import / Export')
    if os.path.exists(IMPORT_PATH):
        st.success(f"Found import file: {IMPORT_PATH}")
    uploaded = st.file_uploader('Upload integrated_inventory.csv',type='csv')
    if uploaded:
        with open(IMPORT_PATH,'wb') as f: f.write(uploaded.getbuffer())
        st.success('File saved. Restart app to import.')
    # Export current summary
    if st.button('Export Current Inventory to CSV'):
        df_p = pd.read_sql('SELECT item_name,category_id,quantity,unit_price,total_price,date FROM purchases',conn)
        df_s = pd.read_sql('SELECT item_name,category_id,quantity,unit_price,total_price,date FROM sales',conn)
        df_r = pd.read_sql('SELECT * FROM reminders',conn)
        df = df_p.merge(df_s, on='item_name', how='outer', suffixes=('_in','_out')).merge(df_r,on='item_name',how='left')
        df.to_csv('exported_inventory.csv',index=False)
        st.download_button('Download exported_inventory.csv','exported_inventory.csv','text/csv')

elif page == "Dashboard":
    st.title("📊 Inventory Dashboard")
    # Summary
    purchases = pd.read_sql('SELECT item_name,category_id,SUM(quantity) qty,SUM(total_price) expense FROM purchases GROUP BY item_name,category_id',conn)
    sales = pd.read_sql('SELECT item_name,category_id,SUM(quantity) qty,SUM(total_price) revenue FROM sales GROUP BY item_name,category_id',conn)
    cats = {v:k for k,v in get_categories().items()}
    summary = purchases.merge(sales,on=['item_name','category_id'],how='outer').fillna(0)
    summary['In Stock'] = summary['qty_x']-summary['qty_y']
    summary['Category'] = summary['category_id'].map(cats)
    st.dataframe(summary.rename(columns={'item_name':'Item','qty_x':'Purchased','qty_y':'Sold','expense':'Expense','revenue':'Revenue'})[['Item','Category','Purchased','Sold','In Stock']])
    # Financial
    total_exp = summary['expense'].sum()
    total_rev = summary['revenue'].sum()
    st.subheader('💰 Financial Overview')
    st.metric('Total Expense',f"{total_exp:.2f}")
    st.metric('Total Revenue',f"{total_rev:.2f}")
    st.metric('Net Profit',f"{total_rev-total_exp:.2f}")
    # Reminders
    rems = pd.read_sql('SELECT item_name FROM reminders WHERE remind=1',conn)
    if not rems.empty:
        st.subheader('⚠️ Items Needing Reorder')
        for item in rems['item_name']:
            st.warning(f"{item} 需補貨提醒")

elif page == "Manage Categories":
    st.title("⚙️ Manage Categories")
    with st.form("cat_form"):
        name = st.text_input('New Category Name')
        if st.form_submit_button('Add Category') and name:
            add_category(name)
            st.success(f"Added: {name}")
    st.table(pd.DataFrame(get_categories().items(),columns=['Category','ID']))

elif page == "Add Purchase":
    st.title("➕ Add Purchase")
    cats = get_categories()
    with st.form('p_form'):
        item = st.text_input('Item Name')
        cat = st.selectbox('Category',list(cats.keys()))
        qty = st.number_input('Quantity',min_value=1,value=1)
        price = st.number_input('Unit Price',min_value=0.0,format='%.2f')
        if st.form_submit_button('Save'):
            add_purchase(item,cats[cat],qty,price)
            st.success('Purchase recorded')

elif page == "Add Sale":
    st.title("➕ Add Sale")
    cats = get_categories()
    with st.form('s_form'):
        item = st.text_input('Item Name')
        cat = st.selectbox('Category',list(cats.keys()))
        qty = st.number_input('Quantity',min_value=1,value=1)
        price = st.number_input('Unit Price',min_value=0.0,format='%.2f')
        if st.form_submit_button('Save'):
            add_sale(item,cats[cat],qty,price)
            st.success('Sale recorded')

else:  # View Records
    st.title("📚 All Records")
    dfp = pd.read_sql('SELECT p.id, p.date, p.item_name as Item, c.name as Category, p.quantity as Qty, p.unit_price as Price FROM purchases p JOIN categories c ON p.category_id=c.id ORDER BY date DESC',conn)
    dfs = pd.read_sql('SELECT s.id, s.date, s.item_name as Item, c.name as Category, s.quantity as Qty, s.unit_price as Price FROM sales s JOIN categories c ON s.category_id=c.id ORDER BY date DESC',conn)
    st.subheader('Purchases'); st.dataframe(dfp)
    st.subheader('Sales');    st.dataframe(dfs)
