import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'widgets/team_search_input.dart';
import 'widgets/analysis_card.dart'; // Import del nostro widget di layout espandibile

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
  // 1. Variabili di Stato Dinamiche (con valori di default di test)
  String matchId = "12345";
  String homeTeam = "Juventus";
  String awayTeam = "Milan";

  // Future gestito nello stato per controllare l'esecuzione al tap del bottone
  Future<Map<String, dynamic>>? _dashboardFuture;

  // Lista di squadre disponibili per l'Autocomplete
  final List<String> squadreDisponibili = [
    'Atalanta', 'Bologna', 'Cagliari', 'Empoli', 'Fiorentina',
    'Genoa', 'Inter', 'Juventus', 'Lazio', 'Lecce',
    'Milan', 'Monza', 'Napoli', 'Parma', 'Roma',
    'Salernitana', 'Sampdoria', 'Sassuolo', 'Torino', 'Udinese', 'Venezia', 'Verona'
  ];

  @override
  void initState() {
    super.initState();
    // Prima chiamata automatica all'avvio
    _dashboardFuture = fetchDashboardData();
  }

  // Metodo per scatenare una nuova analisi al click del bottone
  void _eseguiAnalisi() {
    setState(() {
      _dashboardFuture = fetchDashboardData();
    });
  }

  Future<Map<String, dynamic>> fetchDashboardData() async {
    final String baseUrl = 'https://schizzo-analytics.onrender.com';

    // 1. Chiamata POST per il Motore Matematico (Poisson)
    http.Response statsResponse = await http.post(
      Uri.parse('$baseUrl/analizza'),
      headers: {"Content-Type": "application/json"},
      body: json.encode({
        "match_id": matchId,
        "squadra_casa": homeTeam,
        "squadra_ospite": awayTeam,
      }),
    );

    // Fallback di sicurezza: se la rotta /analizza non risponde, tenta /predict
    if (statsResponse.statusCode != 200) {
      statsResponse = await http.post(
        Uri.parse('$baseUrl/predict'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "match_id": matchId,
          "home": homeTeam,
          "away": awayTeam,
        }),
      );
    }

    // 2. Chiamata GET per gli Esperti
    final expertsResponse = await http.get(Uri.parse('$baseUrl/esperti/$matchId'));

    if (statsResponse.statusCode == 200) {
      final statsData = json.decode(statsResponse.body);
      
      // Estrazione dinamica e sicura delle percentuali
      Map<String, dynamic> stats = {};
      if (statsData.containsKey('previsioni_poisson')) {
        stats = Map<String, dynamic>.from(statsData['previsioni_poisson']);
      } else if (statsData.containsKey('risultato')) {
        stats = Map<String, dynamic>.from(statsData['risultato']);
      } else {
        stats = statsData;
      }

      // Estrazione sicura dei dati esperti
      Map<String, dynamic> experts = {};
      if (expertsResponse.statusCode == 200) {
        final expertsData = json.decode(expertsResponse.body);
        if (expertsData is Map<String, dynamic> && expertsData.containsKey('modulo_esperti')) {
          experts = Map<String, dynamic>.from(expertsData['modulo_esperti']);
        } else if (expertsData is Map<String, dynamic> && expertsData.containsKey('esperti')) {
          experts = Map<String, dynamic>.from(expertsData['esperti']);
        }
      }

      return {
        "stats": stats,
        "experts": experts,
      };
    } else {
      throw Exception('Errore nel recupero dati: ${statsResponse.statusCode}');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text("Analisi Match: Schizzo")),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            // ==========================================
            // 🎛️ PANNELLO INPUT INTELLIGENTE
            // ==========================================
            Card(
              elevation: 3,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Seleziona Partita",
                      style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 16),
                    
                    // Input Squadra Casa con Autocomplete
                    TeamSearchInput(
                      label: "Squadra Casa",
                      availableTeams: squadreDisponibili,
                      onTeamSelected: (selected) {
                        setState(() {
                          homeTeam = selected;
                        });
                      },
                    ),
                    const SizedBox(height: 12),

                    // Input Squadra Trasferta con Autocomplete
                    TeamSearchInput(
                      label: "Squadra Trasferta",
                      availableTeams: squadreDisponibili,
                      onTeamSelected: (selected) {
                        setState(() {
                          awayTeam = selected;
                        });
                      },
                    ),
                    const SizedBox(height: 12),

                    // Campo Match ID
                    TextField(
                      decoration: InputDecoration(
                        labelText: "Match ID (opzionale)",
                        prefixIcon: const Icon(Icons.numbers),
                        border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      onChanged: (val) {
                        matchId = val;
                      },
                    ),
                    const SizedBox(height: 16),

                    // Bottone Analizza
                    ElevatedButton.icon(
                      onPressed: _eseguiAnalisi,
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size.fromHeight(50),
                        backgroundColor: Colors.indigo,
                        foregroundColor: Colors.white,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      icon: const Icon(Icons.analytics),
                      label: const Text(
                        "ANALIZZA PARTITA",
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 20),

            // ==========================================
            // 📊 RISULTATI ANALISI (CON ANALYSIS CARD)
            // ==========================================
            FutureBuilder<Map<String, dynamic>>(
              future: _dashboardFuture,
              builder: (context, snapshot) {
                if (snapshot.connectionState == ConnectionState.waiting) {
                  return const Padding(
                    padding: EdgeInsets.symmetric(vertical: 40.0),
                    child: Center(child: CircularProgressIndicator()),
                  );
                } else if (snapshot.hasError) {
                  return Padding(
                    padding: const EdgeInsets.symmetric(vertical: 20.0),
                    child: Center(
                      child: Text(
                        "Errore: ${snapshot.error}",
                        style: const TextStyle(color: Colors.red, fontWeight: FontWeight.bold),
                      ),
                    ),
                  );
                } else if (!snapshot.hasData) {
                  return const SizedBox.shrink();
                }

                final data = snapshot.data!;
                return Column(
                  children: [
                    // 1. Modulo Poisson (Attivo)
                    AnalysisCard(
                      title: "Statistiche Poisson ($homeTeam vs $awayTeam)",
                      icon: Icons.functions,
                      themeColor: Colors.indigo,
                      badgeText: "MATH",
                      data: data['stats'],
                      initiallyExpanded: true,
                    ),

                    // 2. Modulo Esperti (Attivo)
                    AnalysisCard(
                      title: "Consigli Esperti",
                      icon: Icons.psychology,
                      themeColor: Colors.orange[800]!,
                      badgeText: "DB",
                      data: data['experts'],
                      initiallyExpanded: true,
                    ),

                    // 3. Modulo Flussi Monetari (Pronto per la Fase 3)
                    AnalysisCard(
                      title: "Flussi Monetari",
                      icon: Icons.attach_money,
                      themeColor: Colors.green[700]!,
                      badgeText: "SOON",
                      data: const {},
                      initiallyExpanded: false,
                    ),

                    // 4. Modulo Whale Alert (Pronto per la Fase 3)
                    AnalysisCard(
                      title: "Whale Alert",
                      icon: Icons.warning_amber_round,
                      themeColor: Colors.redAccent,
                      badgeText: "SOON",
                      data: const {},
                      initiallyExpanded: false,
                    ),
                  ],
                );
              },
            ),
          ],
        ),
      ),
    );
  }
}