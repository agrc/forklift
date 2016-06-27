#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

import logging
import secrets
from config import get_config_prop
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from smtplib import SMTP


log = logging.getLogger('forklift')


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
    if get_config_prop('sendEmails'):
        smtp.sendmail(secrets.from_address, to, message.as_string())
        smtp.quit()
    else:
        log.info('sendEmails is False. No email sent.')

    return smtp
