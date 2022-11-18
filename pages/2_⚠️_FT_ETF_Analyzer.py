from datetime import datetime
from click import style
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid

with st.spinner('Loading All Sales & Territory Data. This May Take A Minute. Please wait...'):
    # Read in the FT ETF Sales Data
    sheet_df_dictonary = pd.read_excel('https://cvf-prod.s3.amazonaws.com/media/documents/cf07815e8d57fb7b2dd61f72a0b7b8fa9115383321a637672d9f0c56f4e10695.' + st.secrets['etf_sales_slug'] + '.xlsx',
                                       engine='openpyxl', 
                                       sheet_name=['Table2'], 
                                       skiprows=0)
    ft_etf_sales_df = sheet_df_dictonary['Table2']

    # Read in the FT Wholesaler Territory Data
    ft_wholesaler_df = pd.read_excel('https://cvf-prod.s3.amazonaws.com/media/documents/47ae571678a1d3fbe67eef4500ac3c1c4ecdafb8d95bf4cfb7a4b8cc27af71a5.' + st.secrets['ft_wholesaler_slug'] + '.xlsx',
                                     engine='openpyxl', 
                                     skiprows=0)