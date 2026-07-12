Tenere traccia della cronologia delle modifiche del buffer.

**Tipo di plugin: Globale**

``ChangeHistory`` è un plugin globale.  Può essere aperta una sola istanza.

Questo plugin serve a registrare qualsiasi modifica al buffer dati.  Ad esempio,
un registro delle modifiche comparirebbe qui se una nuova immagine viene aggiunta
a un mosaico tramite il plugin ``Mosaic``.  Come ``Contents``, il registro è
ordinato per canale e poi per nome dell'immagine.

**Uso**

La cronologia dovrebbe rimanere indipendentemente da quale canale o immagine sia
attivo.  È possibile aggiungere nuova cronologia, ma la vecchia cronologia non
può essere eliminata, a meno che non venga eliminata l'immagine/il canale
stesso.

Il metodo ``redo()`` intercetta un evento ``'add-image-info'`` e mostra qui i
metadati correlati.  I metadati si ottengono come segue::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

Sia ``'time_modified'`` che ``'reason_modified'`` devono essere impostati
esplicitamente dal plugin chiamante, nello stesso metodo che emette la callback
``'add-image-info'``, in questo modo::

        # Questo modifica il buffer dati
        image.set_data(new_data, ...)
        # Aggiungi una descrizione per ChangeHistory
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
