import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:url_launcher/url_launcher.dart';

class TradingAgentsAdvancedPage extends StatefulWidget {
  const TradingAgentsAdvancedPage({super.key});
  @override
  State<TradingAgentsAdvancedPage> createState() => _TradingAgentsAdvancedPageState();
}

class _TradingAgentsAdvancedPageState extends State<TradingAgentsAdvancedPage> {
  final url = TextEditingController();
  final cash = TextEditingController();
  final currency = TextEditingController(text: 'INR');
  final positions = TextEditingController();
  final ticker = TextEditingController(text: 'RELIANCE.NS');
  final tickers = TextEditingController(text: 'RELIANCE.NS,NVDA,AAPL');
  final analysisDate = TextEditingController(text: DateTime.now().toIso8601String().substring(0, 10));
  final start = TextEditingController(text: '2026-01-01');
  final end = TextEditingController(text: DateTime.now().toIso8601String().substring(0, 10));
  final runId = TextEditingController();
  final quickModel = TextEditingController();
  final deepModel = TextEditingController();
  final quickProvider = TextEditingController();
  final deepProvider = TextEditingController();
  final outputLanguage = TextEditingController(text: 'English');
  final debateRounds = TextEditingController(text: '1');
  final riskRounds = TextEditingController(text: '1');
  final Set<String> analysts = {'market', 'news', 'fundamentals', 'social'};
  bool usePortfolio = true, checkpoint = true, html = true, busy = false;
  Map<String, dynamic> config = {};
  List<dynamic> reports = [];
  String memoryText = '';
  String resultText = '', error = '', status = 'Enter a public HTTPS TradingAgents backend URL.';

  Uri endpoint(String path) {
    final raw = url.text.trim().replaceAll(RegExp(r'/+$'), '');
    final base = Uri.tryParse(raw);
    if (base == null || base.scheme != 'https' || base.host.isEmpty || base.userInfo.isNotEmpty ||
        base.hasQuery || base.hasFragment || base.host == 'localhost' || base.host == '127.0.0.1') {
      throw const FormatException('Enter a public HTTPS backend URL.');
    }
    return base.replace(path: base.path.replaceAll(RegExp(r'/+$'), '') + '/v1' + path);
  }

  Map<String, dynamic> decode(http.Response response) {
    dynamic value;
    try { value = jsonDecode(response.body); } catch (_) {
      throw Exception('Backend returned invalid JSON (HTTP ' + response.statusCode.toString() + ').');
    }
    if (response.statusCode >= 400) {
      throw Exception(value is Map ? (value['detail'] ?? 'HTTP ' + response.statusCode.toString()).toString() : 'HTTP error');
    }
    if (value is! Map) throw Exception('Unexpected backend response format.');
    return Map<String, dynamic>.from(value);
  }

  Future<Map<String, dynamic>> get(String path) async =>
      decode(await http.get(endpoint(path), headers: {'accept': 'application/json'}).timeout(const Duration(seconds: 20)));

  Future<Map<String, dynamic>> post(String path, Map<String, dynamic> body) async =>
      decode(await http.post(endpoint(path), headers: {'accept': 'application/json', 'content-type': 'application/json'},
        body: jsonEncode(body)).timeout(const Duration(minutes: 60)));

  Future<void> action(Future<void> Function() callback) async {
    if (busy) return;
    setState(() { busy = true; error = ''; status = 'Working…'; });
    try { await callback(); if (mounted) setState(() => status = 'Request completed'); }
    catch (e) { if (mounted) setState(() { error = e.toString().replaceFirst('Exception: ', ''); status = 'Action failed'; }); }
    finally { if (mounted) setState(() => busy = false); }
  }

