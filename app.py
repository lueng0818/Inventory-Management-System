# --- UI 選單定義 ---
st.sidebar.title('庫存管理系統')
menu = st.sidebar.radio('功能選單', [
    '類別管理',
    '品項管理',
    '細項管理',
    '進貨',
    '銷售',
    '儀表板'
])

# --- 各功能分支 --- 
if menu == '類別管理':
    # 類別管理的程式碼...
    pass

elif menu == '品項管理':
    # 品項管理的程式碼...
    pass

elif menu == '細項管理':
    # 細項管理的程式碼...
    pass

elif menu == '進貨':
    st.title('➕ 批次匯入 / 手動記錄進貨')
    tab1, tab2 = st.tabs(['批次匯入', '手動記錄'])
    with tab1:
        # 下載 CSV 範例
        sample_df = pd.DataFrame({
            '類別': ['首飾', '配件'],
            '品項': ['項鍊', '戒指'],
            '細項': ['金屬鍊', '銀戒'],
            '買入數量': [10, 5],
            '買入單價': [100.0, 200.0]
        })
        csv_example = sample_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            '下載進貨範例檔 (CSV)',
            csv_example,
            file_name='purchase_template.csv',
            mime='text/csv'
        )

        uploaded = st.file_uploader('上傳進貨 Excel/CSV', type=['xlsx','xls','csv'])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
            except:
                df = pd.read_csv(uploaded)
            count = 批次匯入進貨(df)
            st.success(f'批次匯入 {count} 筆進貨記錄')

    with tab2:
        # 手動記錄進貨的程式碼...
        pass

elif menu == '銷售':
    # 銷售的程式碼...
    pass

elif menu == '儀表板':
    # 儀表板的程式碼...
    pass

# 進貨
# --- 進貨分支 ---
elif menu == '進貨':
    st.title('➕ 批次匯入 / 手動記錄進貨')
    tab1, tab2 = st.tabs(['批次匯入', '手動記錄'])
    with tab1:
        # 下載 CSV 範例
        sample_df = pd.DataFrame({
            '類別': ['首飾', '配件'],
            '品項': ['項鍊', '戒指'],
            '細項': ['金屬鍊', '銀戒'],
            '買入數量': [10, 5],
            '買入單價': [100.0, 200.0]
        })
        csv_example = sample_df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載進貨範例檔 (CSV)', csv_example,
                           file_name='purchase_template.csv', mime='text/csv')

        uploaded = st.file_uploader('上傳進貨 Excel/CSV', type=['xlsx','xls','csv'])
        if uploaded:
            try:
                df = pd.read_excel(uploaded)
            except:
                df = pd.read_csv(uploaded)
            count = 批次匯入進貨(df)
            st.success(f'批次匯入 {count} 筆進貨記錄')

    with tab2:
        # 手動記錄同之前邏輯
        ...

# --- 銷售分支 ---
elif menu == '銷售':
    st.title('➕ 批次匯入 / 手動記錄銷售')
    tab1, tab2 = st.tabs(['批次匯入', '手動記錄'])
    with tab1:
        # 下載 CSV 範例
        sample_sales = pd.DataFrame({
            '類別': ['首飾', '配件'],
            '品項': ['手鍊', '耳環'],
            '細項': ['皮革鍊', '珍珠耳環'],
            '賣出數量': [2, 3],
            '賣出單價': [150.0, 80.0]
        })
        csv_sales_example = sample_sales.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載銷售範例檔 (CSV)', csv_sales_example,
                           file_name='sales_template.csv', mime='text/csv')

        up_s = st.file_uploader('上傳銷售 Excel/CSV', type=['xlsx','xls','csv'])
        if up_s:
            try:
                df_sls = pd.read_excel(up_s)
            except:
                df_sls = pd.read_csv(up_s)
            count_s = 批次匯入銷售(df_sls)
            st.success(f'批次匯入 {count_s} 筆銷售記錄')
    with tab_s1:
        # 下載範例檔
        sample_sales = pd.DataFrame({
            '類別': ['首飾', '配件'],
            '品項': ['手鍊', '耳環'],
            '細項': ['皮革鍊', '珍珠耳環'],
            '賣出數量': [2, 3],
            '賣出單價': [150.0, 80.0]
        })
        csv_sales_example = sample_sales.to_csv(index=False, encoding='utf-8-sig')
        st.download_button('下載銷售範例檔 (CSV)', csv_sales_example, file_name='sales_template.csv', mime='text/csv')

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
