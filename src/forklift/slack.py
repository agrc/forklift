#!/usr/bin/env python
# * coding: utf8 *
"""
slack.py
A module that holds the constructs for using the slack api
"""

import math
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from json import dumps

from .models import Crate

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


def _safely_access(report, prop):
    if prop not in report:
        return None

    value = report[prop]

    if isinstance(value, Exception):
        return str(value)

    return value


def lift_report_to_blocks(report):
    """turns the forklift lift report object into slack blocks"""
    message = Message()

    message.add(SectionBlock(":tractor:       :package: *Forklift Lift Report* :package:      :tractor:"))

    percent = _safely_access(report, "num_success_pallets") / _safely_access(report, "total_pallets") * 100
    if percent == 100:
        percent = ":100:"
    else:
        percent = f"{str(math.floor(percent))}% success"

    message.add(
        ContextBlock(
            [
                f'*{datetime.now().strftime("%B %d, %Y")}*',
                _safely_access(report, "hostname"),
                f'*{_safely_access(report, "num_success_pallets")}* of *{_safely_access(report, "total_pallets")}* pallets ran successfully',
                f"{percent}",
                f'total time: *{_safely_access(report, "total_time")}*',
            ]
        )
    )

    message.add(DividerBlock())

    if _safely_access(report, "git_errors"):
        git_block = SectionBlock("git errors")

        for error in _safely_access(report, "git_errors"):
            git_block.fields.append(Text.to_text(error, MAX_LENGTH_SECTION_FIELD))

        message.add(git_block)

    if _safely_access(report, "import_errors"):
        import_block = SectionBlock("python import errors")

        for error in _safely_access(report, "import_errors"):
            import_block.fields.append(Text.to_text(error, MAX_LENGTH_SECTION_FIELD))

        message.add(import_block)

    for pallet in _safely_access(report, "pallets"):
        success = ":fire:"

        if _safely_access(pallet, "success"):
            success = ":heavy_check_mark:"

        message.add(SectionBlock(f'{success} *{_safely_access(pallet, "name").split(":")[-1]}*'))
        message.add(
            ContextBlock(
                [
                    f'{_safely_access(pallet, "total_processing_time")}{"  |  " + _safely_access(pallet, "message") if _safely_access(pallet, "message") else ""}'
                ]
            )
        )

        crate_elements = []

        for crate in _safely_access(pallet, "crates"):
            show_message = False
            if _safely_access(crate, "result") in [Crate.CREATED, Crate.UPDATED, Crate.NO_CHANGES]:
                result = "🟢"
            elif _safely_access(crate, "result") in [Crate.UPDATED_OR_CREATED_WITH_WARNINGS]:
                result = "🟡"
            elif _safely_access(crate, "result") == Crate.WARNING:
                result = "🔵"
            else:
                show_message = True
                result = ":fire:"

            text = f'{result} *{_safely_access(crate, "name")}*'
            if show_message:
                text += "\n" + _safely_access(crate, "crate_message")

            crate_elements.append(text)

            if len(crate_elements) == MAX_CONTEXT_ELEMENTS:
                message.add(ContextBlock(crate_elements))
                crate_elements.clear()

        if len(crate_elements) > 0:
            message.add(ContextBlock(crate_elements))

    return message.get_messages()


