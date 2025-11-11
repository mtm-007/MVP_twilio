from flask import Flask, request, jsonify, Response, render_template
from flask_cors import CORS
from twilio.jwt.access_token import AccessToken
from twilio.jwt.access_token.grants import VoiceGrant
from twilio.twiml.voice_response import VoiceResponse
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_API_KEY = os.getenv("TWILIO_API_KEY")
TWILIO_API_SECRET = os.getenv("TWILIO_API_SECRET")
TWIML_APP_SID = os.getenv("TWIML_APP_SID")
TWILIO_NUMBER = os.getenv("TWILIO_NUMBER")

# Web page
@app.route("/")
def index():
    return render_template("index.html")

# Token endpoint
@app.route("/token")
def token():
    identity = request.args.get("identity", "webUser")

    voice_grant = VoiceGrant(
        outgoing_application_sid=TWIML_APP_SID,
        incoming_allow=False
    )

    token = AccessToken(TWILIO_ACCOUNT_SID, TWILIO_API_KEY, TWILIO_API_SECRET, identity=identity)
    token.add_grant(voice_grant)

    return jsonify(identity=identity, token=token.to_jwt().decode("utf-8"))

# TwiML endpoint
@app.route("/voice", methods=["POST"])
def voice():
    to_number = request.form.get("To")
    resp = VoiceResponse()
    if to_number.startswith("+"):
        resp.dial(to_number, callerId=TWILIO_NUMBER)
    else:
        resp.dial(client=to_number)
    return Response(str(resp), mimetype="text/xml")

if __name__ == "__main__":
    app.run(port=3000, debug=True)
