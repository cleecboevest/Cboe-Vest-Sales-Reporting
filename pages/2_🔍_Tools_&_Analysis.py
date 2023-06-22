from datetime import datetime
from click import style
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, AgGridTheme, GridUpdateMode

from pathlib import Path
import yaml
from yaml import SafeLoader
import streamlit_authenticator as stauth

def format_dollar_amount(amount):
    formatted_absolute_amount = '${:,.2f}'.format(abs(amount))
    if round(amount, 2) < 0:
        return f'-{formatted_absolute_amount}'
    return formatted_absolute_amount

def format_headers(df):
     df['AUM'] = df['AUM'].apply(lambda x: format_dollar_amount(x))
     #df['Industry AUM'] = df['Industry AUM'].apply(lambda x: format_dollar_amount(x))
     #df['NNA'] = df['NNA'].apply(lambda x: format_dollar_amount(x))
     #df['Industry NNA'] = df['Industry NNA'].apply(lambda x: format_dollar_amount(x))
     return df

def format_ticker_headers(df):
     for column in df:
          df[column] = df[column].apply(lambda x: format_dollar_amount(x))
     #df['Industry AUM'] = df['Industry AUM'].apply(lambda x: format_dollar_amount(x))
     #df['NNA'] = df['NNA'].apply(lambda x: format_dollar_amount(x))
     #df['Industry NNA'] = df['Industry NNA'].apply(lambda x: format_dollar_amount(x))
     return df

@st.cache_data(ttl=21*24*3600)
def load_vest_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_vest_wholesalers = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_vest_wholesalers

@st.cache_data(ttl=21*24*3600)
def load_ft_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_ft_wholesalers = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_ft_wholesalers

@st.cache_data(ttl=21*24*3600)
def load_etf_analyzer_data(url):
     #----------READ IN DATA--------
     # Read in the FT ETF Sales Data
     df_etf_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_etf_master

@st.cache_data(ttl=21*24*3600)
def load_uit_data(url):
     #----------READ IN DATA--------
     # Read in the FT UIT Sales Data
     df_uit_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_uit_master

#---------- SETTINGS ----------
page_title = "FT Sales Intelligence"
page_icon = ":money_with_wings:"
layout = "wide"
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout)

#-------------- USER AUTHENTICATION ----------

# load config file
file_path = Path(__file__).parents[1] / "config.yaml"
with file_path.open("rb") as file:
     config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
     config['credentials'],
     config['cookie']['name'],
     config['cookie']['key'],
     config['cookie']['expiry_days'],
     config['preauthorized']
)

name, authentication_status, username = authenticator.login("Login", "main")

if 'authentication_status' not in st.session_state:
     st.session_state['authentication_status'] = authentication_status
     
if authentication_status == False:
     st.error("Username or password is incorrect.")
     
if authentication_status == None:
     st.warning("Please enter your username and password.")

