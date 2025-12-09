import os
import subprocess
from uuid import uuid4

import markdown.extensions.fenced_code
import stripe 
from flask import(
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    render_template_string,
    request,
    url_for
)
from replit import db, web
from werkzeug.utils import secure_filename

#create flask app
app = Flask(__name__, static_folder='static', static_url_path='')

#specify your apps urls
DOMAIN = ""

stripe.api_key = os.environ["STRIPE_API_KEY"]
webhook_secret = os.environ["STRIPE_WEBHOOK_SECRET"]

#Database setup
def db_init():
    if "content" not in db.keys():
        db["content"] = {}
    if "orders" not in db.keys():
        db["orders"] = {}
    #create directories
    if not os.path.exists("static"):
        os.mkdir("static")
    if not os.path.exists("content"):
        os.mkdir("content")

db_init()

#homepage
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

#when form submitted
@app.route("upload", methods=["POST"])
def upload():
    file = request.files['file']
    email = request.form['email']
    if file.filename == '':
        flash('No file selected for uploading')
        return redirect(url_for('home'))
    
    if file:
        filename = secure_filename(file.filename)
        unique_id = str(uuid4())
        file_path = os.path.join('content', unique_id + '_' + filename)
        file.save(file_path)

        #add the unique_id and filename + email to the database
        db["content"][unique_id] = {"path": file_path, "email": email}
        return redirect(url_for('checkout', file_id = unique_id))
    
    return "File upload failed"