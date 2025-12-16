import os
import subprocess
import json
import re
from uuid import uuid4
from dotenv import load_dotenv

load_dotenv()

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
#DOMAIN = ""
DOMAIN = os.environ.get("DOMAIN", "http://localhost:5000")


#app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
stripe.api_key = os.getenv("STRIPE_API_KEY")
webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

#----local db json 
DB_FILE = "local_db.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r") as f:
            return json.load(f)
    return {"content": {}, "orders":{}}

def save_db(db_data):
    with open(DB_FILE, "w") as f:
        json.dump(db_data,f, indent=4)

db=load_db()

#Database setup
def db_init():
    #if "content" not in db.keys():
    if "content" not in db:
        db["content"] = {}
    if "orders" not in db:  #.keys():
        db["orders"] = {}
    #create directories
    if not os.path.exists("static"):
        os.mkdir("static")
    if not os.path.exists("content"):
        os.mkdir("content")


db_init()
save_db(db)

#email validation
def is_valid_email(email):
    pattern = f'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

#homepage
@app.route("/", methods=["GET"])
def home():
    return render_template("index.html")

#when form submitted
@app.route("/upload", methods=["POST"])
def upload():
    #file = request.files['file']
    email = request.form.get('email', '').strip()
    prompt = request.form.get('prompt', '').strip()

    # if file.filename == '':
    #     flash('No file selected for uploading')
    #     return redirect(url_for('home'))
    
    # if file:
    #     filename = secure_filename(file.filename)
    unique_id = str(uuid4())
    #     file_path = os.path.join('content', unique_id + '_' + filename)
    #     file.save(file_path)

    #add the unique_id and filename + email to the database
    db["content"][unique_id] = {"email": email, "prompt":prompt, "status": "pending"}#"path": file_path, 
    save_db(db)

    return redirect(url_for('checkout', file_id = unique_id))
    
    #return "File upload failed"


