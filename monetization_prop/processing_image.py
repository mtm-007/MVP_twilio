import smtplib,ssl, os, argparse,requests
import base64
import replicate
#import Sendinblue
import sib_api_v3_sdk
from sib_api_v3_sdk.reset import ApiException
from PIL import Image
from io import BytesIO

#replicate setup,with upscaling model for demo 
replicate = replicate.Client(api_token=os.environ["REPLICATE_API_TOKEN"])
replicate_url = ""

#email setup
#sendinBlue api configuration
configuration = sib_api_v3_sdk.Configuration()
configuration.api_key['api_key'] = os.environ["BREVO_API_KEY"]
#initialize the SendinBlue API instance
api_instance = sib_api_v3_sdk = sib_api_v3_sdk.TransactionEmailsApi(
    sib_api_v3_sdk.ApiClient(configuration))


#function to send the image to the user
def send_email(to_address, image_url):

    #Download the image
    image_data = requests.get(image_url).content

    #Encode the image in Base64
    image_base64 = base64.b64encode(image_data).decode('utf-8')

    #create a SendSmtEmailAttachement object
    attachment=sib_api_v3_sdk.SendSmtpEmailAttachment(
        content=image_base64, name="processes_image.jpg")
    
    #SendinBlue mailing parameters
    subject = "Your results are ready!"
    html_content = "The image is attached :)"

    sender = {"name": "Your App name", "email": "you@youremail.com"}

    #create a sendsmtp Email object with attachment
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{
            "email":to_address,
            "name": to_address.split("@")[0]
        }],
        html_content=html_content,
        sender=sender,
        subject=subject,
        attachment=[attachment] #attach the image here
    )

    try:
        #send the email
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(api_response)
        return {"message": "Email sent succesfully!"}
    except ApiException as e:
        print("Exception when calling SMTPApi->send_transac_email: %s\n" % e)


#the important bit 
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--file_path', type=str, required=True)
    parser.add_argument('--email', type=str, required=True)
    parser.add_argument('--debug', type=bool, default=False)
    args = parser.parse_args()

    #process the image and other inputs with replicate
    with open(args.file_path, 'rb') as image:
        output_url = replicate.run(replicate_url, input={"image": image})
    if args.debug: print(output_url)

    #send the result via email
    send_email(args.email, output_url)

    #and finally, delete the photo and any other user data
    os.remove(args.file_path)