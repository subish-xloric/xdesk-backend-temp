import json
from types import SimpleNamespace
import smtplib

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email import encoders
from email.mime.text import MIMEText
from email.mime.image import MIMEImage

from cryptography.fernet import Fernet

#from email.MIMEImage import MIMEImage



from django.conf import settings
from pTracker.common.utility import Utility
from pTracker.common.file_manager import FileManager

class Dict2Class(object):
    def __init__(self, my_dict):
        for key in my_dict:
            setattr(self, key, my_dict[key])

class Email():

    def __init__(self, mail_host='default'):

        self.mail_host = mail_host
        if self.mail_host == "office365":
            self.__ses_host = 'smtp.office365.com'
            self.__ses_port = 587 #465
        else:
            self.__ses_host = 'ws08.servername.online'
            self.__ses_port = 587 #465
        #mail.gdom.net :


    def send_attachment(self, mail_dto):
        result = None
        try :
            """
            mail_dto.subject
            mail_dto.from_address
            mail_dto.body
            mail_dto.file_content
            mail_dto.file_name
            mail_dto.to_addresses
            mail_dto.smtp_username
            mail_dto.smtp_password
            """
            msg = MIMEMultipart()
            msg['Subject'] = mail_dto.subject
            msg['From'] = mail_dto.from_address
            msg.preamble = 'You will not see this in a MIME-aware mail reader.\n'
            msg.attach(MIMEText((mail_dto.body),'html',"utf-8"))
            part1 = MIMEBase('application', 'octet-stream')
            part1.set_payload(mail_dto.file_content)
            part1.add_header('Content-Disposition', 'attachment;filename='+str(mail_dto.file_name))
            encoders.encode_base64(part1)
            msg.attach(part1)

            smtp_server = smtplib.SMTP(self.__ses_host, self.__ses_port)
            smtp_server.ehlo()
            smtp_server.starttls()
            smtp_server.ehlo
            smtp_server.login(mail_dto.smtp_username, mail_dto.smtp_password)

            addresses = mail_dto.to_addresses
            for to_address in addresses:
                smtp_server.sendmail(mail_dto.from_address, to_address, msg.as_string())
            smtp_server.close()
        except Exception as e:
            Utility().log("Error in the method send_attachment, Error is {0}".format(str(e)))

        finally:
            return result



    def send_html_mail(self, mail_dto):
        """With this function we send out our HTML email"""

        # Create message container - the correct MIME type is multipart/alternative here!
        MESSAGE = MIMEMultipart('alternative')
        MESSAGE['subject'] = mail_dto.subject
        #MESSAGE['To'] = TO
        MESSAGE['From'] = mail_dto.from_address
        MESSAGE.preamble = """Your mail reader does not support the report format.Please visit us online!"""

        # Record the MIME type text/html.
        HTML_BODY = MIMEText(mail_dto.body, 'html')

        # Attach parts into message container.
        # According to RFC 2046, the last part of a multipart message, in this case
        # the HTML message, is best and preferred.
        MESSAGE.attach(HTML_BODY)

        smtp_server = smtplib.SMTP(self.__ses_host, self.__ses_port)
        smtp_server.ehlo()
        smtp_server.starttls()
        smtp_server.ehlo
        smtp_server.login(mail_dto.smtp_username, mail_dto.smtp_password)
        addresses = mail_dto.to_addresses
        for to_address in addresses:
            MESSAGE['To'] = to_address
            smtp_server.sendmail(mail_dto.from_address, to_address, MESSAGE.as_string())
        smtp_server.close()


    def send_html_mail_v1(self, mail_dto, is_convertion_need=0):
        # Send an HTML email with an embedded image and a plain text message for
        # email clients that don't want to display the HTML.

        # Create the root message and fill in the from, to, and subject headers
        if is_convertion_need:
            mail_dto = Dict2Class(mail_dto)

        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = mail_dto.subject
        msgRoot['From'] = mail_dto.from_address
        try:
            msgRoot.add_header('Reply-To', mail_dto.reply_to_address)
        except:
            pass
        msgRoot.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        # We reference the image in the IMG SRC attribute by the ID we give it below
        msgText = MIMEText(mail_dto.body, 'html')
        msgAlternative.attach(msgText)

        try:
            msgImage = MIMEImage(mail_dto.image)
            msgImage.add_header('Content-ID', '<image1>')
            msgRoot.attach(msgImage)
        except:
            pass

        try:
            file_data = FileManager().read_encrypted_file(mail_dto.file_path+mail_dto.file_name)
            if file_data is not None:
                attachment = MIMEBase('application', 'octet-stream')
                attachment.set_payload(file_data)
                encoders.encode_base64(attachment)
                attachment.add_header('Content-Disposition', 'attachment', filename=mail_dto.file_name)
                msgRoot.attach(attachment)
        except:
            pass

        smtp_server = smtplib.SMTP(self.__ses_host, self.__ses_port)
        smtp_server.ehlo()
        smtp_server.starttls()
        smtp_server.ehlo
        smtp_server.login(mail_dto.smtp_username, mail_dto.smtp_password)
        addresses = mail_dto.to_addresses
        try:
            cc_addresses = mail_dto.cc_addresses
            msgRoot['CC'] = ",".join(cc_addresses)

        except:
            cc_addresses = []

        try:
            bcc_address = mail_dto.bcc_address

        except:
            bcc_address = []

        for to_address in addresses:
            msgRoot['To'] = to_address
            smtp_server.sendmail(mail_dto.from_address, to_address, msgRoot.as_string())

        if cc_addresses:
            for to_address in cc_addresses:
                smtp_server.sendmail(mail_dto.from_address, to_address, msgRoot.as_string())
        if bcc_address:
            for to_address in bcc_address:
                smtp_server.sendmail(mail_dto.from_address, to_address, msgRoot.as_string())


        smtp_server.close()


    def send_html_mail_v2(self, mail_dto, is_convertion_need=0):
        # Send an HTML email with an embedded image and a plain text message for
        # email clients that don't want to display the HTML.

        # Create the root message and fill in the from, to, and subject headers
        # mail_dto.to_addresses = ['abijith.nm@mydomain.com']
        # mail_dto.cc_addresses = ['abdul.jaseem@mydomain.com']
        if is_convertion_need:
            mail_dto = Dict2Class(mail_dto)

        msgRoot = MIMEMultipart('related')
        msgRoot['Subject'] = mail_dto.subject
        msgRoot['From'] = mail_dto.from_address
        msgRoot.preamble = 'This is a multi-part message in MIME format.'

        # Encapsulate the plain and HTML versions of the message body in an
        # 'alternative' part, so message agents can decide which they want to display.
        msgAlternative = MIMEMultipart('alternative')
        msgRoot.attach(msgAlternative)

        # We reference the image in the IMG SRC attribute by the ID we give it below
        msgText = MIMEText(mail_dto.body, 'html')
        msgAlternative.attach(msgText)

        try:
            msgImage = MIMEImage(mail_dto.image)
            msgImage.add_header('Content-ID', '<image1>')
            msgRoot.attach(msgImage)
            msgImage1 = MIMEImage(mail_dto.logo)
            msgImage1.add_header('Content-ID', '<logo>')
            msgRoot.attach(msgImage1)
        except:
            pass
        smtp_server = smtplib.SMTP(self.__ses_host, self.__ses_port)
        smtp_server.ehlo()
        smtp_server.starttls()
        smtp_server.ehlo
        smtp_server.login(mail_dto.smtp_username, mail_dto.smtp_password)
        addresses = mail_dto.to_addresses
        try:
            cc_addresses = mail_dto.cc_addresses
            msgRoot['CC'] = ",".join(cc_addresses)


        except:
            cc_addresses = []
        for to_address in addresses:
            msgRoot['To'] = to_address
            smtp_server.sendmail(mail_dto.from_address, to_address, msgRoot.as_string())

        if cc_addresses:
            for to_address in cc_addresses:
                smtp_server.sendmail(mail_dto.from_address, to_address, msgRoot.as_string())

        smtp_server.close()