  Future<void> refreshAll() => action(() async {
    final c = await get('/config');
    final p = await get('/portfolio');
    final r = await get('/reports');
    final m = await get('/memory');
    if (!mounted) return;
    setState(() {
      config = c;
      final settings = c['settings'] is Map ? Map<String, dynamic>.from(c['settings'] as Map) : <String, dynamic>{};
      quickModel.text = (settings['TRADINGAGENTS_QUICK_THINK_LLM'] ?? '').toString();
      deepModel.text = (settings['TRADINGAGENTS_DEEP_THINK_LLM'] ?? '').toString();
      quickProvider.text = (settings['TRADINGAGENTS_QUICK_THINK_PROVIDER'] ?? '').toString();
      deepProvider.text = (settings['TRADINGAGENTS_DEEP_THINK_PROVIDER'] ?? '').toString();
      outputLanguage.text = (settings['TRADINGAGENTS_OUTPUT_LANGUAGE'] ?? 'English').toString();
      debateRounds.text = (settings['TRADINGAGENTS_MAX_DEBATE_ROUNDS'] ?? '1').toString();
      riskRounds.text = (settings['TRADINGAGENTS_MAX_RISK_ROUNDS'] ?? '1').toString();
      reports = r['reports'] is List ? List<dynamic>.from(r['reports'] as List) : [];
      memoryText = m['available'] == true ? (m['content'] ?? '').toString() : '';
      cash.text = p['cash']?.toString() ?? '';
      currency.text = p['currency']?.toString() ?? 'INR';
      final rows = p['positions'] is List ? List<dynamic>.from(p['positions'] as List) : [];
      positions.text = rows.map((row) => (row['ticker'] ?? '') .toString() + ':' +
        (row['quantity'] ?? '') .toString() + ':' + (row['average_price'] ?? '') .toString()).join('\n');
      status = c['framework_cli_available'] == true ? 'Backend and TradingAgents CLI detected' : 'Backend reachable; CLI unavailable';
    });
  });

  Future<void> savePortfolio() => action(() async {
    final rows = <Map<String, dynamic>>[];
    for (final line in positions.text.split('\n')) {
      if (line.trim().isEmpty) continue;
      final parts = line.trim().split(':');
      if (parts.length < 2 || parts.length > 3 || parts.first.trim().isEmpty) {
        throw const FormatException('Use TICKER:QUANTITY:AVERAGE_PRICE, one holding per line.');
      }
      final quantity = double.tryParse(parts[1].trim());
      final average = parts.length == 3 && parts[2].trim().isNotEmpty ? double.tryParse(parts[2].trim()) : null;
      if (quantity == null || (parts.length == 3 && parts[2].trim().isNotEmpty && average == null)) {
        throw const FormatException('Quantity and average price must be numeric.');
      }
      rows.add({'ticker': parts[0].trim().toUpperCase(), 'quantity': quantity, 'average_price': average});
    }
    final cashValue = cash.text.trim().isEmpty ? null : double.tryParse(cash.text.trim());
    if (cash.text.trim().isNotEmpty && cashValue == null) throw const FormatException('Cash must be numeric.');
    final response = await http.put(endpoint('/portfolio'), headers: {'content-type': 'application/json', 'accept': 'application/json'},
      body: jsonEncode({'cash': cashValue, 'currency': currency.text.trim().isEmpty ? 'INR' : currency.text.trim(), 'positions': rows}))
      .timeout(const Duration(seconds: 20));
    final saved = decode(response);
    if (mounted) setState(() => resultText = 'Portfolio saved: ' + (saved['status'] ?? '').toString());
  });

  Future<void> runResearch() => action(() async {
    if (ticker.text.trim().isEmpty) throw const FormatException('Enter a ticker.');
    if (analysts.isEmpty) throw const FormatException('Select at least one analyst.');
    final r = await post('/advanced/run', {
      'ticker': ticker.text.trim().toUpperCase(), 'date': analysisDate.text.trim(),
      'analysts': ['market','news','fundamentals','social'].where(analysts.contains).toList(),
      'use_portfolio': usePortfolio, 'checkpoint_enabled': checkpoint, 'clear_checkpoints': false, 'html_report': html,
      'quick_model': quickModel.text.trim().isEmpty ? null : quickModel.text.trim(),
      'deep_model': deepModel.text.trim().isEmpty ? null : deepModel.text.trim(),
      'quick_provider': quickProvider.text.trim().isEmpty ? null : quickProvider.text.trim(),
      'deep_provider': deepProvider.text.trim().isEmpty ? null : deepProvider.text.trim(),
      'output_language': outputLanguage.text.trim().isEmpty ? null : outputLanguage.text.trim(),
      'debate_rounds': int.tryParse(debateRounds.text.trim()),
      'risk_rounds': int.tryParse(riskRounds.text.trim()),
    });
    if (mounted) setState(() => resultText = (r['summary'] ?? r['status']).toString() + '\n\n' + (r['report'] ?? '').toString());
  });

