Apportare modifiche alle impostazioni del canale graficamente nell'interfaccia.

**Tipo di plugin: Locale**

``Preferences`` è un plugin locale, il che significa che è associato a un canale.
È possibile aprire un'istanza per ciascun canale.

**Uso**

Il plugin ``Preferences`` imposta le preferenze *su base per canale*.  Le
preferenze di un dato canale sono ereditate dal canale « Image » finché non
vengono impostate e salvate esplicitamente usando questo plugin.

Se viene premuto « Save Settings », le impostazioni verranno salvate nella
cartella $HOME/.ginga dell'utente (un file « channel_NAME.cfg » per ciascun
canale NAME) in modo che quando un canale con lo stesso nome viene creato in
future sessioni di Ginga, otterrà le stesse impostazioni.

**Preferenze di distribuzione del colore**

.. figure:: figures/cdist-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di distribuzione del colore

   Preferenze « Color Distribution ».

Le preferenze « Color Distribution » controllano le preferenze usate per la
conversione da valore del dato a indice di colore che avviene dopo l'applicazione
dei livelli di taglio e appena prima che venga eseguita la mappatura finale del
colore.  Riguarda come i valori tra i livelli di taglio basso e alto vengono
distribuiti alla fase di mappatura del colore e dell'intensità.

Il controllo « Algorithm » serve a impostare l'algoritmo usato per la mappatura.
Fai clic sul controllo per mostrare l'elenco, o semplicemente scorri la rotellina
del mouse passando il cursore sul controllo.  Ci sono otto algoritmi disponibili:
linear, log, power, sqrt, squared, asinh, sinh e histeq.  Il nome di ciascun
algoritmo indica come i dati vengono mappati ai colori della mappa dei colori.
« linear » è quello predefinito.

**Preferenze di mappatura del colore**

.. figure:: figures/cmap-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di mappatura del colore

   Preferenze « Color Mapping ».

Le preferenze « Color Mapping » controllano le preferenze usate per la mappa dei
colori e la mappa dell'intensità, usate durante la fase finale del processo di
mappatura del colore.  Insieme alle preferenze « Color Distribution », queste
controllano la mappatura dei valori dei dati in una rappresentazione visiva RGB a
24 bpp.

Il controllo « Colormap » seleziona quale mappa dei colori deve essere caricata e
usata.  Fai clic sul controllo per mostrare l'elenco, o semplicemente scorri la
rotellina del mouse passando il cursore sul controllo.

.. note:: Ginga viene fornito con una buona selezione di mappe dei colori, ma se
          ne vuoi di più, puoi aggiungerne di personalizzate o, se ``matplotlib``
          è installato, puoi caricare tutte quelle che ha.  Vedi « Customizing
          Ginga » per i dettagli.

Il controllo « Intensity » seleziona quale mappa dell'intensità deve essere usata
con la mappa dei colori.  La mappa dell'intensità viene applicata appena prima
della mappa dei colori, e può servire a cambiare la scala lineare standard dei
valori in una scala invertita, logaritmica, ecc.

La casella « Invert CMap » può servire a invertire la mappa dei colori
selezionata (nota che diverse mappe dei colori sono anche selezionabili dal
controllo « Colormap » in forma invertita).

Il controllo « Rotate » può servire a ruotare la mappa dei colori, mentre il
pulsante « Unrotate CMap » ripristinerà la rotazione al suo stato predefinito,
non ruotato.

Il pulsante « Color Defaults » reimposterà tutti i controlli di mappatura del
colore ai valori predefiniti: mappa dei colori « gray », intensità « ramp »
(lineare), e nessuna inversione o rotazione della mappa dei colori.

**Preferenze di contrasto e luminosità (bias)**

.. figure:: figures/contrast-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di contrasto e luminosità (bias)

   Preferenze « Contrast and Brightness (Bias) ».

I controlli « Contrast » e « Brightness » imposteranno il contrasto e la
luminosità (detta anche « bias ») del visualizzatore.  Offrono un'alternativa a
1) usare la modalità contrasto all'interno della finestra del visualizzatore, o
2) manipolare la barra dei colori trascinando (per impostare la
luminosità/bias) o scorrendo (per impostare il contrasto).

