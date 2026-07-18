import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

void main() => runApp(const SchizzoApp());

class SchizzoApp extends StatelessWidget {
  const SchizzoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Schizzo Dashboard',
      theme: ThemeData(
        primarySwatch: Colors.indigo,
        useMaterial3: true,
      ),
      home: const DashboardScreen(),
    );
  }
}

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashboardScreenState extends State<DashboardScreen> {
  // Esempio di match_id, home e away. 
  // In futuro potrai rendere questi valori dinamici tramite input utente.
  final String matchId = "12345";
  final String homeTeam = "Juventus";
  final String awayTeam = "Milan";

  Future<Map<String, dynamic>> fetchDashboardData() async {
    final String baseUrl = 'https://schizzo-analytics.onrender.com';

    // 1. Chiamata POST per il Motore Matematico (Poisson)
    final statsResponse = await http.post(
      Uri.parse('$baseUrl/predict'),
      headers: {"Content-Type": "application/json"},
      body: json.encode({
        "match_id": matchId,
        "home": homeTeam,
        "away": awayTeam,
      }),
    );

    // 2. Chiamata GET per gli Esperti
    final expertsResponse = await http.get(Uri.parse('$baseUrl/esperti/$matchId'));

    if (statsResponse.statusCode == 200 && expertsResponse.statusCode == 200) {
      final statsData = json.decode(statsResponse.body);
      final expertsData = json.decode(expertsResponse.body);

      return {
        "stats": statsData['risultato'], // Estraiamo solo il dizionario delle percentuali
        "experts": expertsData['esperti'], // Estraiamo solo il dizionario degli esperti
      };
    } else {
      throw Exception('Errore nel recupero dati: ${statsResponse.statusCode}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Analisi Match: Schizzo")),
      body: FutureBuilder<Map<String, dynamic>>(
        future: fetchDashboardData(),
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          } else if (snapshot.hasError) {
            return Center(child: Text("Errore: ${snapshot.error}"));
          }

          final data = snapshot.data!;
          return SingleChildScrollView(
            padding: const EdgeInsets.all(16.0),
            child: Column(
              children: [
                _buildCard("Statistiche Poisson", data['stats']),
                const SizedBox(height: 16),
                _buildCard("Consigli Esperti", data['experts']),
              ],
            ),
          );
        },
      ),
    );
  }

  Widget _buildCard(String title, Map<String, dynamic> content) {
    return Card(
      elevation: 4,
      child: Padding(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(title, style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 18)),
            const Divider(),
            ...content.entries.map((entry) => Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4.0),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(entry.key, style: const TextStyle(fontWeight: FontWeight.w500)),
                      Text(entry.value.toString()),
                    ],
                  ),
                )),
          ],
        ),
      ),
    );
  }
}