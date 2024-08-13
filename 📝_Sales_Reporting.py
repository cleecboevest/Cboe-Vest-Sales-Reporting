from pathlib import Path
import yaml
from yaml import SafeLoader

import streamlit as st
import streamlit_authenticator as stauth
import pandas as pd
from st_aggrid import AgGrid

def format_dollar_amount(amount):
    formatted_absolute_amount = '${:,.2f}'.format(abs(amount))
    if round(amount, 2) < 0:
        return f'-{formatted_absolute_amount}'
    return formatted_absolute_amount

@st.cache_data(ttl=21*24*3600)
def load_mf_sales_data(url):
     #----------READ IN DATA--------
     # Read in the Broadridge Data
     df_mf_master = pd.read_excel(url,sheet_name='Sales Data Merge',engine='openpyxl',skiprows=0)
     return df_mf_master

@st.cache_data(ttl=21*24*3600)
def load_mf_cohort_data(url):
     #----------READ IN DATA--------
     # Read in the Broadridge Data
     df_mf_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_mf_master

@st.cache_data(ttl=30*24*3600)
def load_vest_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_vest_wholesalers = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_vest_wholesalers

@st.cache_data(ttl=21*24*3600)
def load_etf_data(url):
     #----------READ IN DATA--------
     # Read in the FT ETF Sales Data
     df_etf_master = pd.read_excel(url,sheet_name='Sales Data',engine='openpyxl',skiprows=0)
     return df_etf_master

@st.cache_data(ttl=21*24*3600)
def load_uit_data(url):
     #----------READ IN DATA--------
     # Read in the FT UIT Sales Data
     df_uit_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_uit_master

#---------- SETTINGS ----------
page_title = "Sales Dashboard"
page_icon = ":money_with_wings:"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)

#-------------- USER AUTHENTICATION ----------

# load config file
file_path = Path(__file__).parent / "config.yaml"
with file_path.open("rb") as file:
     config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
     config['credentials'],
     config['cookie']['name'],
     config['cookie']['key'],
     config['cookie']['expiry_days'],
     config['preauthorized']
)
     
   
name, authentication_status, username = authenticator.login()

if 'authentication_status' not in st.session_state:
     st.session_state['authentication_status'] = authentication_status

if authentication_status == False:
     st.error("Username or password is incorrect.")
     
if authentication_status == None:
     st.warning("Please enter your username and password.")

