import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';
import 'dart:async';

void main() {
  runApp(const MasterCalculatorApp());
}

class MasterCalculatorApp extends StatelessWidget {
  const MasterCalculatorApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Football Analysis Pro',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF121212),
        primaryColor: const Color(0xFF0055FF),
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF0055FF), 
          secondary: Color(0xFFFF6600),
          surface: Color(0xFF1E1E1E),
        ),
        fontFamily: 'Roboto', 
      ),
      home: const AnalisiMatchScreen(),
    );
  }
}

class MethodColorReplacement {
  const MethodColorReplacement();
  Color call() => const Color(0xFF121212);
}

class AnalisiMatchScreen extends StatefulWidget {
  const AnalisiMatchScreen({super.key});

  @override
  State<AnalisiMatchScreen> createState() => _AnalisiMatchScreenState();
}

class _AnalisiMatchScreenState extends State<AnalisiMatchScreen> {
  DateTime? selectedDate;
  final TextEditingController homeTeamController = TextEditingController();
  final TextEditingController awayTeamController = TextEditingController();
  
  final FocusNode homeFocusNode = FocusNode();
  final FocusNode awayFocusNode = FocusNode();
  
  bool isLoading = false;
  String panelEspertiTesto = 'I pronostici non sono ancora caricati. Clicca su "Avvia Master Calculator" per avviare il motore di Poisson.';
  Map<String, dynamic> intelligenceData = {
    'mister': 'In attesa di calcolo...',
    'arbitro': 'Indice non calcolato...',
    'infortunati': 'API in attesa...',
    'stadium': 'Lat/Lon non inserite...',
    'flussi': 'Analisi quote sospesa...'
  };
  Map<String, dynamic> poissonResults = {};

  final List<String> squadreSupportate = [
    'Juventus', 'Inter', 'Milan', 'Napoli', 'Roma', 'Lazio', 'Frosinone',
    'Palermo', 'Bari', 'Sampdoria', 'Parma',
    'Real Madrid', 'Barcellona', 'Atletico Madrid', 
    'Manchester City', 'Arsenal', 'Liverpool', 'Manchester United',
    'Bayern Monaco', 'Borussia Dortmund', 'Bayer Leverkusen',
    'Paris Saint-Germain', 'Olympique Marsiglia', 'Lione'
  ];

  @override
  void dispose() {
    homeTeamController.dispose();
    awayTeamController.dispose();
    homeFocusNode.dispose();
    awayFocusNode.dispose();
    super.dispose();
  }

