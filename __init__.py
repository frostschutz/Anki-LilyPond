# -*- coding: utf-8 -*-
# Copyright (c) 2012 Andreas Klauer <Andreas.Klauer@metamorpher.de>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""
LilyPond (GNU Music Typesetter) integration addon for Anki 2.

Code is based on / inspired by libanki's LaTeX integration.
"""

# --- Imports: ---

import cgi
import re
import shutil
from html.entities import entitydefs
from typing import Any
from typing import Dict

from anki import Collection
from anki.cards import Card
from anki.lang import _
from anki.media import MediaManager
from anki.models import NoteType
from anki.utils import call
from anki.utils import checksum
from anki.utils import stripHTML
from anki.utils import tmpfile
from aqt import gui_hooks
from aqt import mw
from aqt.editor import Editor
from aqt.qt import *
from aqt.utils import getOnlyText
from aqt.utils import showInfo

# --- Globals: ---

# Load configuration options
_config = mw.addonManager.getConfig(__name__)

TEMP_FILE = tmpfile("lilypond", ".ly")
LILYPOND_CMD = ["lilypond"] + _config['command_line_params'] + ["--o", TEMP_FILE, TEMP_FILE]
OUTPUT_FILE_EXT = _config["output_file_ext"]
DEFAULT_TEMPLATE = _config['default_template']
# TODO Extract these to config file?
LILYPOND_PATTERN = "%ANKI%"     # Substitution targets in templates
LILYPOND_SPLIT = "%%%"          # LilyPond code section delimiter
USER_FILES_DIR = os.path.join(mw.pm.addonFolder(), __name__, "user_files")  # Template directory
TAG_REGEXP = re.compile(r"\[lilypond(=(?P<template>[a-z0-9_-]+))?\](?P<code>.+?)\[/lilypond\]",     # Match tagged code
                        re.DOTALL | re.IGNORECASE)
FIELD_NAME_REGEXP = re.compile(r"^(?P<field>.*)-lilypond(-(?P<template>[a-z0-9_-]+))?$",    # Match LilyPond field names
                               re.DOTALL | re.IGNORECASE)
TEMPLATE_NAME_REGEXP = re.compile(r"^[a-z0-9_-]+$", re.DOTALL | re.IGNORECASE)  # Template names must match this
IMG_TAG_REGEXP = re.compile("^<img.*>$", re.DOTALL | re.IGNORECASE)


loaded_templates = {}   # Dict of template name: template code, avoids reading from file repeatedly
lilypondCache = {}      # Cache for error-producing code, avoid re-rendering erroneous code


os.environ['PATH'] = f"{os.environ['PATH']}:/usr/local/bin"     # TODO Platform independence?


# --- Templates: ---

def tpl_file(name):
    """Build the full filename for template name."""
    return os.path.join(USER_FILES_DIR, "%s.ly" % (name,))


def set_template(name, content):
    """Set and save a template."""
    loaded_templates[name] = content
    f = open(tpl_file(name), 'w')
    f.write(content)


def get_template(name: str = DEFAULT_TEMPLATE, code: str = LILYPOND_PATTERN) -> str:
    """
        Load template by name and fill it with code.
    :param name: Name of template, default is used if passed None
    :param code: LilyPond code to insert into template
    :return: Templated code
    """

    if not name:
        name = DEFAULT_TEMPLATE

    tpl = None

    if name not in loaded_templates:
        try:
            tpl = open(tpl_file(name)).read()
            if tpl and LILYPOND_PATTERN in tpl:
                loaded_templates[name] = tpl
        finally:
            if name not in loaded_templates:
                raise IOError("LilyPond Template %s not found or not valid." % (name,))

    # Replace one or more occurrences of LILYPOND_PATTERN

    codes = code.split(LILYPOND_SPLIT)

    r = loaded_templates[name]

    for code in codes:
        r = r.replace(LILYPOND_PATTERN, code, 1)

    return r


# --- GUI: ---

def templatefiles():
    """Produce list of template files."""
    return [f for f in os.listdir(USER_FILES_DIR)
            if f.endswith(".ly")]


def addtemplate():
    """Dialog to add a new template file."""
    name = getOnlyText("Please choose a name for your new LilyPond template:")

    if not TEMPLATE_NAME_REGEXP.match(name):
        showInfo("Empty template name or invalid characters.")
        return

    if os.path.exists(tpl_file(name)):
        showInfo("A template with that name already exists.")

    set_template(name)
    mw.addonManager.onEdit(tpl_file(name))


def lilypondMenu():
    """Extend the addon menu with lilypond template entries."""

    lilypond_menu = mw.form.menuTools.addMenu('Lilypond')
    a = QAction(_("Add template..."), mw)
    a.triggered.connect(lambda _, o=mw: addtemplate())
    lilypond_menu.addAction(a)

    for file in templatefiles():
        m = lilypond_menu.addMenu(os.path.splitext(file)[0])
        a = QAction(_("Edit..."), mw)
        p = os.path.join(USER_FILES_DIR, file)
        a.triggered.connect(lambda _, o=mw: mw.addonManager.onEdit(i))
        m.addAction(a)
        a = QAction(_("Delete..."), mw)
        a.triggered.connect(lambda _, o=mw: mw.addonManager.onRem(i))
        m.addAction(a)


# --- Functions: ---

def _ly_from_html(ly):
    """Convert entities and fix newlines."""

    ly = re.sub(r"<(br|div|p) */?>", "\n", ly)
    ly = stripHTML(ly)

    ly = ly.replace("&nbsp;", " ")

    for match in re.compile(r"&([a-zA-Z]+);").finditer(ly):
        if match.group(1) in entitydefs:
            ly = ly.replace(match.group(), entitydefs[match.group(1)])

    return ly


def _build_img(ly, fname):
    """
        Build the image file itself and add it to the media dir.
    :param ly: LilyPond code
    :param fname: Filename for rendered image
    :return: None if successful, else error message
    """
    lyfile = open(TEMP_FILE, "w")
    lyfile.write(ly.decode("utf-8"))
    lyfile.close()

    log = open(TEMP_FILE + ".log", "w")

    if call(LILYPOND_CMD, stdout=log, stderr=log):
        return _err_msg("lilypond")

    # add to media
    try:
        shutil.move(TEMP_FILE + OUTPUT_FILE_EXT, os.path.join(mw.col.media.dir(), fname))
    except:
        return _("Could not move LilyPond image file to media dir. No output?<br>") + _err_msg("lilypond")


def _img_link(template, ly_code) -> str:
    """
        Convert LilyPond code to an HTML img tag, rendering image if necessary.

        Note that code producing an error will be cached for performance reasons
        so Anki may need be resarted after fixing errors in LilyPond configuration, etc.
    :param template: Template, uses default if passed None
    :param ly_code: LilyPond code
    :return: HTML img tag
    """

    if not template:
        template = DEFAULT_TEMPLATE

    # Finalize LilyPond source.
    ly_code = get_template(template, ly_code)
    ly_code = ly_code.encode("utf8")

    filename = f"lilypond-{checksum(ly_code)}{OUTPUT_FILE_EXT}"

    link = f'<img src="{filename}" alt="{ly_code}">'

    # Build image if necessary.
    if os.path.exists(filename):
        # Image for given code already exists
        return link
    else:
        # Need to render image

        if filename in lilypondCache:
            # Already tried to render this code & got error
            return lilypondCache[filename]

        err = _build_img(ly_code, filename)
        if err:
            # Error rendering, cache filename (i.e. code checksum) to avoid trying to re-render in future
            # TODO Account for transient errors (i.e. beyond those in code) that can be solved by re-rendering
            lilypondCache[filename] = err
            return err
        else:
            return link


def _err_msg(type):
    """Error message, will be displayed in the card itself."""
    msg = (_("Error executing %s.") % type) + "<br>"
    try:
        log = open(TEMP_FILE + ".log", "r").read()
        if log:
            msg += """<small><pre style="text-align: left">""" + cgi.escape(log) + "</pre></small>"
    except:
        msg += _("Have you installed lilypond?")
    return msg


def _getfields(notetype: Union[NoteType,Dict[str,Any]]):
    '''Get list of field names for given note type'''
    return list(field['name'] for field in notetype['flds'])


# --- Hooks: ---

def _munge_string(text: str) -> str:
    """
        Replaces tagged LilyPond code with rendered images
    :return: Text with tags substituted in-place
    """
    for match in TAG_REGEXP.finditer(text):
        ly_code = _ly_from_html(match.group(TAG_REGEXP.groupindex['code']))
        template_name = match.group(TAG_REGEXP.groupindex['template'])
        text = text.replace(
            match.group(), _img_link(template_name, ly_code)
        )

    return text


gui_hooks.card_will_show.append(lambda html, card, kind: _munge_string(html))


def munge_field(txt: str, editor: Editor):
    """Parse -lilypond field/lilypond tags in field before saving"""
    fields = _getfields(editor.note.model())
    if field_match := FIELD_NAME_REGEXP.match(fields[editor.currentField]):
        # LilyPond field
        template_name = field_match.group(FIELD_NAME_REGEXP.groupindex['template'])

        if (dest_field := field_match.group(FIELD_NAME_REGEXP.groupindex['field']) + "-lilypondimg") in fields:
            # Target field exists, populate it
            editor.note[dest_field] = _img_link(template_name, txt)
            return txt
        else:
            # Substitute in-place

            if IMG_TAG_REGEXP.match(txt):
                # Field already contains rendered image
                return txt

            return _img_link(template_name, txt)
    else:
        # Normal field
        # Substitute LilyPond tags
        return _munge_string(txt)


gui_hooks.editor_will_munge_html.append(munge_field)


# Commenting out until I can work out how to replace the
# onEdit and onRem calls in Anki 2.1
# def profileLoaded():
#     """Monkey patch the addon manager."""
#     lilypondMenu()
#
#
# addHook("profileLoaded", profileLoaded)

anki_check = MediaManager.check


def alert(message):
    box = QMessageBox()
    box.setText(str(message))
    box.exec_()


# def lilypond_check(self, local=None):
#     files = []
#     for nid, mid, fields in self.col.db.execute("SELECT id, mid, flds FROM notes"):
#         model = self.col.models.get(mid)
#         note = self.col.getNote(nid)
#         data = [None, note.id]
#         flist = splitFields(fields)
#         fields = {}
#         for (name, (idx, conf)) in list(self.col.models.fieldMap(model).items()):
#             fields[name] = flist[idx]
#         (fields, note_files) = munge_fields(fields, model, data, self.col)
#         files = files + note_files
#     anki_results = anki_check(self, local)
#     files_to_delete = [x for x in anki_results[1] if x not in files]
#     return anki_results[0], files_to_delete, anki_results[2]
#
#
# MediaManager.check = lilypond_check

# --- End of file. ---
