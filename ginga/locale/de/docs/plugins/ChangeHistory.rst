Verlauf der Pufferänderungen verfolgen.

**Plugin-Typ: Global**

``ChangeHistory`` ist ein globales Plugin.  Es kann nur eine Instanz geöffnet
werden.

Dieses Plugin dient dazu, alle Änderungen am Datenpuffer zu protokollieren.  Zum
Beispiel würde hier ein Änderungsprotokoll erscheinen, wenn über das Plugin
``Mosaic`` ein neues Bild zu einem Mosaik hinzugefügt wird.  Wie bei
``Contents`` ist das Protokoll nach Kanal und dann nach Bildname sortiert.

**Verwendung**

Der Verlauf sollte erhalten bleiben, unabhängig davon, welcher Kanal oder
welches Bild aktiv ist.  Neuer Verlauf kann hinzugefügt werden, aber alter
Verlauf kann nicht gelöscht werden, es sei denn, das Bild/der Kanal selbst wird
gelöscht.

Die Methode ``redo()`` greift ein ``'add-image-info'``-Ereignis auf und zeigt
zugehörige Metadaten hier an.  Die Metadaten werden wie folgt bezogen::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

Sowohl ``'time_modified'`` als auch ``'reason_modified'`` müssen vom aufrufenden
Plugin explizit in derselben Methode gesetzt werden, die den
``'add-image-info'``-Callback auslöst, etwa so::

        # Dies ändert den Datenpuffer
        image.set_data(new_data, ...)
        # Beschreibung für ChangeHistory hinzufügen
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
