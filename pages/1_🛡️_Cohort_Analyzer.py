from datetime import datetime
from click import style
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder, ColumnsAutoSizeMode, AgGridTheme

from pathlib import Path
import yaml
from yaml import SafeLoader
import streamlit_authenticator as stauth
import io
from streamlit_dynamic_filters import DynamicFilters



def format_dollar_amount(amount):
    formatted_absolute_amount = '${:,.2f}'.format(abs(amount))
    if round(amount, 2) < 0:
        return f'-{formatted_absolute_amount}'
    return formatted_absolute_amount

def format_headers(df):
     df['AUM'] = df['AUM'].apply(lambda x: format_dollar_amount(x))
     df['Industry AUM'] = df['Industry AUM'].apply(lambda x: format_dollar_amount(x))
     df['NNA'] = df['NNA'].apply(lambda x: format_dollar_amount(x))
     df['Industry NNA'] = df['Industry NNA'].apply(lambda x: format_dollar_amount(x))
     return df

def to_excel(df) -> bytes:
     output = io.BytesIO()
     writer = pd.ExcelWriter(output, engine="xlsxwriter")
     df.to_excel(writer, sheet_name="Sheet1")
     writer.close()
     processed_data = output.getvalue()
     return processed_data

@st.cache_data(ttl=21*24*3600)
def load_vest_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_vest_wholesalers = pd.read_excel(url,engine='openpyxl')
     return df_vest_wholesalers

@st.cache_data(ttl=21*24*3600)
def load_ft_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_ft_wholesalers = pd.read_excel(url,engine='openpyxl', dtype={'Zip': str})
     return df_ft_wholesalers

@st.cache_data(ttl=21*24*3600)
def load_mf_data(url):
     #----------READ IN DATA--------
     # Read in the Broadridge Data
     df_mf_master = pd.read_excel(url,engine='openpyxl', dtype={'Postal Code': str})
     return df_mf_master

@st.cache_data(ttl=21*24*3600)
def load_territory_data(url):
     #----------READ IN DATA--------
     # Read in the Wholesaler Territory Data
     df_territory_master = pd.read_csv(url, dtype={'Zip': str})
     return df_territory_master


def load_data():
     # Load all the sales data
     #df_vest_wholesalers = load_vest_wholesaler_data(st.secrets['vest_wholesaler_url'])
     df_mf_master = load_mf_data(st.secrets['mf_analyzer_url'])
     #df_ft_wholesalers = load_ft_wholesaler_data(st.secrets['ft_wholesaler_url'])
     df_territory_master = load_territory_data(st.secrets['master_territory_url'])
     
     #return df_vest_wholesalers, df_mf_master, df_ft_wholesalers
     return df_mf_master, df_territory_master

@st.cache_data(ttl=21*24*3600)
def process_dataframe(df_mf_master, df_territory_master):
     
     # Define the column headers to display
     column_headers = ['Client Defined Category Name','IS Outsider','ETF/SMA Outsider','SP Outsider','COM Outsider','Vest','Intermediary Firm Name', 'Initiating Firm Name','Address Line 1', 'Address Line 2', 'City','Postal Code','State/Region','Channel','AUM','Industry AUM','NNA','Industry NNA']
     date_options = df_mf_master['Month/Year (Asset Date)'].dt.strftime('%Y-%m-%d').unique().tolist()
     
     # Select the most recent date in the file and only display results from the most recent period
     date_select = date_options[-1]
     df_mf_master = df_mf_master[df_mf_master['Month/Year (Asset Date)'] == date_select]
     
     # Perform operations on the data by merging relevant dataframes
     #df_merged_wholesalers = df_ft_wholesalers.merge(df_vest_wholesalers, left_on=['State'], right_on=['State'], how="left")
     # Strip the hyphens away from the MF Data zip codes
     #df_mf_master['Postal Code'] = df_mf_master['Postal Code'].str[:5]
     
     #df_master_merged = df_mf_master.merge(df_territory_master, left_on=['Postal Code'], right_on=['Zip'], how='left', suffixes=(None,'_right'))
     # The master Dataframe is now complete. We can now start filtering on the data
     df_mf_master = df_mf_master.replace({'Client Defined Category Name':{'BUIGX':'Buffer10/Hedged Equity','KNGIX':'Covered Call','ENGIX':'Buffer20/Innovator','RYSE':'IR Hedge','BTCVX':'Crypto'}})     
     df_mf_master = df_mf_master[column_headers]
     
     return df_mf_master


