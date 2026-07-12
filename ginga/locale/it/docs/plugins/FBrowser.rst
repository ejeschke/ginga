Un plugin per navigare nel filesystem locale e caricare file.

**Tipo di plugin: Globale o Locale**

``FBrowser`` è un plugin ibrido globale/locale, il che significa che può essere
invocato in entrambi i modi.  Se invocato come plugin locale è associato a un
canale ed è possibile aprire un'istanza per ciascun canale.  Può anche essere
aperto come plugin globale.

**Uso**

Naviga nell'albero delle cartelle fino a raggiungere la posizione dei file che
desideri caricare.  Puoi fare doppio clic su un file per caricarlo nel canale
associato, oppure trascinare un file in una finestra del visualizzatore di
canale per caricarlo in un qualsiasi visualizzatore di canale.

È possibile selezionare più file tenendo premuto ``Ctrl`` (``Command`` su Mac),
oppure facendo ``Shift``-clic per selezionare un intervallo contiguo di file.

Puoi anche inserire il percorso completo delle immagini desiderate nella casella
di testo, come ``/mio/percorso/immagine.fits``,
``/mio/percorso/immagine.fits[ext]`` o
``/mio/percorso/immagine*.fits[extname,*]``.

Poiché è un plugin locale, ``FBrowser`` ricorderà la sua ultima cartella se
chiuso e poi riavviato.
