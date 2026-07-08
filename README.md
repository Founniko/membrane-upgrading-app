# membrane-upgrading-app

Simplified membrane-based biogas upgrading Streamlit application.

Files included:
- membrane_app.py : core model and functions
- membrane_streamlit.py : Streamlit UI
- requirements.txt : Python dependencies
- .gitignore

Quick local run (using Anaconda/conda):

1. Open Anaconda Prompt and create/activate environment (optional):
   conda create -n membrane python=3.11 -y
   conda activate membrane

2. Install requirements:
   pip install -r requirements.txt

3. Run Streamlit app:
   streamlit run membrane_streamlit.py

Then open the URL shown by Streamlit (usually http://localhost:8501).

To deploy on Streamlit Cloud:
- Push this repository to GitHub, then go to https://share.streamlit.io and create a new app
  using this repository and the main file path `membrane_streamlit.py`.
