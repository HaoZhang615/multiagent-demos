import streamlit as st
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

coderapp_page = st.Page("coderapp.py", title="Code Intepretor", icon="🧊")
multitools_page = st.Page("multitoolsapp.py", title="multiple tools usage", icon="🧊")

# Set the page configuration
st.set_page_config(page_title="AutoGen two Agents Demo", page_icon="🧊", layout="wide")

# Set the title of the page
st.title("AutoGen two Agents Demo")

# button to select the page
pg = st.navigation([coderapp_page, multitools_page])
pg.run()