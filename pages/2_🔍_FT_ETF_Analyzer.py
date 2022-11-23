from datetime import datetime
from click import style
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid

from pathlib import Path
import yaml
from yaml import SafeLoader
import streamlit_authenticator as stauth

def format_dollar_amount(amount):
    formatted_absolute_amount = '${:,.2f}'.format(abs(amount))
    if round(amount, 2) < 0:
        return f'-{formatted_absolute_amount}'
    return formatted_absolute_amount

@st.cache
def load_vest_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_vest_wholesalers = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_vest_wholesalers

@st.cache
def load_ft_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_ft_wholesalers = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_ft_wholesalers

@st.cache     
def load_etf_data(url):
     #----------READ IN DATA--------
     # Read in the FT ETF Sales Data
     df_etf_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_etf_master

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
          df_etf_master = load_etf_data(st.secrets['etf_sales_url'])
          df_ft_wholesalers = load_vest_wholesaler_data(st.secrets['ft_wholesaler_url'])
          
     df_etf_master_merged = df_etf_master.merge(df_ft_wholesalers, left_on=['Zip'], right_on=['Zip'], how='left').rename(columns={'City_x':'City','State_x':'State'})
     
     df_buffer_etf_master_merged = df_etf_master_merged[df_etf_master_merged['Ticker'].isin(st.secrets['buffer_etf_tickers'])]
     df_target_income_etf_master_merged = df_etf_master_merged[df_etf_master_merged['Ticker'].isin(st.secrets['target_income_etf_tickers'])]
     
     etf_ticker_options = df_etf_master_merged['Ticker'].sort_values().unique().tolist()
     date_options = df_etf_master_merged['Date'].dt.strftime('%m-%Y').unique().tolist()
     sp_wholesaler_options = df_etf_master_merged['SP Outsider'].unique().tolist()
     etf_wholesaler_options = df_etf_master_merged['ETF Outsider'].unique().tolist()
     uit_wholesaler_options = df_etf_master_merged['COM Outsider'].unique().tolist()
     
     etf_df_headers = ['Account','Sub Acct Name','Office Address','City','State','Zip','Ticker','AUM','SP Outsider','ETF Outsider','COM Outsider']
     
     st.subheader("Wholesaler Ranking")
     with st.expander('SP Wholesaler Ranking'):
          with st.form('SP Wholesaler Rank Form'):
          
               date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1)
               #sp_wholesaler_select = st.selectbox('Please Select the External SP Wholesaler:', sp_wholesaler_options)
               submitted = st.form_submit_button("Submit")

               if submitted:
                    df_sp_wholesaler_rank = df_buffer_etf_master_merged.where(df_buffer_etf_master_merged['Date'] == date_select).groupby(['SP Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False)
                    df_sp_wholesaler_rank['AUM'] = df_sp_wholesaler_rank['AUM'].apply(lambda x: format_dollar_amount(x))
                    AgGrid(df_sp_wholesaler_rank)
                    
     with st.expander('ETF Wholesaler Ranking'):
          with st.form('ETF Wholesaler Rank Form'):
          
               date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1)
               #sp_wholesaler_select = st.selectbox('Please Select the External SP Wholesaler:', sp_wholesaler_options)
               submitted = st.form_submit_button("Submit")

               if submitted:
                    df_sp_wholesaler_rank = df_target_income_etf_master_merged.where(df_target_income_etf_master_merged['Date'] == date_select).groupby(['ETF Outsider'], as_index=False)['AUM'].sum().sort_values(by=['AUM'],ascending=False)
                    df_sp_wholesaler_rank['AUM'] = df_sp_wholesaler_rank['AUM'].apply(lambda x: format_dollar_amount(x))
                    AgGrid(df_sp_wholesaler_rank)
                    
     st.subheader("Analyze By Ticker")
     with st.expander('Clients By ETF Ticker'):
          with st.form('Clients By ETF Ticker'):
          
               date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1)
               #sp_wholesaler_select = st.selectbox('Please Select the External SP Wholesaler:', sp_wholesaler_options)
               etf_ticker_select = st.selectbox('Please select the ticker you want to analyze sales data:', etf_ticker_options)
               submitted = st.form_submit_button("Submit")
               

               if submitted:
                    df_clients_by_ticker = df_etf_master_merged[df_etf_master_merged['Ticker'].isin([etf_ticker_select])].where(df_etf_master_merged['Date'] == date_select).sort_values(by=['AUM'], ascending=False)[etf_df_headers].fillna('').head(100)
                    df_clients_by_ticker['AUM'] = df_clients_by_ticker['AUM'].apply(lambda x: format_dollar_amount(x))
                    AgGrid(df_clients_by_ticker)
                    
     with st.expander('Clients By ETF Ticker and Wholesaler'):
          date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1)
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
          

          if st.button('Submit'):
               if st.session_state['sp_wholesaler']:
                    df_by_client_and_wholesaler = df_buffer_etf_master_merged[df_buffer_etf_master_merged['Ticker'].isin([etf_ticker_select])].where((df_buffer_etf_master_merged['Date'] == date_select) & (df_buffer_etf_master_merged['SP Outsider'] == wholesaler_select)).sort_values(by=['AUM'], ascending=False)[etf_df_headers].dropna(how='all')
               else:
                    df_by_client_and_wholesaler = df_target_income_etf_master_merged[df_target_income_etf_master_merged['Ticker'].isin([etf_ticker_select])].where((df_target_income_etf_master_merged['Date'] == date_select) & (df_target_income_etf_master_merged['SP Outsider'] == wholesaler_select)).sort_values(by=['AUM'], ascending=False)[etf_df_headers].dropna(how='all')
               df_by_client_and_wholesaler['AUM'] = df_by_client_and_wholesaler['AUM'].apply(lambda x: format_dollar_amount(x))
               AgGrid(df_by_client_and_wholesaler)
