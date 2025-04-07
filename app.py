from flask import Flask, render_template, request
from pymysql import connections
import os
import time
import boto3
import sys
from botocore.exceptions import NoCredentialsError

# Group info
GROUP_NAME = os.environ.get("GROUP_NAME", "Group9")
GROUP_SLOGAN = os.environ.get("GROUP_SLOGAN", "Secure. Scalable. Cloud.")

app = Flask(__name__)

# MySQL config
DBHOST = os.environ.get("DBHOST", "mysql-container")
DBUSER = os.environ.get("DBUSER", "root")
DBPWD = os.environ.get("DBPWD", "pw")
DATABASE = os.environ.get("DATABASE", "employees")
DBPORT = int(os.environ.get("DBPORT", 3306))

# Color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}

COLOR = os.environ.get('APP_COLOR', "lime")
if COLOR not in color_codes:
    print(f"Invalid APP_COLOR: {COLOR}. Defaulting to 'lime'.")
    COLOR = "lime"

# --- 🔽 Download image from S3 ---
def download_image_from_s3(bucket_name, s3_key, local_path):
    image_url = f"s3://{bucket_name}/{s3_key}"
    try:
        s3 = boto3.client('s3')
        s3.download_file(bucket_name, s3_key, local_path)
        print(f"[INFO] Downloaded image from {image_url}")
        print(f"[LOG] Background image URL: {image_url}")  # ← Log for assignment
        return True
    except NoCredentialsError:
        print(f"[ERROR] AWS credentials not found.")
        print(f"[LOG] Background image URL: {image_url}")  # ← Still log the URL even on failure
    except Exception as e:
        print(f"[ERROR] Failed to download image from {image_url}: {e}")
        print(f"[LOG] Background image URL: {image_url}")
    return False


# Use env variables (simulating ConfigMap)
S3_BUCKET = os.environ.get("S3_BUCKET_NAME")
S3_KEY = os.environ.get("S3_IMAGE_KEY")  # e.g., "Seneca.png"
LOCAL_IMAGE_PATH = "static/Seneca.png"

if S3_BUCKET and S3_KEY:
    downloaded = download_image_from_s3(S3_BUCKET, S3_KEY, LOCAL_IMAGE_PATH)
    if not downloaded:
        print("[WARN] Using existing/static background image")
else:
    print("[WARN] S3_BUCKET_NAME or S3_IMAGE_KEY not set — skipping image download")

# --- 🛢️ Retry MySQL connection ---
MAX_RETRIES = 5
RETRY_DELAY = 5
db_conn = None

def connect_to_db():
    global db_conn
    for attempt in range(MAX_RETRIES):
        try:
            db_conn = connections.Connection(
                host=DBHOST,
                port=DBPORT,
                user=DBUSER,
                password=DBPWD,
                db=DATABASE
            )
            print("✅ Successfully connected to MySQL")
            return
        except Exception as e:
            print(f"MySQL Connection attempt {attempt + 1} failed: {e}")
            time.sleep(RETRY_DELAY)
    print("❌ MySQL connection failed after multiple retries. Exiting.")
    exit(1)

# 💡 Only run DB connection if NOT in pytest
if not any("pytest" in arg for arg in sys.argv):
    connect_to_db()
else:
    print("🧪 Skipping DB connection during tests")
# --- Routes ---
@app.route("/", methods=['GET'])
def home():
    return render_template('addemp.html', color=color_codes[COLOR],
                           group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

@app.route("/about", methods=['GET'])
def about():
    return render_template('about.html', color=color_codes[COLOR],
                           group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

@app.route("/addemp", methods=['POST'])
def AddEmp():
    emp_id = request.form.get('emp_id')
    first_name = request.form.get('first_name')
    last_name = request.form.get('last_name')
    primary_skill = request.form.get('primary_skill')
    location = request.form.get('location')

    insert_sql = "INSERT INTO employee (emp_id, first_name, last_name, primary_skill, location) VALUES (%s, %s, %s, %s, %s)"

    try:
        with db_conn.cursor() as cursor:
            cursor.execute(insert_sql, (emp_id, first_name, last_name, primary_skill, location))
            db_conn.commit()
        emp_name = f"{first_name} {last_name}"
        print(f"[INFO] Employee {emp_name} added successfully")
    except Exception as e:
        print(f"[ERROR] Inserting employee failed: {e}")
        db_conn.rollback()
        emp_name = "Error"

    return render_template('addempoutput.html', name=emp_name, color=color_codes[COLOR],
                           group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

@app.route("/getemp", methods=['GET'])
def GetEmp():
    return render_template("getemp.html", color=color_codes[COLOR],
                           group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

@app.route("/fetchdata", methods=['POST'])
def FetchData():
    emp_id = request.form.get('emp_id')

    if not emp_id:
        print("No Employee ID provided")
        return render_template("getempoutput.html", id="N/A", fname="N/A",
                               lname="N/A", interest="N/A", location="N/A",
                               color=color_codes[COLOR],
                               group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location FROM employee WHERE emp_id=%s"

    try:
        with db_conn.cursor() as cursor:
            cursor.execute(select_sql, (emp_id,))
            result = cursor.fetchone()

        if not result:
            print("Employee not found")
            return render_template("getempoutput.html", id="N/A", fname="N/A",
                                   lname="N/A", interest="N/A", location="N/A",
                                   color=color_codes[COLOR],
                                   group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

        output = {
            "emp_id": result[0],
            "first_name": result[1],
            "last_name": result[2],
            "primary_skills": result[3],
            "location": result[4],
        }

        return render_template("getempoutput.html", id=output["emp_id"], fname=output["first_name"],
                               lname=output["last_name"], interest=output["primary_skills"], location=output["location"],
                               color=color_codes[COLOR],
                               group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

    except Exception as e:
        print(f"[ERROR] Fetching employee failed: {e}")

    return render_template("getempoutput.html", id="N/A", fname="N/A",
                           lname="N/A", interest="N/A", location="N/A",
                           color=color_codes[COLOR],
                           group_name=GROUP_NAME, group_slogan=GROUP_SLOGAN)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=81, debug=True)
