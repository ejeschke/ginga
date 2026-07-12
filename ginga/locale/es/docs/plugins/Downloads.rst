
GUI de descargas para el visor de referencia de Ginga.

**Tipo de complemento: Global**

``Download`` es un complemento global.  Solo se puede abrir una instancia.

**Uso**

Abra este complemento para monitorizar el progreso de las descargas de URI.
Iníciela usando el menú «Plugins» u «Operations», y seleccionando el complemento
«Downloads» de la categoría «Util».

Si desea iniciar una descarga, simplemente arrastre una URI a un visor de imagen
de canal o al panel ``Thumbs``.

Puede eliminar la información sobre una descarga en cualquier momento haciendo
clic en el botón «Borrar» de su entrada.  Puede borrar las entradas de todas las
descargas haciendo clic en el botón «Borrar todo» en la parte inferior.

Actualmente, no es posible cancelar una descarga en curso.

**Ajustes**

La opción ``auto_clear_download``, si se establece en `True`, hará que una
entrada de descarga se elimine automáticamente del panel cuando la descarga se
complete.  No elimina ningún archivo descargado.

La carpeta de descargas puede ser definida por el usuario asignando un valor al
ajuste «download_folder» en ~/.ginga/general.cfg.  Si no se asigna, toma por
defecto una carpeta en el directorio temporal predeterminado específico de la
plataforma (según indica el módulo «tempfile» de Python).
