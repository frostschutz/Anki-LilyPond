# -*- coding: utf-8 -*-
# Copyright (c) 2012 Andreas Klauer <Andreas.Klauer@metamorpher.de>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

"""
LilyPond (GNU Music Typesetter) integration addon for Anki 2.

Code is based on / inspired by libanki's LaTeX integration.
"""

# --- Imports: ---

import cgi
import os
import re
import shutil
from html.entities import entitydefs

from anki.hooks import addHook
from anki.lang import _
from anki.media import MediaManager
from anki.utils import call
from anki.utils import checksum
from anki.utils import splitFields
from anki.utils import stripHTML
from anki.utils import tmpfile
from aqt import mw
from aqt.qt import *
from aqt.utils import getOnlyText
from aqt.utils import showInfo

# --- Globals: ---

# http://lilypond.org/doc/v2.14/Documentation/usage/lilypond-output-in-other-programs#inserting-lilypond-output-into-other-programs

lilypondFile = tmpfile("lilypond", ".ly")
os.environ['PATH'] = f"{os.environ['PATH']}:/usr/local/bin"
lilypondCmd = ["lilypond", "-dbackend=eps", "-dno-gs-load-fonts", "-dinclude-eps-fonts",
               "--o", lilypondFile, "--png", lilypondFile]
lilypondPattern = "%ANKI%"
lilypondSplit = "%%%"
lilypondTemplate = """
\\paper{
  indent=0\\mm
  line-width=120\\mm
  oddFooterMarkup=##f
  oddHeaderMarkup=##f
  bookTitleMarkup = ##f
  scoreTitleMarkup = ##f
}

\\relative c'' { %s }
""" % (lilypondPattern,)
lilypondTemplates = {}
lilypondDir = os.path.join(mw.pm.addonFolder(), __name__, "lilypond")
lilypondRegexp = re.compile(r"\[lilypond(|=([a-z0-9_-]+))\](.+?)\[/lilypond\]", re.DOTALL | re.IGNORECASE)
lilypondFieldRegexp = re.compile(r"lilypond(|-([a-z0-9_-]+))$", re.DOTALL | re.IGNORECASE)
lilypondNameRegexp = re.compile(r"^[a-z0-9_-]+$", re.DOTALL | re.IGNORECASE)
lilypondCache = {}


# --- Templates: ---

def tpl_file(name):
    """Build the full filename for template name."""
    return os.path.join(lilypondDir, "%s.ly" % (name,))


def set_template(name, content):
    """Set and save a template."""
    lilypondTemplates[name] = content
    f = open(tpl_file(name), 'w')
    f.write(content)


def get_template(name, code):
    """Load template by name and fill it with code."""
    if name is None:
        name = "default"

    tpl = None

    if name not in lilypondTemplates:
        try:
            tpl = open(tpl_file(name)).read()
            if tpl and lilypondPattern in tpl:
                lilypondTemplates[name] = tpl
        except:
            if name == "default":
                tpl = lilypondTemplate
                set_template("default", tpl)
        finally:
            if name not in lilypondTemplates:
                raise IOError("LilyPond Template %s not found or not valid." % (name,))

    # Replace one or more occurences of lilypondPattern

    codes = code.split(lilypondSplit)

    r = lilypondTemplates[name]

    for code in codes:
        r = r.replace(lilypondPattern, code, 1)

    return r


# --- GUI: ---

def templatefiles():
    """Produce list of template files."""
    return [f for f in os.listdir(lilypondDir)
            if f.endswith(".ly")]


def addtemplate():
    """Dialog to add a new template file."""
    name = getOnlyText("Please choose a name for your new LilyPond template:")

    if not lilypondNameRegexp.match(name):
        showInfo("Empty template name or invalid characters.")
        return

    if os.path.exists(tpl_file(name)):
        showInfo("A template with that name already exists.")

    set_template(name, lilypondTemplate)
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
        p = os.path.join(lilypondDir, file)
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


