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
    st.write("UNDER CONSTRUCTION")