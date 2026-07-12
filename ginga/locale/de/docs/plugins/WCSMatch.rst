``WCSMatch`` ist ein globales Plugin für den Ginga-Bildbetrachter, mit dem Sie
Bilder mit unterschiedlichen Skalierungen und Ausrichtungen zu
Betrachtungszwecken mithilfe des Weltkoordinatensystems (WCS) der Bilder grob
ausrichten können.

**Plugin-Typ: Global**

``WCSMatch`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet werden.

**Verwendung**

Zur Verwendung starten Sie einfach das Plugin und wählen in der
Plugin-Oberfläche im Auswahlmenü „Referenzkanal“ einen Kanal aus.  Das in
diesem Kanal enthaltene Bild wird als Referenz für die Synchronisierung der
Bilder in den anderen Kanälen verwendet.

Die Kanäle werden in der Betrachtung synchronisiert (Verschiebung, Skalierung
(Zoom), Transformationen (Spiegelungen) und Drehung).  Die Kontrollkästchen
„Verschiebung angleichen“, „Skalierung angleichen“, „Transformationen
angleichen“ und „Drehung angleichen“ können aktiviert werden oder nicht, um zu
steuern, welche Eigenschaften zwischen den Kanälen synchronisiert werden.

Um die Synchronisierung vollständig „aufzuheben“, wählen Sie einfach „None“ aus
dem Auswahlmenü „Referenzkanal“.

Derzeit gibt es keine Möglichkeit, die vom Plugin betroffenen Kanäle
einzuschränken.
