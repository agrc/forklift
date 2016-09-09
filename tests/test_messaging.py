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
from os import environ


@patch('forklift.messaging.get_config_prop')
@patch('forklift.messaging.SMTP', autospec=True)
class SendEmail(unittest.TestCase):
    def setUp(self):
        environ['FORKLIFT_FROM_ADDRESS'] = 'test'
        environ['FORKLIFT_SMTP_SERVER'] = 'test'
        environ['FORKLIFT_SMTP_PORT'] = 'test'

    def test_to_addresses(self, SMTP_mock, get_config_prop_mock):
        get_config_prop_mock.return_value = True
        smtp = send_email(['one@utah.gov', 'two@utah.gov'], '', '', attachment='None')

        self.assertEqual(smtp.sendmail.call_args[0][1], ['one@utah.gov', 'two@utah.gov'])

        smtp = send_email('one@utah.gov', '', '', attachment='None')

        self.assertEqual(smtp.sendmail.call_args[0][1], 'one@utah.gov')

    def test_string_body(self, SMTP_mock, get_config_prop_mock):
        get_config_prop_mock.return_value = True
        smtp = send_email('hello@utah.gov', 'subject', 'body', attachment='None')

        self.assertIn('Subject: subject', smtp.sendmail.call_args[0][2])
        self.assertIn('body', smtp.sendmail.call_args[0][2])

    def test_html_body(self, SMTP_mock, get_config_prop_mock):
        get_config_prop_mock.return_value = True
        message = MIMEMultipart()
        message.attach(MIMEText('<p>test</p>', 'html'))
        message.attach(MIMEText('test'))

        smtp = send_email('hello@utah.gov', 'subject', message, attachment='None')

        self.assertIn('test', smtp.sendmail.call_args[0][2])

    def test_send_emails_false(self, SMTP_mock, get_config_prop_mock):
        get_config_prop_mock.return_value = False

        self.assertIsNone(send_email('hello@utah.gov', 'subject', 'body', attachment='None'))
