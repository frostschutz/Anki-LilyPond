LilyPond Templates for Integration Addon
----------------------------------------

This directory holds template files for LilyPond.

Templates can be created and edited from within Anki, 
using the Tools->Addons->lilypond-> Menu.

Please restart Anki when you change templates.

The default template is default.ly and used by:

    [lilypond]code[/lilypond]
    [lilypond=default]code[/lilypond]
    somefield-lilypond

All other templates have to be specified by name:

    [lilypond=name]code[/lilypond]
    somefield-lilypond-name

In the template, %ANKI% will be replaced with code.

Multiple codes can be specified, by separating them with %%%:

    [lilypond]
    code1
    %%%
    code2
    [/lilypond]

In the template, the first occurence of %ANKI% will be replaced
with code1, the second occurence of %ANKI% with code2.

The number of %ANKI% in the template has to match the number 
of codes used for this template always, otherwise the
remaining occurences of %ANKI% will not be replaced, or the 
surplus specified codes will not be inserted.
