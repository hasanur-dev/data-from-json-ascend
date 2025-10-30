import streamlit as st
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import re
import os

# ---------------- CONFIG ----------------
SHEET_LINK = "https://docs.google.com/spreadsheets/d/1JN_F8ZJ9FePn1OywSNuJrfPaBN8fP4W8W5gciIe0lLI/edit?gid=0#gid=0"
TAB_NAME = "Sheet1"
# ----------------------------------------

# Load environment variables


st.set_page_config(page_title="Ascend Match Uploader", page_icon="🎯", layout="centered")
st.title("🎮 Ascend Match Data → Google Sheets")

uploaded_file = st.file_uploader("Upload your JSON match file", type=["json"])

def get_google_credentials():
    creds_dict = {
        "type": st.secrets["GOOGLE"]["GOOGLE_TYPE"],
        "project_id": st.secrets["GOOGLE"]["GOOGLE_PROJECT_ID"],
        "private_key_id": st.secrets["GOOGLE"]["GOOGLE_PRIVATE_KEY_ID"],
        "private_key": st.secrets["GOOGLE"]["GOOGLE_PRIVATE_KEY"].replace("\\n", "\n"),
        "client_email": st.secrets["GOOGLE"]["GOOGLE_CLIENT_EMAIL"],
        "client_id": st.secrets["GOOGLE"]["GOOGLE_CLIENT_ID"],
        "auth_uri": st.secrets["GOOGLE"]["GOOGLE_AUTH_URI"],
        "token_uri": st.secrets["GOOGLE"]["GOOGLE_TOKEN_URI"],
        "auth_provider_x509_cert_url": st.secrets["GOOGLE"]["GOOGLE_AUTH_PROVIDER_CERT_URL"],
        "client_x509_cert_url": st.secrets["GOOGLE"]["GOOGLE_CLIENT_CERT_URL"],
        "universe_domain": st.secrets["GOOGLE"]["GOOGLE_UNIVERSE_DOMAIN"],
    }
    return creds_dict

if uploaded_file:
    data = json.load(uploaded_file)
    rows = []

    for player_id, player_data in data.items():
        game_name = player_data.get("gameName", "")
        agent_info = list(player_data.get("agent", {}).values())
        agent = agent_info[0]["agent"] if agent_info else ""
        stats = player_data.get("side", {}).get("Total", {})

        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)
        kd = round(stats.get("kd", 0), 2)
        acs = round(stats.get("acs", 0), 2)
        first_kills = stats.get("firstKills", 0)
        clutches = stats.get("clutchesWon", 0)
        plants = stats.get("bombPlants", 0)

        rows.append([game_name, agent, kills, deaths, assists, kd, acs, first_kills, clutches, plants])

    df = pd.DataFrame(rows, columns=["IGN", "Agent", "Kills", "Deaths", "Assists", "K/D", "ACS", "FirstKills", "Clutches", "PostPlants"])

    team_a = df.iloc[:5].sort_values(by="ACS", ascending=False).reset_index(drop=True)
    team_b = df.iloc[5:].sort_values(by="ACS", ascending=False).reset_index(drop=True)

    st.subheader("Team A (sorted by ACS)")
    st.dataframe(team_a)
    st.subheader("Team B (sorted by ACS)")
    st.dataframe(team_b)

    combined = pd.concat([
        pd.DataFrame([["=== TEAM A ==="] + [""] * (len(df.columns) - 1)], columns=df.columns),
        team_a,
        pd.DataFrame([[""] * len(df.columns)], columns=df.columns),
        pd.DataFrame([["=== TEAM B ==="] + [""] * (len(df.columns) - 1)], columns=df.columns),
        team_b
    ], ignore_index=True)

    if st.button("📤 Upload to Google Sheets"):
        try:
            creds_dict = get_google_credentials()
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)

            match = re.search(r"/d/([a-zA-Z0-9-_]+)", SHEET_LINK)
            if not match:
                st.error("❌ Invalid Google Sheet link format.")
            else:
                sheet_id = match.group(1)
                spreadsheet = client.open_by_key(sheet_id)
                worksheet = spreadsheet.worksheet(TAB_NAME)

                num_rows = len(combined) + 5
                num_cols = len(combined.columns)
                cell_range = f"A1:{chr(65 + num_cols - 1)}{num_rows}"

                worksheet.update(cell_range, [combined.columns.values.tolist()] + combined.values.tolist())
                st.success(f"✅ Data successfully updated in '{TAB_NAME}' of linked sheet!")
        except Exception as e:
            st.error(f"❌ Error: {e}")
