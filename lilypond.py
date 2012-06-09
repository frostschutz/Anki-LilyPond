# -*- coding: utf-8 -*-
# Copyright (c) 2012 Andreas Klauer <Andreas.Klauer@metamorpher.de>
# License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

'''
LilyPond (GNU Music Typesetter) integration addon for Anki 2.

Code is based on / inspired by libanki's LaTeX integration.
'''

# --- Imports: ---

from anki.hooks import addHook
from anki.lang import _
from anki.utils import call, checksum, stripHTML, tmpfile
from aqt import mw
from aqt.qt import *
from htmlentitydefs import entitydefs
import cgi, os, re, shutil

# --- Globals: ---

# http://lilypond.org/doc/v2.14/Documentation/usage/lilypond-output-in-other-programs#inserting-lilypond-output-into-other-programs

lilypondFile = tmpfile("lilypond", ".ly")
lilypondCmd = ["lilypond", "-dbackend=eps", "-dno-gs-load-fonts", "-dinclude-eps-fonts", "--o", lilypondFile, "--png", lilypondFile]
lilypondTemplates = {}
lilypondRegexp = re.compile(r"\[lilypond(|=([a-z0-9_-]+))\](.+?)\[/lilypond\]", re.DOTALL | re.IGNORECASE)

# --- Templates: ---

def tpl_file(name):
    return os.path.join(mw.pm.addonFolder(), "lilypond", "%s.ly" % (name,))

def setTemplate(name, content):
    lilypondTemplates[name] = content
    f = open(tpl_file(name), 'w')
    f.write(content)

def getTemplate(name, code):
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
                tpl = u"""
\\paper{
  indent=0\\mm
  line-width=120\\mm
  oddFooterMarkup=##f
  oddHeaderMarkup=##f
  bookTitleMarkup = ##f
  scoreTitleMarkup = ##f
}

\\relative c'' { %s }
""" % (pattern,)
                setTemplate("default", tpl)
        finally:
            if name not in lilypondTemplates:
                raise IOError, "LilyPond Template %s not found or not valid." % (name,)

    return lilypondTemplates[name].replace(pattern, code)

# --- Functions: ---

def _lyFromHtml(ly):
    "Convert entities and fix newlines."
    ly = ly.replace("&nbsp;", " ")

    for match in re.compile(r"&([a-zA-Z]+);").finditer(ly):
        if match.group(1) in entitydefs:
            ly = ly.replace(match.group(), entitydefs[match.group(1)])
    ly = re.sub(r"<(br|div|p) */?>", "\n", ly)
    ly = stripHTML(ly)
    return ly


def _buildImg(col, ly, fname):
    print "buildImg", ly

    lyfile = open(lilypondFile, "w")
    lyfile.write(ly)
    lyfile.close()

    log = open(lilypondFile+".log", "w")

    if call(lilypondCmd, stdout=log, stderr=log):
        return _errMsg("lilypond")

    # add to media
    shutil.copyfile(lilypondFile+".png", os.path.join(col.media.dir(), fname))

def _imgLink(col, template, ly):
    print "_imgLink", ly

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
        err = _buildImg(col, ly, fname)
        if err:
            return err
        else:
            return link

def _errMsg(type):
    msg = (_("Error executing %s.") % type) + "<br>"
    try:
        log = open(lilypondFile+".log", "r").read()
        if not log:
            raise Exception()
        msg += """<small><pre style="text-align: left">""" + cgi.escape(log) + "</pre></small>"
    except:
        msg += _("Have you installed lilypond?")
        pass
    return msg

# --- Hooks: ---

def mungeFields(fields, model, data, col):
    for fld in model['flds']:
        field = fld['name']

        print "checking", fields[field], "..."

        for match in lilypondRegexp.finditer(fields[field]):
            print "match", match.group()
            fields[field] = fields[field].replace(
                match.group(), _imgLink(col, match.group(2), _lyFromHtml(match.group(3)))
            )

    return fields

addHook("mungeFields", mungeFields)

# --- End of file. ---
