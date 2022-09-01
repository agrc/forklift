#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

import gzip
import io
import logging
from base64 import b64encode
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Attachment, Disposition, FileContent, FileName, FileType
from smtplib import SMTP

import pkg_resources
import requests

from .config import get_config_prop

log = logging.getLogger('forklift')
send_emails_override = None


def send_email(to, subject, body, attachments=[]):
    '''
    to: string | string[]
    subject: string
    body: string | MIMEMultipart
    attachments: string[] - paths to text files to attach to the email

    Send an email.
    '''
    if send_emails_override is False:
        log.info('send_emails_override is False. No email sent.')

        return
    elif send_emails_override is True:
        pass
    else:
        user_email_preference = get_config_prop('sendEmails')

        if user_email_preference is False:
            log.info('forklift config is set to skip emails. No email sent.')

            return

    email_server = get_config_prop('email')

    if 'apiKey' in email_server and email_server['apiKey'] is not None and email_server['apiKey'].strip() != '':
        return _send_email_with_sendgrid(email_server, to, subject, body, attachments)
    else:
        return _send_email_with_smtp(email_server, to, subject, body, attachments)

def send_to_slack(url, messages):
    '''sends a message to the webhook url
    messages: the blocks to send to slack split at the maximum value of 50'''

    if messages is None or url is None:
        return

    if not isinstance(messages, list):
        messages = [messages]

    for message in messages:
        response = requests.post(
            url, data=message, headers={'Content-Type': 'application/json'}
        )

        if response.status_code != 200:
            raise ValueError(f'Request to slack returned an error {response.status_code}, the response is: {response.text}')

def _send_email_with_sendgrid(email_server, to, subject, body, attachments=[]):
    '''
    email_server: dict
    to: string | string[]
    subject: string
    body: string | MIMEMultipart
    attachments: string[] - paths to text files to attach to the email

    Send an email.
    '''
    from_address = email_server['fromAddress']
    api_key = email_server['apiKey']

    if None in [from_address, api_key]:
        log.warning('Required environment variables for sending emails do not exist. No emails sent. See README.md for more details.')

        return

    message = Mail(
        from_email=from_address,
        to_emails=to,
        subject=subject,
        html_content=body)

    for location in attachments:
        path = Path(location)

        encoded_log = _gzip(path)

        if encoded_log is None:
            continue

        content = b64encode(encoded_log).decode()

        message.attachment = Attachment(
            FileContent(content), FileName(f'{path.name}.gz'), FileType('x-gzip'), Disposition('attachment')
        )

    try:
        client = SendGridAPIClient(api_key)

        return client.send(message)
    except Exception as e:
        log.error(f'Error sending email with SendGrid: {e}')

        return e

def _send_email_with_smtp(email_server, to, subject, body, attachments=[]):
    '''
    email_server: dict
    to: string | string[]
    subject: string
    body: string | MIMEMultipart
    attachments: string[] - paths to text files to attach to the email

    Send an email.
    '''
    from_address = email_server['fromAddress']
    smtp_server = email_server['smtpServer']
    smtp_port = email_server['smtpPort']

    if None in [from_address, smtp_server, smtp_port]:
        log.warning('Required environment variables for sending emails do not exist. No emails sent. See README.md for more details.')

        return

    if not isinstance(to, str):
        to_addresses = ','.join(to)
    else:
        to_addresses = to

    if isinstance(body, str):
        message = MIMEMultipart()
        message.attach(MIMEText(body, 'html'))
    else:
        message = body

    version = MIMEText(f'<p>Forklift version: {pkg_resources.require("forklift")[0].version}</p>', 'html')
    message.attach(version)

    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = to_addresses

    for path in attachments:
        path = Path(path)
        content = _gzip(path)

        attachment = MIMEApplication(content, 'x-gzip')
        attachment.add_header(f'Content-Disposition', 'attachment; filename="{path.name}.gz"')

        message.attach(attachment)

    smtp = SMTP(smtp_server, smtp_port)
    smtp.sendmail(from_address, to, message.as_string())
    smtp.quit()

    return smtp

def _gzip(location):
    '''
    location: string - path to a file

    gzip a file and return the bytes to the gzipped file
    '''
    path = Path(location)

    if not path.is_file():
        return None

    with (open(path, 'rb')) as log_file, io.BytesIO() as encoded_log:
        gzipper = gzip.GzipFile(mode='wb', fileobj=encoded_log)
        gzipper.writelines(log_file)
        gzipper.close()

        return encoded_log.getvalue()
