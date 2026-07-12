
Un plugin per navigare tra le HDU di un file FITS o tra i piani di un cubo 3D o
di un dataset a dimensione superiore.

**Tipo di plugin: Locale**

``MultiDim`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

``MultiDim`` è un plugin progettato per gestire cubi di dati e file FITS a più
HDU.  Se hai aperto un'immagine di questo tipo in Ginga, avviare questo plugin
ti permetterà di spostarti su altre sezioni del cubo o visualizzare altre HDU.

Per un cubo di dati, puoi salvare una sezione come immagine usando il pulsante
« Salva sezione » o creare un filmato usando il pulsante « Salva filmato »
inserendo gli indici di sezione « Inizio » e « Fine ».  Questa funzione richiede
che ``mencoder`` sia installato.

Per una tabella FITS, i suoi dati vengono letti usando una tabella Astropy.  Le
unità delle colonne sono mostrate proprio sotto l'intestazione principale
(« None » se non c'è unità).  Per le colonne mascherate, i valori mascherati
vengono sostituiti con valori di riempimento predefiniti.

**Sfogliare le HDU**

Usa l'elenco a discesa delle HDU nella parte superiore dell'interfaccia per
sfogliare e selezionare una HDU da aprire nel canale.

**Navigare nei cubi**

Usa i controlli nella parte inferiore dell'interfaccia per selezionare l'asse e
scorrere i piani di quell'asse.

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_MultiDim.cfg``, dove ``~`` è la tua
directory HOME:

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
