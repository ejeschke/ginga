``WCSMatch`` è un plugin globale per il visualizzatore di immagini Ginga che
permette di allineare grossolanamente immagini con scale e orientamenti diversi
a scopo di visualizzazione, usando il sistema di coordinate mondiale (WCS)
delle immagini.

**Tipo di plugin: Globale**

``WCSMatch`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Per usarlo, avvia semplicemente il plugin e, dall'interfaccia del plugin,
seleziona un canale dal menu a discesa « Canale di riferimento ».  L'immagine
contenuta in quel canale verrà usata come riferimento per sincronizzare le
immagini negli altri canali.

I canali verranno sincronizzati nella visualizzazione (panoramica, scala (zoom),
trasformazioni (capovolgimenti) e rotazione).  Le caselle « Allinea la
panoramica », « Allinea la scala », « Allinea le trasformazioni » e « Allinea la
rotazione » possono essere selezionate o meno per controllare quali attributi
vengono sincronizzati tra i canali.

Per « sbloccare » completamente la sincronizzazione, seleziona semplicemente
« None » dal menu a discesa « Canale di riferimento ».

Attualmente non c'è modo di limitare i canali interessati dal plugin.
