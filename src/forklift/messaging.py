#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

import secrets
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTP


def send_email(to, subject, body):
    '''
    to: string | string[]
    subject: string
    body: string | MIMEMultipart

    Send an email.
    '''

    if not isinstance(to, basestring):
        to_addresses = ','.join(to)
    else:
        to_addresses = to

    if isinstance(body, basestring):
        message = MIMEMultipart()
        message.attach(MIMEText(body))
    else:
        message = body

    message['Subject'] = subject
    message['From'] = secrets.from_address
    message['To'] = to_addresses

    smtp = SMTP(secrets.smtp_server, secrets.smtp_port)
    smtp.sendmail(secrets.from_address, to_addresses, message.as_string())
    smtp.quit()

    return smtp
