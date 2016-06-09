#!/usr/bin/env python
# * coding: utf8 *
'''
test_messaging.py

A module that contains tests for messaging.py
'''

import unittest
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from forklift.messaging import send_email
from mock import patch


@patch('forklift.messaging.SMTP', autospec=True)
class SendEmail(unittest.TestCase):
    def test_to_addresses(self, SMTP_mock):
        smtp = send_email(['one@utah.gov', 'two@utah.gov'], '', '')

        self.assertEqual(smtp.sendmail.call_args[0][1], 'one@utah.gov,two@utah.gov')

        smtp = send_email('one@utah.gov', '', '')

        self.assertEqual(smtp.sendmail.call_args[0][1], 'one@utah.gov')

    def test_string_body(self, SMTP_mock):
        smtp = send_email('hello@utah.gov', 'subject', 'body')

        self.assertIn('Subject: subject', smtp.sendmail.call_args[0][2])
        self.assertIn('body', smtp.sendmail.call_args[0][2])

    def test_html_body(self, SMTP_mock):
        message = MIMEMultipart()
        message.attach(MIMEText('<p>test</p>', 'html'))
        message.attach(MIMEText('test'))

        smtp = send_email('hello@utah.gov', 'subject', message)

        self.assertIn('test', smtp.sendmail.call_args[0][2])
