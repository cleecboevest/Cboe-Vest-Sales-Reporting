import streamlit as st
import pandas as pd

from pathlib import Path
import yaml
from yaml import SafeLoader
import streamlit_authenticator as stauth

def format_dollar_amount(amount):
    formatted_absolute_amount = '${:,.2f}'.format(abs(amount))
    if round(amount, 2) < 0:
        return f'-{formatted_absolute_amount}'
    return formatted_absolute_amount

@st.cache_data(ttl=21*24*3600)
def load_data(url):
    # Read in the data
    df = pd.read_excel(url, engine='openpyxl', skiprows=0, usecols=[
        'Initiating Firm Name',
        'Client Defined Category Name',
        'ETF/SMA Outsider',
        'Channel',
        'AUM',
        'Industry AUM',
        'NNA',
        'Industry NNA'
    ])
    return df

st.set_page_config(page_title="Industry AUM Lookup", page_icon="📈", layout="wide")

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

    # Title
    st.title("Industry AUM Lookup")
    st.write("""
    This page extracts Industry AUM from the Cohort Analyzer output. 
    """)
    st.write("""
    !! This page takes about 30 seconds to load the first time !!
    """)

    # Load data
    url = st.secrets["mf_analyzer_url"]
    df = load_data(url)
    # Create a unique list of all ETF/SMA Outsider from df
    etf_sma_outsiders = df['ETF/SMA Outsider'].dropna().unique().tolist()
    etf_sma_outsiders.sort()

    # Get user input for "ETF/SMA Outside" using a dropdown box with search functionality
    etf_outsider = st.selectbox(
        "Select ETF/SMA Outsider",
        options=etf_sma_outsiders,
        index=None,
        placeholder="Choose an ETF/SMA Outsider...",
    )
    # Get user input for firm names
    firm_names = st.text_area("Enter firm names (separated by new lines)")

    # Add a button to extract data
    extract_button = st.button("Extract data")

    # Process data when the button is clicked or when Control+Enter is pressed
    if extract_button or firm_names:
        firm_names = [name.strip() for name in firm_names.split("\n") if name.strip()]

        if firm_names:
            # Create a dictionary to store the order of input
            firm_order = {name.lower(): index for index, name in enumerate(firm_names)}
            
            # Filter and process the dataframe
            filtered_df = df[(df['Initiating Firm Name'].str.lower().isin([name.lower() for name in firm_names])) & 
                             (df['ETF/SMA Outsider'] == etf_outsider) &
                             (df['Channel'] == 'RIA')]
            category_mapping = {
                'BUIGX': 'Hedged Equity',
                'KNGIX': 'Covered Call',
                'ENGIX': 'Innovator',
                'RYSE ': 'IR Hedge',
                'BTCVX': 'Crypto'
            }
            filtered_df.loc[filtered_df['Client Defined Category Name'].isin(category_mapping), 'Client Defined Category Name'] = filtered_df['Client Defined Category Name'].map(category_mapping)
            filtered_df = filtered_df.groupby(['Initiating Firm Name', 'Client Defined Category Name'])['Industry AUM'].sum().reset_index()
            filtered_df['Industry AUM'] = filtered_df['Industry AUM'].apply(format_dollar_amount)
            
            # Pivot the dataframe
            pivoted_df = filtered_df.pivot(index='Initiating Firm Name', columns='Client Defined Category Name', values='Industry AUM')
            # Replace the index with the case of the text inputs
            pivoted_df.index = pivoted_df.index.map(lambda x: next((name for name in firm_names if name.lower() == x.lower()), x))
            
            # Create a DataFrame with all input firm names
            all_firms_df = pd.DataFrame(index=[name for name in firm_names])
            # Merge the pivoted dataframe with all_firms_df, making the merge case-insensitive
            result_df = all_firms_df.merge(
                pivoted_df.reset_index(),
                how='left',
                left_index=True,
                right_on=pivoted_df.index.name,
                suffixes=('', '_y')
            )
            result_df.index = result_df[pivoted_df.index.name].str.lower()
            result_df.drop(columns=[pivoted_df.index.name], inplace=True)
            
            # Sort the dataframe based on the input order
            result_df['sort_order'] = result_df.index.str.lower().map(firm_order)
            result_df = result_df.sort_values('sort_order')
            
            # Replace the index with the case of the text inputs
            result_df.index = result_df.index.map(lambda x: next((name for name in firm_names if name.lower() == x), x))
            
            # Remove the sort_order column and reset the index
            result_df = result_df.drop('sort_order', axis=1).reset_index()
            result_df.columns.name = None  # Remove the name from the columns index
            
            # Set the firm name column as the index
            #result_df.set_index(firm_name_column, inplace=True)

            # Display the filtered data side by side
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Sorted based on Input")
                st.dataframe(result_df)
            with col2:
                st.subheader("Show only firms with Industry AUM")
                st.dataframe(pivoted_df)
        else:
            st.warning("Please enter at least one firm name.")

    # New section for autocomplete and filtered results
    st.markdown("---")
    st.subheader("Single Firm Lookup")

    # Get unique list of Initiating Firm Names
    unique_firm_names = sorted(df['Initiating Firm Name'].unique())

    # Create an autocomplete input for Firm Name
    selected_firm = st.selectbox(
        "Enter or Select Firm Name",
        options=[""] + unique_firm_names,
        index=0,
        key="firm_name_input"
    )

    if selected_firm:
        # Filter the dataframe for the selected firm
        firm_df = df[(df['Initiating Firm Name'] == selected_firm) & 
                     (df['ETF/SMA Outsider'] == etf_outsider) & 
                     (df['Channel'] == 'RIA')]
        
        # Apply category mapping
        category_mapping = {
            'BUIGX': 'Hedged Equity',
            'KNGIX': 'Covered Call',
            'ENGIX': 'Innovator',
            'RYSE ': 'IR Hedge',
            'BTCVX': 'Crypto'
        }
        firm_df.loc[firm_df['Client Defined Category Name'].isin(category_mapping), 'Client Defined Category Name'] = firm_df['Client Defined Category Name'].map(category_mapping)
        
        # Group by Client Defined Category Name and sum the Industry AUM
        firm_summary = firm_df.groupby('Client Defined Category Name')['Industry AUM'].sum().reset_index()
        
        # Format the Industry AUM
        firm_summary['Industry AUM'] = firm_summary['Industry AUM'].apply(format_dollar_amount)
        
        # Display the results
        st.write(f"Industry AUM for {selected_firm}:")
        st.dataframe(firm_summary)
    else:
        st.info("Please select a firm to view its Industry AUM.")