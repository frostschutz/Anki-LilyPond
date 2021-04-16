# [LilyPond](https://lilypond.org/) integration for [Anki](https://apps.ankiweb.net/)

Add sheet music snippets to your Anki deck, wrapped in `[lilypond][/lilypond]` tags.

This addon requires LilyPond in order to work.

## How to use

* Wrap inline LilyPond code in tags:
  ```
  [lilypond]c d e[/lilypond]
  ```

* Create fields for LilyPond code with `-lilypond` at the end of the field's name,
  e.g. `front-lilypond` or `back-lilypond`. The entire contents of which will be
  rendered, tags not required:
  ```
  c d e
  ```

Please refer to the LilyPond homepage and documentation for details on
how to write LilyPond code.


### Templates

The styling of LilyPond output is controlled by templates. The default template looks
like this: 

```
\paper{
  indent=0\mm
  line-width=120\mm
  oddFooterMarkup=##f 
  oddHeaderMarkup=##f 
  bookTitleMarkup = ##f 
  scoreTitleMarkup = ##f 
}

{ %ANKI% }
```

Where `%ANKI%` will be replaced with the code to be rendered.

You can add your own templates to the `user_files` directory in the addoon's files
(see `Tools -> Addons -> LilyPond Integration -> View Files`). You'll need to restart
Anki after making any changes.

To use a template called `exampleTemplate`:
* In inline tags:
  ```
  [lilypond=exampleTemplate]c d e[/lilypond]
  ```
* In a LilyPond field add `-exampleTemplate` to the end of the field's name, e.g.
  `front-lilypond-exampleTemplate`.
  

#### Multi-part templates 

You can create a template with multiple occurrences of `%ANKI%`, then separate sections
of code with `%%%` which will then be substituted in to the corresponding occurrences.

For example with the LilyPond code 
```
c d e
%%%
f g a
```

the first occurrence of `%ANKI%` in the template will be replaced with `c d e`, and
the second occurrence of `%ANKI%` with will be replaced with `f g a`.

Surplus occurrences of `%ANKI%` in the template will be left as-is (which will cause
errors in LilyPond). Surplus sections of code will be ignored.



## Mobile/Web support

Anki addons are desktop only, so by default, LilyPond images won't appear
on other platforms since those platforms won't know what to make of a
`[lilypond]` tag or how to treat a `-lilypond` field.

As a workaround you can use LilyPond fields and for each field create another field
with the same name but ending with `-lilypondimg`. The desktop addon will replace
the contents of this field with the rendered image. You can then use this field in
your notes.

For example, if your field is `front-lilypond`, with content `c d e`, create the field
`front-lilypondimg` and use the `front-lilypondimg` field in your card template
wherever you want the rendered music to appear. As long as you create your cards on
desktop so that the plugin can generate the image this image will then be visable on
all platforms.

Note that the contents of the `-lilypondimg` field will be overwritten so don't put
anything important in there.

## ToDo
[x] Configuration parameters for lilypond executable
[] Config options for <img> HTML tag attributes (alt, etc.)
[] Menu integration (for templates?)
[] Is it true that changing templates requires restarting?