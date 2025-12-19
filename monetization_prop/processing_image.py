import os, argparse, requests, base64, modal
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
#from PIL import Image
#from io import BytesIO
from dotenv import load_dotenv
from db import update_content_image

load_dotenv()

#email setup
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api-key'] = os.getenv("SIB_API_V3_KEY")
api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

#function to send the image to the user
def send_email_with_attachment( to_address, prompt, image_bytes, filename):
    #Encode the image in Base64
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    #create a SendSmtEmailAttachement object
    attachment=sib_api_v3_sdk.SendSmtpEmailAttachment(content=image_base64, name=filename)#"processes_image.jpg")
  
    #create a sendsmtp Email object with attachment
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{ "email":to_address, "name": to_address.split("@")[0] }],
        html_content=f"<p>Your image for prompt: <b>{prompt}</b> is ready!</p>",
        sender={"name": "AI Generator", "email": "gptagent.unlock@gmail.com"},
        subject="Your AI Generated Image",
        attachment=[attachment]) #attach the image here

    try:
        #send the email
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(api_response)
        return {"message": "Email sent succesfully!"}
    except ApiException as e:
        print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    #parser.add_argument('--file_path', type=str, required=True)
    parser.add_argument('--email', type=str, required=True)
    parser.add_argument('--prompt', type=str, required=True)
    parser.add_argument('--file_id', type=str, required=True)
    args = parser.parse_args()

    f = modal.Function.lookup("diffusion-service", "DiffusionModel.generate_and_save")
    filename, image_bytes = f.remote(args.prompt)

    static_path = f"static/generated/{filename}"
    os.makedirs("static/generated", exist_ok=True)
    with open(static_path, "wb") as f_out:
        f_out.write(image_bytes)

    DB_FILE = os.environ.get("DB_FILE", "sqlite3_database.db")
    
    update_content_image(args.file_id, f"/{static_path}")
    print(f"SQLite database updated for file_id: {args.file_id}")

    send_email_with_attachment(args.email, args.prompt, image_bytes, filename)
    print("Done! Email sent successfully and Image saved to {static_path}")

