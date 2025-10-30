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

    for _, player in data.items():
        name = player.get("gameName", "")
        agent_data = list(player.get("agent", {}).values())
        agent = agent_data[0]["agent"] if agent_data else "Unknown"

        stats = player.get("side", {}).get("Total", {})
        kills = stats.get("kills", 0)
        deaths = stats.get("deaths", 0)
        assists = stats.get("assists", 0)
        kd = round(stats.get("kd", 0), 2)
        acs = round(stats.get("acs", 0), 2)
        first_kills = stats.get("firstKills", 0)
        clutches = stats.get("clutchesWon", 0)
        plants = stats.get("bombPlants", 0)
        wins = stats.get("wins", 0)

        rows.append({
            "IGN": name,
            "Agent": agent,
            "Kills": kills,
            "Deaths": deaths,
            "Assists": assists,
            "K/D": kd,
            "ACS": acs,
            "FirstKills": first_kills,
            "Clutches": clutches,
            "Plants": plants,
            "Wins": wins
        })

    df = pd.DataFrame(rows)

    # Separate by win flag
    winners = df[df["Wins"] == 1].sort_values(by="ACS", ascending=False).reset_index(drop=True)
    losers = df[df["Wins"] == 0].sort_values(by="ACS", ascending=False).reset_index(drop=True)

    st.subheader("🏆 Winners (sorted by ACS)")
    st.dataframe(winners)
    st.subheader("❌ Losers (sorted by ACS)")
    st.dataframe(losers)

    # Combine for upload
    combined = pd.concat([
        pd.DataFrame([["=== WINNERS ==="] + [""] * (len(df.columns) - 1)], columns=df.columns),
        winners,
        pd.DataFrame([[""] * len(df.columns)], columns=df.columns),
        pd.DataFrame([["=== LOSERS ==="] + [""] * (len(df.columns) - 1)], columns=df.columns),
        losers
    ], ignore_index=True)

    if st.button("📤 Upload to Google Sheets"):
        try:
            creds = get_google_credentials()
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(creds, scope)
            client = gspread.authorize(credentials)

            sheet_id = re.search(r"/d/([a-zA-Z0-9-_]+)", SHEET_LINK).group(1)
            sheet = client.open_by_key(sheet_id)
            worksheet = sheet.worksheet(TAB_NAME)

            worksheet.clear()  # Overwrite previous data
            worksheet.update([combined.columns.values.tolist()] + combined.fillna("").values.tolist())

            st.success(f"✅ Data uploaded to {TAB_NAME} successfully!")
        except Exception as e:
            st.error(f"❌ Error: {e}")
