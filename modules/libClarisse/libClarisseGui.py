"""
A series of generic clarisse UI functions.
"""

try:
    import ix
except ImportError:
    ix = None


# ------------------------------------------------------------------------------
def display_yes_no_dialog(msg, title):
    """
    Displays dialog box with a yes/no choice.

    :param msg: The message to display.

    :param title: The title of the dialog box.

    :return: True if the user's choice is "yes", False if they choose "no".
    """

    dlg = ix.application.message_box(msg, title, ix.api.AppDialog.cancel(),
                                     ix.api.AppDialog.STYLE_YES_NO)

    return dlg.is_yes()


# ------------------------------------------------------------------------------
def display_message_dialog(msg, title):
    """
    Displays a dialog box containing a simple message.

    :param msg: The message to display.

    :param title: The title of the dialog box.

    :return: Nothing.
    """

    ix.application.message_box(msg, title, ix.api.AppDialog.ok(),
                               ix.api.AppDialog.STYLE_OK)


# ------------------------------------------------------------------------------
def display_error_dialog(msg, title):
    """
    Display an error message.

    :param msg: The message to display.

    :param title: The title of the dialog box.
    """

    ix.application.message_box(msg, title, ix.api.AppDialog.cancel(),
                               ix.api.AppDialog.STYLE_OK)


# ------------------------------------------------------------------------------
def display_get_path_dialog(title):
    """
    Displays dialog box requesting a directory from the user.

    :param title: The title of the dialog box.

    :return: The path to the dialog chosen by the user. None if the user presses
    "cancel".
    """

    path = ix.api.GuiWidget.open_folder(ix.application, '', title)

    if path == "":
        return None

    return path


# ------------------------------------------------------------------------------
def display_get_text_dialog(msg, title):
    """
    Displays dialog box requesting a directory from the user.

    :param msg: The message to display.

    :param title: The title of the dialog box.

    :return: The text entered by the user.
    """

    text = ix.api.GuiWidget.open_folder(ix.application, '', title)

    return text
