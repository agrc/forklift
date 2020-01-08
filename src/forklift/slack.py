#!/usr/bin/env python
# * coding: utf8 *
'''
slack.py
A module that holds the constructs for using the slack api
'''

import math
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from json import dumps


MAX_BLOCKS = 50
MAX_CONTEXT_ELEMENTS = 10
MAX_SECTION_FIELD_ELEMENTS = 10
MAX_LENGTH_SECTION = 3000
MAX_LENGTH_SECTION_FIELD = 2000

def split(arr, size):
    result = []
    while len(arr) > size:
        piece = arr[:size]
        result.append(piece)
        arr = arr[size:]

    result.append(arr)

    return result


def lift_report_to_blocks(report):
    '''turns the forklift lift report object into blocks
    '''
    message = Message()

    message.add(SectionBlock(f':tractor:       :package: *Forklift Lift Report* :package:      :tractor:'))

    percent = report['num_success_pallets'] / report['total_pallets'] * 100
    if percent == 100:
        percent = ':100:'
    else:
        percent = f'{str(math.floor(percent))} success'

    message.add(
        ContextBlock([
            f'*{datetime.now().strftime("%B %d, %Y")}*',
            report['hostname'],
            f'*{report["num_success_pallets"]}* of *{report["total_pallets"]}* pallets ran successfully',
            f'{percent}',
            f'total time: *{report["total_time"]}*',
        ])
    )

    message.add(DividerBlock())

    if report['git_errors']:
        git_block = SectionBlock('git errors')

        for error in report['git_errors']:
            git_block.fields.append(error)

        message.add(git_block)

    if report['import_errors']:
        import_block = SectionBlock('python import errors')

        for error in report['import_errors']:
            import_block.fields.append(error)

        message.add(import_block)

    for pallet in report['pallets']:
        success = ':fire:'

        if pallet['success']:
            success = ':heavy_check_mark:'

        message.add(SectionBlock(f'{success} *{pallet["name"].split(":")[2]}*'))
        message.add(ContextBlock([f'{pallet["total_processing_time"]}{"  |  " + pallet["message"] if pallet["message"] else ""}']))

        crate_elements = []

        for crate in pallet['crates']:
            if crate['result'] in ['Data updated successfully.', 'Created table successfully.', 'No changes found.']:
                result = '🟢'
            elif crate['result'] in ['Warning generated during update and data updated successfully.']:
                result = '🟡'
            elif crate['result'] == 'Warning generated during update. Data not modified.':
                result = '🔵'
            else:
                result = ':fire:'

            text = f'{result} *{crate["name"]}*'
            crate_elements.append(text)

            if len(crate_elements) == MAX_CONTEXT_ELEMENTS:
                message.add(ContextBlock(crate_elements))
                crate_elements.clear()

        if len(crate_elements) > 0:
            message.add(ContextBlock(crate_elements))

    return message.get_messages()


class BlockType(Enum):
    '''available block type enums
    '''
    SECTION = 'section'
    DIVIDER = 'divider'
    CONTEXT = 'context'


class Block(ABC):
    '''Basis block containing attributes and behavior common to all
    Block is an abstract class and cannot be sent directly.
    '''

    def __init__(self, block):
        self.type = block

    def _attributes(self):
        return {'type': self.type.value}

    @abstractmethod
    def _resolve(self):
        pass

    def __repr__(self):
        return dumps(self._resolve(), indent=2)


class Text():
    '''A text class formatted using slacks markdown syntax
    '''

    def __init__(self, text):
        self.text = text

    def _resolve(self):
        text = {
            'type': 'mrkdwn',
            'text': self.text,
        }

        return text

    @staticmethod
    def to_text(text, max_length=None):
        if max_length and len(text) > max_length:
            text = text[:max_length]

        return Text(text=text)

    def __str__(self):
        return dumps(self._resolve(), indent=2)


class SectionBlock(Block):
    ''' A section is one of the most flexible blocks available
    '''

    def __init__(self, text=None, fields=None):
        super().__init__(block=BlockType.SECTION)

        if text is not None:
            self.text = Text.to_text(text, MAX_LENGTH_SECTION)
        if fields and len(fields) > 0:
            self.fields = [Text.to_text(field, MAX_LENGTH_SECTION_FIELD) for field in fields]

    def _resolve(self):
        section = self._attributes()

        if self.text:
            section['text'] = self.text._resolve()

        if self.fields:
            section['fields'] = [field._resolve() for field in self.fields]

        return section


class ContextBlock(Block):
    ''' Displays message context. Typically used after a section
    '''
    def __init__(self, elements):
        super().__init__(block=BlockType.CONTEXT)

        self.elements = []

        for element in elements:
            self.elements.append(Text.to_text(element, MAX_LENGTH_SECTION_FIELD))

        if len(self.elements) > MAX_CONTEXT_ELEMENTS:
            raise Exception('Context blocks can hold a maximum of ten elements')

    def _resolve(self):
        context = self._attributes()
        context['elements'] = [element._resolve() for element in self.elements]

        return context


class DividerBlock(Block):
    ''' A content divider like an <hr>
    '''

    def __init__(self):
        super().__init__(block=BlockType.DIVIDER)

    def _resolve(self):
        return self._attributes()


class Message:
    ''' A Slack message object that can be converted to a JSON string for use with
    the Slack message API.
    '''

    def __init__(self, text='', blocks=None):
        if isinstance(blocks, list):
            self.blocks = blocks
        elif isinstance(blocks, Block):
            self.blocks = [blocks]
        else:
            self.blocks = None

        self.text = text

    def add(self, block):
        if self.blocks is None:
            self.blocks = []

        self.blocks.append(block)

    def _resolve(self, blocks=None):
        if blocks is None:
            blocks = self.blocks

        message = {}
        if self.blocks:
            message['blocks'] = [block._resolve() for block in blocks]

        if self.text or self.text == '':
            message['text'] = self.text

        return message

    def json(self):
        return dumps(self._resolve(), indent=2)

    def get_messages(self):
        splits = split(self.blocks, MAX_BLOCKS)
        splits = [dumps(self._resolve(blocks), indent=2) for blocks in splits]

        return splits

    def __repr__(self):
        return self.json()

    def __getitem__(self, item):
        return self._resolve()[item]

    def keys(self):
        return self._resolve()
