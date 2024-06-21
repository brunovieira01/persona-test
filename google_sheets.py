import streamlit as st
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json

# Define the scope
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# json with credentials
GOOGLE_SET = {
    "type": st.secrets["GOOGLE_SETTINGS"]["type"],
    "project_id": st.secrets["GOOGLE_SETTINGS"]["project_id"],
    "private_key_id": st.secrets["GOOGLE_SETTINGS"]["private_key_id"],
    "private_key": st.secrets["GOOGLE_SETTINGS"]["private_key"].replace("\\n","\n"),
    "client_email": st.secrets["GOOGLE_SETTINGS"]["client_email"],
    "client_id": st.secrets["GOOGLE_SETTINGS"]["client_id"],
    "auth_uri": st.secrets["GOOGLE_SETTINGS"]["auth_uri"],
    "token_uri": st.secrets["GOOGLE_SETTINGS"]["token_uri"],
    "auth_provider_x509_cert_url": st.secrets["GOOGLE_SETTINGS"]["auth_provider_x509_cert_url"],
    "client_x509_cert_url": st.secrets["GOOGLE_SETTINGS"]["client_x509_cert_url"]
}

# Connect API
GOOGLE = st.secrets["secrets"]["GOOGLE_API_KEY"]
# Select Sheet
SPREADSHEET_ID = '1uJzYgfFsjzNxEFkXKHoKvM3pG5SpSzmS8Dn6goGYeRk'
RANGE_NAME = 'Sheet1!A1:A999'


def google_computer_engine():
  credentials = service_account.Credentials.from_service_account_info(GOOGLE_SET)
  return build('sheets', 'v4', credentials=credentials).spreadsheets()

def find_values(sheets):
  result = sheets.values().get(spreadsheetId=SPREADSHEET_ID, range=RANGE_NAME).execute()
  values = result.get('values', [])
  return values

def find_empty_cell(values):
    """string with first empty cell"""
    for i, row in enumerate(values):
        if len(row) < 1 or row[0] == '':
            return i + 1  # +1 because Sheets API is 1-indexed
    
    row_number = len(values) + 1  # if no empty cell found, return the next row
    # Find the first empty cell in column A
    cell_range = f'Sheet1!A{row_number}'
    return cell_range

