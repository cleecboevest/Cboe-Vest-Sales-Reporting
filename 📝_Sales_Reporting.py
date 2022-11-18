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

@st.cache
def load_mf_data(url):
     #----------READ IN DATA--------
     # Read in the Broadridge Data
     df_mf_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_mf_master

@st.cache
def load_vest_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_vest_wholesalers = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_vest_wholesalers

@st.cache     
def load_etf_data(url):
     #----------READ IN DATA--------
     # Read in the FT ETF Sales Data
     df_etf_master = pd.read_excel(url,engine='openpyxl',skiprows=0)
     return df_etf_master

@st.cache     
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
          df_mf_master = load_mf_data(st.secrets['broadridge_url'])
          df_etf_master = load_etf_data(st.secrets['etf_sales_url'])
          df_uit_master = load_uit_data(st.secrets['uit_sales_url'])
          df_vest_wholesalers = load_vest_wholesaler_data(st.secrets['vest_wholesaler_url'])

     # Load in the data and perform operations on the Dataframe
     # Merged Master_Table and Sheet1 into df3
     df_mf_master_merged = df_mf_master.merge(df_vest_wholesalers, left_on=['State/Region'], right_on=['State'], how='inner')
     df_etf_master_merged = df_etf_master.merge(df_vest_wholesalers, left_on=['State'], right_on=['State'], how='inner')
     df_uit_master_merged = df_uit_master.merge(df_vest_wholesalers, left_on=['Office State'], right_on=['State'], how='inner')
     date_options = df_mf_master['Month/Year (Asset Date)'].dt.strftime('%m-%Y').unique().tolist()

     # Filtered NNA
     df3_nna = df_mf_master_merged[df_mf_master_merged['NNA'].notnull()]

     # Sorted NNA in descending order
     #df3 = df3.sort_values(by='NNA', ascending=False, na_position='last')

     # There will be a Selectbox that will allow the user to select a date to analyze. It will default to the most recent date
     date_select = st.selectbox('Please select the date you want to analyze sales data:', date_options, index=len(date_options)-1)

     # Filter the Original MF dataframe by keeping only the date the user selected 
     selected_date_master = df_mf_master[df_mf_master['Month/Year (Asset Date)'] == pd.to_datetime(date_select + "-01",format='%m-%Y-%d')]
     selected_prev_date_master = df_mf_master[df_mf_master['Month/Year (Asset Date)'] == (pd.to_datetime(date_select + "-01",format='%m-%Y-%d') - pd.DateOffset(months=1))]

     # Filter the date on the merged table as well. We will use this table for wholesaler filter
     selected_date_df3_master = df_mf_master_merged[df_mf_master_merged['Month/Year (Asset Date)'] == pd.to_datetime(date_select + "-01",format='%m-%Y-%d')]
     selected_prev_date_df3_master = df_mf_master_merged[df_mf_master_merged['Month/Year (Asset Date)'] == (pd.to_datetime(date_select + "-01",format='%m-%Y-%d') - pd.DateOffset(months=1))]


     # Create tabs that will be based on each wholesaler
     firm, capizzi, mortimer, poggi, sullivan = st.tabs(['Firm', 'Capizzi', 'Mortimer', 'Sullivan', 'Poggi'])

     # Firm Wide Tab
     with firm:
          # Create the headers
          st.header("Overall Firm Summary")
          col1, col2 = st.columns(2)
          
          # Calculate total AUM
          #selected_date_AUM = df3_selected_month['AUM'].sum()
          #selected_prev_date_AUM = df3_previous_month['AUM'].sum()
          selected_date_AUM = selected_date_master['AUM'].sum()
          selected_prev_date_AUM = selected_prev_date_master['AUM'].sum()
          change_in_AUM = selected_date_AUM - selected_prev_date_AUM
          col1.metric("Total Mutual Funds AUM", format_dollar_amount(selected_date_AUM), format_dollar_amount(change_in_AUM))
          col1.caption("Month Over Month Change")

          # Calculate total NNA by filtering from the master table all blank values in the NNA column
          # then we create a new dataframe and use this to get NNA
          selected_date_NNA = selected_date_master[selected_date_master['NNA'].notnull()]['NNA'].sum()
          selected_prev_date_NNA = selected_prev_date_master[selected_prev_date_master['NNA'].notnull()]['NNA'].sum()
          change_in_NNA = selected_date_NNA - selected_prev_date_NNA
          col2.metric("Total Mutual Funds NNA", format_dollar_amount(selected_date_NNA), format_dollar_amount(change_in_NNA))
          col2.caption("Month Over Month Change")
          
          st.markdown("""---""")
          
          line_col, bar_col = st.columns(2)
          
          with line_col:
               st.line_chart(df_mf_master.groupby(['Month/Year (Asset Date)'], as_index=False).sum(), x='Month/Year (Asset Date)', y='AUM')
          with bar_col:
               st.bar_chart(df_mf_master_merged.where(df_mf_master_merged['Month/Year (Asset Date)'] == date_select).groupby(['Wholesaler'], as_index=False).sum(), x='Wholesaler', y='AUM')
          

     # Capizzi Tab     
     with capizzi:
          # Create the headers
          st.header("Capizzi Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_df3_master[selected_date_df3_master['Wholesaler'].str.contains('Capizzi', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_df3_master[selected_prev_date_df3_master['Wholesaler'].str.contains('Capizzi', na=False)]
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
          
          st.subheader('Top 20 Clients')
          AgGrid(selected_date_df3_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')

     # Morti Tab     
     with mortimer:
          # Create the headers
          st.header("Capizzi Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_df3_master[selected_date_df3_master['Wholesaler'].str.contains('Mortimer', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_df3_master[selected_prev_date_df3_master['Wholesaler'].str.contains('Mortimer', na=False)]
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
          
          st.subheader('Top 20 Clients')
          AgGrid(selected_date_df3_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')
          
     # Sullivan Tab     
     with sullivan:
          # Create the headers
          st.header("Sullivan Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_df3_master[selected_date_df3_master['Wholesaler'].str.contains('Sullivan', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_df3_master[selected_prev_date_df3_master['Wholesaler'].str.contains('Sullivan', na=False)]
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
          
          st.subheader('Top 20 Clients')
          AgGrid(selected_date_df3_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')
          
     # Poggi Tab     
     with poggi:
          # Create the headers
          st.header("Poggi Summary")
          col1, col2 = st.columns(2)
          
          # Filtered Wholesaler to calculate the AUM
          selected_date_df3_master_by_wholesaler = selected_date_df3_master[selected_date_df3_master['Wholesaler'].str.contains('Poggi', na=False)]
          selected_prev_date_df3_master_by_wholesaler = selected_prev_date_df3_master[selected_prev_date_df3_master['Wholesaler'].str.contains('Poggi', na=False)]
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
          
          st.subheader('Top 20 Clients')
          AgGrid(selected_date_df3_master_by_wholesaler[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                                       'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                                       'NNA']].sort_values(by=['AUM'], ascending=False).head(20),
               width='100%')
          
          st.subheader('Top 10 Inflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=False).head(10),
               width='100%')
          
          st.subheader('Top 10 Outflows')
          AgGrid(selected_date_NNA[['Intermediary Firm Name', 'Initiating Firm Name', 'Address Line 1', 'Address Line 2',
                                   'City', 'State/Region', 'Postal Code', 'Client Defined Category Name', 'AUM', 
                                   'NNA']].sort_values(by=['NNA'], ascending=True).head(10),
               width='100%')