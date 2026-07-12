Il plugin ``Pan`` fornisce una piccola immagine di panoramica che offre una
vista d'insieme « a volo d'uccello » dell'immagine di canale che ha avuto per
ultima il focus.  Se l'immagine del canale è ingrandita 2X o più, la regione di
panoramica viene mostrata graficamente nell'immagine ``Pan`` con un rettangolo.

**Tipo di plugin: Locale**

``Pan`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

L'immagine del canale può essere spostata facendo clic e/o trascinando per
posizionare il rettangolo.  Usando il pulsante destro del mouse per trascinare
un rettangolo si obbliga il visualizzatore di immagini del canale a cercare di
corrispondere alla regione (tenendo conto delle differenze di proporzioni tra il
rettangolo disegnato e le dimensioni della finestra).  Scorrere nell'immagine
``Pan`` esegue lo zoom dell'immagine del canale.

La mappa di colore/intensità e i livelli di taglio dell'immagine ``Pan`` vengono
aggiornati quando vengono modificati nell'immagine di canale corrispondente.
L'immagine ``Pan`` mostra anche la bussola del sistema di coordinate mondiale
(WCS), se sono presenti metadati WCS validi nell'HDU FITS visualizzato nel
canale.

Il plugin ``Pan`` appare di solito come un sotto-riquadro sotto la scheda
« Info », accanto al plugin ``Info``.

Questo plugin di solito non è configurato come chiudibile, ma l'utente può
renderlo tale impostando l'opzione « closeable » su True nel file di
configurazione; in tal caso i pulsanti Chiudi e Aiuto verranno aggiunti in fondo
all'interfaccia.
