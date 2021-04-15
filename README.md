LilyPond - music notation for everyone - http://lilypond.org/
=============================================================

With this addon, you can add sheet music snippets to your Anki deck,
wrapped in [lilypond]c d e[/lilypond] tags.

For this addon to work, you have to install LilyPond first.

LilyPond homepage: http://lilypond.org
LilyPond download: http://lilypond.org/download.html
LilyPond tutorial:
http://lilypond.org/doc/v2.16/Documentation/learning/index.html

This addon on GitHub: https://github.com/frostschutz/lilypond-anki


How to use
----------

This addon understands lilypond tags:

    [lilypond]c d e[/lilypond]

Alternatively, you can create fields dedicated to LilyPond, e.g.
front-lilypond or back-lilypond, and omit the lilypond tags for them:

    c d e

With lilypond in the field name, it will act as if the entire field
content was wrapped in [lilypond][/lilypond] tags.

This addon allows the creation of custom templates (see below), and
specifying which template to use:

    [lilypond=default]c d e[/lilypond]
    [lilypond=yourtemplate]c d e[/lilypond]

The name of the default template is default, so [lilypond=default] is
identical to [lilypond].

You can also use templates in lilypond fields by giving them names like
front-lilypond-yourtemplate, back-lilypond-yourtemplate, etc.


Mobile/Web support
------------------

Anki addons are desktop only, so by default, LilyPond images won't appear
on other platforms since those platforms won't know what to make of a
[lilypond] tag or how to treat a lilypond field.

However, if you are using LilyPond fields, and for each field create
another field called lilypondimg, the desktop plugin will autofill
it with the image tag.

For example, if your field is 'front-lilypond', with content 'c d e',
and you have another field 'front-lilypondimg', and use only the 'front-lilypondimg'
field in your card template, the image will appear on all platforms (provided
that the desktop plugin generated the image once and the images were synced
to the other platforms as well).

Note: Please do not add any other text to the front-lilypondimg field, as
it will be overwritten and discarded by the addon.


LilyPond Templates
------------------

The addons/lilypond directory holds template files for LilyPond.

Templates can be created and edited from within Anki, using the
Tools->Addons->lilypond-> Menu.

Please restart Anki when you change templates.

The default template is default.ly and used by:

    [lilypond]code[/lilypond]
    [lilypond=default]code[/lilypond]
    somefield-lilypond

All other templates have to be specified by name:

    [lilypond=templatename]code[/lilypond]
    somefield-lilypond-templatename

In the template, %ANKI% will be replaced with code.

Multiple codes can be specified, by separating them with %%%:

    [lilypond]
    code1
    %%%
    code2
    [/lilypond]

In the template, the first occurence of %ANKI% will be replaced with
code1, the second occurence of %ANKI% with code2.

The number of %ANKI% in the template has to match the number of codes
used for this template always, otherwise the remaining occurences of
%ANKI% will not be replaced, or the surplus specified codes will not be
inserted.

The default template looks like this:

    \paper{
      indent=0\mm
      line-width=120\mm
      oddFooterMarkup=##f
      oddHeaderMarkup=##f
      bookTitleMarkup = ##f
      scoreTitleMarkup = ##f
    }

    \relative c'' { %ANKI% }

Please refer to the LilyPond homepage and documentation for details on
how to write LilyPond code.
