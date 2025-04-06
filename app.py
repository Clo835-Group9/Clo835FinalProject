
from flask import Flask, render_template, request
from pymysql import connections
import os
import time

app = Flask(__name__)

# Fetch environment variables  for the webapp
DBHOST = os.environ.get("DBHOST", "mysql-container")
DBUSER = os.environ.get("DBUSER", "root")
DBPWD = os.environ.get("DBPWD", "pw")
DATABASE = os.environ.get("DATABASE", "employees")
DBPORT = int(os.environ.get("DBPORT", 3306))  # Default to 3306 if not set

# Retry logic for MySQL connection
MAX_RETRIES = 5
RETRY_DELAY = 5  # Seconds
db_conn = None

for attempt in range(MAX_RETRIES):
    try:
        db_conn = connections.Connection(
            host=DBHOST,
            port=DBPORT,
            user=DBUSER,
            password=DBPWD,
            db=DATABASE
        )
        print("Successfully connected to MySQL")
        break
    except Exception as e:
        print(f"MySQL Connection attempt {attempt + 1} failed: {e}")
        time.sleep(RETRY_DELAY)
else:
    print("MySQL connection failed after multiple retries. Exiting.")
    exit(1)

# Define supported color codes
color_codes = {
    "red": "#e74c3c",
    "green": "#16a085",
    "blue": "#89CFF0",
    "blue2": "#30336b",
    "pink": "#f4c2c2",
    "darkblue": "#130f40",
    "lime": "#C1FF9C",
}

# Default color from environment variable
COLOR = os.environ.get('APP_COLOR', "lime")
if COLOR not in color_codes:  
    print(f"Invalid APP_COLOR: {COLOR}. Defaulting to 'lime'.")
    COLOR = "lime"

@app.route("/", methods=['GET'])
def home():
    return render_template('addemp.html', color=color_codes[COLOR])

@app.route("/about", methods=['GET'])
def about():
    return render_template('about.html', color=color_codes[COLOR])
    
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
        print(f"Employee {emp_name} added successfully")
    except Exception as e:
        print(f"Error inserting employee: {e}")
        db_conn.rollback()
        emp_name = "Error"

    return render_template('addempoutput.html', name=emp_name, color=color_codes[COLOR])

@app.route("/getemp", methods=['GET'])
def GetEmp():
    return render_template("getemp.html", color=color_codes[COLOR])

@app.route("/fetchdata", methods=['POST'])
def FetchData():
    emp_id = request.form.get('emp_id')

    if not emp_id:
        print(" No Employee ID provided")
        return render_template("getempoutput.html", id="N/A", fname="N/A",
                               lname="N/A", interest="N/A", location="N/A", color=color_codes[COLOR])

    select_sql = "SELECT emp_id, first_name, last_name, primary_skill, location FROM employee WHERE emp_id=%s"

    try:
        with db_conn.cursor() as cursor:
            cursor.execute(select_sql, (emp_id,))
            result = cursor.fetchone()

        if not result:
            print(" Employee not found")
            return render_template("getempoutput.html", id="N/A", fname="N/A",
                                   lname="N/A", interest="N/A", location="N/A", color=color_codes[COLOR])

        output = {
            "emp_id": result[0],
            "first_name": result[1],
            "last_name": result[2],
            "primary_skills": result[3],
            "location": result[4],
        }

        return render_template("getempoutput.html", id=output["emp_id"], fname=output["first_name"],
                               lname=output["last_name"], interest=output["primary_skills"], location=output["location"], color=color_codes[COLOR])

    except Exception as e:
        print(f"Error fetching employee: {e}")

    return render_template("getempoutput.html", id="N/A", fname="N/A", lname="N/A", interest="N/A", location="N/A", color=color_codes[COLOR])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
