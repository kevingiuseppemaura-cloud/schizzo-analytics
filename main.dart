import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';
import 'widgets/team_search_input.dart';
import 'widgets/analysis_card.dart';

void main() => runApp(const SchizzoApp());

class SchizzoApp extends StatelessWidget {
  const SchizzoApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Schizzo Analytics',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF1E3A8A), 
          primary: const Color(0xFF1E3A8A),
          secondary: const Color(0xFFFF6B00), 
        ),
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
  String homeTeam = "";
  String awayTeam = "";

  Future<Map<String, dynamic>>? _dashboardFuture;
  bool _haAnalizzato = false;

  final List<String> squadreDisponibili = [
    'Atalanta', 'Bologna', 'Cagliari', 'Como', 'Cremonese', 'Empoli', 'Fiorentina',
    'Frosinone', 'Genoa', 'Inter', 'Juventus', 'Lazio', 'Lecce', 'Mantova',
    'Milan', 'Modena', 'Monza', 'Napoli', 'Palermo', 'Parma', 'Pisa', 'Roma',
    'Salernitana', 'Sampdoria', 'Sassuolo', 'Sudtirol', 'Torino', 'Udinese', 'Venezia', 'Verona'
  ];

  void _eseguiAnalisi() {
    if (homeTeam.isEmpty || awayTeam.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Seleziona sia la squadra di casa che di trasferta!"),
          backgroundColor: Colors.redAccent,
        ),
      );
      return;
    }

    FocusScope.of(context).unfocus();

    setState(() {
      _haAnalizzato = true;
      _dashboardFuture = fetchDashboardData();
    });
  }

  Future<Map<String, dynamic>> fetchDashboardData() async {
    const String baseUrl = 'https://schizzo-analytics.onrender.com';
    final String internalMatchId = "${homeTeam.toLowerCase()}_${awayTeam.toLowerCase()}";
    const int timeoutSeconds = 60;

    try {
      http.Response statsResponse = await http.post(
        Uri.parse('$baseUrl/analizza'),
        headers: {"Content-Type": "application/json"},
        body: json.encode({
          "match_id": internalMatchId,
          "squadra_casa": homeTeam,
          "squadra_ospite": awayTeam,
        }),
      ).timeout(const Duration(seconds: timeoutSeconds));

      if (statsResponse.statusCode != 200) {
        statsResponse = await http.post(
          Uri.parse('$baseUrl/predict'),
          headers: {"Content-Type": "application/json"},
          body: json.encode({
            "match_id": internalMatchId,
            "home": homeTeam,
            "away": awayTeam,
          }),
        ).timeout(const Duration(seconds: timeoutSeconds));
      }

      if (statsResponse.statusCode != 200) {
        throw Exception('Errore nel recupero dati statistiche (Codice: ${statsResponse.statusCode})');
      }

      final expertsResponse = await http.get(
        Uri.parse('$baseUrl/esperti/$internalMatchId'),
      ).timeout(const Duration(seconds: timeoutSeconds));

      final statsDataDecoded = json.decode(statsResponse.body);
      
      if (statsDataDecoded is! Map<String, dynamic>) {
        throw Exception('Formato dati statistiche non valido ricevuto dal server.');
      }
      final statsData = statsDataDecoded;

      Map<String, dynamic> stats = {};
      if (statsData.containsKey('previsioni_poisson')) {
        stats = Map<String, dynamic>.from(statsData['previsioni_poisson']);
      } else if (statsData.containsKey('risultato')) {
        stats = Map<String, dynamic>.from(statsData['risultato']);
      } else {
        stats = statsData;
      }

      Map<String, dynamic> infoContext = {};
      if (statsData.containsKey('info_match')) {
        infoContext = Map<String, dynamic>.from(statsData['info_match']);
      } else if (statsData.containsKey('contesto')) {
        infoContext = Map<String, dynamic>.from(statsData['contesto']);
      } else {
        infoContext = {
          "Stadio Casa": "In attesa di lettura DB stadi",
          "Terreno & Copertura": "Naturale/Sintetico - Coperto/Scoperto (Da DB)",
          "Allenatore Casa": "Dato da DB Allenatori",
          "Allenatore Ospite": "Dato da DB Allenatori",
          "Arbitro Designato": "In attesa di designazione",
          "Severità Arbitro": "Da 1 a 10 (Da DB Arbitri)",
          "Meteo Live": "In attesa dati",
        };
      }

      Map<String, dynamic>? whaleData;
      if (statsData.containsKey('whale_alert')) {
        whaleData = Map<String, dynamic>.from(statsData['whale_alert']);
      }

      Map<String, dynamic> experts = {};
      if (expertsResponse.statusCode == 200) {
        final expertsData = json.decode(expertsResponse.body);
        if (expertsData is Map<String, dynamic>) {
          if (expertsData.containsKey('modulo_esperti')) {
            experts = Map<String, dynamic>.from(expertsData['modulo_esperti']);
          } else if (expertsData.containsKey('esperti')) {
            experts = Map<String, dynamic>.from(expertsData['esperti']);
          }
        }
      }

      return {
        "stats": stats,
        "experts": experts,
        "info_match": infoContext,
        "whale_alert": whaleData,
      };

    } on Exception catch (e) {
      throw Exception('Problema di connessione: $e');
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF4F6F9),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1E3A8A), 
        foregroundColor: Colors.white,
        title: const Row(
          children: [
            Icon(Icons.bolt, color: Color(0xFFFF6B00)), 
            SizedBox(width: 8),
            Text(
              "Schizzo Analytics",
              style: TextStyle(fontWeight: FontWeight.bold),
            ),
          ],
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Card(
              elevation: 2,
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
              child: Padding(
                padding: const EdgeInsets.all(16.0),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      "Seleziona Partita",
                      style: TextStyle(
                        fontSize: 18, 
                        fontWeight: FontWeight.bold,
                        color: Color(0xFF1E3A8A),
                      ),
                    ),
                    const SizedBox(height: 16),
                    
                    TeamSearchInput(
                      label: "Squadra Casa",
                      availableTeams: squadreDisponibili,
                      onTeamSelected: (selected) {
                        setState(() { homeTeam = selected; });
                      },
                    ),
                    const SizedBox(height: 12),

                    TeamSearchInput(
                      label: "Squadra Trasferta",
                      availableTeams: squadreDisponibili,
                      onTeamSelected: (selected) {
                        setState(() { awayTeam = selected; });
                      },
                    ),
                    const SizedBox(height: 16),

                    ElevatedButton.icon(
                      onPressed: _eseguiAnalisi,
                      style: ElevatedButton.styleFrom(
                        minimumSize: const Size.fromHeight(50),
                        backgroundColor: const Color(0xFF1E3A8A), 
                        foregroundColor: Colors.white,
                        elevation: 3,
                        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                      ),
                      icon: const Icon(Icons.bolt, color: Color(0xFFFF6B00)),
                      label: const Text(
                        "ANALIZZA PARTITA",
                        style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                      ),
                    ),
                  ],
                ),
              ),
            ),

            const SizedBox(height: 16),

            !_haAnalizzato
                ? const Card(
                    elevation: 1,
                    child: Padding(
                      padding: EdgeInsets.all(24.0),
                      child: Column(
                        children: [
                          Icon(Icons.analytics_outlined, size: 48, color: Colors.grey),
                          SizedBox(height: 12),
                          Text(
                            "Seleziona le squadre e premi 'ANALIZZA PARTITA' per avviare il calcolo.",
                            textAlign: TextAlign.center,
                            style: TextStyle(color: Colors.grey, fontSize: 14),
                          ),
                        ],
                      ),
                    ),
                  )
                : FutureBuilder<Map<String, dynamic>>(
                    future: _dashboardFuture,
                    builder: (context, snapshot) {
                      if (snapshot.connectionState == ConnectionState.waiting) {
                        return const Padding(
                          padding: EdgeInsets.symmetric(vertical: 40.0),
                          child: Center(
                            child: CircularProgressIndicator(color: Color(0xFFFF6B00)),
                          ),
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
                      final whaleData = data['whale_alert'];
                      final infoData = data['info_match'] as Map<String, dynamic>? ?? {};

                      return Column(
                        children: [
                          if (whaleData != null && whaleData['attivo'] == true)
                            _buildWhaleAlertBanner(
                              volumeEffettivo: whaleData['volume_effettivo'] ?? "N/D",
                              volumeNormale: whaleData['volume_normale'] ?? "N/D",
                              sbilanciamento: whaleData['sbilanciamento'] ?? "N/D",
                            ),

                          AnalysisCard(
                            title: "Info & Contesto Match",
                            icon: Icons.stadium,
                            themeColor: Colors.purple[700]!,
                            badgeText: "INFO",
                            data: infoData,
                            initiallyExpanded: false,
                          ),

                          AnalysisCard(
                            title: "Statistiche Poisson ($homeTeam vs $awayTeam)",
                            icon: Icons.functions,
                            themeColor: const Color(0xFF1E3A8A),
                            badgeText: "MATH",
                            data: data['stats'] ?? {},
                            initiallyExpanded: true,
                          ),

                          AnalysisCard(
                            title: "Consigli Esperti",
                            icon: Icons.psychology,
                            themeColor: const Color(0xFFFF6B00),
                            badgeText: "DB",
                            data: data['experts'] ?? {},
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

  Widget _buildWhaleAlertBanner({
    required String volumeEffettivo,
    required String volumeNormale,
    required String sbilanciamento,
  }) {
    return Container(
      margin: const EdgeInsets.only(bottom: 16.0),
      padding: const EdgeInsets.all(16.0),
      decoration: BoxDecoration(
        color: Colors.red[900],
        borderRadius: BorderRadius.circular(12),
        boxShadow: [
          BoxShadow(
            color: Colors.red.withOpacity(0.4),
            blurRadius: 10,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              Icon(Icons.warning_amber_rounded, color: Colors.amber, size: 28),
              SizedBox(width: 8),
              Text(
                "WHALE ALERT",
                style: TextStyle(
                  color: Colors.white,
                  fontSize: 16,
                  fontWeight: FontWeight.bold,
                  letterSpacing: 1.1,
                ),
              ),
            ],
          ),
          const Divider(color: Colors.white24, height: 20),
          Text(
            "Flusso: $volumeEffettivo (Media: $volumeNormale)",
            style: const TextStyle(color: Colors.white, fontSize: 13, fontWeight: FontWeight.w500),
          ),
          const SizedBox(height: 4),
          Text(
            "Polarizzazione: $sbilanciamento",
            style: const TextStyle(color: Colors.amber, fontSize: 13, fontWeight: FontWeight.bold),
          ),
        ],
      ),
    );
  }
}