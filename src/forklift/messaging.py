#!/usr/bin/env python
# * coding: utf8 *
'''
email.py

A module that contains a method for sending emails
'''

import gzip
import io
import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from os import environ
from os.path import basename, isfile
from smtplib import SMTP

from .config import get_config_prop

log = logging.getLogger('forklift')
skip_emails = False


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

    if not isinstance(to, str):
        to_addresses = ','.join(to)
    else:
        to_addresses = to

    if isinstance(body, str):
        message = MIMEMultipart()
        message.attach(MIMEText(body, 'html'))
    else:
        message = body

    message['Subject'] = subject
    message['From'] = from_address
    message['To'] = to_addresses

    if isfile(attachment):
        with (open(attachment, 'rb')) as log_file, io.BytesIO() as encoded_log:
            gzipper = gzip.GzipFile(mode='wb', fileobj=encoded_log)
            gzipper.writelines(log_file)
            gzipper.close()

            log_file_attachment = MIMEApplication(encoded_log.getvalue(), 'x-gzip')
            log_file_attachment.add_header('Content-Disposition', 'attachment; filename="{}"'.format(basename(attachment + '.gz')))

            message.attach(log_file_attachment)

    if get_config_prop('sendEmails') and not skip_emails:
        smtp = SMTP(smtp_server, smtp_port)
        smtp.sendmail(from_address, to, message.as_string())
        smtp.quit()

        return smtp

    log.info('sendEmails is False. No email sent.')
