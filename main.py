import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const SchizzoApp());

class SchizzoApp extends StatelessWidget {
  const SchizzoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(
        cardTheme: const CardThemeData(margin: EdgeInsets.symmetric(vertical: 8.0), elevation: 4),
      ),
      home: const SchizzoDashboard(),
    );
  }
}

class SchizzoDashboard extends StatefulWidget {
  const SchizzoDashboard({super.key});
  @override
  State<SchizzoDashboard> createState() => _SchizzoDashboardState();
}

class _SchizzoDashboardState extends State<SchizzoDashboard> {
  final String baseUrl = 'http://127.0.0.1:8000'; // Assicurati sia l'IP corretto del PC se usi un emulatore
  final _homeCtrl = TextEditingController();
  final _awayCtrl = TextEditingController();
  final _matchIdCtrl = TextEditingController();
  final _arbCtrl = TextEditingController(text: '1.0');
  
  Map<String, dynamic>? _risultati;
  bool _isLoading = false;

  Future<void> analizzaMatch() async {
    setState(() => _isLoading = true);
    try {
      final response = await http.post(
        Uri.parse('$baseUrl/predict'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'home': _homeCtrl.text.trim(), 
          'away': _awayCtrl.text.trim(),
          'match_id': _matchIdCtrl.text.trim(),
          'arbitro_severity': double.tryParse(_arbCtrl.text) ?? 1.0,
        }),
      );
      
      if (response.statusCode == 200) {
        setState(() => _risultati = jsonDecode(response.body));
      } else {
        throw Exception('Errore server: ${response.statusCode}');
      }
    } catch (e) {
      ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text('Errore: $e')));
    } finally {
      setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('⚡ SCHIZZO V5.3', style: TextStyle(fontWeight: FontWeight.bold)),
        backgroundColor: Colors.blueGrey[900],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          children: [
            TextField(controller: _homeCtrl, decoration: const InputDecoration(labelText: 'Casa')),
            TextField(controller: _awayCtrl, decoration: const InputDecoration(labelText: 'Ospite')),
            TextField(controller: _matchIdCtrl, decoration: const InputDecoration(labelText: 'Match ID')),
            TextField(controller: _arbCtrl, decoration: const InputDecoration(labelText: 'Severità Arbitro')),
            const SizedBox(height: 20),
            ElevatedButton(
              onPressed: _isLoading ? null : analizzaMatch,
              child: _isLoading ? const CircularProgressIndicator(color: Colors.white) : const Text('ELABORA'),
            ),
            
            if (_risultati != null) ...[
              const SizedBox(height: 16),
              _buildResultCard(),
              if (_risultati!['panel_esperti'] != null)
                _buildExpertPanel(Map<String, dynamic>.from(_risultati!['panel_esperti'])),
              if (_risultati!['modello_poisson'] != null)
                _buildPoissonSection(Map<String, dynamic>.from(_risultati!['modello_poisson'])),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultCard() {
    return Card(
      color: Colors.grey[900],
      child: ListTile(
        title: Text(_risultati!['match'], style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.amber)),
        trailing: Text("Rischio: ${_risultati!['rischio_cartellini']}", style: const TextStyle(color: Colors.orange)),
      ),
    );
  }

  Widget _buildExpertPanel(Map<String, dynamic> experts) {
    return Card(
      color: Colors.black54,
      child: ExpansionTile(
        leading: const Icon(Icons.psychology, color: Colors.purpleAccent),
        title: const Text("Panel Esperti"),
        children: experts.entries.map((e) => ListTile(title: Text(e.key.toUpperCase()), trailing: Text(e.value.toString()))).toList(),
      ),
    );
  }

  Widget _buildPoissonSection(Map<String, dynamic> poisson) {
    return Card(
      color: Colors.grey[900],
      child: ExpansionTile(
        initiallyExpanded: true,
        leading: const Icon(Icons.analytics, color: Colors.blueAccent),
        title: const Text("ANALISI POISSON"),
        children: [
          // 1X2
          if (poisson['mercato_1X2'] != null)
            ListTile(title: const Text("Mercato 1X2"), subtitle: Text(poisson['mercato_1X2'].toString())),
          
          // Gol/No Gol
          if (poisson['gol_nogol'] != null)
            ExpansionTile(title: const Text("Gol / No Gol"), children: (poisson['gol_nogol'] as Map).entries.map((e) => ListTile(title: Text(e.key), trailing: Text(e.value.toString()))).toList()),

          // Under/Over
          if (poisson['under_over_completo'] != null)
            ExpansionTile(title: const Text("Under / Over"), children: (poisson['under_over_completo'] as Map).entries.map((e) => ListTile(title: Text(e.key), subtitle: Text("U: ${e.value['Under']} | O: ${e.value['Over']}"))).toList()),

          // Multigol
          if (poisson['multigol_completo'] != null)
            ExpansionTile(title: const Text("Multigol"), children: (poisson['multigol_completo'] as Map).entries.map((e) => ListTile(title: Text(e.key), trailing: Text(e.value.toString()))).toList()),

          // Risultati Esatti
          if (poisson['risultati_esatti'] != null)
            ExpansionTile(title: const Text("Risultati Esatti"), children: (poisson['risultati_esatti'] as Map).entries.map((e) => ListTile(title: Text(e.key), trailing: Text(e.value.toString()))).toList()),
        ],
      ),
    );
  }
}