  Future<void> clearCheckpoints() async {
    final yes = await showDialog<bool>(context: context, builder: (context) => AlertDialog(
      title: const Text('Clear saved checkpoints?'),
      content: const Text('This removes resumable checkpoints only; it does not delete reports or portfolio data.'),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
        FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Clear')),
      ]));
    if (yes != true || !mounted) return;
    await action(() async {
      final r = await post('/checkpoints/clear', {});
      if (mounted) setState(() => resultText = (r['status'] ?? '').toString() + ': ' + (r['message'] ?? '').toString());
    });
  }

  Future<void> runGrid() => action(() async {
    final symbols = tickers.text.split(',').map((s) => s.trim().toUpperCase()).where((s) => s.isNotEmpty).toList();
    final a = DateTime.tryParse(start.text.trim()), b = DateTime.tryParse(end.text.trim());
    if (symbols.isEmpty || a == null || b == null || a.isAfter(b)) {
      throw const FormatException('Enter tickers and valid dates; start must be on or before end.');
    }
    final r = await post('/backtest-grid', {
      'tickers': symbols, 'start_date': start.text.trim(), 'end_date': end.text.trim(),
      'every_n_days': 7, 'analysts': ['market','news','fundamentals','social'].where(analysts.contains).toList(),
      'run_id': runId.text.trim().isEmpty ? null : runId.text.trim(),
    });
    if (mounted) setState(() => resultText = (r['summary'] ?? r['status']).toString() + '\n\n' + (r['report'] ?? '').toString());
  });

  Future<void> openReport(Map<String, dynamic> report) async {
    final name = report['name']?.toString() ?? '';
    if (name.isEmpty) return;
    try {
      final ok = await launchUrl(endpoint('/reports/open/' + Uri.encodeComponent(name)), mode: LaunchMode.externalApplication);
      if (!ok && mounted) setState(() => error = 'Could not open report in browser.');
    } catch (e) { if (mounted) setState(() => error = e.toString()); }
  }

  Widget field(TextEditingController controller, String label, {int lines = 1, String? hint}) =>
    Padding(padding: const EdgeInsets.only(bottom: 8), child: TextField(controller: controller, maxLines: lines,
      decoration: InputDecoration(labelText: label, hintText: hint)));

  Widget section(String title, IconData icon, List<Widget> children) => Card(
    child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
      Row(children: [Icon(icon), const SizedBox(width: 8), Expanded(child: Text(title, style: const TextStyle(fontWeight: FontWeight.w900, fontSize: 16)))]),
      const SizedBox(height: 10), ...children,
    ])));

  @override
  void dispose() {
    url.dispose(); cash.dispose(); currency.dispose(); positions.dispose(); ticker.dispose(); tickers.dispose();
    analysisDate.dispose(); start.dispose(); end.dispose(); runId.dispose(); quickModel.dispose(); deepModel.dispose();
    quickProvider.dispose(); deepProvider.dispose(); outputLanguage.dispose(); debateRounds.dispose(); riskRounds.dispose(); super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final settings = config['settings'] is Map ? Map<String, dynamic>.from(config['settings'] as Map) : <String, dynamic>{};
    final gaps = config['configuration_gaps'] is List ? List<dynamic>.from(config['configuration_gaps'] as List) : <dynamic>[];
    final providers = config['configured_providers'] is List ? List<dynamic>.from(config['configured_providers'] as List) : <dynamic>[];
    return ListView(padding: const EdgeInsets.all(12), children: [
      const Text('TRADINGAGENTS ADVANCED WORKSPACE', style: TextStyle(fontSize: 20, fontWeight: FontWeight.w900)),
      const Text('Portfolio • checkpoint recovery • reports • grid backtests • model settings • historical integrity'),
      field(url, 'Backend public HTTPS URL', hint: 'https://your-service.up.railway.app'),
      Wrap(spacing: 8, children: [
        FilledButton.icon(onPressed: busy ? null : refreshAll, icon: const Icon(Icons.sync), label: const Text('Connect / refresh')),
        OutlinedButton.icon(onPressed: busy ? null : clearCheckpoints, icon: const Icon(Icons.delete_sweep), label: const Text('Clear checkpoints')),
      ]),
      ListTile(leading: Icon(busy ? Icons.sync : Icons.info_outline), title: Text(status),
        subtitle: Text('TradingAgents CLI: ' + (config['framework_cli_available'] == true ? 'available' : 'not verified'))),
      if (error.isNotEmpty) Card(child: Padding(padding: const EdgeInsets.all(10), child: Text(error, style: const TextStyle(color: Colors.orangeAccent)))),
      if (gaps.isNotEmpty) section('Backend setup gaps', Icons.warning_amber, [
        const Text('Set these environment variables on the backend. API keys must never be stored in the APK.'),
        Text(gaps.map((e) => '• ' + e.toString()).join('\n')),
      ]),
      section('2. Portfolio & Holdings', Icons.account_balance_wallet, [
        const Text('One holding per line: TICKER:QUANTITY:AVERAGE_PRICE. Quantity 0 explicitly represents a flat position.'),
        field(cash, 'Available cash (optional)'), field(currency, 'Currency label'),
        field(positions, 'Holdings', lines: 4, hint: 'RELIANCE.NS:10:1420.5\nAAPL:2:190'),
        FilledButton.icon(onPressed: busy ? null : savePortfolio, icon: const Icon(Icons.save), label: const Text('Save portfolio to backend')),
        CheckboxListTile(contentPadding: EdgeInsets.zero, value: usePortfolio, onChanged: busy ? null : (v) => setState(() => usePortfolio = v ?? false),
          title: const Text('Include saved portfolio in analysis')),
      ]),
      section('3. Checkpoint recovery & research', Icons.restart_alt, [
        field(ticker, 'Ticker'), field(analysisDate, 'Analysis date (YYYY-MM-DD)'),
        const Text('Analysts'),
        Wrap(spacing: 5, children: [
          for (final entry in const {'market':'Market / Technical','news':'News','fundamentals':'Fundamentals','social':'Social sentiment'}.entries)
            FilterChip(label: Text(entry.value), selected: analysts.contains(entry.key),
              onSelected: busy ? null : (v) => setState(() { if (v) { analysts.add(entry.key); } else { analysts.remove(entry.key); } })),
        ]),
        SwitchListTile(contentPadding: EdgeInsets.zero, value: checkpoint, onChanged: busy ? null : (v) => setState(() => checkpoint = v),
          title: const Text('Enable checkpoint resume')),
        SwitchListTile(contentPadding: EdgeInsets.zero, value: html, onChanged: busy ? null : (v) => setState(() => html = v),
          title: const Text('Save HTML report')),
        FilledButton.icon(onPressed: busy ? null : runResearch, icon: const Icon(Icons.play_arrow), label: const Text('Run research')),
      ]),
      section('4. Multi-ticker backtest grid', Icons.query_stats, [
        field(tickers, 'Comma-separated tickers'), field(start, 'Start date (YYYY-MM-DD)'), field(end, 'End date (YYYY-MM-DD)'),
        field(runId, 'Resume run ID (optional)'),
        FilledButton.icon(onPressed: busy ? null : runGrid, icon: const Icon(Icons.grid_view), label: const Text('Run backtest grid')),
        const Text('Only metrics/output returned by the installed framework are displayed; this UI does not invent returns or win rates.'),
      ]),
      section('5. Provider / model settings', Icons.tune, [
        Text('Detected providers: ' + (providers.isEmpty ? 'none detected' : providers.join(', '))),
        for (final key in settings.keys) ListTile(dense: true, contentPadding: EdgeInsets.zero, title: Text(key),
          subtitle: Text(settings[key]?.toString().isNotEmpty == true ? settings[key].toString() : 'Not configured')),
        const Text('These overrides apply only to the next research run. Provider credentials must already exist on the backend; secrets never return to the app.'),
        field(quickProvider, 'Quick-tier provider (optional)', hint: 'openai, anthropic, openrouter, nvidia, ollama'),
        field(quickModel, 'Quick-tier model (optional)', hint: 'Model ID configured for the selected provider'),
        field(deepProvider, 'Deep-tier provider (optional)', hint: 'openai, anthropic, openrouter, nvidia, ollama'),
        field(deepModel, 'Deep-tier model (optional)', hint: 'Model ID configured for the selected provider'),
        field(outputLanguage, 'Report language'),
        field(debateRounds, 'Debate rounds (1–10)'),
        field(riskRounds, 'Risk rounds (1–10)'),
        const Text('If an override fails, verify the model exists for that provider and its backend-only API key is configured.'),
      ]),
      section('6. HTML reports & memory', Icons.description, [
        Row(children: [const Expanded(child: Text('Saved reports', style: TextStyle(fontWeight: FontWeight.w800))),
          IconButton(onPressed: busy ? null : refreshAll, icon: const Icon(Icons.refresh))]),
        if (reports.isEmpty) const Text('No saved reports found. Check results directory and mount a persistent volume at /data.'),
        for (final item in reports) if (item is Map) ListTile(
          contentPadding: EdgeInsets.zero, leading: Icon(item['format'] == 'html' ? Icons.language : Icons.description),
          title: Text((item['name'] ?? 'Report').toString()),
          subtitle: Text((item['format'] ?? 'file').toString() + ' • ' + (item['size_bytes'] ?? '?').toString() + ' bytes • ' + (item['modified_at'] ?? '').toString()),
          trailing: IconButton(icon: const Icon(Icons.open_in_browser), onPressed: () => openReport(Map<String, dynamic>.from(item)))),
        const Text('Saved decision memory log'),
        if (memoryText.isEmpty) const Text('No memory log found at the configured backend path yet.'),
        if (memoryText.isNotEmpty) SelectableText(memoryText, style: const TextStyle(fontSize: 12)),
        const Text('Memory content is displayed only when the backend framework has written the configured log.'),
      ]),
      section('7. Point-in-time data integrity', Icons.verified_user_outlined, [
        const ListTile(contentPadding: EdgeInsets.zero, leading: Icon(Icons.info_outline), title: Text('Historical integrity: NOT VERIFIED'),
          subtitle: Text('Before trusting backtests, verify installed framework version, source publication timestamps and absence of future-data leakage.')),
        Text((config['point_in_time_policy'] ?? 'Connect to backend to read its policy.').toString()),
        Text('Persistent volume: ' + (config['persistent_volume_expected'] == true ? 'expected at /data' : 'not confirmed; configure a persistent volume')),
      ]),
      if (resultText.isNotEmpty) section('Latest result', Icons.receipt_long, [
        SelectableText(resultText, style: const TextStyle(fontSize: 12)),
        Align(alignment: Alignment.centerRight, child: TextButton.icon(onPressed: () async {
          await Clipboard.setData(ClipboardData(text: resultText));
          if (mounted) ScaffoldMessenger.of(context).showSnackBar(const SnackBar(content: Text('Result copied')));
        }, icon: const Icon(Icons.copy), label: const Text('Copy result'))),
      ]),
      const Padding(padding: EdgeInsets.all(8), child: Text('Research only. Portfolio is informational context, not a broker connection or order. A passing APK build does not prove live data quality.', style: TextStyle(color: Colors.orangeAccent))),
    ]);
  }
}
