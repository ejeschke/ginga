Il plugin ``Header`` fornisce un elenco dei metadati associati all'immagine.

**Tipo di plugin: Globale**

``Header`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Il plugin ``Header`` mostra i metadati delle parole chiave FITS dell'immagine.
Inizialmente vengono mostrati solo i metadati dell'HDU primario.  Tuttavia, in
combinazione con il plugin ``MultiDim``, verranno mostrati i metadati degli
altri HDU.  Vedere ``MultiDim`` per i dettagli.

Se la casella « Ordinabile » in basso a sinistra dell'interfaccia è
selezionata, facendo clic sull'intestazione di una colonna la tabella viene
ordinata in base ai valori di quella colonna, il che può essere utile per
individuare rapidamente una particolare parola chiave.

La casella « Includi l'intestazione primaria » attiva o disattiva l'inclusione
delle parole chiave dell'HDU primario.  Questa opzione può essere disabilitata
se l'immagine è stata creata con l'opzione di non salvare l'intestazione
primaria.
