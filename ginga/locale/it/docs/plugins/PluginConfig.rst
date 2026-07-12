
Il plugin ``PluginConfig`` permette di configurare i plugin visibili nei tuoi
menu.

**Tipo di plugin: Globale**

``PluginConfig`` è un plugin globale.  Può essere aperta una sola istanza.

**Uso**

``PluginConfig`` serve a configurare i plugin da usare in Ginga.  Gli elementi
configurabili per ciascun plugin includono:

* se è abilitato (e quindi se compare nei menu)
* la categoria del plugin (usata per costruire la gerarchia dei menu)
* lo spazio di lavoro in cui il plugin si aprirà
* se è un plugin globale, se si avvia automaticamente all'avvio del
  visualizzatore di riferimento
* se il nome del plugin debba essere nascosto (non comparire nei menu di
  attivazione dei plugin)

All'avvio di ``PluginConfig`` verrà mostrata una tabella dei plugin.  Per
modificare gli attributi sopra indicati per i plugin, fai clic su « Modifica »,
che aprirà una finestra di dialogo per modificare la tabella.

Per ciascun plugin che desideri configurare, fai clic su una voce nella
tabella principale e poi regola le impostazioni nella finestra di dialogo,
quindi fai clic su « Imposta » nella finestra di dialogo per riportare le
modifiche nella tabella.  Se non fai clic su « Imposta », nella tabella non
viene cambiato nulla.  Quando hai finito di modificare le configurazioni, fai
clic su « Chiudi » nella finestra di dialogo per chiudere la finestra di
modifica.

.. note:: Non è consigliabile cambiare lo spazio di lavoro di un plugin a meno
          che tu non scelga uno spazio di lavoro di dimensioni compatibili con
          l'originale, poiché il plugin potrebbe non essere visualizzato
          correttamente.  In caso di dubbio, lascia invariato lo spazio di
          lavoro.  Inoltre, disabilitare i plugin nella categoria « Systems »
          può far smettere di funzionare alcune funzionalità attese.


.. important:: Per far persistere le modifiche tra i riavvii di Ginga, fai
               clic su « Salva » per salvare le impostazioni (in
               `$HOME/.ginga/plugins.json`).  Riavvia Ginga per vedere le
               modifiche ai menu (tramite le modifiche di « category »).
               **Rimuovi questo file manualmente se vuoi ripristinare le
               configurazioni dei plugin ai valori predefiniti**.
