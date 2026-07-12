Suivre l'historique des modifications du tampon.

**Type de plugin : Global**

``ChangeHistory`` est un plugin global.  Une seule instance peut être ouverte.

Ce plugin sert à journaliser toute modification du tampon de données.  Par
exemple, un journal des modifications apparaîtrait ici si une nouvelle image est
ajoutée à une mosaïque via le plugin ``Mosaic``.  Comme ``Contents``, le journal
est trié par canal, puis par nom d'image.

**Utilisation**

L'historique doit rester quel que soit le canal ou l'image actif.  Un nouvel
historique peut être ajouté, mais l'ancien historique ne peut pas être supprimé,
à moins que l'image/le canal lui-même ne soit supprimé.

La méthode ``redo()`` capte un événement ``'add-image-info'`` et affiche ici les
métadonnées associées.  Les métadonnées sont obtenues comme suit::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

``'time_modified'`` et ``'reason_modified'`` doivent tous deux être définis
explicitement par le plugin appelant, dans la même méthode qui émet le rappel
``'add-image-info'``, comme ceci::

        # Ceci modifie le tampon de données
        image.set_data(new_data, ...)
        # Ajouter une description pour ChangeHistory
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
