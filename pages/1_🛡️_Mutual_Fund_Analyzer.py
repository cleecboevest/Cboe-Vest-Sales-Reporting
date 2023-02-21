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
     writer.save()
     processed_data = output.getvalue()
     return processed_data

@st.cache_data
def load_vest_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_vest_wholesalers = pd.read_excel(url,engine='openpyxl')
     return df_vest_wholesalers

@st.cache_data
def load_ft_wholesaler_data(url):
     #----------READ IN DATA--------
     # Read in the Cboe Vest Wholesaler Territory Data
     df_ft_wholesalers = pd.read_excel(url,engine='openpyxl', dtype={'Zip': str})
     return df_ft_wholesalers

@st.cache_data
def load_mf_data(url):
     #----------READ IN DATA--------
     # Read in the Broadridge Data
     df_mf_master = pd.read_excel(url,engine='openpyxl', dtype={'Postal Code': str})
     return df_mf_master


def load_data():
     # Load all the sales data
     df_vest_wholesalers = load_vest_wholesaler_data(st.secrets['vest_wholesaler_url'])
     df_mf_master = load_mf_data(st.secrets['mf_analyzer_url'])
     df_ft_wholesalers = load_ft_wholesaler_data(st.secrets['ft_wholesaler_url'])
     
     return df_vest_wholesalers, df_mf_master, df_ft_wholesalers

@st.cache_data
def process_dataframe(df_vest_wholesalers, df_mf_master, df_ft_wholesalers):
     
     # Define the column headers to display
     column_headers = ['Client Defined Category Name','ETF Outsider','SP Outsider','Wholesaler','Intermediary Firm Name', 'Initiating Firm Name','Address Line 1', 'Address Line 2', 'City','Postal Code','State/Region','Channel','AUM','Industry AUM','NNA','Industry NNA']
     date_options = df_mf_master['Month/Year (Asset Date)'].dt.strftime('%Y-%m-%d').unique().tolist()
     
     # Select the most recent date in the file and only display results from the most recent period
     date_select = date_options[-1]
     df_mf_master = df_mf_master[df_mf_master['Month/Year (Asset Date)'] == date_select]
     
     # Perform operations on the data by merging relevant dataframes
     df_merged_wholesalers = df_ft_wholesalers.merge(df_vest_wholesalers, left_on=['State'], right_on=['State'], how="left")
     # Strip the hyphens away from the MF Data zip codes
     df_mf_master['Postal Code'] = df_mf_master['Postal Code'].str[:5]
     
     df_master_merged = df_mf_master.merge(df_merged_wholesalers, left_on=['Postal Code'], right_on=['Zip'], how='left', suffixes=(None,'_right'))
     # The master Dataframe is now complete. We can now start filtering on the data
     df_master_merged = df_master_merged.replace({'Client Defined Category Name':{'BUIGX #1':'Buffer10/Hedged Equity','BUIGX #2':'Innovator ETFs','KNGIX':'Aristocrats/Gold','ENGIX':'Buffer20/Bitcoin','KNG':'Income ETFs'}})
     df_master_merged = df_master_merged[column_headers]
     
     return df_master_merged


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
          to_filter_columns = st.multiselect("Filter dataframe on", 
                                             ['Cohort', 'ETF Outsider', 'SP Outsider', 'Vest Wholesaler', 'Channel'])
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
               elif column == 'Vest Wholesaler':
                    user_vestperson_input = right.multiselect(
                         f"Select the {column}",
                         df2['Wholesaler'].sort_values().unique(),
                    )
                    df2 = df2[df2['Wholesaler'].isin(user_vestperson_input)].sort_values(by=['AUM'], ascending=False)
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
          
     return df2 if len(to_filter_columns) > 0 else df2.head(100)

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

     st.title('Mutual Fund Analyzer')
     st.write("Use this tool to analyze the latest month's Broadridge mutual fund sales. Filter by cohorts, wholesalers, AUM, etc. Export results into an Excel to share with others.")
     
     df_vest_wholesalers, df_mf_master, df_ft_wholesalers = load_data()
     df = process_dataframe(df_vest_wholesalers, df_mf_master, df_ft_wholesalers)
     
     # Build and filter the dataframe
     updated_df = filter_dataframe(df)
     
     # Configure the AG-Groid options to better display the data
     gb = GridOptionsBuilder.from_dataframe(updated_df)
     gb.configure_pagination(paginationPageSize=100)
     gridOptions = gb.build()
     
          
     output = AgGrid(
          updated_df,
          gridOptions=gridOptions,
          columns_auto_size_mode=ColumnsAutoSizeMode.FIT_ALL_COLUMNS_TO_VIEW,
          theme=AgGridTheme.ALPINE,
          )