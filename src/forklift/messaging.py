#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

import logging
from config import get_config_prop
from email import encoders
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from os import environ
from os.path import basename
from os.path import isfile
from smtplib import SMTP

log = logging.getLogger('forklift')


def send_email(to, subject, body, attachment=''):
    '''
    to: string | string[]
    subject: string
    body: string | MIMEMultipart
    attachment: string - the path to a text file to attach.

    Send an email.
    '''
    from_address = environ.get('FORKLIFT_FROM_ADDRESS')
    smtp_server = environ.get('FORKLIFT_SMTP_SERVER')
    smtp_port = environ.get('FORKLIFT_SMTP_PORT')

    if None in [from_address, smtp_server, smtp_port]:
        log.warn('Required environment variables for sending emails do not exist. No emails sent. See README.md for more details.')
        return

    if not isinstance(to, basestring):
        to_addresses = ','.join(to)
    else:
        to_addresses = to

    if isinstance(body, basestring):
        message = MIMEMultipart()
        message.attach(MIMEText(body, 'html'))
    else:
        message = body

    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = to_addresses

    if isfile(attachment):
        log_file_attachment = MIMEBase('application', 'octet-stream')
        log_file_attachment.add_header('Content-Disposition', 'attachment; filename="{}"'.format(basename(attachment)))

        with (open(attachment, 'rb')) as log_file:
            log_file_attachment.set_payload(log_file.read())

        encoders.encode_base64(log_file_attachment)
        message.attach(log_file_attachment)

    if get_config_prop('sendEmails'):
        smtp = SMTP(smtp_server, smtp_port)
        smtp.sendmail(from_address, to, message.as_string())
        smtp.quit()

        return smtp

    log.info('sendEmails is False. No email sent.')
