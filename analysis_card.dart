import 'package:flutter/material.dart';

class AnalysisCard extends StatelessWidget {
  final String title;
  final IconData icon;
  final Color themeColor;
  final Map<String, dynamic> data;
  final bool initiallyExpanded;
  final String? badgeText;

  const AnalysisCard({
    Key? key,
    required this.title,
    required this.icon,
    required this.themeColor,
    required this.data,
    this.initiallyExpanded = true,
    this.badgeText,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Card(
      elevation: 3,
      margin: const EdgeInsets.symmetric(vertical: 8.0),
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      clipBehavior: Clip.antiAlias,
      child: ExpansionTile(
        initiallyExpanded: initiallyExpanded,
        leading: CircleAvatar(
          backgroundColor: themeColor.withOpacity(0.15),
          child: Icon(icon, color: themeColor),
        ),
        // Expanded previene l'overflow orizzontale del titolo
        title: Row(
          children: [
            Expanded(
              child: Text(
                title,
                overflow: TextOverflow.ellipsis,
                style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 15),
              ),
            ),
            if (badgeText != null) ...[
              const SizedBox(width: 6),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                decoration: BoxDecoration(
                  color: themeColor.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(12),
                ),
                child: Text(
                  badgeText!,
                  style: TextStyle(
                    color: themeColor,
                    fontSize: 11,
                    fontWeight: FontWeight.bold,
                  ),
                ),
              ),
            ]
          ],
        ),
        children: [
          Padding(
            padding: const EdgeInsets.all(16.0),
            child: data.isEmpty
                ? const Center(
                    child: Text(
                      "Nessun dato disponibile.",
                      style: TextStyle(color: Colors.grey, fontStyle: FontStyle.italic),
                    ),
                  )
                : Column(
                    children: data.entries.map((entry) {
                      // Formattazione etichetta (es: esito_1x2 -> ESITO 1X2)
                      final cleanKey = entry.key.replaceAll('_', ' ').toUpperCase();

                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6.0),
                        child: Row(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            // Nome del parametro a sinistra
                            Expanded(
                              flex: 2,
                              child: Text(
                                cleanKey,
                                style: const TextStyle(
                                  fontWeight: FontWeight.w600,
                                  fontSize: 13,
                                  color: Colors.black87,
                                ),
                              ),
                            ),
                            const SizedBox(width: 8),
                            // Valore formattato a destra
                            Expanded(
                              flex: 3,
                              child: Align(
                                alignment: Alignment.centerRight,
                                child: _buildFormattedValue(entry.value),
                              ),
                            ),
                          ],
                        ),
                      );
                    }).toList(),
                  ),
          ),
        ],
      ),
    );
  }

  // Helper per spezzettare e pulire i dati annidati (Mappe, Liste, Percentuali)
  Widget _buildFormattedValue(dynamic value) {
    if (value is Map) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: value.entries.map((e) {
          return Padding(
            padding: const EdgeInsets.only(bottom: 2.0),
            child: Text(
              "${e.key}: ${e.value}%",
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            ),
          );
        }).toList(),
      );
    } else if (value is List) {
      return Column(
        crossAxisAlignment: CrossAxisAlignment.end,
        children: value.map((item) {
          if (item is Map) {
            final res = item['risultato'] ?? item['esito'] ?? item.toString();
            final prob = item['probabilita'] ?? item['prob'] ?? '';
            return Text(
              "$res ${prob != '' ? '($prob%)' : ''}",
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
            );
          }
          return Text(
            item.toString(),
            style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 13),
          );
        }).toList(),
      );
    } else {
      final String strVal = value.toString();
      final double? valueAsNum = double.tryParse(
        strVal.replaceAll('%', '').replaceAll(',', '.'),
      );

      return Text(
        strVal.endsWith('%') || valueAsNum == null ? strVal : "$strVal%",
        style: TextStyle(
          fontWeight: FontWeight.bold,
          fontSize: 14,
          color: (valueAsNum != null && valueAsNum > 60)
              ? Colors.orange[800] // Colore arancione per i valori alti
              : Colors.black87,
        ),
      );
    }
  }
}