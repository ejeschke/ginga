
Un complemento para componer imágenes RGB a partir de imágenes monocromas
constituyentes.

**Tipo de complemento: Local**

``Compose`` es un complemento local, lo que significa que está asociado a un
canal.  Se puede abrir una instancia para cada canal.

**Uso**

Inicie el complemento ``Compose`` desde el menú «Operation->RGB» (abajo) o
«Plugins->RGB» (arriba).  La pestaña debería aparecer bajo la pestaña
«Dialogs» en el visor de la derecha como «IMAGE:Compose».

1. Seleccione el tipo de composición que desea hacer en el desplegable «Compose
   Type»: «RGB» para componer tres imágenes monocromas en una imagen a color,
   «Alpha» para componer una serie de imágenes como capas con distintos valores
   alfa para cada capa.
2. Pulse «Nueva imagen» para empezar a componer una nueva imagen.

***Para la composición RGB***

1. Arrastre sus tres imágenes constituyentes que formarán los planos R, G y B a
   la ventana «Preview» -- arrástrelas en el orden R (rojo), G (verde) y B
   (azul).  Alternativamente, puede cargar las imágenes en el visor de canal una
   a una y, tras cada una, pulsar «Insertar desde canal» (igualmente, hágalo en
   el orden R, G y B).

En la interfaz del complemento, las imágenes R, G y B deberían aparecer como
tres controles deslizantes en el área «Layers» del complemento, y la vista
previa debería mostrar una versión de baja resolución de cómo se ve la imagen
compuesta con los deslizadores ajustados.

.. figure:: figures/compose-rgb.png
   :width: 800px
   :align: center
   :alt: Componiendo una imagen RGB

   Componiendo una imagen RGB.

2. Juegue con los niveles alfa de cada capa usando los deslizadores del
   complemento ``Compose``; a medida que ajuste un deslizador, la imagen de
   vista previa debería actualizarse.
3. Cuando vea algo que le guste, puede guardarlo en un archivo usando el botón
   «Guardar como» (use «jpeg» o «png» como extensión de archivo), o insertarlo
   en el canal usando el botón «Guardar en canal».

***Para la composición Alpha***

Para la composición de tipo Alpha, las imágenes simplemente se combinan en el
orden mostrado en la pila, siendo la capa 0 la capa inferior, y las capas
sucesivas apiladas encima.  El nivel alfa de cada capa es ajustable mediante un
deslizador de la misma manera que se explicó arriba.

.. figure:: figures/compose-alpha.png
   :width: 800px
   :align: center
   :alt: Componiendo una imagen con Alpha

   Componiendo una imagen con Alpha.

1. Arrastre sus N imágenes constituyentes que formarán las capas a la ventana
   «Preview», o cargue las imágenes en el visor de canal una a una y, tras cada
   una, pulse «Insertar desde canal» (la primera imagen estará en la parte
   inferior de la pila -- capa 0).
2. Juegue con los niveles alfa de cada capa usando los deslizadores del
   complemento ``Compose``; a medida que ajuste un deslizador, la imagen de
   vista previa debería actualizarse.
3. Cuando vea algo que le guste, puede guardarlo en un archivo usando el botón
   «Guardar como» (use «fits» como extensión de archivo), o insertarlo en el
   canal usando el botón «Guardar en canal».

***Notas generales***

- La ventana de vista previa es simplemente un widget de ginga, por lo que se
  aplican todas las asignaciones habituales; puede establecer mapas de color,
  niveles de corte, etc. con las asignaciones de ratón y teclado.