# If authenticated, then start the app     
if authentication_status == True:

     # Render logout button
     authenticator.logout('Logout', 'sidebar')
     st.sidebar.title(f"Welcome {name}!")
     
     #----------STATUS MESSAGE------
     with st.spinner('Loading All Sales Data. This May Take A Minute. Please wait...'):
          df_mf_sales_master = load_mf_sales_data(st.secrets['mf_sales_url'])
          df_mf_cohort_master = load_mf_cohort_data(st.secrets['mf_analyzer_url'])
          df_etf_master = load_etf_data(st.secrets['etf_sales_url'])
          df_uit_master = load_uit_data(st.secrets['uit_sales_url'])
          df_vest_wholesalers = load_vest_wholesaler_data(st.secrets['vest_wholesaler_url'])

     # Load in the data and perform operations on the Dataframe
     # Merged Master_Table and Sheet1 into df3
     #df_mf_master_merged = df_mf_master.merge(df_vest_wholesalers, left_on=['State/Region'], right_on=['State'], how='outer')
     #df_etf_master_merged = df_etf_master.merge(df_vest_wholesalers, left_on=['State'], right_on=['State'], how='left')
     df_uit_master_merged = df_uit_master.merge(df_vest_wholesalers, left_on=['State'], right_on=['State'], how='left')
     date_options = df_mf_sales_master['Month/Year (Asset Date)'].dt.strftime('%m-%Y').unique().tolist()
     
     # Filtered NNA
     #df3_nna = df_mf_master_merged[df_mf_master_merged['NNA'].notnull()]

     # Sorted NNA in descending order
     #df3 = df3.sort_values(by='NNA', ascending=False, na_position='last')

     # There will be a Selectbox that will allow the user to select a date to analyze. It will default to the most recent date
     date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1)

     # Filter the Original MF dataframe by keeping only the date the user selected 
     #selected_date_master = df_mf_master[df_mf_master['Month/Year (Asset Date)'] == pd.to_datetime(date_select + "-01",format='%m-%Y-%d')]
     #selected_prev_date_master = df_mf_master[df_mf_master['Month/Year (Asset Date)'] == (pd.to_datetime(date_select + "-01",format='%m-%Y-%d') - pd.DateOffset(months=1))]

     # Filter the date on the merged table as well. We will use this table for wholesaler filter
     selected_date_mf_master = df_mf_sales_master[df_mf_sales_master['Month/Year (Asset Date)'] == pd.to_datetime(date_select + "-01",format='%m-%Y-%d')]
     selected_prev_date_mf_master = df_mf_sales_master[df_mf_sales_master['Month/Year (Asset Date)'] == (pd.to_datetime(date_select + "-01",format='%m-%Y-%d') - pd.DateOffset(months=1))]
     selected_date_etf_master = df_etf_master[df_etf_master['Date'] == pd.to_datetime(date_select + "-01",format='%m-%Y-%d')]
     selected_prev_date_etf_master = df_etf_master[df_etf_master['Date'] == (pd.to_datetime(date_select + "-01",format='%m-%Y-%d') - pd.DateOffset(months=1))]
     selected_date_uit_master = df_uit_master_merged[df_uit_master_merged['Date'] == pd.to_datetime(date_select + "-01",format='%m-%Y-%d')]
     selected_prev_date_uit_master = df_uit_master_merged[df_uit_master_merged['Date'] == (pd.to_datetime(date_select + "-01",format='%m-%Y-%d') - pd.DateOffset(months=1))]

     # Create tabs that will be based on each wholesaler
     firm, capizzi, torok, mortimer, poggi, sullivan, unknown = st.tabs(['Firm', 'Capizzi', 'Torok', 'Mortimer', 'Poggi', 'Sullivan','Unknown'])
     
     # Calculate Total Firm AUM
     selected_date_mf_AUM = selected_date_mf_master['AUM'].sum()
     selected_date_etf_AUM = selected_date_etf_master['AUM'].sum()
     selected_date_uit_AUM = selected_date_uit_master['AUM'].sum()
     total_firm_aum = selected_date_mf_AUM + selected_date_etf_AUM + selected_date_uit_AUM

     # Firm Wide Tab
     with firm:
          
          # Create the headers
          st.header(f"Overall Firm Summary (AUM {format_dollar_amount(total_firm_aum)})")
          st.write(f"As of {date_select}")
          col1, col2 = st.columns(2)
          
          # Calculate total AUM
          #selected_date_AUM = df3_selected_month['AUM'].sum()
          #selected_prev_date_AUM = df3_previous_month['AUM'].sum()
          #selected_date_mf_AUM = selected_date_mf_master['AUM'].sum()
          selected_prev_date_mf_AUM = selected_prev_date_mf_master['AUM'].sum()
          change_in_AUM = selected_date_mf_AUM - selected_prev_date_mf_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_mf_AUM), format_dollar_amount(change_in_AUM))
          col1.caption("Month Over Month Change")

          # Calculate total NNA by filtering from the master table all blank values in the NNA column
          # then we create a new dataframe and use this to get NNA
          selected_date_NNA = selected_date_mf_master['NNA'].sum()
          selected_prev_date_NNA = selected_prev_date_mf_master['NNA'].sum()
          change_in_NNA = selected_date_NNA - selected_prev_date_NNA
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          # Calculate ETF Assets for Firm and display
          etf_firm, uit_firm = st.columns(2)
          #selected_date_etf_AUM = selected_date_etf_master['AUM'].sum()
          selected_prev_date_etf_AUM = selected_prev_date_etf_master['AUM'].sum()
          change_in_AUM = selected_date_etf_AUM - selected_prev_date_etf_AUM
          etf_firm.metric("Total ETF AUM", format_dollar_amount(selected_date_etf_AUM), format_dollar_amount(change_in_AUM))
          etf_firm.caption("Month Over Month Change")
          
          # Calculate UIT Assets for Firm and display
          #selected_date_uit_AUM = selected_date_uit_master['Princ Amt'].sum()
          selected_prev_date_uit_AUM = selected_prev_date_uit_master['AUM'].sum()
          change_in_AUM = selected_date_uit_AUM - selected_prev_date_uit_AUM
          uit_firm.metric("Total UIT AUM", format_dollar_amount(selected_date_uit_AUM), format_dollar_amount(change_in_AUM))
          uit_firm.caption("Month Over Month Change")
          
          st.markdown("""---""")
          
          mf_line_col, mf_bar_col, mf_bar_by_ticker = st.columns(3)
          
          with mf_line_col:
               mf_line_col.subheader("Mutual Fund Assets Over Time")
               st.line_chart(df_mf_sales_master.groupby(['Month/Year (Asset Date)'], as_index=False).sum(), x='Month/Year (Asset Date)', y='AUM')
          with mf_bar_col:
               mf_bar_col.subheader("Mutual Fund Assets By Wholesaler")
               st.bar_chart(selected_date_mf_master[['Vest Wholesaler','AUM']].groupby(['Vest Wholesaler'], as_index=False).sum(), x='Vest Wholesaler', y='AUM')
          with mf_bar_by_ticker:
               mf_bar_by_ticker.subheader("Mutual Fund Assets By Product")
               st.bar_chart(selected_date_mf_master[['Client Defined Category Name','AUM']].groupby(['Client Defined Category Name'], as_index=False).sum(), x='Client Defined Category Name', y='AUM')
          
          etf_line_col, etf_bar_col, etf_bar_by_ticker = st.columns(3)
          
          with etf_line_col:
               etf_line_col.subheader("ETF Assets Over Time")
               st.line_chart(df_etf_master.groupby(['Date'], as_index=False).sum(), x='Date', y='AUM')
          with etf_bar_col:
               etf_bar_col.subheader("ETF Assets By Wholesaler")
               st.bar_chart(selected_date_etf_master[['Vest Wholesaler','AUM']].groupby(['Vest Wholesaler'], as_index=False).sum(), x='Vest Wholesaler', y='AUM')
          with etf_bar_by_ticker:
               etf_bar_by_ticker.subheader("ETF Assets By Ticker")
               st.bar_chart(selected_date_etf_master[['Ticker','AUM']].groupby(['Ticker'], as_index=False).sum(), x='Ticker', y='AUM')
               
          uit_line_col, uit_bar_col, uit_bar_by_ticker = st.columns(3)
          
          with uit_line_col:
               uit_line_col.subheader("UIT Assets Over Time")
               st.line_chart(df_uit_master_merged.groupby(['Date'], as_index=False).sum(), x='Date', y='AUM')
          with uit_bar_col:
               uit_bar_col.subheader("UIT Assets By Wholesaler")
               st.bar_chart(selected_date_uit_master[['Wholesaler','AUM']].groupby(['Wholesaler'], as_index=False).sum(), x='Wholesaler', y='AUM')
          with uit_bar_by_ticker:
               uit_bar_by_ticker.subheader("UIT Assets By Ticker")
               st.bar_chart(selected_date_uit_master[['Ticker','AUM']].groupby(['Ticker'], as_index=False).sum(), x='Ticker', y='AUM')
               
          
               
          

     # Capizzi Tab     
     with capizzi:
          # Create the headers
          st.header("Capizzi Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_mf_master[selected_date_mf_master['Vest Wholesaler'].str.contains('Capizzi', na=False)]
          df_mf_cohort_master_by_wholesaler = df_mf_cohort_master[df_mf_cohort_master['Vest'].str.contains('Capizzi', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_mf_master[selected_prev_date_mf_master['Vest Wholesaler'].str.contains('Capizzi', na=False)]
          selected_date_AUM = selected_date_df3_master_by_wholesaler['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_df3_master_by_wholesaler['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption('Month Over Month Change')
          
          # Net New Assets Calculations
          selected_date_NNA = selected_date_df3_master_by_wholesaler[selected_date_df3_master_by_wholesaler['NNA'].notnull()]
          selected_prev_date_NNA = selected_prev_date_df3_master_by_wholesaler[selected_prev_date_df3_master_by_wholesaler['NNA'].notnull()]
          change_in_NNA = selected_date_NNA['NNA'].sum() - selected_prev_date_NNA['NNA'].sum()
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA['NNA'].sum()), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          #st.subheader("Metrics")
          #zizi_mf_line, zizi_mf_bar = st.columns(2)
          
          st.markdown("""---""")
          
          st.subheader('Top 20 Clients')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%',key='capizzi20')
          
          st.subheader('Top 10 Inflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')

     # Torok Tab     
     with torok:
          # Create the headers
          st.header("Torok Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_mf_master[selected_date_mf_master['Vest Wholesaler'].str.contains('Torok', na=False)]
          df_mf_cohort_master_by_wholesaler = df_mf_cohort_master[df_mf_cohort_master['Vest'].str.contains('Torok', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_mf_master[selected_prev_date_mf_master['Vest Wholesaler'].str.contains('Torok', na=False)]
          selected_date_AUM = selected_date_df3_master_by_wholesaler['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_df3_master_by_wholesaler['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption('Month Over Month Change')
          
          # Net New Assets Calculations
          selected_date_NNA = selected_date_df3_master_by_wholesaler[selected_date_df3_master_by_wholesaler['NNA'].notnull()]
          selected_prev_date_NNA = selected_prev_date_df3_master_by_wholesaler[selected_prev_date_df3_master_by_wholesaler['NNA'].notnull()]
          change_in_NNA = selected_date_NNA['NNA'].sum() - selected_prev_date_NNA['NNA'].sum()
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA['NNA'].sum()), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          #st.subheader("Metrics")
          #zizi_mf_line, zizi_mf_bar = st.columns(2)
          
          st.markdown("""---""")
          
          st.subheader('Top 20 Clients')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%',key='torok20')
          
          st.subheader('Top 10 Inflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')


     # Morti Tab     
     with mortimer:
          # Create the headers
          st.header("Mortimer Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_mf_master[selected_date_mf_master['Vest Wholesaler'].str.contains('Morti', na=False)]
          df_mf_cohort_master_by_wholesaler = df_mf_cohort_master[df_mf_cohort_master['Vest'].str.contains('Morti', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_mf_master[selected_prev_date_mf_master['Vest Wholesaler'].str.contains('Morti', na=False)]
          selected_date_AUM = selected_date_df3_master_by_wholesaler['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_df3_master_by_wholesaler['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption('Month Over Month Change')
          
          # Net New Assets Calculations
          selected_date_NNA = selected_date_df3_master_by_wholesaler[selected_date_df3_master_by_wholesaler['NNA'].notnull()]
          selected_prev_date_NNA = selected_prev_date_df3_master_by_wholesaler[selected_prev_date_df3_master_by_wholesaler['NNA'].notnull()]
          change_in_NNA = selected_date_NNA['NNA'].sum() - selected_prev_date_NNA['NNA'].sum()
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA['NNA'].sum()), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          st.markdown("""---""")
          
          st.subheader('Top 20 Clients')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%',key='mortimer20')
          
          st.subheader('Top 10 Inflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%',key='mortimer_top_10_inflow')
          
          st.subheader('Top 10 Outflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%',key='mortimer_top_10_outflow')
          
     # Poggi Tab     
     with poggi:
          # Create the headers
          st.header("Poggi Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_mf_master[selected_date_mf_master['Vest Wholesaler'].str.contains('Poggi', na=False)]
          df_mf_cohort_master_by_wholesaler = df_mf_cohort_master[df_mf_cohort_master['Vest'].str.contains('Poggi', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_mf_master[selected_prev_date_mf_master['Vest Wholesaler'].str.contains('Poggi', na=False)]
          selected_date_AUM = selected_date_df3_master_by_wholesaler['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_df3_master_by_wholesaler['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption('Month Over Month Change')
          
          # Net New Assets Calculations
          selected_date_NNA = selected_date_df3_master_by_wholesaler[selected_date_df3_master_by_wholesaler['NNA'].notnull()]
          selected_prev_date_NNA = selected_prev_date_df3_master_by_wholesaler[selected_prev_date_df3_master_by_wholesaler['NNA'].notnull()]
          change_in_NNA = selected_date_NNA['NNA'].sum() - selected_prev_date_NNA['NNA'].sum()
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA['NNA'].sum()), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          st.markdown("""---""")
          
          st.subheader('Top 20 Clients')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')
          
     # Sullivan Tab     
     with sullivan:
          # Create the headers
          st.header("Sullivan Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_mf_master[selected_date_mf_master['Vest Wholesaler'].str.contains('Sullivan', na=False)]
          df_mf_cohort_master_by_wholesaler = df_mf_cohort_master[df_mf_cohort_master['Vest'].str.contains('Sullivan', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_mf_master[selected_prev_date_mf_master['Vest Wholesaler'].str.contains('Sullivan', na=False)]
          selected_date_AUM = selected_date_df3_master_by_wholesaler['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_df3_master_by_wholesaler['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption('Month Over Month Change')
          
          # Net New Assets Calculations
          selected_date_NNA = selected_date_df3_master_by_wholesaler[selected_date_df3_master_by_wholesaler['NNA'].notnull()]
          selected_prev_date_NNA = selected_prev_date_df3_master_by_wholesaler[selected_prev_date_df3_master_by_wholesaler['NNA'].notnull()]
          change_in_NNA = selected_date_NNA['NNA'].sum() - selected_prev_date_NNA['NNA'].sum()
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA['NNA'].sum()), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          st.markdown("""---""")
          
          st.subheader('Top 20 Clients')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')
          
     # Unknown Tab     
     with unknown:
          # Create the headers
          st.header("Unknown Region Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_mf_master[selected_date_mf_master['Vest Wholesaler'].isnull()]
          df_mf_cohort_master_by_wholesaler = df_mf_cohort_master[df_mf_cohort_master['Vest'].isnull()]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_mf_master[selected_prev_date_mf_master['Vest Wholesaler'].isnull()]
          selected_date_AUM = selected_date_df3_master_by_wholesaler['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_df3_master_by_wholesaler['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption('Month Over Month Change')
          
          # Net New Assets Calculations
          selected_date_NNA = selected_date_df3_master_by_wholesaler[selected_date_df3_master_by_wholesaler['NNA'].notnull()]
          selected_prev_date_NNA = selected_prev_date_df3_master_by_wholesaler[selected_prev_date_df3_master_by_wholesaler['NNA'].notnull()]
          change_in_NNA = selected_date_NNA['NNA'].sum() - selected_prev_date_NNA['NNA'].sum()
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA['NNA'].sum()), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          st.markdown("""---""")
          
          st.subheader('Top 20 Clients')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(df_mf_cohort_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                    'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                    'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')