def _build_img(col, ly, fname):
    """Build the image PNG file itself and add it to the media dir."""
    lyfile = open(lilypondFile, "w")
    lyfile.write(ly.decode("utf-8"))
    lyfile.close()

    log = open(lilypondFile + ".log", "w")

    if call(lilypondCmd, stdout=log, stderr=log):
        return _err_msg("lilypond")

    # add to media
    try:
        shutil.move(lilypondFile + ".png", os.path.join(col.media.dir(), fname))
    except:
        return _("Could not move LilyPond PNG file to media dir. No output?<br>") + _err_msg("lilypond")


def _img_link(col, template, ly, filename):
    """Build an <img src> link for given LilyPond code."""

    # Finalize LilyPond source.
    ly = get_template(template, ly)
    ly = ly.encode("utf8")

    link = '<img src="%s">' % (filename,)

    # Build image if necessary.
    if os.path.exists(filename):
        return link
    else:
        # avoid errornous cards killing performance
        if filename in lilypondCache:
            return lilypondCache[filename]

        err = _build_img(col, ly, filename)
        if err:
            lilypondCache[filename] = err
            return err
        else:
            return link


def _err_msg(type):
    """Error message, will be displayed in the card itself."""
    msg = (_("Error executing %s.") % type) + "<br>"
    try:
        log = open(lilypondFile + ".log", "r").read()
        if log:
            msg += """<small><pre style="text-align: left">""" + cgi.escape(log) + "</pre></small>"
    except:
        msg += _("Have you installed lilypond?")
    return msg


# --- Hooks: ---

def munge_fields_with_file_list(fields, model, data, col):
    """Parse lilypond tags before they are displayed."""

    files = []

    # Ignore duplicated mungeFields call for the answer side.
    if 'FrontSide' in fields:
        return fields, []

    for fld in model['flds']:
        field = fld['name']

        # check field name
        match = lilypondFieldRegexp.search(field)

        # Derive image filename from source.

        if match \
                and fields[field] != "(%s)" % (field,) \
                and fields[field] != "ankiflag":
            ly = _ly_from_html(fields[field])
            filename = "lilypond-%s.png" % (checksum(ly),)
            files.append(filename)
            fields[field] = _img_link(col, match.group(2), ly, filename)

            # autofill field for web:
            imgfield = field.replace("lilypond", "lilypondimg", 1)
            if imgfield in fields and fields[field] != fields[imgfield]:
                fields[imgfield] = fields[field]
                col.findReplace((data[1],), "^.*$", fields[field], regex=True, field=imgfield)
            continue

        # check field contents
        for match in lilypondRegexp.finditer(fields[field]):
            ly = _ly_from_html(match.group(3))
            filename = "lilypond-%s.png" % (checksum(ly),)
            files.append(filename)
            fields[field] = fields[field].replace(
                match.group(), _img_link(col, match.group(2), ly, filename)
            )
    return fields, files


def munge_fields(fields, model, data, col):
    lilypond_munge = munge_fields_with_file_list(fields, model, data, col)[0]
    return lilypond_munge


addHook("mungeFields", munge_fields)


def profileLoaded():
    """Monkey patch the addon manager."""
    get_template(None, "")  # creates default.ly if does not exist

    # Commenting out until I can work out how to replace the
    # onEdit and onRem calls in Anki 2.1
    # lilypondMenu()


addHook("profileLoaded", profileLoaded)

anki_check = MediaManager.check


def alert(message):
    box = QMessageBox()
    box.setText(str(message))
    box.exec_()


def lilypond_check(self, local=None):
    files = []
    for nid, mid, fields in self.col.db.execute("SELECT id, mid, flds FROM notes"):
        model = self.col.models.get(mid)
        note = self.col.getNote(nid)
        data = [None, note.id]
        flist = splitFields(fields)
        fields = {}
        for (name, (idx, conf)) in list(self.col.models.fieldMap(model).items()):
            fields[name] = flist[idx]
        (fields, note_files) = munge_fields_with_file_list(fields, model, data, self.col)
        files = files + note_files
    anki_results = anki_check(self, local)
    files_to_delete = [x for x in anki_results[1] if x not in files]
    return anki_results[0], files_to_delete, anki_results[2]


MediaManager.check = lilypond_check

# --- End of file. ---
