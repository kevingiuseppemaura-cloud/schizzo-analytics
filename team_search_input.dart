import 'package:flutter/material.dart';

class TeamSearchInput extends StatelessWidget {
  final String label;
  final List<String> availableTeams;
  final Function(String) onTeamSelected;

  const TeamSearchInput({
    Key? key,
    required this.label,
    required this.availableTeams,
    required this.onTeamSelected,
  }) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return Autocomplete<String>(
      // 1. Logica di ricerca: filtra le squadre in base a ciò che scrivi
      optionsBuilder: (TextEditingValue textEditingValue) {
        if (textEditingValue.text.isEmpty) {
          return const Iterable<String>.empty();
        }
        return availableTeams.where((String team) {
          return team.toLowerCase().contains(textEditingValue.text.toLowerCase());
        });
      },
      // 2. Azione quando selezioni una squadra dal menu a tendina
      onSelected: (String selection) {
        onTeamSelected(selection);
      },
      // 3. Design del campo di testo
      fieldViewBuilder: (context, textEditingController, focusNode, onFieldSubmitted) {
        return TextFormField(
          controller: textEditingController,
          focusNode: focusNode,
          decoration: InputDecoration(
            labelText: label,
            hintText: 'Inizia a digitare...',
            prefixIcon: const Icon(Icons.sports_soccer, color: Colors.blueAccent),
            border: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12.0),
            ),
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(12.0),
              borderSide: const BorderSide(color: Colors.blueAccent, width: 2.0),
            ),
            filled: true,
            fillColor: Colors.grey[50],
          ),
        );
      },
    );
  }
}