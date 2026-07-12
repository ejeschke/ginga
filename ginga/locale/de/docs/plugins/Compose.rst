
Ein Plugin zum Zusammensetzen von RGB-Bildern aus einzelnen Monochrombildern.

**Plugin-Typ: Lokal**

``Compose`` ist ein lokales Plugin, das heißt, es ist einem Kanal zugeordnet.
Für jeden Kanal kann eine Instanz geöffnet werden.

**Verwendung**

Starten Sie das Plugin ``Compose`` über das Menü „Operation->RGB“ (unten) oder
„Plugins->RGB“ (oben).  Der Reiter sollte im Betrachter rechts unter dem Reiter
„Dialogs“ als „IMAGE:Compose“ erscheinen.

1. Wählen Sie die Art der Komposition, die Sie erstellen möchten, aus dem
   Auswahlmenü „Compose Type“: „RGB“, um drei Monochrombilder zu einem Farbbild
   zusammenzusetzen, „Alpha“, um eine Reihe von Bildern als Ebenen mit
   unterschiedlichen Alphawerten für jede Ebene zusammenzusetzen.
2. Drücken Sie „Neues Bild“, um mit dem Zusammensetzen eines neuen Bildes zu
   beginnen.

***Für die RGB-Komposition***

1. Ziehen Sie Ihre drei Einzelbilder, die die R-, G- und B-Ebenen bilden, in das
   Fenster „Preview“ -- ziehen Sie sie in der Reihenfolge R (Rot), G (Grün) und
   B (Blau).  Alternativ können Sie die Bilder eines nach dem anderen in den
   Kanalbetrachter laden und nach jedem „Aus Kanal einfügen“ drücken (ebenfalls
   in der Reihenfolge R, G und B).

In der Plugin-Oberfläche sollten die R-, G- und B-Bilder als drei
Schieberegler-Steuerelemente im Bereich „Layers“ des Plugins erscheinen, und die
Vorschau sollte eine niedrig aufgelöste Version davon zeigen, wie das
Kompositbild mit den eingestellten Reglern aussieht.

.. figure:: figures/compose-rgb.png
   :width: 800px
   :align: center
   :alt: Zusammensetzen eines RGB-Bildes

   Zusammensetzen eines RGB-Bildes.

2. Spielen Sie mit den Alphastufen jeder Ebene über die Schieberegler im Plugin
   ``Compose``; während Sie einen Regler anpassen, sollte sich das
   Vorschaubild aktualisieren.
3. Wenn Sie etwas sehen, das Ihnen gefällt, können Sie es mit der Schaltfläche
   „Speichern unter“ in eine Datei speichern (verwenden Sie „jpeg“ oder „png“
   als Dateiendung) oder es mit der Schaltfläche „In Kanal speichern“ in den
   Kanal einfügen.

***Für die Alpha-Komposition***

Bei der Komposition vom Typ Alpha werden die Bilder einfach in der im Stapel
gezeigten Reihenfolge kombiniert, wobei Ebene 0 die unterste Ebene ist und
weitere Ebenen darüber gestapelt werden.  Die Alphastufe jeder Ebene ist über
einen Schieberegler in derselben Weise wie oben beschrieben anpassbar.

.. figure:: figures/compose-alpha.png
   :width: 800px
   :align: center
   :alt: Alpha-Zusammensetzen eines Bildes

   Alpha-Zusammensetzen eines Bildes.

1. Ziehen Sie Ihre N Einzelbilder, die die Ebenen bilden, in das Fenster
   „Preview“, oder laden Sie die Bilder eines nach dem anderen in den
   Kanalbetrachter und drücken nach jedem „Aus Kanal einfügen“ (das erste Bild
   ist unten im Stapel -- Ebene 0).
2. Spielen Sie mit den Alphastufen jeder Ebene über die Schieberegler im Plugin
   ``Compose``; während Sie einen Regler anpassen, sollte sich das
   Vorschaubild aktualisieren.
3. Wenn Sie etwas sehen, das Ihnen gefällt, können Sie es mit der Schaltfläche
   „Speichern unter“ in eine Datei speichern (verwenden Sie „fits“ als
   Dateiendung) oder es mit der Schaltfläche „In Kanal speichern“ in den Kanal
   einfügen.

***Allgemeine Hinweise***

- Das Vorschaufenster ist einfach ein Ginga-Widget, sodass alle üblichen
  Bindungen gelten; Sie können Farbkarten, Cut-Level usw. mit den Maus- und
  Tastaturbindungen einstellen.
