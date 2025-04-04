import os
import pandas as pd
import streamlit as st
from googleapiclient.discovery import build
from google.oauth2.service_account import Credentials
import io

# Load Google Drive API credentials
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE") or "C:/Yellow.ai/Streamlit_Dashboard_Cloud_Cost/grafana-cost-management-4470e527209e.json"
FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or "1USaI7qHuUfj2wDUD13eg-xFqMC7cD17j"

# Validate environment variables
if not os.path.exists(SERVICE_ACCOUNT_FILE):
    st.error(f"Error: Service account file not found at {SERVICE_ACCOUNT_FILE}")
    st.stop()

if not FOLDER_ID:
    st.error("Error: GOOGLE_DRIVE_FOLDER_ID is not set.")
    st.stop()

# Authenticate with Google Drive API
def authenticate_google_drive():
    try:
        creds = Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE)
        service = build("drive", "v3", credentials=creds)
        return service
    except Exception as e:
        st.error(f"Google Drive authentication failed: {e}")
        st.stop()

# Fetch list of files and folders inside a given folder
def list_files(service, parent_folder_id):
    try:
        query = f"'{parent_folder_id}' in parents"
        results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
        return results.get("files", [])
    except Exception as e:
        st.error(f"Failed to fetch files: {e}")
        return []

# Find a subfolder inside a given parent folder
def get_subfolder_id(service, parent_folder_id, subfolder_name):
    files = list_files(service, parent_folder_id)
    for file in files:
        if file["name"] == subfolder_name and file["mimeType"] == "application/vnd.google-apps.folder":
            return file["id"]
    return None

# Read CSV file from Google Drive
def read_csv_from_drive(service, file_id):
    try:
        request = service.files().get_media(fileId=file_id)
        file_stream = io.BytesIO(request.execute())
        file_stream.seek(0)

        return pd.read_csv(file_stream, encoding='utf-8', error_bad_lines=False)
    except Exception as e:
        st.error(f"Failed to read CSV file: {e}")
        return None

# Streamlit UI
st.title("📊 Cloud Cost Data Explorer")

# Authenticate with Google Drive
service = authenticate_google_drive()

# Fetch root-level folders
root_folders = list_files(service, FOLDER_ID)
provider_folders = {f["name"]: f["id"] for f in root_folders if f["mimeType"] == "application/vnd.google-apps.folder"}

# Select cloud provider folder
selected_provider = st.selectbox("📁 Select Cloud Provider:", list(provider_folders.keys()))

# Get 2025 folder ID
selected_provider_id = provider_folders[selected_provider]
folder_2025_id = get_subfolder_id(service, selected_provider_id, "2025")

if folder_2025_id:
    st.subheader(f"📂 2025 Folder inside {selected_provider}")

    # List folders inside 2025 (1, 2, 3, etc.)
    subfolders = list_files(service, folder_2025_id)
    numbered_folders = {f["name"]: f["id"] for f in subfolders if f["mimeType"] == "application/vnd.google-apps.folder"}

    if numbered_folders:
        selected_numbered_folder = st.selectbox("📂 Select Subfolder:", list(numbered_folders.keys()))
        selected_folder_id = numbered_folders[selected_numbered_folder]

        # List deeper subfolders (e.g., 24, 25 inside 3)
        deeper_subfolders = list_files(service, selected_folder_id)
        deeper_folder_options = {f["name"]: f["id"] for f in deeper_subfolders if f["mimeType"] == "application/vnd.google-apps.folder"}

        if deeper_folder_options:
            selected_deeper_folder = st.selectbox("📂 Select a deeper subfolder:", list(deeper_folder_options.keys()))
            selected_deeper_folder_id = deeper_folder_options[selected_deeper_folder]

            # List files inside the final selected folder
            final_files = list_files(service, selected_deeper_folder_id)

            if final_files:
                # Filter only CSV files
                csv_files = {
                    f["name"]: f["id"]
                    for f in final_files
                    if f["mimeType"] in ["text/csv", "application/vnd.ms-excel"]
                }

                # Display all files
                for file in final_files:
                    st.write(f"📄 **{file['name']}** _(Type: {file['mimeType']})_")

                # Allow user to select a CSV file
                if csv_files:
                    selected_file = st.selectbox("📄 Select a CSV file to open:", list(csv_files.keys()))
                    file_id = csv_files[selected_file]

                    # Read and display CSV content
                    df = read_csv_from_drive(service, file_id)
                    if df is not None:
                        st.write(f"### 📊 Preview of {selected_file}")
                        st.table(df.head(10))  # Limited preview

                        # **New Features: Data Analysis & Visualization**
                        st.subheader("📈 Data Analysis & Visualization")

                        # Summary Statistics
                        st.write("### 📊 Summary Statistics")
                        st.write(df.describe())

                        # Column selection for visualization
                        numeric_columns = df.select_dtypes(include=['number']).columns.tolist()
                        if numeric_columns:
                            selected_column = st.selectbox("📊 Select a column for visualization:", numeric_columns)

                            # Bar Chart
                            st.write("### 📊 Bar Chart")
                            st.bar_chart(df[selected_column])

                            # Line Chart
                            st.write("### 📈 Line Chart")
                            st.line_chart(df[selected_column])
                        else:
                            st.warning("⚠️ No numeric columns found for visualization.")

                        # Filtering Data
                        st.subheader("🔍 Data Filtering")
                        filter_column = st.selectbox("🔎 Select a column to filter:", df.columns)
                        unique_values = df[filter_column].unique()
                        selected_value = st.selectbox("🎯 Select a value to filter:", unique_values)
                        filtered_df = df[df[filter_column] == selected_value]
                        st.write("### 🔍 Filtered Data")
                        st.table(filtered_df.head(10))

                else:
                    st.warning("⚠️ No CSV files found in this folder.")

            else:
                st.warning("⚠️ No files found in the selected subfolder.")

        else:
            st.warning("⚠️ No deeper subfolders found inside the selected folder.")

    else:
        st.warning("⚠️ No subfolders found inside 2025.")

else:
    st.warning(f"⚠️ '2025' folder not found inside {selected_provider}.")
