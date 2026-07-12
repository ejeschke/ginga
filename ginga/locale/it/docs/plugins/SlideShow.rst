Riprodurre una presentazione di immagini.

**Tipo di plugin: Locale**

``SlideShow`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

***Caricare una presentazione***

Dopo aver avviato il plugin, puoi usare il pulsante « Carica » per caricare una
presentazione (vedi sotto per il formato del file della presentazione).  Puoi
poi ricaricare questa presentazione dopo aver modificato esternamente il file
in qualsiasi momento premendo « Ricarica ».

***Riprodurre una presentazione***

I pulsanti « Precedente » e « Successivo » possono servire ad andare indietro e
avanti manualmente all'interno dell'elenco.  Il controllo a pulsante rotante
tra questi due pulsanti ti porterà a una diapositiva particolare all'interno
dell'elenco.

I pulsanti « Avvia » e « Ferma » servono ad avviare o fermare l'avanzamento
automatico all'interno della presentazione.

***Controllare la durata***

Ogni diapositiva può avere un parametro « duration » separato (in secondi) per
controllare quanto tempo attendere prima di passare alla diapositiva
successiva, ma se questo manca per una diapositiva viene usata la durata
predefinita.  La durata predefinita può essere impostata usando il controllo
contrassegnato « Durata predefinita ».

Sotto il controllo della durata predefinita c'è un'etichetta che mostra la
durata della diapositiva e la durata totale della presentazione.

**Formato del file della presentazione**

Il formato del file della presentazione è un file di testo semplice separato da
virgole (CSV) con una riga di intestazione.  Il file deve contenere almeno una
colonna, intitolata « file ».  Questa colonna contiene i nomi dei file
(relativi o assoluti) dei percorsi ai file da caricare per ciascuna
diapositiva.

***Colonne facoltative***

* « duration »:  deve contenere la durata (in secondi) per ciascuna diapositiva
* « position »: indica la posizione della diapositiva nella presentazione.
  Si possono usare numeri in virgola mobile per rendere più facile riordinare
  le diapositive durante la modifica del file della presentazione.
