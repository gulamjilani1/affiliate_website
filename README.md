Affiliate Site — ready-to-run.

1. Create virtualenv:
   python -m venv venv
   source venv/bin/activate   # Mac/Linux
   venv\Scripts\activate      # Windows PowerShell

2. Install:
   pip install -r requirements.txt

3. Copy .env.example to .env and set SECRET_KEY.

4. Run:
   python app.py
   Visit http://127.0.0.1:5000

5. To deploy: push to GitHub and connect repo to Railway.
