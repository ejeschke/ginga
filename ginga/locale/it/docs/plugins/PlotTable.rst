Un plugin per visualizzare un grafico di base di due colonne selezionate
qualsiasi di una tabella.

**Tipo di plugin: Locale**

``PlotTable`` è un plugin locale, il che significa che è associato a un canale.
Non è un singleton, il che significa che è possibile aprire più istanze per
ciascun canale.

**Uso**

``PlotTable`` è un plugin progettato per tracciare due colonne selezionate
qualsiasi di un dato HDU di tabella FITS (accessibile tramite ``MultiDim``).
Per le colonne mascherate, i dati mascherati non vengono mostrati (anche se solo
uno della coppia ``(X, Y)`` è mascherato).
È pensato come un modo per esaminare rapidamente i dati di una tabella e non per
un'analisi scientifica dettagliata.