#checkout page
@app.route("/checkout/<file_id>", methods=["GET"])
def checkout(file_id):

    #check the file exists in the database
    file_info = db["content"].get(file_id)
    if not file_info:
    #if file_id not in db["content"].keys():
        return "Invalid file ID", 404
    
    #pull out relevant info
    #file_info = db["content"][file_id]
    email = file_info["email"]

    try:
        success_url=DOMAIN + '/success?session_id={CHECKOUT_SESSION_ID}'
        cancel_url=DOMAIN+ '/cancel'

        print(f"Creating stripe session with:")
        print(f"   success_url: {success_url}")
        print(f"  cancel_url: {cancel_url}")

        #create stripe checkout session
        session = stripe.checkout.Session.create(
            payment_method_types = ["card"],
            line_items = [{
                'price_data': {
                    'currency': 'usd',
                    'unit_amount' : 350,
                    'product_data': {
                        'name': 'AI Generated Image',
                    },
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url
        )
        print(f"Stripe session created: {session['id']}")
        print(f"Checkout URL: {session['url']}")

        #link session in file_id
        db["orders"][session["id"]]={ "file_id": file_id,  "email":email, "processed":False}
        save_db(db)

        #redirect to stripe checkout
        return render_template("checkout.html",
                               session_id = session.id,
                               stripe_publishable_key=os.getenv("STRIPE_PUBLISHABLE_KEY"))
        return redirect(session['url'])
    
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return "Payment system error. Please try again.", 500


#the page they'll see if payment is cancelled
@app.route("/cancel")
def cancel():
    return render_template_string(
        "<h1>Cancelled</h1><p>Your payment was cancelled.</p><p><a href='/'>Go back to the homepage</a><p/>"
    )


#you could do the processeing of the image hee, but for
#ease of debugging its in a seperate script.
def process_image(email, prompt,file_id):#filename, 
    #get environment variable to pass to subprocess
    env = os.environ.copy()

    command =[
        "python", "processing_image.py",
        "--email",email, 
        "--prompt",prompt, 
        "--file_id", file_id, # "--file_path", filename,
    ]
    try:
        subprocess.Popen(command, env=env)
    except Exception as e:
        print(f"Error starting image processing: {e}")

#stripe webhook
@app.route("/webhook", methods=['POST'])
def stripe_webhook():
    payload = request.get_data(as_text=True)
    signature = request.headers.get('Stripe-Signature')

    #verify the stripe webhook signature
    try:
        event = stripe.Webhook.construct_event(
            payload, 
            signature, 
            webhook_secret) 
        
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    #log all event
    print(f"Received webhook event: {event['type']}")
    
    #handle the event
    if event['type']=='checkout.session.completed':
        session = event['data']['object']
        #session_id = session["id"]
        
        #reload db to get latest data
        global db
        db = load_db()

        order = db["orders"].get(session["id"])
        if not order:
            return jsonify({'status': ' order not found'}), 200
        
        if order.get("processed"):
            return jsonify({'status': 'already processed'}), 200
        
        file_id = order["file_id"]
        content = db["content"].get(file_id)

        if content:
            print(f"Starting image processing for file_id: {file_id}")
            process_image(content["email"], content["prompt"], file_id)#content["path"], 
            order["processed"] = True
            save_db(db) #when using local json db
            print(f"Order marked as processed: {session}")

        return jsonify({'status': 'ok'}),200
    
    # Add this return for other event types
    return jsonify({'status': 'event received'}), 200
        # if session['id'] in db["orders"]:
        #     #retrive associated file_id from database
        #     file_id= db["orders"][session]['id']['file_id']

        #     #use this to fetch the associated file path and email
        #     file_path = db["content"][file_id]['path']
        #     email = db["content"][file_id]['email']

        #     #process the image (if it exists)
        #     if file_path:
        #         process_image(file_path, email)
        # return jsonify({'status': 'success'}),200

@app.route("/check_status/<file_id>", methods=["GET"])
def check_status(file_id):
    """API endpoint to check if image processing is complete"""
    global db
    db = load_db()

    content = db["content"].get(file_id)
    if not content:
        return jsonify({"status": "not_found"}),404
    
    #check if we have an image url stored
    if content.get("image_url"):
        return jsonify({
            "status": "complete",
            "image_url": content["image_url"],
            "prompt": content["prompt"]
        })
    else:
        return jsonify({"status": "processing"})
    
@app.route("/success")
def success():
    session_id = request.args.get('session_id')
    print(f"Success page - session_id: {session_id}")

    if not session_id:
        return "No session ID provided", 400
    
    try:
        #get the session id from stripe directly
        session = stripe.checkout.Session.retrieve(session_id)

        #the session contains metadata or we can search our orders, but first
        # lets reload the DB in case webhook already processed
        global db
        db = load_db()
        print(f"Orders in DB: {list(db['orders'].keys())}")

        #try to find the order
        order = db["orders"].get(session_id)
        print(f"Found order: {order}")
        if order:
            #find the file_id associated with this session
            file_id = order.get("file_id") 
            print(f"File ID: {file_id}")
        else:
            file_id = None
            for order_id, order_data in db["orders"].items():
                if order_id == session_id:
                    file_id =order_data.get("file_id")
                    break

        if not file_id:
            return render_template_string(""" 
                <!DOCTYPE html>
                <html>
                <head>
                    <title>Payment Successful</title>
                    <style>
                        body {
                            font-family: Arial, sans-serif;
                            text-align: center;
                            padding: 50px;
                            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                            min-height: 100vh;
                        }
                        .container {
                            background: white;
                            padding: 40px;
                            border-radius: 10px;
                            max-width: 500px;
                            margin: 0 auto;
                        }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <h1>✓ Payment Successful!</h1>
                        <p>Your order is being processed. Please check your email shortly for your generated image.</p>
                        <p style="color: #999; margin-top: 20px;">This page will refresh automatically...</p>
                        <p style="margin-top: 30px;">
                            <a href='/' style="color: #667eea; text-decoration: none; font-weight: bold;">Create another image →</a>
                        </p>
                    </div>
                    <script>
                        setTimeout(function(){
                            location.reload();
                        }, 3000); // Reload after 3 seconds
                    </script>
                </body>
                </html>
        """)
        return render_template("success.html", file_id=file_id)
    
    except stripe.error.StripeError as e:
        print(f"Stripe error: {e}")
        return "Error retrieving payment session", 500

#show readme
@app.route('/readme')
def readme():
    readme_file = open("README.md", "r")
    md_template_string = markdown.markdown(readme_file.read(), extensions=["fenced_code"])

    return md_template_string


#run
if __name__=="__main__":
    print("Registered routes:")
    for rule in app.url_map.iter_rules():
        print(f" {rule.endpoint}: {rule.rule}")
    app.run(host="0.0.0.0", port=5000, debug=True)