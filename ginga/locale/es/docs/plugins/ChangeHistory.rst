Llevar un registro del historial de cambios del búfer.

**Tipo de complemento: Global**

``ChangeHistory`` es un complemento global.  Solo se puede abrir una instancia.

Este complemento se usa para registrar cualquier cambio en el búfer de datos.
Por ejemplo, aquí aparecería un registro de cambios si se añade una nueva imagen
a un mosaico mediante el complemento ``Mosaic``.  Al igual que ``Contents``, el
registro se ordena por canal y luego por nombre de imagen.

**Uso**

El historial debe permanecer sin importar qué canal o imagen esté activo.  Se
puede añadir historial nuevo, pero el historial antiguo no se puede eliminar, a
menos que se elimine la propia imagen/canal.

El método ``redo()`` capta un evento ``'add-image-info'`` y muestra aquí los
metadatos relacionados.  Los metadatos se obtienen de la siguiente manera::

        channel = self.fv.get_channel_info(chname)
        iminfo = channel.get_image_info(imname)
        timestamp = iminfo.time_modified
        description = iminfo.reason_modified  # Optional

Tanto ``'time_modified'`` como ``'reason_modified'`` deben ser establecidos
explícitamente por el complemento que llama, en el mismo método que emite la
retrollamada ``'add-image-info'``, así::

        # Esto cambia el búfer de datos
        image.set_data(new_data, ...)
        # Añadir descripción para ChangeHistory
        info = dict(time_modified=datetime.now(tz=tz.UTC),
                    reason_modified='Data has changed')
        self.fv.update_image_info(image, info)
