#!/usr/bin/env python
# * coding: utf8 *
"""
slack.py
A module that holds the constructs for using the slack api
"""

import math
from datetime import datetime

from supervisor.slack import Message, SectionBlock, ContextBlock, DividerBlock, Text

from .models import Crate

MAX_CONTEXT_ELEMENTS = 10
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
                f"*{datetime.now().strftime('%B %d, %Y')}*",
                _safely_access(report, "hostname"),
                f"*{_safely_access(report, 'num_success_pallets')}* of *{_safely_access(report, 'total_pallets')}* pallets ran successfully",
                f"{percent}",
                f"total time: *{_safely_access(report, 'total_time')}*",
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

        message.add(SectionBlock(f"{success} *{_safely_access(pallet, 'name').split(':')[-1]}*"))
        message.add(
            ContextBlock(
                [
                    f"{_safely_access(pallet, 'total_processing_time')}{'  |  ' + _safely_access(pallet, 'message') if _safely_access(pallet, 'message') else ''}"
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

            text = f"{result} *{_safely_access(crate, 'name')}*"
            if show_message:
                text += "\n" + _safely_access(crate, "crate_message")

            crate_elements.append(text)

            if len(crate_elements) == MAX_CONTEXT_ELEMENTS:
                message.add(ContextBlock(crate_elements))
                crate_elements.clear()

        if len(crate_elements) > 0:
            message.add(ContextBlock(crate_elements))

    return message


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
                f"*{datetime.now().strftime('%B %d, %Y')}*",
                _safely_access(report, "hostname"),
                f"*{_safely_access(report, 'num_success_pallets')}* of *{_safely_access(report, 'total_pallets')}* pallets ran successfully",
                f"{percent}",
                f"total time: *{_safely_access(report, 'total_time')}*",
            ]
        )
    )

    message.add(DividerBlock())

    if _safely_access(report, "server_reports") and len(_safely_access(report, "server_reports")) > 0:
        for server_status in _safely_access(report, "server_reports"):
            success = ":fire:"
            if _safely_access(server_status, "success"):
                success = ":white_check_mark:"

            message.add(SectionBlock(f"{success} *{_safely_access(server_status, 'name')}*"))

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

        message.add(SectionBlock(f"{success} *{_safely_access(pallet, 'name').split(':')[-1]}*"))

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

    return message
