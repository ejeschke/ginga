
Un complemento para navegar por las HDU de un archivo FITS o por los planos de
un cubo 3D o un conjunto de datos de dimensión superior.

**Tipo de complemento: Local**

``MultiDim`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

``MultiDim`` es un complemento diseñado para manejar cubos de datos y archivos
FITS de múltiples HDU.  Si ha abierto una imagen de este tipo en Ginga, iniciar
este complemento le permitirá desplazarse a otros cortes del cubo o ver otras
HDU.

Para un cubo de datos, puede guardar un corte como imagen usando el botón
«Guardar corte» o crear una película usando el botón «Guardar película»
introduciendo los índices de corte «Inicio» y «Fin».  Esta función requiere que
``mencoder`` esté instalado.

Para una tabla FITS, sus datos se leen usando una tabla de Astropy.  Las
unidades de las columnas se muestran justo debajo del encabezado principal
(«None» si no hay unidad).  Para las columnas enmascaradas, los valores
enmascarados se sustituyen por valores de relleno predefinidos.

**Explorar las HDU**

Use la lista desplegable de HDU en la parte superior de la interfaz para
explorar y seleccionar una HDU que abrir en el canal.

**Navegar por los cubos**

Use los controles de la parte inferior de la interfaz para seleccionar el eje y
recorrer los planos de ese eje.

**Configuración del usuario**

Es personalizable usando ``~/.ginga/plugin_MultiDim.cfg``, donde ``~`` es su
directorio HOME:

.. code-block:: Python

  #
  # MultiDim plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_MultiDim.cfg"

  # Sort option for HDU listing.
  # Available attributes:
  #   'index' -- Extension index
  #   'name' -- Extension name
  #   'extver' -- Extension version number
  #   'htype' -- HDU type (PrimaryHDU, ImageHDU, TableHDU)
  #   'dtype' -- Data type
  # Example to sort by HDU name and extver:
  #   sort_keys = ['name', 'extver']
  # Default is to sort by index only:
  sort_keys = ['index']

  # Reverse for HDU listing?
  sort_reverse = False
