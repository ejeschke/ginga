++++++++++++++++++++
What's New in Ginga?
++++++++++++++++++++

Ver 1.5-20130923184124
======================

Efficiency improvements
-----------------------
Efforts to improve speed of entire rendering pipeline and widget
specific redrawing 

* Decent improvements, Ginga can now render HD video (no sound) at 30
  FPS on older hardware (see scripts/example1_video.py).  This
  translates to a slightly speedier feel overall for many operations
  viewing regular scientific files.
* Fixed a bug that gave an error message of 
  Callback.py:83 (make_callback) | Error making callback 'field-info':
  'Readout' object has no attribute 'fitsimage'

* Version bump


Ver 1.4.20130718005402
======================

New Agg backend
---------------
There is now an Agg rendering version of the ImageView object.

* uses the python "aggdraw" module for drawing; get it here  -->
  https://github.com/ejeschke/aggdraw 
* this will make it easy to support all kinds of surfaces because the
  graphics drawing code does not have to be replicated for each
  toolkit
* see example code in /scripts/example1_agg_gtk.py
* currently not needed for Gtk, Qt versions of the object

New Tk backend
--------------
There is now a Tk rendering version of the ImageView object.

* see ginga.tkw.ImageViewTk
* renders on a Tk canvas
* see example code in /scripts/example{1,2}_tk.py
* you will need the aggdraw module (see above) to use it

AutoCuts
--------
* the ginga.AutoCuts module has been refactored into individual classes
  for each algorithm 
* The Preferences plugin for ginga now exposes all of the parameters
    used for each cut levels algorithm and will save them

Etc
---
* additions to the manual (still incomplete, but coming along)
* lots of docstrings for methods added (sphinx API doc coming)
* many colors added to the color drawing example programs
* WhatsNew.txt file added
