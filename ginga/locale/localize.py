#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Localization support for ginga and applications built on it.

ginga registers its own message domain on import.  A downstream application
adds its own translations by calling :func:`register` once at startup::

    from ginga.locale import localize
    localize.register('myapp', os.path.join(mypkg_dir, 'locale'))

After that, ``_tr()`` (and the caption translation in ``build_info``, plugin
docstring lookups, etc.) consult the application's catalog as well as ginga's,
so the application's own UI strings and help documents are localized through
the same shared widget/plugin machinery.  The active language is global and
applies to every registered catalog.
"""
import gettext
import os

# ginga's own locale directory (kept public for backward compatibility)
localedir = os.path.abspath(os.path.dirname(__file__))

# Registered translation sources, in registration order.  ginga registers
# itself on import; downstream applications call register() to add their own.
# _tr() consults them most-recently-registered first, so an application's
# catalog overrides ginga's for a shared message id (app-catalog-wins).
_registry = []

# The requested language: None/'' honors the environment
# (LANGUAGE/LC_ALL/LC_MESSAGES/LANG); a code overrides it.  Applied to every
# registered catalog.
_lang_pref = None


def _load_catalog(domain, ldir, code):
    languages = None if code in (None, '') else [code]
    # fallback=True: untranslated strings come back unchanged, so English (the
    # source language) always works even with no compiled catalog.
    return gettext.translation(domain, ldir, languages=languages,
                               fallback=True)


def register(domain, localedir):
    """Register a gettext message domain and its locale directory.

    ``localedir`` should contain ``<lang>/LC_MESSAGES/<domain>.mo`` catalogs
    and, optionally, ``<lang>/docs/<category>/*.rst`` help documents.
    Applications built on ginga call this once at startup so their own UI
    strings (including captions passed through ginga's shared widgets) and
    help documents are localized alongside ginga's.  Registering the same
    ``(domain, localedir)`` twice is a no-op.
    """
    for ent in _registry:
        if ent['domain'] == domain and ent['localedir'] == localedir:
            return
    _registry.append(dict(domain=domain, localedir=localedir,
                          catalog=_load_catalog(domain, localedir, _lang_pref)))


# ginga registers itself
register('ginga', localedir)


def _tr(message):
    """Translate `message` into the active language.

    Consults every registered catalog, most-recently-registered first
    (app-catalog-wins); returns the original string if none has a translation.
    """
    for ent in reversed(_registry):
        translated = ent['catalog'].gettext(message)
        if translated != message:
            return translated
    return message


# conventional gettext alias
_ = _tr


def N_(message):
    """Mark `message` for translation without translating it now (gettext_noop).

    Use for strings that must be defined before the UI language is applied
    (e.g. class-attribute lists), so the extractor still records them; then
    translate at display time with ``_tr()``.
    """
    return message


def set_language(code=None):
    """Set the active UI language for all registered catalogs.

    `code` is a locale code such as ``'ja'`` or ``'en'``.  Pass ``None`` or
    ``''`` (the default) to honor the environment variables
    (LANGUAGE/LC_ALL/LC_MESSAGES/LANG).
    """
    global _lang_pref
    _lang_pref = None if code in (None, '') else code
    for ent in _registry:
        ent['catalog'] = _load_catalog(ent['domain'], ent['localedir'],
                                       _lang_pref)


def get_language():
    """Return the code of the active language (e.g. ``'ja'``), or None when
    running in English / fallback.
    """
    if _lang_pref not in (None, ''):
        return _lang_pref
    # env-resolved: read the language from any loaded catalog's header
    for ent in _registry:
        lang = ent['catalog'].info().get('language')
        if lang:
            return lang
    return None


def get_localized_doc(name, category='plugins'):
    """Return a translated long-form help document for the active language,
    or None if there isn't one.

    Searches each registered locale directory for
    ``<localedir>/<lang>/docs/<category>/<name>.rst`` (most-recently-registered
    first).  These are tracked source files (whole-document translations), used
    for text too large for the gettext catalogs (e.g. plugin docstrings shown
    as help).  Returns None (caller uses the English source) when the language
    is English/unset or no file is found.
    """
    lang = get_language()
    if lang is None or lang == 'en':
        return None
    for ent in reversed(_registry):
        path = os.path.join(ent['localedir'], lang, 'docs', category,
                            name + '.rst')
        try:
            with open(path, encoding='utf-8') as f:
                return f.read()
        except OSError:
            continue
    return None


def get_message(key, default='', category='messages'):
    """Return a localized multi-line message block for the active language.

    Like :func:`get_localized_doc`, but for paragraph-sized help text that
    lives inline in the source: `default` (the English text) is returned when
    there is no translation file
    (``<localedir>/<lang>/docs/<category>/<key>.rst``).
    """
    text = get_localized_doc(key, category=category)
    return default if text is None else text


# All widget-type tokens understood by build_info() captions.  Used by the
# custom Babel extractor to recognize a caption row.
KNOWN_WTYPES = frozenset([
    'label', 'llabel', 'textentry', 'entry', 'textentryset', 'entryset',
    'combobox', 'comboboxedit', 'spinbox', 'spinbutton', 'spinfloat',
    'vbox', 'hbox', 'hslider', 'hscale', 'vslider', 'vscale',
    'checkbox', 'checkbutton', 'radiobutton', 'togglebutton', 'button',
    'spacer', 'textarea', 'toolbar', 'progress', 'menubar', 'dial',
])

# The subset of caption widget types whose title is shown to the user and so
# should be translated.  (llabel is excluded: its text is a dynamic value,
# set at runtime, not a fixed label.)
TRANSLATABLE_WTYPES = frozenset([
    'label', 'button', 'checkbox', 'checkbutton', 'radiobutton',
    'togglebutton',
])

# Prefix that opts a caption title out of translation (and is stripped).
NO_TRANSLATE_PREFIX = '^'


def translate_caption(title, wtype):
    """Process one build_info() caption ``(title, wtype)`` pair.

    Returns ``(key_title, disp_title)``:

    - ``key_title`` is the English string from which the Bunch key is derived
      (with any leading ``^`` opt-out marker stripped).  Deriving the key from
      English keeps widget keys stable across languages so existing code that
      looks up ``b.<name>`` keeps working.
    - ``disp_title`` is the text actually shown: translated when the widget
      type displays its title and the title is not opted out with a leading
      ``^``; otherwise the (marker-stripped) English text.
    """
    if title.startswith(NO_TRANSLATE_PREFIX):
        title = title[len(NO_TRANSLATE_PREFIX):]
        return title, title
    if wtype in TRANSLATABLE_WTYPES:
        return title, _tr(title)
    return title, title


# Display names for the shipped languages, each written in its own script.
# Used for the Language menu; these are shown as-is regardless of the active
# UI language (a language is self-identifying in its own script).
LANGUAGE_NAMES = {
    'en': 'English',
    'de': 'Deutsch',
    'es': 'Español',
    'fr': 'Français',
    'it': 'Italiano',
    'ja': '日本語',
    'ko': '한국어',
    'zh': '中文',
}


def get_language_name(code):
    """Return the native-script display name for a language code, or the code
    itself if unknown.
    """
    return LANGUAGE_NAMES.get(code, code)


def get_available_languages():
    """Return the sorted list of language codes with a compiled catalog
    (``<code>/LC_MESSAGES/<domain>.mo``) installed in any registered locale
    directory.  English (the source language) is always included, since it
    works via fallback.
    """
    langs = set(['en'])
    for ent in _registry:
        try:
            for name in os.listdir(ent['localedir']):
                mo = os.path.join(ent['localedir'], name, 'LC_MESSAGES',
                                  ent['domain'] + '.mo')
                if os.path.isfile(mo):
                    langs.add(name)
        except OSError:
            pass
    return sorted(langs)
