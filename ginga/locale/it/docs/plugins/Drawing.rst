Un plugin per disegnare forme sulla tela (grafica sovrapposta).

**Tipo di plugin: Locale**

``Drawing`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

Questo plugin può essere usato per disegnare molte forme diverse sulla
visualizzazione dell'immagine.  In modalità « disegna », seleziona una forma dal
menu a discesa, regola i parametri della forma (se necessario) e disegna
sull'immagine usando il pulsante sinistro del mouse.  Puoi scegliere di disegnare
nello spazio dei pixel o WCS.

Per spostare o modificare una forma esistente, imposta il plugin in modalità
« modifica » o « sposta », rispettivamente.

Per salvare le forme disegnate come immagine di maschera, fai clic sul pulsante
« Crea maschera » e vedrai una nuova immagine di maschera creata in Ginga.
Quindi usa il plugin ``SaveImage`` per salvarla come FITS a estensione singola.
Nota che la maschera assumerà la dimensione dell'immagine visualizzata.  Pertanto,
per creare maschere di dimensioni di immagine diverse, devi ripetere i passaggi
più volte.

Le forme disegnate sulla tela possono essere caricate e/o salvate nel formato
astropy-regions (compatibile con le regioni DS9).  Per usarlo devi avere
installato il pacchetto astropy-regions.  Disegna semplicemente oggetti sulla
tela, con coordinate « data » (pixel) o « wcs ».  Nota che non tutti gli oggetti
della tela di Ginga possono essere convertiti in forme di regioni e alcuni
attributi potrebbero non essere salvati, potrebbero essere ignorati o potrebbero
causare errori nel tentativo di caricare le forme delle regioni in altri
software.