def ship_report_to_blocks(report):
    """turns the forklift ship report object into slack blocks"""
    message = Message()

    message.add(SectionBlock(":tractor:       :rocket: *Forklift Ship Report* :rocket:      :tractor:"))

    percent = _safely_access(report, "num_success_pallets") / _safely_access(report, "total_pallets") * 100
    if percent == 100:
        percent = ":100:"
    else:
        percent = f"{str(math.floor(percent))}% success"

    message.add(
        ContextBlock(
            [
                f'*{datetime.now().strftime("%B %d, %Y")}*',
                _safely_access(report, "hostname"),
                f'*{_safely_access(report, "num_success_pallets")}* of *{_safely_access(report, "total_pallets")}* pallets ran successfully',
                f"{percent}",
                f'total time: *{_safely_access(report, "total_time")}*',
            ]
        )
    )

    message.add(DividerBlock())

    if _safely_access(report, "server_reports") and len(_safely_access(report, "server_reports")) > 0:
        for server_status in _safely_access(report, "server_reports"):
            success = ":fire:"
            if _safely_access(server_status, "success"):
                success = ":white_check_mark:"

            message.add(SectionBlock(f'{success} *{_safely_access(server_status, "name")}*'))

            if server_status.get("has_service_issues", False):
                items = split(_safely_access(server_status, "problem_services"), MAX_CONTEXT_ELEMENTS)

                for item in items:
                    message.add(ContextBlock(item))
            elif _safely_access(server_status, "success"):
                message.add(ContextBlock([":rocket: All services started"]))

            if len(_safely_access(server_status, "message")) > 0:
                message.add(ContextBlock([_safely_access(server_status, "message")]))

            message.add(SectionBlock("Datasets shipped"))

            shipped_data = ["No data updated"]
            if len(_safely_access(server_status, "successful_copies")) > 0:
                shipped_data = _safely_access(server_status, "successful_copies")

            items = split(shipped_data, MAX_CONTEXT_ELEMENTS)

            for item in items:
                message.add(ContextBlock(item))

            message.add(DividerBlock())

    message.add(SectionBlock("*Pallets Report*"))

    for pallet in _safely_access(report, "pallets"):
        success = ":fire:"

        if _safely_access(pallet, "success"):
            success = ":heavy_check_mark:"

        message.add(SectionBlock(f'{success} *{_safely_access(pallet, "name").split(":")[-1]}*'))

        post_copy_processed = shipped = ":red_circle:"
        if _safely_access(pallet, "post_copy_processed"):
            post_copy_processed = ":white_check_mark:"
        if _safely_access(pallet, "shipped"):
            shipped = ":white_check_mark:"

        elements = [_safely_access(pallet, "total_processing_time")]

        if _safely_access(pallet, "message"):
            elements.append(_safely_access(pallet, "message"))

        elements.append(f"Post copy processed: {post_copy_processed}")
        elements.append(f"Shipped: {shipped}")

        items = split(elements, MAX_CONTEXT_ELEMENTS)
        for item in items:
            message.add(ContextBlock(item))

    return message.get_messages()


class BlockType(Enum):
    """available block type enums"""

    SECTION = "section"
    DIVIDER = "divider"
    CONTEXT = "context"


class Block(ABC):
    """Basis block containing attributes and behavior common to all
    Block is an abstract class and cannot be sent directly.
    """

    def __init__(self, block):
        self.type = block

    def _attributes(self):
        return {"type": self.type.value}

    @abstractmethod
    def _resolve(self):
        pass

    def __repr__(self):
        return dumps(self._resolve(), indent=2)


class Text:
    """A text class formatted using slacks markdown syntax"""

    def __init__(self, text):
        self.text = text

    def _resolve(self):
        text = {
            "type": "mrkdwn",
            "text": self.text,
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
    """A section is one of the most flexible blocks available"""

    def __init__(self, text=None, fields=None):
        super().__init__(block=BlockType.SECTION)
        self.fields = []

        if text is not None:
            self.text = Text.to_text(text, MAX_LENGTH_SECTION)
        if fields and len(fields) > 0:
            self.fields = [Text.to_text(field, MAX_LENGTH_SECTION_FIELD) for field in fields]

    def _resolve(self):
        section = self._attributes()

        if self.text:
            section["text"] = self.text._resolve()

        if self.fields and len(self.fields) > 0:
            section["fields"] = [field._resolve() for field in self.fields]

        return section


class ContextBlock(Block):
    """Displays message context. Typically used after a section"""

    def __init__(self, elements):
        super().__init__(block=BlockType.CONTEXT)

        self.elements = []

        for element in elements:
            self.elements.append(Text.to_text(element, MAX_LENGTH_SECTION_FIELD))

        if len(self.elements) > MAX_CONTEXT_ELEMENTS:
            raise Exception("Context blocks can hold a maximum of ten elements")

    def _resolve(self):
        context = self._attributes()
        context["elements"] = [element._resolve() for element in self.elements]

        return context


class DividerBlock(Block):
    """A content divider like an <hr>"""

    def __init__(self):
        super().__init__(block=BlockType.DIVIDER)

    def _resolve(self):
        return self._attributes()


class Message:
    """A Slack message object that can be converted to a JSON string for use with
    the Slack message API.
    """

    def __init__(self, text="", blocks=None):
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
            message["blocks"] = [block._resolve() for block in blocks]

        if self.text or self.text == "":
            message["text"] = self.text

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
