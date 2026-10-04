def _clean_list(values):
    """
    Remove empty values from a list.
    """
    if not values:
        return []

    return [
        str(value).strip()
        for value in values
        if str(value).strip()
    ]


def _clean_dict(values):
    """
    Convert field_values dictionary into readable text.
    """
    if not values:
        return ""

    parts = []

    for key, value in values.items():

        key = str(key).strip()
        value = str(value).strip()

        if key and value:
            parts.append(
                f"{key}: {value}"
            )

    return "\n".join(parts)


def build_screenshot_text(record, screenshot_id):
    """
    Build semantically meaningful text for embedding.

    We intentionally exclude noisy OCR fields such as
    buttons, labels and menus from the embedding text.
    They remain available as Neo4j properties.
    """

    screen_name = str(
        record.get("screen_name", "")
    ).strip()

    module = str(
        record.get("module", "")
    ).strip()

    dialog_boxes = _clean_list(
        record.get("dialog_boxes", [])
    )

    tables = _clean_list(
        record.get("tables", [])
    )

    warning_messages = _clean_list(
        record.get("warning_messages", [])
    )

    error_messages = _clean_list(
        record.get("error_messages", [])
    )

    field_values = _clean_dict(
        record.get("field_values", {})
    )

    user_action = str(
        record.get("user_action", "")
    ).strip()

    parts = []

    parts.append(
        f"Screenshot ID: {screenshot_id}"
    )

    if screen_name:
        parts.append(
            f"Screen: {screen_name}"
        )

    if module:
        parts.append(
            f"Module: {module}"
        )

    if dialog_boxes:
        parts.append(
            "Dialog Boxes:\n"
            + "\n".join(dialog_boxes)
        )

    if tables:
        parts.append(
            "Tables:\n"
            + "\n".join(tables)
        )

    if warning_messages:
        parts.append(
            "Warning Messages:\n"
            + "\n".join(warning_messages)
        )

    if error_messages:
        parts.append(
            "Error Messages:\n"
            + "\n".join(error_messages)
        )

    if field_values:
        parts.append(
            "Field Values:\n"
            + field_values
        )

    if user_action:
        parts.append(
            "User Action:\n"
            + user_action
        )

    return "\n\n".join(parts)