def filter_dataframe(df):
     """
     Adds a UI on top of a dataframe to let viewers filter columns
     Args:
          df (pd.DataFrame): Original dataframe
     Returns:
          pd.DataFrame: Filtered dataframe
     """
     modify = st.checkbox("Add filters")
     
     if 'df_to_download' not in st.session_state:
          st.session_state.df_to_download = format_headers(df.head(100))
     
     if not modify:
          return st.session_state.df_to_download

     df2 = df.copy()

     modification_container = st.container()

     with modification_container:
          
          dynamic_filters = DynamicFilters(df, filters=['Cohort', 'IS Outsider','ETF/SMA Outsider', 'SP Outsider', 'COM Outsider', 'Vest', 'Channel'])
          
          with st.sidebar:
               st.write("Apply filters in any order below 👇")
               
          dynamic_filters.display_filters(location='sidebar')
          dynamic_filters.display_df()
          
          '''
          to_filter_columns = st.multiselect("Filter dataframe on", 
                                             ['Cohort', 'Institutional Outsider','ETF Outsider', 'SP Outsider', 'COM Outsider', 'Vest Wholesaler', 'Channel'])
          for column in to_filter_columns:
               left, right = st.columns((1, 20))
               left.write("↳")
               # Let's start filtering columns
               if column == 'Cohort':
                    user_cohort_input = right.multiselect(
                         f"Select the {column}",
                         df2['Client Defined Category Name'].unique(),
                    )
                    df2 = df2[df2['Client Defined Category Name'].isin(user_cohort_input)].sort_values(by=['AUM'], ascending=False)
               elif column == 'Institutional Outsider':
                    user_institutionalperson_input = right.multiselect(
                         f"Select the {column}",
                         df2['Institutional Outsider'].sort_values().unique(),
                    )
                    df2 = df2[df2['Institutional Outsider'].isin(user_institutionalperson_input)].sort_values(by=['AUM'], ascending=False)
               elif column == 'ETF Outsider':
                    user_etfperson_input = right.multiselect(
                         f"Select the {column}",
                         df2['ETF Outsider'].sort_values().unique(),
                    )
                    df2 = df2[df2['ETF Outsider'].isin(user_etfperson_input)].sort_values(by=['AUM'], ascending=False)
               elif column == 'SP Outsider':
                    user_spperson_input = right.multiselect(
                         f"Select the {column}",
                         df2['SP Outsider'].sort_values().unique(),
                    )
                    df2 = df2[df2['SP Outsider'].isin(user_spperson_input)].sort_values(by=['AUM'], ascending=False)
               elif column == 'COM Outsider':
                    user_comperson_input = right.multiselect(
                         f"Select the {column}",
                         df2['COM Outsider'].sort_values().unique(),
                    )
                    df2 = df2[df2['COM Outsider'].isin(user_comperson_input)].sort_values(by=['AUM'], ascending=False)
               elif column == 'Vest Wholesaler':
                    user_vestperson_input = right.multiselect(
                         f"Select the {column}",
                         df2['Vest Wholesaler'].sort_values().unique(),
                    )
                    df2 = df2[df2['Vest Wholesaler'].isin(user_vestperson_input)].sort_values(by=['AUM'], ascending=False)
               elif column == 'Channel':
                    user_channel_input = right.multiselect(
                         f"Select the {column}",
                         df2['Channel'].sort_values().unique(),
                    )
                    df2 = df2[df2['Channel'].isin(user_channel_input)].sort_values(by=['AUM'], ascending=False)
               else:
                    user_text_input = right.text_input(
                    f"Substring or regex in {column}",
                    )
                    if user_text_input:
                         df = df[df[column].str.contains(user_text_input)]
          '''
                         
          # Save the DF as a state for future downloading
          st.session_state.df_to_download = df2
          
          # Add a download to Excel button
          st.download_button(
               'Download As Excel',
               data=to_excel(st.session_state.df_to_download),
               file_name='Mutual Fund Cohort Data.xlsx',
               mime='application/vnd.ms-excel',
               )

     # Apply dollar formatting to the AUM and NNA columns for Advisor + Industry
     df2 = format_headers(df2)
          
     #return df2 if len(to_filter_columns) > 0 else df2.head(100)
     return df2

#---------- SETTINGS ----------
page_title = "Mutual Fund Analyzer"
page_icon = "🛡️"
layout = "wide"
initial_sidebar_state = 'collapsed'
st.set_page_config(page_title=page_title, page_icon=page_icon, layout=layout, initial_sidebar_state=initial_sidebar_state)

#-------------- USER AUTHENTICATION ----------

# load config file
file_path = Path(__file__).parents[1] / "config.yaml"
with file_path.open("rb") as file:
     config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
     config['credentials'],
     config['cookie']['name'],
     config['cookie']['key'],
     config['cookie']['expiry_days']
)

try:   
     authenticator.login()
except Exception as e:
     st.error("Username or password is incorrect.")
     st.stop()
     
if st.session_state['authentication_status']:
    authenticator.logout('Logout', 'sidebar')
    st.sidebar.title(f'Welcome *{st.session_state["name"]}*')
elif st.session_state['authentication_status'] is False:
    st.error('Username/password is incorrect')
elif st.session_state['authentication_status'] is None:
    st.warning('Please enter your username and password')

# If authenticated, then start the app     
if st.session_state['authentication_status']:

     st.title('Mutual Fund Analyzer')
     st.write("Use this tool to analyze the latest month's Broadridge mutual fund sales. Filter by cohorts, wholesalers, AUM, etc. Export results into an Excel to share with others.")
     
     #df_vest_wholesalers, df_mf_master, df_ft_wholesalers = load_data()
     df_mf_master, df_territory_master = load_data()
     #df = process_dataframe(df_vest_wholesalers, df_mf_master, df_ft_wholesalers)
     df = process_dataframe(df_mf_master, df_territory_master)
     df.fillna({'Client Defined Category Name':'None', 'IS Outsider':'None', 'ETF/SMA Outsider':'None', 'SP Outsider':'None', 'COM Outsider':'None', 'Vest':'None'}, inplace=True)
     
     # Build and filter the dataframe
     #updated_df = filter_dataframe(df)
     dynamic_filters = DynamicFilters(df, filters=['Client Defined Category Name','IS Outsider','ETF/SMA Outsider','SP Outsider','COM Outsider','Vest','Channel'])
          
     st.write("Apply filters in any order below 👇")
               
     dynamic_filters.display_filters(location='columns', num_columns=2, gap='small')
     dynamic_filters.display_df(use_container_width=True)
     
     # Configure the AG-Grid options to better display the data
     #gb = GridOptionsBuilder.from_dataframe(updated_df)
     #gb.configure_pagination(paginationAutoPageSize=False, paginationPageSize=100)
     #gridOptions = gb.build()
     
     #output = AgGrid(
     #     updated_df,
     #     gridOptions=gridOptions,
     #     columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW,
     #     theme=AgGridTheme.ALPINE,
     #     )