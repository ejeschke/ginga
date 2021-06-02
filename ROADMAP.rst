Roadmap for Ginga
=================

This is a roadmap for Ginga development, which lays out
the long-term plans for this package.

*Note: As a caveat, this is a living document, and
will evolve as priorities grow and shift.*

Last updated: Jun 2021

Short-Term Goals
----------------

Things that might happen in the next release or two:

* Replace ``astropy_wcs`` with ``astropy_wcs_ape14`` and deprecate the latter
  module. [#959]

Mid-Term Goals
--------------

Things that might happen in 1-1.5 years:

* Improve vector types support (e.g., efficient rendering of many
  objects of a single type).
* Python 3.10 support.

Long-Term Goals
---------------

Things that are nice to have but do not have a specific
implementation timeline:

* Complete documentation overhaul with more user-friendly examples.
* Out-of-memory big data support.
* Better remote interface to reference viewer.


Completed Goals
---------------

Goals that were completed, in reverse chronological order:

* Initial ASDF and GWCS support (with v3.0 release in late 2019).
* Drop Python 2 support (with v3.0 release in late 2019).
* Last major release that is compatible with Python 2 (time frame: late
  2018). Beginning with v3.x.y, Ginga will be Python 3 compatible only.
* Convert ``master`` to be Python 3.5-compatible (and above) only
  (time frame: early 2019).
* Python 3.7 support.
