#
# This is open-source software licensed under a BSD license.
# Please see the file LICENSE.txt for details.
#
"""Regenerate the gettext message template (ginga.pot) for the reference
viewer.

Ginga marks translatable strings two ways, and this tool extracts both:

1. Explicit ``_tr("...")`` / ``_("...")`` calls (standard Babel extraction).
2. ``build_info()`` caption titles.  Those are plain strings inside caption
   tuples (``('Label:', 'label', ...)``); ``build_info`` translates the
   display text at runtime while keeping the widget key in English (see
   ``ginga.locale.localize.translate_caption``), so Babel cannot see them as
   ordinary keyword calls.  This module AST-parses caption tuples and pulls
   the titles of the user-visible widget types (skipping ``^``-opted-out
   titles and non-display types).

Usage::

    python -m ginga.locale._extract [srcdir] [-o outfile]

Requires Babel (a build/development dependency, not a runtime one).
"""
import ast
import os
import sys

from ginga.locale.localize import (
    KNOWN_WTYPES, TRANSLATABLE_WTYPES, NO_TRANSLATE_PREFIX)


def iter_caption_messages(source, filename='<unknown>'):
    """Yield ``(lineno, text)`` for each translatable ``build_info()`` caption
    title found in `source` (a string of Python code).
    """
    try:
        tree = ast.parse(source, filename=filename)
    except SyntaxError:
        return
    for node in ast.walk(tree):
        # A captions argument is a non-empty tuple/list whose every element is
        # itself a tuple (a caption row).  Requiring the tuple-of-tuples shape
        # avoids matching flat wtype tuples like ('checkbox', 'checkbutton')
        # that appear in the widget library itself.
        if not isinstance(node, (ast.Tuple, ast.List)):
            continue
        rows = node.elts
        if len(rows) == 0 or not all(isinstance(r, ast.Tuple) for r in rows):
            continue
        for row in rows:
            elts = row.elts
            n = len(elts)
            if n < 2 or (n % 2) != 0:
                continue
            # a caption row has a known wtype string at every odd position
            wtype_nodes = elts[1::2]
            if not all(isinstance(t, ast.Constant) and
                       isinstance(t.value, str) and
                       t.value in KNOWN_WTYPES for t in wtype_nodes):
                continue
            for i in range(0, n, 2):
                name_node, wtype = elts[i], elts[i + 1].value
                if wtype not in TRANSLATABLE_WTYPES:
                    continue
                if not (isinstance(name_node, ast.Constant) and
                        isinstance(name_node.value, str)):
                    continue
                title = name_node.value
                if title.startswith(NO_TRANSLATE_PREFIX) or title.strip() == '':
                    continue
                yield (name_node.lineno, title)


def build_catalog(srcdir='ginga'):
    from babel.messages.catalog import Catalog
    from babel.messages.extract import extract_from_dir

    catalog = Catalog(project='ginga', charset='utf-8')

    # pass 1: explicit _tr()/_()/N_() calls
    for filename, lineno, message, comments, context in extract_from_dir(
            srcdir, method_map=[('**.py', 'python')],
            keywords={'_tr': None, '_': None, 'N_': None}):
        catalog.add(message, locations=[(os.path.join(srcdir, filename),
                                         lineno)],
                    auto_comments=comments)

    # pass 2: build_info() caption titles
    for root, dirs, files in os.walk(srcdir):
        for fn in sorted(files):
            if not fn.endswith('.py'):
                continue
            path = os.path.join(root, fn)
            with open(path, encoding='utf-8') as f:
                src = f.read()
            for lineno, text in iter_caption_messages(src, path):
                catalog.add(text, locations=[(path, lineno)])

    return catalog


def main(argv=None):
    from babel.messages.pofile import write_po

    argv = list(sys.argv[1:] if argv is None else argv)
    outfile = 'ginga/locale/ginga.pot'
    if '-o' in argv:
        i = argv.index('-o')
        outfile = argv[i + 1]
        del argv[i:i + 2]
    srcdir = argv[0] if argv else 'ginga'

    catalog = build_catalog(srcdir)
    with open(outfile, 'wb') as f:
        write_po(f, catalog, width=76, sort_output=True)
    print("wrote %d messages to %s" % (len(catalog), outfile))
    return 0


if __name__ == '__main__':
    sys.exit(main())
