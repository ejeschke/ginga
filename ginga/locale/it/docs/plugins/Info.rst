
Il plugin ``Info`` fornisce un pannello di metadati comunemente utili
sull'immagine del canale a fuoco.  Le informazioni comuni includono alcuni valori
di intestazione dei metadati, coordinate, dimensioni dell'immagine, valori minimo
e massimo, ecc.  Man mano che il cursore viene spostato sull'immagine, i valori
X, Y, Value, RA e DEC vengono aggiornati per riflettere il valore sotto il
cursore.

**Tipo di plugin: Globale**

``Info`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

In fondo all'interfaccia di ``Info`` ci sono i controlli di distribuzione del
colore e dei livelli di taglio.  Il selettore sopra le caselle dei livelli di
taglio ti consente di scegliere tra diversi algoritmi di distribuzione che
mappano i valori dell'immagine alla mappa dei colori.  Le scelte sono « linear »,
« log », « power », « sqrt », « squared », « asinh », « sinh » e « histeq »
(equalizzazione dell'istogramma).

Sotto questo, i livelli di taglio basso e alto sono mostrati e possono essere
regolati.  Premere il pulsante « Auto Levels » ricalcolerà i livelli di taglio in
base all'algoritmo attuale dei livelli di taglio automatici e ai parametri
definiti nelle preferenze del canale.

Sotto il pulsante « Auto Levels », lo stato delle impostazioni di « Cut New »,
« Zoom New » e « Center New » è mostrato per il canale attualmente attivo.
Questi indicano come le nuove immagini aggiunte al canale saranno influenzate dai
livelli di taglio automatici, dall'adattamento alla finestra e dallo spostamento
al centro dell'immagine.

La casella « Follow New » controlla se il visualizzatore mostrerà automaticamente
le nuove immagini aggiunte al canale.  La casella « Raise New » controlla se una
finestra del visualizzatore di immagini viene sollevata quando viene aggiunta una
nuova immagine.  Questi due controlli possono essere utili, ad esempio, se un
programma esterno sta aggiungendo immagini al visualizzatore, e desideri evitare
l'interruzione del tuo lavoro nell'esaminare una particolare immagine.

Come plugin globale, ``Info`` risponde a un cambio di focus a un nuovo canale
mostrando i metadati del nuovo canale.  Compare tipicamente sotto la scheda
« Synopsis » nell'interfaccia utente.

Questo plugin di solito non è configurato per essere chiudibile, ma l'utente può
renderlo tale impostando l'impostazione « closeable » su True nel file di
configurazione -- allora i pulsanti Chiudi e Aiuto verranno aggiunti nella parte
inferiore dell'interfaccia.
