.. _ch-internationalization:

++++++++++++++++++++
Internationalization
++++++++++++++++++++

Ginga has support for internationalization using Python standards.
A translation catalog is maintained within the installed package (in
``ginga.locale``), and some of the example programs will change
visibly if the `LANG` environment variable is set to one of the
supported languages.

We need help preparing new translations! If you are willing to provide a
translation for Ginga strings into a new language, please follow the
instructions below.

===========================
Internationalizing New Code
===========================

When you add user-facing text to Ginga (or to an application built on it),
follow these conventions so that it can be translated.

Short UI strings
----------------

Import the translation function and wrap literal strings with it:

.. code-block:: python

    from ginga.locale.localize import _tr

    label = Widgets.Label(_tr("Cut Levels"))
    btn.set_tooltip(_tr("Reset contrast"))
    fr = Widgets.Frame(_tr("Color Mapping"))

``_tr`` returns the string unchanged when there is no translation, so English
always works.  Wrap Labels, Buttons, CheckBoxes, RadioButtons, tooltips,
Frame/Expander titles, menu item names, notebook tab titles and the like.

``build_info`` captions
-----------------------

Captions passed to ``ginga.gw.Widgets.build_info`` are translated
automatically -- do **not** wrap the caption strings with ``_tr``.  The widget
key is derived from the *English* text, so ``b.<name>`` lookups keep working in
every language.  Only the displayed widget types (``label``, ``button``,
``checkbox``, ``radiobutton``, ``togglebutton``) are translated; the titles of
value widgets (``entry``, ``combobox``, ``spinbox``) are used only as keys and
are left alone, as is the dynamic text of an ``llabel``.

Prefix a caption title with ``^`` to opt it out of translation (the marker is
stripped from the displayed text); use this for placeholder labels whose text
is set at runtime:

.. code-block:: python

    captions = (("Threshold:", 'label', '^xlbl_threshold', 'label'), ...)

Strings defined before the language is set
------------------------------------------

For strings that must exist before the UI language has been applied (e.g.
values in a class-attribute list), mark them with ``N_`` -- which does nothing
at runtime but is seen by the message extractor -- and translate them with
``_tr`` at display time:

.. code-block:: python

    from ginga.locale.localize import _tr, N_

    self.wstypes_c = [N_('Tabs'), N_('Grid'), N_('MDI'), N_('Stack')]
    ...
    for name in self.wstypes_c:
        cbox.append_text(_tr(name))

Combo boxes that carry values
-----------------------------

If a combo box's item strings are written back into settings or compared
against specific values in a callback, do **not** translate the items --
translating would break the round-trip.  Either leave the combo untranslated,
or translate only the *displayed* items and recover the canonical value by
index in the callback.

Long help text
--------------

Text that is too large for the message catalog -- plugin and mode docstrings,
and paragraph-sized help blurbs -- is translated as whole files rather than as
gettext messages.  Place a translated file at
``ginga/locale/<lang>/docs/<category>/<name>.rst``:

* plugin docstrings: category ``plugins``, ``<name>`` is the plugin class name
  (looked up by ``GingaPlugin._get_docstring``);
* mode docstrings: category ``modes``, ``<name>`` is the mode class name
  (looked up by ``mode_base.get_docstring``);
* inline blurbs: call ``localize.get_message(key, english_default)`` in the
  code and add ``ginga/locale/<lang>/docs/messages/<key>.rst``.

If no translated file exists for the active language, the English source is
used.  These ``.rst`` files are tracked in the repository (unlike the compiled
catalogs).

Regenerating the message template
---------------------------------

Because ``build_info`` captions are translated at runtime, the standard Babel
extractor cannot see them.  Regenerate ``ginga.pot`` with Ginga's own two-pass
extractor (it collects both ``_tr``/``N_`` calls and ``build_info`` captions):

.. code-block:: bash

    $ python -m ginga.locale._extract


The compiled ``.mo`` catalogs are build artifacts: they are produced
automatically at build time (a ``build_py`` step runs ``compile_catalog``) and
are **not** committed.  Only the ``.po`` sources and the ``docs`` files are
tracked in the repository.

Reuse in applications built on Ginga
------------------------------------

An application built on Ginga can share this machinery instead of duplicating
it.  Register your own message domain and locale directory once at startup:

.. code-block:: python

    from ginga.locale import localize
    localize.register('myapp', os.path.join(mypkg_dir, 'locale'))


``_tr`` then consults your catalog as well as Ginga's (your catalog takes
precedence for a shared message id), so your application's own UI strings --
including captions passed through Ginga's shared widgets -- and help documents
are localized through the same code.  Build your own message template with
``ginga.locale._extract.build_catalog('myapp')``, and ship your own ``.po``,
``.mo`` and ``docs`` files under your package's locale directory.

===========================
Preparing a New Translation
===========================
Before starting you will need a git clone of the
`Ginga repository <https://github.com/ejeschke/ginga>`_.
If you plan to submit your translation as a github pull request, then it
is best to fork Ginga in your own github account, and then check it out
locally from there.  Otherwise you can simply git clone the repo from
the link above.

You will also need to install "babel":

.. code-block:: bash

    $ pip install babel


To make the master translation template, go into the top level of the
Ginga repository and execute:

   $ python -m ginga.locale._extract

   this creates a file "ginga.pot" in ginga/locale

.. note:: Use ``python -m ginga.locale._extract`` rather than
   ``python setup.py extract_messages``: Ginga translates ``build_info``
   captions at runtime, so the standard Babel extractor would miss them.

To make a particular translation instance for the first time:

.. code-block:: bash

    $ python setup.py init_catalog -l <lang> -i ginga/locale/ginga.pot \
        -o ginga/locale/<lang>/LC_MESSAGES/ginga.po


where <lang> is a particular code from the CLDR
(`Common Locale Data Repository
<https://www.loc.gov/standards/iso639-2/php/code_list.php>`_)

Modify the <lang>/LC_MESSAGES/ginga.po file to include the translations
in the new language.

To compile the translations to binary:

.. code-block:: bash

    $ python setup.py compile_catalog -d ginga/locale -f


Install ginga:

.. code-block:: bash

    $ pip install .


Set the environment variable LANG to <lang> (if needed):

.. code-block:: bash

    $ export LANG=<lang>


Run an example program to see if it worked:

.. code-block:: bash

    $ python ginga/examples/gw/example2.py --loglevel=20 --stderr


The user interface elements should show up in the new language.

==========================
Updating Translation Files
==========================

If you need ever to update the translation instances (e.g. added new
strings that need to be translated), this will merge the new entries
into the individual files:

.. code-block:: bash

    $ python setup.py update_catalog -l <lang> -i ginga/locale/ginga.pot \
        -o ginga/locale/<lang>/LC_MESSAGES/ginga.po


Then repeat the compilation and installation steps.

========================
Submitting a Translation
========================

Ideally, make a new branch in your fork of the ginga repository on
github, commit your new `ginga.po` file to the branch, push it up to
your fork and submit it as a pull request:

.. code-block:: bash

    $ git branch new-lang-<lang>
    $ git checkout new-lang-<lang>
    $ git add ginga/locale/<lang>/LC_MESSAGES/ginga.po
    $ git commit
    $ git push origin new-lang-<lang>
    # follow instructions to make a pull request in your browser


If this all sounds too complicated, you can make the `ginga.po` file
available somewhere (cloud storage, etc) and notify us in the
`"Issues" area of Ginga's github home <https://github.com/ejeschke/ginga/issues>`_.

