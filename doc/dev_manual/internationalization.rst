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

   $ python setup.py extract_messages

   this creates a file "ginga.pot" in ginga/locale

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

