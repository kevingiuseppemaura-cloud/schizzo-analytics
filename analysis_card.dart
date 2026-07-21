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
        title: Row(
          children: [
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
            ),
            if (badgeText != null) ...[
              const SizedBox(width: 8),
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
                      "Nessun dato disponibile per questo modulo.",
                      style: TextStyle(color: Colors.grey, italic: true),
                    ),
                  )
                : Column(
                    children: data.entries.map((entry) {
                      final double? valueAsNum = double.tryParse(
                        entry.value.toString().replaceAll('%', '').replaceAll(',', '.'),
                      );

                      return Padding(
                        padding: const EdgeInsets.symmetric(vertical: 6.0),
                        child: Row(
                          mainAxisAlignment: MainAxisAlignment.spaceBetween,
                          children: [
                            Text(
                              entry.key,
                              style: const TextStyle(
                                fontWeight: FontWeight.w500,
                                fontSize: 14,
                              ),
                            ),
                            Row(
                              children: [
                                Text(
                                  entry.value.toString(),
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    fontSize: 14,
                                    color: (valueAsNum != null && valueAsNum > 60)
                                        ? Colors.green[700]
                                        : Colors.black87,
                                  ),
                                ),
                              ],
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
}