I controlli « Default Contrast » e « Default Brightness » riportano le rispettive
impostazioni al valore predefinito.

**Preferenze di tagli automatici**

.. figure:: figures/autocuts-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di tagli automatici

   Preferenze « Auto Cuts ».

Le preferenze « Auto Cuts » controllano il calcolo dei livelli di taglio per la
vista quando viene premuto il pulsante o il tasto dei livelli di taglio
automatici, o al caricamento di una nuova immagine con i tagli automatici
abilitati.  Puoi anche impostare i livelli di taglio manualmente da qui.

I campi « Cut Low » e « Cut High » possono servire a specificare manualmente i
livelli di taglio inferiore e superiore.  Premere « Cut Levels » imposterà i
livelli a questi valori manualmente.  Se un valore manca, si assume che assuma
per impostazione predefinita il valore attuale.

Premere « Auto Levels » calcolerà i livelli secondo un algoritmo.  Il controllo
« Auto Method » serve a scegliere quale algoritmo di tagli automatici viene
usato: « minmax » (valori minimo massimo), « median » (basato sul filtraggio
mediano), « histogram » (basato su un istogramma dell'immagine), « stddev »
(basato sulla deviazione standard dei valori dei pixel) o « zscale » (basato
sull'algoritmo ZSCALE reso popolare da IRAF).  Man mano che l'algoritmo cambia,
anche le caselle sotto di esso possono cambiare per consentire modifiche a
parametri particolari di ciascun algoritmo.

**Preferenze di trasformazione**

.. figure:: figures/transform-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di trasformazione

   Preferenze « Transform ».

Le preferenze « Transform » consentono di trasformare la vista dell'immagine
capovolgendo la vista in X o Y, scambiando gli assi X e Y, o ruotando l'immagine
di quantità arbitrarie.

Le caselle « Flip X » e « Flip Y » fanno sì che la vista dell'immagine venga
capovolta nell'asse corrispondente.

La casella « Swap XY » fa sì che la vista dell'immagine venga alterata scambiando
gli assi X e Y.  Questo può essere combinato con « Flip X » e « Flip Y » per
ruotare l'immagine a incrementi di 90 gradi.  Queste viste verranno renderizzate
più rapidamente delle rotazioni arbitrarie che usano il controllo « Rotate ».

Il controllo « Rotate » ruoterà la vista dell'immagine della quantità
specificata.  Il valore deve essere specificato in gradi.  « Rotate » può essere
specificato insieme al capovolgimento e allo scambio.

Il pulsante « Restore » ripristinerà la vista alla vista predefinita, che è non
capovolta, non scambiata e non ruotata.

**Preferenze WCS**

.. figure:: figures/wcs-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze WCS

   Preferenze « WCS ».

Le preferenze « WCS » controllano le preferenze di visualizzazione dei calcoli
del Sistema di Coordinate Mondiale (WCS) usati per riportare la posizione del
cursore nell'immagine.

Il controllo « WCS Coords » serve a selezionare il sistema di coordinate in cui
visualizzare il risultato.

Il controllo « WCS Display » serve a selezionare una lettura sessagesimale
(``H:M:S``) o una lettura in gradi decimali.

**Preferenze di zoom**

.. figure:: figures/zoom-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di zoom

   Preferenze « Zoom ».

Le preferenze « Zoom » controllano il comportamento di zoom/ridimensionamento di
Ginga.  Ginga supporta due algoritmi di zoom, scelti usando il controllo « Zoom
Alg »:

* L'algoritmo « step » ingrandisce l'immagine verso l'interno in passi discreti
  di 1X, 2X, 3X, ecc. o verso l'esterno in passi di 1/2X, 1/3X, 1/4X, ecc.
  Questo algoritmo produce visivamente il minor numero di artefatti, ma è un po'
  più lento a ingrandire su ampi intervalli quando si usa un movimento di
  scorrimento, perché è richiesto più « percorso » per ottenere un grande
  cambiamento di zoom (questo non è il caso se si usano i tasti scorciatoia di
  zoom, come i tasti numerici).

* L'algoritmo « rate » ingrandisce l'immagine facendo avanzare il ridimensionamento
  a una velocità definita dal valore nella casella « Zoom Rate ».  Questa
  velocità è per impostazione predefinita la radice quadrata di 2.  Numeri più
  grandi causano cambiamenti più grandi di scala tra i livelli di zoom.  Se ti
  piace ingrandire le immagini rapidamente, a un piccolo costo di qualità
  dell'immagine, probabilmente vorrai scegliere questa opzione.

Nota che indipendentemente da quale metodo venga scelto per l'algoritmo di zoom,
lo zoom può essere controllato tenendo premuto ``Ctrl`` (grossolano) o ``Shift``
(fine) mentre si scorre per vincolare la velocità di zoom (assumendo le
associazioni del mouse predefinite).

Il controllo « Stretch XY » può servire a stirare uno degli assi (X o Y) rispetto
all'altro.  Seleziona un asse con questo controllo e ruota la rotellina di
scorrimento passando sul controllo « Stretch Factor » per stirare i pixel
nell'asse selezionato.

I controlli « Scale X » e « Scale Y » offrono accesso diretto al ridimensionamento
sottostante, bypassando i passi di zoom discreti.  Qui, si possono digitare
valori esatti per ridimensionare l'immagine.  Al contrario, vedrai questi valori
cambiare man mano che l'immagine viene ingrandita.

I controlli « Scale Min » e « Scale Max » possono servire a porre un limite a
quanto l'immagine può essere ridimensionata.

Il controllo « Interpolation » ti permette di scegliere come l'immagine verrà
interpolata.  A seconda di quali pacchetti di supporto sono installati, si possono
fare le seguenti scelte:

* « basic » è il più vicino vicino usando un algoritmo integrato, questo è sempre
  disponibile, è ragionevolmente veloce ed è quello predefinito.
* « area »
* « bicubic »
* « lanczos »
* « linear »
* « nearest » è il più vicino vicino (usando un pacchetto di supporto)

Il pulsante « Zoom Defaults » ripristinerà i controlli ai valori predefiniti di
Ginga.

**Preferenze di spostamento (pan)**

.. figure:: figures/pan-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di spostamento

   Preferenze « Pan ».

Le preferenze « Pan » controllano il comportamento di spostamento di Ginga.

I controlli « Pan X » e « Pan Y » offrono accesso diretto per impostare la
posizione di spostamento nell'immagine (la parte dell'immagine situata al centro
della finestra) -- puoi vederli cambiare mentre ti sposti nell'immagine.  Puoi
impostare questi valori e poi premere « Apply Pan » per spostarti a quella
posizione esatta.

Se il controllo « Pan Coord » è impostato su « data », allora lo spostamento è
controllato dalle coordinate dei dati nell'immagine; se impostato su « WCS »,
allora i valori mostrati nei controlli « Pan X » e « Pan Y » saranno coordinate
WCS (assumendo un WCS valido nell'immagine).  In quest'ultimo caso, il controllo
« WCS sexagesimal » può essere lasciato deselezionato per mostrare/impostare le
coordinate in gradi, o selezionato per mostrare/impostare i valori in notazione
sessagesimale standard.

Il pulsante « Center Image » imposta la posizione di spostamento al centro
dell'immagine, calcolato dimezzando le dimensioni in X e Y.

La casella « Mark Center », quando selezionata, farà sì che Ginga disegni un
piccolo reticolo al centro dell'immagine.  Questo è utile per conoscere la
posizione di spostamento e per il debug.

**Preferenze generali**

.. figure:: figures/general-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze generali

   Preferenze « General ».

L'impostazione « Num Images » specifica quante immagini possono essere conservate
nei buffer di questo canale prima di essere espulse.  Un valore di zero (0)
significa illimitato -- le immagini non verranno mai espulse.  Se un'immagine è
stata caricata da un archivio accessibile e viene espulsa, verrà automaticamente
ricaricata se l'immagine viene rivisitata navigando nel canale.

L'impostazione « Sort Order » determina se le immagini vengono ordinate nel canale
alfabeticamente per nome o per l'ora in cui sono state caricate.  Questo
influenza principalmente l'ordine in cui le immagini vengono scorse quando si
usano i tasti o pulsanti « freccia » su/giù, e non necessariamente come vengono
visualizzate in plugin come « Contents » o « Thumbs » (che generalmente hanno la
propria preferenza di impostazione per l'ordinamento).

La casella « Use scrollbars » controlla se il visualizzatore di canale mostrerà
barre di scorrimento attorno al bordo della cornice del visualizzatore per
spostare l'immagine.

**Preferenze di ripristino (visualizzatore)**

.. figure:: figures/reset-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di ripristino (visualizzatore)

   Preferenze « Reset » (visualizzatore).

Ogni visualizzatore di canale ha un *profilo di visualizzatore* che viene
inizializzato allo stato del visualizzatore subito dopo la creazione e il
ripristino delle impostazioni salvate per quel canale.  Quando si passa da
un'immagine all'altra, gli attributi del visualizzatore possono essere
ripristinati a questo profilo secondo le caselle selezionate in questa sezione.
*Se non è selezionato nulla, non verrà ripristinato nulla dal profilo di
visualizzatore*.

Per usare questa funzione, imposta le tue preferenze di visualizzatore come
preferisci e fai clic sul pulsante « Update Viewer Profile » in fondo al plugin.
Ora seleziona quali elementi devono essere ripristinati a quei valori tra le
immagini.  Infine, fai clic sul pulsante « Save Settings » in fondo se vuoi che
queste impostazioni siano persistenti tra i riavvii di Ginga e impostate come
profilo utente predefinito per questo canale quando riavvii ginga e ricrei questo
canale.

* « Reset Scale » ripristinerà il livello di zoom (scala) al profilo di
  visualizzatore
* « Reset Pan » ripristinerà la posizione di spostamento al profilo di
  visualizzatore
* « Reset Transform » ripristinerà qualsiasi trasformazione di
  capovolgimento/scambio al profilo di visualizzatore
* « Reset Rotation » ripristinerà qualsiasi rotazione al profilo di
  visualizzatore
* « Reset Cuts » ripristinerà qualsiasi livello di taglio al profilo di
  visualizzatore
* « Reset Distribution » ripristinerà qualsiasi distribuzione del colore al
  profilo di visualizzatore
* « Reset Contrast » ripristinerà qualsiasi contrasto/bias al profilo di
  visualizzatore
* « Reset Color Map » ripristinerà qualsiasi impostazione della mappa dei colori
  al profilo di visualizzatore

.. tip:: Se usi questa funzione potresti anche voler impostare « Remember (Image)
         Preferences » (vedi sotto).

.. note:: L'ordine completo delle regolazioni è:

          * qualsiasi elemento di ripristino dal profilo di visualizzatore
            predefinito, se presente
          * qualsiasi elemento memorizzato dal profilo dell'immagine viene
            applicato, se presente
          * qualsiasi regolazione automatica (cuts/zoom/center) viene applicata,
            se non è stata sovrascritta da un'impostazione memorizzata

**Preferenze di memorizzazione (immagine)**

.. figure:: figures/remember-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di memorizzazione (immagine)

   Preferenze « Remember » (immagine).

Quando un'immagine viene caricata, viene creato un *profilo dell'immagine* e
allegato ai metadati dell'immagine nel canale.  Questi profili vengono
continuamente aggiornati con lo stato del visualizzatore man mano che l'immagine
viene manipolata.  Le preferenze « Remember » controllano quali attributi di
questi profili vengono ripristinati allo stato del visualizzatore quando
l'immagine viene (ri)navigata nel canale:

* « Remember Scale » ripristinerà il livello di zoom (scala) dell'immagine
* « Remember Pan » ripristinerà la posizione di spostamento nell'immagine
* « Remember Transform » ripristinerà qualsiasi trasformazione di capovolgimento o
  scambio di assi
* « Remember Rotation » ripristinerà qualsiasi rotazione dell'immagine
* « Remember Cuts » ripristinerà qualsiasi livello di taglio per l'immagine
* « Remember Distribution » ripristinerà qualsiasi distribuzione del colore
  (linear, log, ecc.)
* « Remember Contrast » ripristinerà qualsiasi regolazione di contrasto/bias
* « Remember Color Map » ripristinerà qualsiasi scelta di mappa dei colori fatta

*Se non è selezionato nulla, non verrà ripristinato nulla dal profilo
dell'immagine*.

.. note:: Questi elementi verranno impostati PRIMA che venga fatta qualsiasi
          regolazione automatica (cut/zoom/center new).  Se un elemento
          memorizzato è impostato, sovrascriverà qualsiasi impostazione di
          regolazione automatica per il canale.

.. tip:: Se usi questa funzione potresti anche voler impostare « Reset (Viewer)
         Preferences » (vedi sopra).

***Un esempio***

Come esempio di uso delle impostazioni Reset e Remember, supponi di usare
frequentemente la regolazione del contrasto.  Vorresti che il contrasto che
imposti con una particolare immagine venga ripristinato quando quell'immagine
viene visualizzata di nuovo.  Tuttavia, quando visualizzi una nuova immagine,
vorresti che il contrasto parta da qualche impostazione normale.

Per ottenere questo, reimposta manualmente il contrasto all'impostazione
predefinita desiderata.  Seleziona « Reset Contrast » e poi premi « Update Viewer
Profile ».  Infine, seleziona « Remember Contrast ».  Fai clic su « Save
Settings » per rendere persistenti le impostazioni del canale.

**Preferenze di nuova immagine**

.. figure:: figures/newimages-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze di nuova immagine

   Preferenze « New Image ».

Le preferenze « New Images » determinano come Ginga reagisce quando una nuova
immagine viene caricata nel canale.  *Questo include quando un'immagine più
vecchia viene rivisitata facendo clic sulla sua miniatura nel plugin ``Thumbs`` o
facendo doppio clic sul suo nome nel plugin ``Contents``*.

L'impostazione « Cut New » controlla se un calcolo automatico dei livelli di
taglio debba essere eseguito sulla nuova immagine, o se debbano essere applicati
i livelli di taglio attualmente impostati.  Le impostazioni possibili sono:

* « off »: usa sempre i livelli di taglio attualmente impostati;
* « once »: calcola nuovi livelli di taglio per la prima immagine visitata, poi
  passa a « off »;
* « override »: calcola nuovi livelli di taglio finché l'utente non li sovrascrive
  impostando manualmente dei livelli di taglio, poi passa a « off »; o
* « on »: calcola sempre nuovi livelli di taglio.

.. tip:: L'impostazione « override » è fornita per la comodità di avere livelli
         di taglio automatici, evitando al contempo che un taglio impostato
         manualmente venga sovrascritto quando viene acquisita una nuova
         immagine.  Quando si digita nella finestra dell'immagine, il tasto punto
         e virgola può servire a riportare la modalità a override (da « off »),
         mentre i due punti imposteranno la preferenza su « on ».  Il plugin
         ``Info`` (scheda: Synopsis) mostra lo stato di questa impostazione.

L'impostazione « Zoom New » controlla se la visita di un'immagine debba impostare
il livello di zoom per adattare l'immagine alla finestra.  Le impostazioni
possibili sono:

* « off »: usa sempre i livelli di zoom attualmente impostati;
* « once »: adatta la prima immagine alla finestra, poi passa a « off »;
* « override »: le immagini vengono adattate automaticamente finché il livello di
  zoom non viene cambiato manualmente, poi la modalità passa automaticamente a
  « off »; o
* « on »: la nuova immagine viene sempre ingrandita per adattarsi.

.. tip:: L'impostazione « override » è fornita per la comodità di avere uno zoom
         automatico, evitando al contempo che un livello di zoom impostato
         manualmente venga sovrascritto quando viene acquisita una nuova
         immagine.  Quando si digita nella finestra dell'immagine, il tasto
         apostrofo (detto anche « virgoletta singola ») può servire a riportare
         la modalità a « override » (da « off »), mentre la virgoletta (detta
         anche « virgoletta doppia ») imposterà la preferenza su « on ».  Il
         plugin ``Info`` (scheda: Synopsis) mostra lo stato di questa
         impostazione.

L'impostazione « Center New » controlla se la visita di un'immagine debba far sì
che la posizione di spostamento venga reimpostata al centro dell'immagine.  Le
impostazioni possibili sono:

* « off »: lascia la posizione di spostamento attuale così com'è;
* « once »: centra la prima immagine visitata, poi passa a « off »;
* « override »: le immagini vengono centrate automaticamente finché la posizione
  di spostamento non viene cambiata manualmente, poi la modalità passa
  automaticamente a « off »; o
* « on »: la nuova immagine viene sempre centrata.

L'impostazione « Follow New » serve a controllare se Ginga cambierà la
visualizzazione se una nuova immagine viene caricata nel canale.  Se
deselezionata, l'immagine viene caricata (come si vede, per esempio, dalla sua
comparsa nella scheda ``Thumbs``), ma la visualizzazione non cambierà alla nuova
immagine.  Questa impostazione è utile nei casi in cui nuove immagini vengono
caricate con qualche mezzo automatizzato in un canale e l'utente desidera
studiare l'immagine attuale senza essere interrotto.

L'impostazione « Raise New » controlla se Ginga solleverà la scheda di un canale
quando un'immagine viene caricata in quel canale.  Se deselezionata, allora Ginga
non solleverà la scheda quando un'immagine viene caricata in quel particolare
canale.

L'impostazione « Create Thumbnail » controlla se Ginga creerà una miniatura per le
immagini caricate in quel canale.  Nei casi in cui molte immagini vengono
caricate frequentemente in un canale (ad es. un feed video a bassa frequenza),
può essere indesiderabile creare miniature per tutte.

L'impostazione « Auto Orient » controlla se Ginga debba tentare di orientare le
immagini per impostazione predefinita secondo i metadati dell'immagine.  Questo è
attualmente utile solo per immagini RGB (ad es. JPEG) che contengono tali
metadati.  Al momento non orienta automaticamente per WCS.

**Preferenze dei profili ICC**

.. figure:: figures/icc-prefs.png
   :width: 400px
   :align: center
   :alt: Preferenze dei profili ICC

   Preferenze « ICC Profiles ».

Ginga può fare uso di profili ICC (gestione del colore) nella catena di rendering
usando la libreria LittleCMS.

.. note:: Per fare uso dei profili ICC, crea una cartella « profiles » nella
          « home » di Ginga (di solito $HOME/.ginga) e metti lì tutti i profili
          necessari.  Un profilo di lavoro dovrebbe essere impostato aggiungendo
          un valore per « icc_working_profile » nel tuo file
          $HOME/.ginga/general.cfg -- non includere alcun percorso iniziale, solo
          il nome file di un file ICC nella cartella profiles.  Questo verrà usato
          per convertire qualsiasi file RGB contenente un profilo al profilo di
          lavoro.

Puoi impostare i profili di uscita per qualsiasi canale in questa sezione del
plugin Preferences.

Il controllo « Output ICC profile » seleziona quale profilo usare per il
rendering di uscita verso il display.  Le scelte sono dai tuoi file di profilo in
$HOME/.ginga/profiles.  Normalmente questo dovrebbe essere un profilo di display.

Il controllo « Rendering intent » sceglie l'algoritmo usato per rendere il colore
nel processo di conversione ICC.  Le scelte sono:

* absolute_colorimetric
* perceptual
* relative_colorimetric
* saturation

« Proof ICC profile » e « Proof intent » sono scelti in modo simile per il
proofing.

La casella « Black point compensation » attiva o disattiva questa funzione nel
processo di conversione del colore.  Vedi la documentazione di LittleCMS o della
gestione del colore ICC in generale per i dettagli su queste scelte.
