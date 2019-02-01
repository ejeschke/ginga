Roadmap for Ginga
==================

This is a roadmap for Ginga development, which lays out
the long-term plans for this package.

*Note: As a caveat, this is a living document, and
will evolve as priorities grow and shift.*

Last updated: August 2018

Short-Term Goals
----------------

Things that might happen in the next release or two:

* Python 3.7 support. (Done)
* Last major release that is compatible with Python 2 (time frame: late
  2018). Beginning with v3.x.y, Ginga will be Python 3 compatible only.

Mid-Term Goals
--------------

Things that might happen in 1-1.5 years:

* Convert ``master`` to be Python 3.5-compatible (and above) only
  (time frame: early 2019).
* Dropping Python 2 support (bug fixes to 2.x.y branches until end of 2019).
* Improve vector types support (e.g., efficient rendering of many
  objects of a single type).
* Support ASDF and GWCS.


Long-Term Goals
---------------

Things that are nice to have but do not have a specific
implementation timeline:

* Complete documentation overhaul with more user-friendly examples.
* Out-of-memory big data support.
* Better remote interface to reference viewer.
