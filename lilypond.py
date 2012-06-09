# -*- coding: utf-8 -*-
# Copyright (c) 2012 Andreas Klauer <Andreas.Klauer@metamorpher.de>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

'''
LilyPond (GNU Music Typesetter) integration addon for Anki 2.

Code is based on / inspired by libanki's LaTeX integration.
'''

# --- Imports: ---

from anki.hooks import addHook, wrap
from anki.lang import _
from anki.utils import call, checksum, stripHTML, tmpfile
from aqt import mw
from aqt.qt import *
from aqt.utils import getOnlyText, showInfo
from htmlentitydefs import entitydefs
import cgi, os, re, shutil

# --- Globals: ---

# http://lilypond.org/doc/v2.14/Documentation/usage/lilypond-output-in-other-programs#inserting-lilypond-output-into-other-programs

lilypondFile = tmpfile("lilypond", ".ly")
lilypondCmd = ["lilypond", "-dbackend=eps", "-dno-gs-load-fonts", "-dinclude-eps-fonts", "--o", lilypondFile, "--png", lilypondFile]
lilypondPattern = "%ANKI%"
lilypondTemplate = u"""
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
lilypondDir = os.path.join(mw.pm.addonFolder(), "lilypond")
lilypondRegexp = re.compile(r"\[lilypond(|=([a-z0-9_-]+))\](.+?)\[/lilypond\]", re.DOTALL | re.IGNORECASE)
lilypondFieldRegexp = re.compile(r"lilypond(|-([a-z0-9_-]+))$", re.DOTALL | re.IGNORECASE)
lilypondNameRegexp = re.compile(r"^[a-z0-9_-]+$", re.DOTALL | re.IGNORECASE)
lilypondCache = {}

# --- Templates: ---

def tpl_file(name):
    '''Build the full filename for template name.'''
    return os.path.join(lilypondDir, "%s.ly" % (name,))

def setTemplate(name, content):
    '''Set and save a template.'''
    lilypondTemplates[name] = content
    f = open(tpl_file(name), 'w')
    f.write(content)

def getTemplate(name, code):
    '''Load template by name and fill it with code.'''
    pattern = "%ANKI%"

    if name is None:
        name="default"

    tpl = None

    if name not in lilypondTemplates:
        try:
            tpl = open(tpl_file(name)).read()
            if tpl and pattern in tpl:
                lilypondTemplates[name] = tpl
        except:
            if name == "default":
                tpl = lilypondTemplate
                setTemplate("default", tpl)
        finally:
            if name not in lilypondTemplates:
                raise IOError, "LilyPond Template %s not found or not valid." % (name,)

    return lilypondTemplates[name].replace(pattern, code)

# --- GUI: ---

def templatefiles():
    '''Produce list of template files.'''
    return [f for f in os.listdir(lilypondDir)
            if f.endswith(".ly")]

def addtemplate():
    '''Dialog to add a new template file.'''
    name = getOnlyText("Please choose a name for your new LilyPond template:")

    if not lilypondNameRegexp.match(name):
        showInfo("Empty template name or invalid characters.")
        return

    if os.path.exists(tpl_file(name)):
        showInfo("A template with that name already exists.")

    setTemplate(name, lilypondTemplate)
    mw.addonManager.onEdit(tpl_file(name))

def lilypondMenu():
    '''Extend the addon menu with lilypond template entries.'''
    lm = None

    for action in mw.form.menuPlugins.actions():
        menu = action.menu()
        if menu and menu.title() == "lilypond":
            lm = menu
            break

    if not lm:
        return

    a = QAction(_("Add template..."), mw)
    mw.connect(a, SIGNAL("triggered()"), addtemplate)
    lm.addAction(a)

    for file in templatefiles():
        m = lm.addMenu(os.path.splitext(file)[0])

        a = QAction(_("Edit..."), mw)
        p = os.path.join(lilypondDir, file)
        mw.connect(a, SIGNAL("triggered()"),
                   lambda p=p: mw.addonManager.onEdit(p))
        m.addAction(a)
        a = QAction(_("Delete..."), mw)
        mw.connect(a, SIGNAL("triggered()"),
                   lambda p=p: mw.addonManager.onRem(p))
        m.addAction(a)

# --- Functions: ---

def _lyFromHtml(ly):
    '''Convert entities and fix newlines.'''
    ly = ly.replace("&nbsp;", " ")

    for match in re.compile(r"&([a-zA-Z]+);").finditer(ly):
        if match.group(1) in entitydefs:
            ly = ly.replace(match.group(), entitydefs[match.group(1)])
    ly = re.sub(r"<(br|div|p) */?>", "\n", ly)
    ly = stripHTML(ly)
    return ly


def _buildImg(col, ly, fname):
    '''Build the image PNG file itself and add it to the media dir.'''
    lyfile = open(lilypondFile, "w")
    lyfile.write(ly)
    lyfile.close()

    log = open(lilypondFile+".log", "w")

    if call(lilypondCmd, stdout=log, stderr=log):
        return _errMsg("lilypond")

    # add to media
    try:
        shutil.copyfile(lilypondFile+".png", os.path.join(col.media.dir(), fname))
    except:
        return _("Could not copy LilyPond PNG file to media dir. No output?<br>")+_errMsg("lilypond")

def _imgLink(col, template, ly):
    '''Build an <img src> link for given LilyPond code.'''
    # Finalize LilyPond source.
    ly = getTemplate(template, ly)
    ly = ly.encode("utf8")

    # Derive image filename from source.
    fname = "lilypond-%s.png" % (checksum(ly),)
    link = '<img src="%s">' % (fname,)

    # Build image if necessary.
    if os.path.exists(fname):
        return link
    else:
        # avoid errornous cards killing performance
        if fname in lilypondCache:
            return lilypondCache[fname]

        err = _buildImg(col, ly, fname)
        if err:
            lilypondCache[fname] = err
            return err
        else:
            return link

def _errMsg(type):
    '''Error message, will be displayed in the card itself.'''
    msg = (_("Error executing %s.") % type) + "<br>"
    try:
        log = open(lilypondFile+".log", "r").read()
        if log:
            msg += """<small><pre style="text-align: left">""" + cgi.escape(log) + "</pre></small>"
    except:
        msg += _("Have you installed lilypond?")
    return msg

# --- Hooks: ---

def mungeFields(fields, model, data, col):
    '''Parse lilypond tags before they are displayed.'''
    for fld in model['flds']:
        field = fld['name']

        # check field name
        match = lilypondFieldRegexp.search(field)

        if match:
            # special case: empty string or (fieldname) for the card browser
            if fields[field] and fields[field] != "(%s)" % (field,):
                fields[field] = _imgLink(col, match.group(2), _lyFromHtml(fields[field]))
            continue

        # check field contents
        for match in lilypondRegexp.finditer(fields[field]):
            fields[field] = fields[field].replace(
                match.group(), _imgLink(col, match.group(2), _lyFromHtml(match.group(3)))
            )

    return fields

addHook("mungeFields", mungeFields)

def profileLoaded():
    '''Monkey patch the addon manager.'''
    mw.addonManager.rebuildAddonsMenu = wrap(mw.addonManager.rebuildAddonsMenu,
                                             lilypondMenu)
    mw.addonManager.rebuildAddonsMenu()

addHook("profileLoaded", profileLoaded)

# --- End of file. ---
