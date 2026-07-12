
GUI di download per il visualizzatore di riferimento Ginga.

**Tipo di plugin: Globale**

``Download`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

Apri questo plugin per monitorare l'avanzamento dei download di URI.  Avvialo
usando il menu « Plugins » o « Operations », e selezionando il plugin
« Downloads » sotto la categoria « Util ».

Se vuoi avviare un download, trascina semplicemente un URI in un visualizzatore
di immagine di canale o nel pannello ``Thumbs``.

Puoi rimuovere le informazioni su un download in qualsiasi momento facendo clic
sul pulsante « Cancella » della sua voce.  Puoi cancellare le voci di tutti i
download facendo clic sul pulsante « Cancella tutto » in fondo.

Attualmente, non è possibile annullare un download in corso.

**Impostazioni**

L'opzione ``auto_clear_download``, se impostata su `True`, farà sì che una voce
di download venga eliminata automaticamente dal pannello quando il download si
completa.  Non rimuove alcun file scaricato.

La cartella di download può essere definita dall'utente assegnando un valore
all'impostazione « download_folder » in ~/.ginga/general.cfg.  Se non è
assegnata, per impostazione predefinita è una cartella nella directory
temporanea predefinita specifica della piattaforma (come indicato dal modulo
« tempfile » di Python).
