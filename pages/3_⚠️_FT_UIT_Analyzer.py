from datetime import datetime
from click import style
import streamlit as st
import pandas as pd
import numpy as np
from st_aggrid import AgGrid

with st.spinner('Loading All Sales & Territory Data. This May Take A Minute. Please wait...'):
    # Read in the FT UIT Sales Data
    ft_uit_sales_df = pd.read_excel('https://cvf-prod.s3.amazonaws.com/media/documents/f468eb983edd0dcaa5a0ae66b3fd6835d5d75a0dd74ee6d0ae10ad1f03bdd81f.' + st.secrets['uit_sales_slug'] + '.xlsx',
                                    engine='openpyxl',
                                    skiprows=0)

    # Read in the FT Wholesaler Territory Data
    ft_wholesaler_df = pd.read_excel('https://cvf-prod.s3.amazonaws.com/media/documents/47ae571678a1d3fbe67eef4500ac3c1c4ecdafb8d95bf4cfb7a4b8cc27af71a5.' + st.secrets['ft_wholesaler_slug'] + '.xlsx',
                                    engine='openpyxl', 
                                    skiprows=0)