  Future<void> _selectDate(BuildContext context) async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now(),
      firstDate: DateTime.now().subtract(const Duration(days: 30)),
      lastDate: DateTime.now().add(const Duration(days: 60)),
      builder: (context, child) {
        return Theme(
          data: Theme.of(context).copyWith(
            colorScheme: const ColorScheme.dark(
              primary: Color(0xFF0055FF),
              onPrimary: Colors.white,
              surface: Color(0xFF1E1E1E),
              onSurface: Colors.white,
            ),
          ),
          child: child!,
        );
      },
    );
    if (picked != null && picked != selectedDate) {
      setState(() {
        selectedDate = picked;
      });
    }
  }

  Future<void> _avviaMasterCalculator() async {
    if (homeTeamController.text.isEmpty || awayTeamController.text.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Inserisci entrambe le squadre per avviare il calcolo.'),
          backgroundColor: Color(0xFFFF6600),
        ),
      );
      return;
    }

    setState(() {
      isLoading = true;
    });

    try {
      final response = await http.post(
        Uri.parse('https://schizzo-analytics.onrender.com/api/calcola-match'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'home': homeTeamController.text,
          'away': awayTeamController.text,
          'date': selectedDate?.toIso8601String(),
        }),
      ).timeout(const Duration(seconds: 15));

      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        setState(() {
          panelEspertiTesto = data['panel_esperti'] ?? 'Nessun dato dal motore.';
          intelligenceData = data['intelligence'] ?? intelligenceData;
          poissonResults = data['poisson'] ?? {};
        });

        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Master Calculator & Poisson completati con successo!'),
            backgroundColor: Color(0xFF0055FF),
          ),
        );
      } else {
        throw Exception('Errore server: ${response.statusCode}');
      }
    } catch (e) {
      setState(() {
        panelEspertiTesto = 'Impossibile connettersi al server su Render: $e';
      });
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Errore di connessione: $e'),
          backgroundColor: Colors.red,
        ),
      );
    } finally {
      setState(() {
        isLoading = false;
      });
    }
  }

  Widget _buildAutocompleteField(String label, TextEditingController controller, FocusNode focusNode) {
    return Autocomplete<String>(
      textEditingController: controller,
      focusNode: focusNode,
      optionsBuilder: (TextEditingValue textEditingValue) {
        if (textEditingValue.text.isEmpty) {
          return const Iterable<String>.empty();
        }
        return squadreSupportate.where((String option) {
          return option.toLowerCase().contains(textEditingValue.text.toLowerCase());
        });
      },
      onSelected: (String selection) {
        controller.text = selection;
      },
      fieldViewBuilder: (context, fieldTextEditingController, fieldFocusNode, onFieldSubmitted) {
        return TextField(
          controller: fieldTextEditingController,
          focusNode: fieldFocusNode,
          style: const TextStyle(color: Colors.white),
          decoration: InputDecoration(
            labelText: label,
            labelStyle: const TextStyle(color: Colors.grey),
            filled: true,
            fillColor: const Color(0xFF1E1E1E),
            enabledBorder: OutlineInputBorder(
              borderSide: const BorderSide(color: Colors.transparent),
              borderRadius: BorderRadius.circular(8),
            ),
            focusedBorder: OutlineInputBorder(
              borderSide: const BorderSide(color: Color(0xFF0055FF), width: 2),
              borderRadius: BorderRadius.circular(8),
            ),
            prefixIcon: const Icon(Icons.shield, color: Color(0xFFFF6600)),
          ),
        );
      },
      optionsViewBuilder: (context, onSelected, options) {
        return Align(
          alignment: Alignment.topLeft,
          child: Material(
            color: const Color(0xFF1E1E1E),
            elevation: 4.0,
            borderRadius: BorderRadius.circular(8),
            child: SizedBox(
              height: 200.0,
              width: MediaQuery.of(context).size.width - 32,
              child: ListView.builder(
                padding: EdgeInsets.zero,
                itemCount: options.length,
                itemBuilder: (BuildContext context, int index) {
                  final String option = options.elementAt(index);
                  return ListTile(
                    title: Text(option, style: const TextStyle(color: Colors.white)),
                    onTap: () => onSelected(option),
                  );
                },
              ),
            ),
          ),
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        backgroundColor: const Color(0xFF121212),
        elevation: 0,
        title: const Text(
          'MATCH ANALYSIS',
          style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 1.5),
        ),
        centerTitle: true,
        bottom: PreferredSize(
          preferredSize: const Size.fromHeight(2.0),
          child: Container(
            color: const Color(0xFF0055FF),
            height: 2.0,
          ),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'PARAMETRI PARTITA',
              style: TextStyle(fontSize: 14, fontWeight: FontWeight.bold, color: Color(0xFF0055FF), letterSpacing: 1.2),
            ),
            const SizedBox(height: 16),
            
            InkWell(
              onTap: () => _selectDate(context),
              child: Container(
                padding: const EdgeInsets.symmetric(vertical: 18, horizontal: 16),
                decoration: BoxDecoration(
                  color: const Color(0xFF1E1E1E),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Text(
                      selectedDate == null 
                          ? 'Seleziona Data Match' 
                          : '${selectedDate!.day.toString().padLeft(2, '0')}/${selectedDate!.month.toString().padLeft(2, '0')}/${selectedDate!.year}',
                      style: const TextStyle(color: Colors.white, fontSize: 16),
                    ),
                    const Icon(Icons.calendar_today, color: Color(0xFFFF6600)),
                  ],
                ),
              ),
            ),
            const SizedBox(height: 16),

            _buildAutocompleteField('Squadra di Casa', homeTeamController, homeFocusNode),
            const SizedBox(height: 16),
            _buildAutocompleteField('Squadra in Trasferta', awayTeamController, awayFocusNode),
            const SizedBox(height: 32),

            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                collapsedBackgroundColor: const Color(0xFF1E1E1E),
                backgroundColor: const Color(0xFF1E1E1E),
                iconColor: const Color(0xFF0055FF),
                collapsedIconColor: Colors.white54,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                collapsedShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                title: const Text(
                  'Intelligence di Campo',
                  style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 16),
                ),
                leading: const Icon(Icons.radar, color: Color(0xFF0055FF)),
                children: [
                  Padding(
                    padding: const EdgeInsets.all(16.0),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _InfoRow(icon: Icons.psychology, title: 'Mister e Tattica', value: intelligenceData['mister']!),
                        _InfoRow(icon: Icons.sports, title: 'Direttore di Gara', value: intelligenceData['arbitro']!),
                        _InfoRow(icon: Icons.medical_services, title: 'Infortunati Critici', value: intelligenceData['infortunati']!),
                        _InfoRow(icon: Icons.stadium, title: 'Stadio e Meteo', value: intelligenceData['stadium']!),
                        _InfoRow(icon: Icons.trending_up, title: 'Flussi di Cassa', value: intelligenceData['flussi']!),
                      ],
                    ),
                  )
                ],
              ),
            ),
            const SizedBox(height: 16),

            Theme(
              data: Theme.of(context).copyWith(dividerColor: Colors.transparent),
              child: ExpansionTile(
                collapsedBackgroundColor: const Color(0xFF1E1E1E),
                backgroundColor: const Color(0xFF1E1E1E),
                iconColor: const Color(0xFFFF6600),
                collapsedIconColor: Colors.white54,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                collapsedShape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                title: const Text(
                  'Panel Esperti & Poisson',
                  style: TextStyle(fontWeight: FontWeight.bold, color: Colors.white, fontSize: 16),
                ),
                leading: const Icon(Icons.group, color: Color(0xFFFF6600)),
                children: [
                  Container(
                    padding: const EdgeInsets.all(16.0),
                    width: double.infinity,
                    decoration: const BoxDecoration(
                      border: Border(left: BorderSide(color: Color(0xFFFF6600), width: 4)),
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Risultati Modello Matematico',
                          style: TextStyle(color: Color(0xFF0055FF), fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        const SizedBox(height: 8),
                        Text(
                          panelEspertiTesto,
                          style: const TextStyle(color: Colors.white70, height: 1.5),
                        ),
                        if (poissonResults.isNotEmpty) ...[
                          const SizedBox(height: 16),
                          const Text(
                            'Linee Under / Over Complete:',
                            style: TextStyle(color: Color(0xFFFF6600), fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          const SizedBox(height: 6),
                          ...((poissonResults['under_over'] as Map<String, dynamic>? ?? {}).entries.map((e) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 2.0),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(e.key, style: const TextStyle(color: Colors.white70)),
                                Text('${e.value}%', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ))),
                          const SizedBox(height: 16),
                          const Text(
                            'Fasce Multigol:',
                            style: TextStyle(color: Color(0xFFFF6600), fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          const SizedBox(height: 6),
                          ...((poissonResults['multigol'] as Map<String, dynamic>? ?? {}).entries.map((e) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 2.0),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text(e.key, style: const TextStyle(color: Colors.white70)),
                                Text('${e.value}%', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ))),
                          const SizedBox(height: 16),
                          const Text(
                            'Top 3 Risultati Esatti:',
                            style: TextStyle(color: Color(0xFFFF6600), fontWeight: FontWeight.bold, fontSize: 14),
                          ),
                          const SizedBox(height: 6),
                          ...((poissonResults['top_3_risultati_esatti'] as List<dynamic>? ?? []).map((res) => Padding(
                            padding: const EdgeInsets.symmetric(vertical: 2.0),
                            child: Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                Text('Risultato: ${res['risultato']}', style: const TextStyle(color: Colors.white70)),
                                Text('${res['probabilita']}%', style: const TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
                              ],
                            ),
                          ))),
                        ],
                      ],
                    ),
                  )
                ],
              ),
            ),
            const SizedBox(height: 40),

            ElevatedButton(
              onPressed: isLoading ? null : _avviaMasterCalculator,
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF0055FF),
                padding: const EdgeInsets.symmetric(vertical: 18),
                shape: RoundedRectangleBorder(
                  borderRadius: BorderRadius.circular(8),
                ),
                elevation: 8,
                shadowColor: const Color(0xFF0055FF).withOpacity(0.5),
              ),
              child: isLoading
                  ? const SizedBox(
                      height: 20,
                      width: 20,
                      child: CircularProgressIndicator(strokeWidth: 2, color: Colors.white),
                    )
                  : const Row(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        Icon(Icons.bolt, color: Colors.white),
                        SizedBox(width: 8),
                        Text(
                          'AVVIA MASTER CALCULATOR',
                          style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold, color: Colors.white, letterSpacing: 1.0),
                        ),
                      ],
                    ),
            ),
            
            const SizedBox(height: 50),
            
            Center(
              child: Column(
                children: [
                  const Icon(Icons.sports_soccer, color: Color(0xFFFF6600), size: 28),
                  const SizedBox(height: 12),
                  const Text(
                    'SIGNATURE EDITION',
                    style: TextStyle(
                      color: Color(0xFF0055FF),
                      letterSpacing: 3.0,
                      fontSize: 12,
                      fontWeight: FontWeight.w900,
                    ),
                  ),
                  const SizedBox(height: 6),
                  Text(
                    'Progettato e sviluppato da Maura Kevin Giuseppe',
                    style: TextStyle(
                      color: Colors.grey.shade600,
                      fontStyle: FontStyle.italic,
                      fontSize: 12,
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}

class _InfoRow extends StatelessWidget {
  final IconData icon;
  final String title;
  final String value;

  const _InfoRow({
    required this.icon,
    required this.title,
    required this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16.0),
      child: Row(
        children: [
          Icon(icon, color: Colors.white54, size: 20),
          const SizedBox(width: 12),
          Expanded(
            flex: 2,
            child: Text(
              title,
              style: const TextStyle(color: Colors.white, fontWeight: FontWeight.w600),
            ),
          ),
          Expanded(
            flex: 3,
            child: Text(
              value,
              style: const TextStyle(color: Colors.grey),
              textAlign: TextAlign.right,
            ),
          ),
        ],
      ),
    );
  }
}