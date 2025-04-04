
## 🛠️ Setup & Installation

### 1️⃣ Install Dependencies
Ensure you have Python installed, then install required libraries:
```bash
pip install streamlit pandas google-auth google-auth-oauthlib google-auth-httplib2 googleapiclient
```

### 2️⃣ Set Up Google Drive Credentials
- Place your **service account JSON key** file in the project folder.
- Update the `SERVICE_ACCOUNT_FILE` path inside the script.

### 3️⃣ Run the App
```bash
streamlit run app.py
```