# If authenticated, then start the app     
if authentication_status == True:
    # Render logout button
     authenticator.logout("Logout", "sidebar")
     st.sidebar.title(f"Welcome {name}!")
     
     #----------STATUS MESSAGE------
     with st.spinner('Loading All Sales Data. This May Take A Minute. Please wait...'):
          df_etf_master = load_etf_analyzer_data(st.secrets['etf_analyzer_url'])
          df_uit_master = load_uit_data(st.secrets['uit_sales_url'])
          df_ft_wholesalers = load_ft_wholesaler_data(st.secrets['ft_wholesaler_url'])
          df_vest_wholesalers = load_vest_wholesaler_data(st.secrets['vest_wholesaler_url'])
     
     # Merge all FT and Vest Wholesalers together     
     df_wholesaler_merged = df_ft_wholesalers.merge(df_vest_wholesalers,left_on='State',right_on='State',how='left')
     # Then merge all wholesalers list with the ETF and UIT data to create a master table by clients and wholesalers
     #df_etf_master_merged = df_etf_master.merge(df_wholesaler_merged, left_on=['Zip'], right_on=['Zip'], how='left').rename(columns={'City_x':'City','State_x':'State'})
     df_uit_master_merged = df_uit_master.merge(df_wholesaler_merged, left_on=['Zip'], right_on=['Zip'], how='left').rename(columns={'City_x':'City','State_x':'State'})
     
     df_buffer_etf_master = df_etf_master[df_etf_master['Ticker'].isin(st.secrets['buffer_etf_tickers'])]
     df_target_income_etf_master = df_etf_master[df_etf_master['Ticker'].isin(st.secrets['target_income_etf_tickers'])]
     
     etf_ticker_options = df_etf_master['Ticker'].sort_values().unique().tolist()
     date_options = df_etf_master['Date'].dt.strftime('%m-%Y').unique().tolist()
     sp_wholesaler_options = df_etf_master['SP Outsider'].sort_values().unique().tolist()
     etf_wholesaler_options = df_etf_master['ETF Outsider'].sort_values().unique().tolist()
     uit_wholesaler_options = df_etf_master['COM Outsider'].sort_values().unique().tolist()
     vest_wholesaler_options = df_etf_master['Wholesaler'].sort_values().unique().tolist()
     
     etf_df_headers = ['Account','Sub Acct Name','Office Address','City','State','Zip','Ticker','AUM','SP Outsider','ETF Outsider','COM Outsider','Wholesaler']
     uit_df_headers = ['Account','Sub Acct Name','Office Address','City','State','Zip','Ticker','AUM','COM Outsider','SP Outsider','ETF Outsider','Wholesaler']
     
     st.subheader("Wholesaler Ranking")
     with st.expander('Wholesaler Ranking'):
          date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1, key='wholesaler ranking select')
          wholesaler_type_select = st.radio("Choose what type of wholesaler you want to rank:", ('Structured','ETF','UIT'), help='Select one or the other to show that type of ranking')
          show_vest_wholesalers = st.checkbox("Filter by Vest Wholesaler",help='Select this box if you want to filter by a certain Vest Wholesaler')
          vest_wholesaler_select = False
          
          if wholesaler_type_select == "ETF":
               split_columns_by_ticker = st.checkbox("Split Columns By Ticker",help='Select this box if you want to split columns by ticker to help rank by ticker.')
          if show_vest_wholesalers:
               vest_wholesaler_select = st.selectbox("Please select the Vest Wholesaler:", vest_wholesaler_options)
          #else:
          #     vest_wholesaler_select = False
          
          # Submit button and then perform operation on data based on the conditions
          if st.button("Submit", key='update_ranking'):
               if wholesaler_type_select == 'Structured':
                    if vest_wholesaler_select:
                         df_wholesaler_rank = df_buffer_etf_master.where((df_buffer_etf_master['Date'] == date_select) & (df_buffer_etf_master['Wholesaler'] == vest_wholesaler_select)).groupby(['SP Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False, ignore_index=True)
                    else:
                         df_wholesaler_rank = df_buffer_etf_master.where((df_buffer_etf_master['Date'] == date_select) & (df_buffer_etf_master['Ticker'].isin(st.secrets['buffer_etf_tickers']))).groupby(['SP Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False, ignore_index=True)
               elif wholesaler_type_select == 'ETF':
                    if vest_wholesaler_select:
                         if split_columns_by_ticker:
                              df_wholesaler_rank = df_target_income_etf_master.where((df_target_income_etf_master['Wholesaler'] == vest_wholesaler_select) & df_target_income_etf_master['Ticker'].isin(st.secrets['target_income_etf_tickers'])).groupby(['ETF Outsider','Ticker','Wholesaler'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False).pivot(index='ETF Outsider',columns='Ticker',values='AUM')
                         else:
                              df_wholesaler_rank = df_target_income_etf_master.where((df_target_income_etf_master['Wholesaler'] == vest_wholesaler_select) & df_target_income_etf_master['Ticker'].isin(st.secrets['target_income_etf_tickers'])).groupby(['ETF Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False, ignore_index=True)
                    elif split_columns_by_ticker:
                         df_wholesaler_rank = df_target_income_etf_master.where(df_target_income_etf_master['Ticker'].isin(st.secrets['target_income_etf_tickers'])).groupby(['ETF Outsider', 'Wholesaler', 'Ticker'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False).pivot(index=['ETF Outsider', 'Wholesaler'], columns='Ticker', values='AUM')
                         for column in df_wholesaler_rank:
                              df_wholesaler_rank[column].astype(float)
                         #df_wholesaler_rank = format_ticker_headers(df_wholesaler_rank)
                         #df_wholesaler_rank.insert(0, 'ETF Outsider', df_wholesaler_rank.index)
                    else:     
                         df_wholesaler_rank = df_target_income_etf_master.where((df_target_income_etf_master['Date'] == date_select) & df_target_income_etf_master['Ticker'].isin(st.secrets['target_income_etf_tickers'])).groupby(['ETF Outsider','Wholesaler'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False, ignore_index=True)
               else:
                    if vest_wholesaler_select:
                         df_wholesaler_rank = df_uit_master_merged.where((df_uit_master_merged['Date'] == date_select) & (df_uit_master_merged['Wholesaler'] == vest_wholesaler_select)).groupby(['COM Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False)
                    else:     
                         df_wholesaler_rank = df_uit_master_merged.where((df_uit_master_merged['Date'] == date_select)).groupby(['COM Outsider','Wholesaler'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False)
               #df_wholesaler_rank['AUM'] = df_wholesaler_rank['AUM'].apply(lambda x: format_dollar_amount(x))
               try:
                    updated_df = format_headers(df_wholesaler_rank)
               except:
                    updated_df = df_wholesaler_rank
               
               # Configure the AG-Grid options to better display the data
               gb = GridOptionsBuilder.from_dataframe(updated_df)
               
               # Build the columns
               gb.configure_default_column(
                    resizable=True,
                    filterable=True,
                    sortable=True,
                    editable=False,)               
               
               gb.configure_pagination(paginationPageSize=100)
               gridOptions = gb.build()
               
               #output = AgGrid(
               #     updated_df,
               #     gridOptions=gridOptions,
               #     columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW,
               #     theme=AgGridTheme.ALPINE,
               #     update_mode=GridUpdateMode.SELECTION_CHANGED
               #     )        
               
               st.dataframe(df_wholesaler_rank)  
                    
     #with st.expander('ETF Wholesaler Ranking'):
     #     with st.form('ETF Wholesaler Rank Form'):
     #     
     #          date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1, key='etf wholesaler ranking select')
     #          submitted = st.form_submit_button("Submit")
     #
     #          if submitted:
     #               df_sp_wholesaler_rank = df_target_income_etf_master_merged.where(df_target_income_etf_master_merged['Date'] == date_select).groupby(['ETF Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False)
     #               df_sp_wholesaler_rank['AUM'] = df_sp_wholesaler_rank['AUM'].apply(lambda x: format_dollar_amount(x))
     #               AgGrid(df_sp_wholesaler_rank)
                    
     st.subheader("Analyze By Ticker")
     with st.expander('Clients By ETF Ticker'):
          with st.form('Clients By ETF Ticker'):
          
               date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1, key='clients by etf')
               #sp_wholesaler_select = st.selectbox('Please Select the External SP Wholesaler:', sp_wholesaler_options)
               etf_ticker_select = st.selectbox('Please select the ticker you want to analyze sales data:', etf_ticker_options)
               submitted = st.form_submit_button("Submit")
               

               if submitted:
                    df_clients_by_ticker = df_etf_master[df_etf_master['Ticker'].isin([etf_ticker_select])].where(df_etf_master['Date'] == date_select).sort_values(by=['AUM'], ascending=False)[etf_df_headers].fillna('').head(100)
                    df_clients_by_ticker['AUM'] = df_clients_by_ticker['AUM'].apply(lambda x: format_dollar_amount(x))
                    AgGrid(df_clients_by_ticker)
                    
     with st.expander('Clients By ETF Ticker and Wholesaler'):
          date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1, key='clients by etf and wholesaler select')
          etf_ticker_select = st.selectbox('Please select the ticker you want to analyze sales data:', etf_ticker_options)
          
          
          if etf_ticker_select in st.secrets['buffer_etf_tickers']:
               if 'sp_wholesaler' not in st.session_state:
                    st.session_state['sp_wholesaler'] =  True
               st.session_state['sp_wholesaler'] = True
               wholesaler_options = sp_wholesaler_options
          else:
               if 'sp_wholesaler' not in st.session_state:
                    st.session_state['sp_wholesaler'] =  False
               st.session_state['sp_wholesaler'] = False
               wholesaler_options = etf_wholesaler_options

          wholesaler_select = st.selectbox('Please Select the External Wholesaler:', wholesaler_options)
          
          
          #submitted = st.form_submit_button("Submit")
          

          if st.button('Submit', key='clients by etf and wholesaler button'):
               if st.session_state['sp_wholesaler']:
                    df_by_client_and_wholesaler = df_buffer_etf_master[df_buffer_etf_master['Ticker'].isin([etf_ticker_select])].where((df_buffer_etf_master['Date'] == date_select) & (df_buffer_etf_master['SP Outsider'] == wholesaler_select)).sort_values(by=['AUM'], ascending=False)[etf_df_headers].dropna(how='all')
               else:
                    df_by_client_and_wholesaler = df_target_income_etf_master[df_target_income_etf_master['Ticker'].isin([etf_ticker_select])].where((df_target_income_etf_master['Date'] == date_select) & (df_target_income_etf_master['SP Outsider'] == wholesaler_select)).sort_values(by=['AUM'], ascending=False)[etf_df_headers].dropna(how='all')
               df_by_client_and_wholesaler['AUM'] = df_by_client_and_wholesaler['AUM'].apply(lambda x: format_dollar_amount(x))
               AgGrid(df_by_client_and_wholesaler)
     
     # Analyze UITs by Wholesaler          
     with st.expander('Clients By UIT'):
          with st.form('Clients By UIT'):
          
               date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1, key='clients by uit')
               #sp_wholesaler_select = st.selectbox('Please Select the External SP Wholesaler:', sp_wholesaler_options)
               #etf_ticker_select = st.selectbox('Please select the ticker you want to analyze sales data:', etf_ticker_options)
               submitted = st.form_submit_button("Submit")
               

               if submitted:
                    df_clients = df_uit_master_merged.where(df_uit_master_merged['Date'] == date_select).sort_values(by=['AUM'], ascending=False)[uit_df_headers].fillna('')
                    #df_clients['AUM'] = df_clients['AUM'].apply(lambda x: format_dollar_amount(x))
                    AgGrid(df_clients)