
``PixTable`` offre un modo per controllare o monitorare i valori dei pixel in
una regione.

**Tipo di plugin: Locale**

``PixTable`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso di base**

Nell'uso più basilare, sposta semplicemente il cursore nel visualizzatore di
canale; un array di valori dei pixel comparirà nella visualizzazione « Pixel
Values » nell'interfaccia del plugin.  Il valore centrale è evidenziato e
corrisponde al valore sotto il cursore.

Puoi scegliere una griglia 3x3, 5x5, 7x7 o 9x9 dal controllo a casella combinata
più a sinistra.  Può aiutare regolare il controllo « Dimensione carattere » per
evitare che i valori dell'array vengano tagliati ai lati.  Puoi anche ingrandire
lo spazio di lavoro del plugin per vedere di più della tabella.

.. note:: L'ordine della tabella dei valori mostrata non corrisponderà
          necessariamente al visualizzatore di canale se l'immagine è
          capovolta, trasposta o ruotata.

**Usare i contrassegni**

Quando imposti e selezioni un contrassegno, i valori dei pixel verranno mostrati
attorno al contrassegno invece che al cursore.  Ci può essere un numero
qualsiasi di contrassegni, e ciascuno è indicato con una « X » numerata.  Cambia
semplicemente il controllo a discesa dei contrassegni per selezionare un
contrassegno diverso e vedere i valori attorno ad esso.  Il contrassegno
attualmente selezionato è mostrato con un colore diverso dagli altri.

I contrassegni rimarranno in posizione anche se viene caricata una nuova
immagine e mostreranno i valori della nuova immagine.  In questo modo puoi
monitorare l'area attorno a un punto se l'immagine si aggiorna frequentemente.

Se la casella « Sposta al contrassegno » è selezionata, allora quando selezioni
un contrassegno diverso dal controllo dei contrassegni, il visualizzatore di
canale si sposterà su quel contrassegno.  Questo può essere utile per
ispezionare gli stessi punti in diverse immagini, specialmente quando si è
ingranditi molto sull'immagine.

.. note:: Se riporti il controllo dei contrassegni su « None », la tabella dei
          pixel si aggiornerà di nuovo mentre sposti il cursore nel
          visualizzatore.

La casella « Caption » può essere usata per impostare un'annotazione testuale che
verrà aggiunta all'etichetta del contrassegno quando viene creato il
contrassegno successivo.  Questo può essere usato per etichettare una
caratteristica nell'immagine, per esempio.

**Eliminare i contrassegni**

Per eliminare un contrassegno, selezionalo nel controllo dei contrassegni e poi
premi il pulsante etichettato « Elimina ».  Per eliminare tutti i contrassegni,
premi il pulsante etichettato « Elimina tutto ».

**Spostare i contrassegni**

Quando il pulsante di opzione « Sposta » è selezionato e un contrassegno è
selezionato, cliccare o trascinare in un punto qualsiasi dell'immagine sposterà
il contrassegno in quella posizione e aggiornerà la tabella dei pixel.  Se
attualmente non è selezionato alcun contrassegno, ne verrà creato uno nuovo e
spostato.

**Disegnare i contrassegni**

Quando il pulsante di opzione « Disegna » è selezionato, cliccare e trascinare
crea un nuovo contrassegno.  Più lungo è il tratto, maggiore è il raggio della
« X ».

**Modificare i contrassegni**

Quando il pulsante di opzione « Modifica » è selezionato dopo che un
contrassegno è stato selezionato, puoi trascinare i punti di controllo del
contrassegno per aumentare il raggio dei bracci della X, oppure puoi trascinare
il riquadro di delimitazione per spostare il contrassegno.  Se i punti di
controllo di modifica non sono mostrati, fai semplicemente clic sul centro di un
contrassegno per abilitarli.

**Tasti speciali**

In modalità « Sposta » i seguenti tasti sono attivi:
- « n » posizionerà un nuovo contrassegno nel punto del cursore
- « m » sposterà il contrassegno attuale (se presente) nel punto del cursore
- « d » eliminerà il contrassegno attuale (se presente)
- « j » selezionerà il contrassegno precedente (se presente)
- « k » selezionerà il contrassegno successivo (se presente)

**Configurazione utente**

È personalizzabile usando ``~/.ginga/plugin_PixTable.cfg``, dove ``~`` è la tua
directory HOME:

.. code-block:: Python

  #
  # PixTable plugin preferences file
  #
  # Place this in file under ~/.ginga with the name "plugin_PixTable.cfg"

  # Default font
  font = 'fixed'

  # Default font size
  fontsize = 12

  # default size for mark point radius
  mark_radius = 10

  # style of point to draw
  mark_style = 'cross'

  # color of non-selected marks
  mark_color = 'purple'

  # color of selected mark
  select_color = 'cyan'

  # whether to update the pixel table when moving a mark around
  drag_update = True
