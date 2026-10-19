import 'dart:convert';

import 'package:flutter/material.dart';
import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';

const _researchModules = <String, String>{
  'Overview': 'Run the complete multi-agent research workflow from one place. Results come from the configured TradingAgents backend.',
  'Analyst Team': 'Technical, fundamentals, news and sentiment analysts gather evidence. Availability depends on the selected analysts and configured data vendors.',
  'Bull / Bear Debate': 'Bullish and bearish researchers challenge the analyst evidence over configurable debate rounds.',
  'Trader Decision': 'The Trader agent synthesizes analyst reports and research debate into a decision report; it is research output, not a live broker order.',
  'Risk & Portfolio': 'Risk-management agents review downside, volatility and the proposal. Portfolio approval remains part of the framework report.',
  'Backtesting': 'Evaluate a ticker over historical dates using the framework CLI. Results depend on model, data coverage and the chosen dates.',
  'Reports & Memory': 'The framework can save HTML reports and a decision memory log when persistence is enabled on the backend.',
  'Provider Status': 'Provider keys and model settings must stay on the backend. This screen only reads readiness metadata and never stores API keys.',
};

class TradingAgentsResearchPage extends StatefulWidget {
  const TradingAgentsResearchPage({super.key, this.initialModule = 'Overview'});

  final String initialModule;

  @override
  State<TradingAgentsResearchPage> createState() => _TradingAgentsResearchPageState();
}

class _TradingAgentsResearchPageState extends State<TradingAgentsResearchPage> {
  final _url = TextEditingController(
    text: const String.fromEnvironment('TRADINGAGENTS_BACKEND_URL', defaultValue: ''),
  );
  final _ticker = TextEditingController(text: 'RELIANCE.NS');
  final _date = TextEditingController(text: DateTime.now().toIso8601String().substring(0, 10));
  final _startDate = TextEditingController(text: '2026-01-01');
  final _endDate = TextEditingController(text: DateTime.now().toIso8601String().substring(0, 10));
  late String _module;
  final Set<String> _selectedAnalysts = {'market', 'news', 'fundamentals', 'social'};
  bool _busy = false;
  Map<String, dynamic> _health = const {};
  String? _error;
  String? _report;
  String? _backtest;
  String _lastAction = '';

  @override
  void initState() {
    super.initState();
    _module = _researchModules.containsKey(widget.initialModule) ? widget.initialModule : 'Overview';
    _restoreUrl();
  }

  Future<void> _restoreUrl() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final saved = prefs.getString('tradingagents_backend_url');
      if (saved != null && saved.trim().isNotEmpty && mounted) {
        setState(() => _url.text = saved);
      }
    } catch (_) {
      // The page remains usable with the configured or manually entered URL
      // if platform preferences are unavailable (for example in widget tests).
    }
  }

  @override
  void dispose() {
    _url.dispose();
    _ticker.dispose();
    _date.dispose();
    _startDate.dispose();
    _endDate.dispose();
    super.dispose();
  }

  Uri _endpoint(String path) {
    final raw = _url.text.trim().replaceAll(RegExp(r'/+$'), '');
    final base = Uri.tryParse(raw);
    if (base == null ||
        base.scheme != 'https' ||
        base.host.isEmpty ||
        base.userInfo.isNotEmpty ||
        base.hasQuery ||
        base.hasFragment ||
        base.host == 'localhost' ||
        base.host == '127.0.0.1') {
      throw const FormatException('TradingAgents backend URL is missing or invalid. Enter the separately deployed public HTTPS base URL (for example https://your-service.up.railway.app), without /health or /v1 paths. The saved URL is shared across all research tabs.');
    }
    return base.replace(path: '${base.path.replaceAll(RegExp(r'/+$'), '')}$path');
  }

  Future<Map<String, dynamic>> _get(String path) async {
    final response = await http.get(_endpoint(path), headers: {'accept': 'application/json'})
        .timeout(const Duration(seconds: 15));
    return _decode(response);
  }

  Future<Map<String, dynamic>> _post(String path, Map<String, dynamic> body,
      {Duration timeout = const Duration(minutes: 5)}) async {
    final response = await http.post(
      _endpoint(path),
      headers: {'accept': 'application/json', 'content-type': 'application/json'},
      body: jsonEncode(body),
    ).timeout(timeout);
    return _decode(response);
  }

  Map<String, dynamic> _decode(http.Response response) {
    dynamic data;
    try {
      data = jsonDecode(response.body);
    } catch (_) {
      throw Exception('Backend returned invalid JSON (HTTP ${response.statusCode}).');
    }
    if (response.statusCode >= 400) {
      final detail = data is Map ? data['detail']?.toString() : null;
      throw Exception(detail?.isNotEmpty == true ? detail! : 'Request failed (HTTP ${response.statusCode}).');
    }
    if (data is! Map) throw Exception('Backend returned an unexpected response shape.');
    return Map<String, dynamic>.from(data);
  }

  Future<void> _run(Future<void> Function() action, String label) async {
    if (_busy) return;
    setState(() {
      _busy = true;
      _error = null;
      _lastAction = label;
    });
    try {
      final prefs = await SharedPreferences.getInstance();
      await prefs.setString('tradingagents_backend_url', _url.text.trim());
      await action();
    } catch (e) {
      if (mounted) setState(() => _error = e.toString().replaceFirst('Exception: ', ''));
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _checkHealth() => _run(() async {
        final result = await _get('/health');
        if (mounted) setState(() => _health = result);
      }, 'Checking backend');

  Future<void> _analyze() => _run(() async {
        final ticker = _ticker.text.trim().toUpperCase();
        if (ticker.isEmpty) throw const FormatException('Enter a ticker, for example RELIANCE.NS.');
        if (_selectedAnalysts.isEmpty) {
          throw const FormatException('Select at least one analyst before running research.');
        }
        final result = await _post('/v1/analyze', {
          'ticker': ticker,
          'date': _date.text.trim(),
          'analysts': ['market', 'news', 'fundamentals', 'social']
              .where(_selectedAnalysts.contains)
              .toList(),
        });
        if (mounted) {
          setState(() {
            _report = (result['report'] ?? result['summary'] ?? 'No report returned.').toString();
            _lastAction = 'Analysis status: ${result['status'] ?? 'UNKNOWN'}';
          });
        }
      }, 'Running multi-agent analysis');

  Future<void> _backtestRun() => _run(() async {
        final ticker = _ticker.text.trim().toUpperCase();
        final start = _startDate.text.trim();
        final end = _endDate.text.trim();
        if (ticker.isEmpty) throw const FormatException('Enter a ticker before starting a backtest.');
        if (DateTime.tryParse(start) == null || DateTime.tryParse(end) == null) {
          throw const FormatException('Use YYYY-MM-DD for both backtest dates.');
        }
        if (DateTime.parse(start).isAfter(DateTime.parse(end))) {
          throw const FormatException('Backtest start date must be on or before the end date.');
        }
        final result = await _post('/v1/backtest', {
          'ticker': ticker, 'start_date': start, 'end_date': end, 'every_n_days': 7,
        }, timeout: const Duration(minutes: 6));
        if (mounted) setState(() => _backtest = (result['report'] ?? result['summary'] ?? 'No backtest report returned.').toString());
      }, 'Running historical backtest');

  @override
  Widget build(BuildContext context) {
    final healthStatus = (_health['analysis_ready'] == true)
        ? 'READY'
        : (_health.isEmpty ? 'NOT CHECKED' : 'SETUP NEEDED');
    return ListView(
      padding: const EdgeInsets.all(12),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Row(children: [
                Icon(Icons.psychology_alt_outlined, color: Color(0xFF12D6FF), size: 30),
                SizedBox(width: 10),
                Expanded(child: Text('TRADINGAGENTS RESEARCH LAB', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w900))),
              ]),
              const SizedBox(height: 6),
              const Text('Multi-agent financial research • No broker orders are placed from this workspace.'),
              const SizedBox(height: 12),
              TextField(
                controller: _url,
                keyboardType: TextInputType.url,
                decoration: const InputDecoration(
                  labelText: 'TradingAgents backend HTTPS URL',
                  hintText: 'https://your-tradingagents-api.example.com',
                  helperText: 'Enter the separately deployed TradingAgents API base URL once; it is shared across the research tabs.',
                ),
              ),
              const SizedBox(height: 8),
              Wrap(spacing: 8, runSpacing: 8, crossAxisAlignment: WrapCrossAlignment.center, children: [
                FilledButton.icon(
                  onPressed: _busy ? null : _checkHealth,
                  icon: const Icon(Icons.health_and_safety_outlined),
                  label: const Text('Check backend'),
                ),
                Chip(label: Text('Backend: $healthStatus')),
              ]),
              if (_health.isNotEmpty) ...[
                const SizedBox(height: 8),
                Text((_health['message'] ?? 'Health response received.').toString()),
                if (_health['configured_providers'] is List)
                  Text('Providers detected: ${(_health['configured_providers'] as List).join(', ')}'),
                if (_health['configuration_gaps'] is List && (_health['configuration_gaps'] as List).isNotEmpty)
                  Text('Missing setup: ${(_health['configuration_gaps'] as List).join(', ')}',
                      style: const TextStyle(color: Colors.orangeAccent)),
              ],
            ]),
          ),
        ),
        Card(
          child: Padding(
            padding: const EdgeInsets.all(14),
            child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
              const Text('Research controls', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
              const SizedBox(height: 10),
              TextField(controller: _ticker, decoration: const InputDecoration(labelText: 'Ticker / symbol', hintText: 'RELIANCE.NS, AAPL, NVDA')),
              const SizedBox(height: 8),
              Text(_researchModules[_module]!, style: const TextStyle(color: Colors.white70)),
              if (_module == 'Overview' || _module == 'Analyst Team' || _module == 'Bull / Bear Debate' || _module == 'Trader Decision' || _module == 'Risk & Portfolio') ...[
                const SizedBox(height: 10),
                const Text('Analyst selection', style: TextStyle(fontWeight: FontWeight.w700)),
                const Text('Choose which research sources participate in this run.', style: TextStyle(color: Colors.white70, fontSize: 12)),
                const SizedBox(height: 4),
                Wrap(
                  spacing: 6,
                  runSpacing: 2,
                  children: [
                    for (final analyst in const {
                      'market': 'Technical / Market',
                      'news': 'News',
                      'fundamentals': 'Fundamentals',
                      'social': 'Social sentiment',
                    }.entries)
                      FilterChip(
                        label: Text(analyst.value),
                        selected: _selectedAnalysts.contains(analyst.key),
                        onSelected: _busy ? null : (selected) {
                          setState(() {
                            if (selected) {
                              _selectedAnalysts.add(analyst.key);
                            } else {
                              _selectedAnalysts.remove(analyst.key);
                            }
                          });
                        },
                      ),
                  ],
                ),
                const SizedBox(height: 8),
                TextField(controller: _date, decoration: const InputDecoration(labelText: 'Analysis date (YYYY-MM-DD)')),
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _busy ? null : _analyze,
                  icon: const Icon(Icons.play_arrow),
                  label: const Text('Run full multi-agent analysis'),
                ),
              ],
              if (_module == 'Backtesting') ...[
                const SizedBox(height: 8),
                TextField(controller: _startDate, decoration: const InputDecoration(labelText: 'Backtest start date (YYYY-MM-DD)')),
                const SizedBox(height: 8),
                TextField(controller: _endDate, decoration: const InputDecoration(labelText: 'Backtest end date (YYYY-MM-DD)')),
                const SizedBox(height: 8),
                FilledButton.icon(
                  onPressed: _busy ? null : _backtestRun,
                  icon: const Icon(Icons.query_stats),
                  label: const Text('Run historical backtest'),
                ),
              ],
              if (_module == 'Reports & Memory')
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.description_outlined),
                  title: Text('Report persistence is backend-controlled'),
                  subtitle: Text('Enable framework save/report options on the backend to retain HTML reports and decision memory. This screen does not invent local history.'),
                ),
              if (_module == 'Provider Status')
                const ListTile(
                  contentPadding: EdgeInsets.zero,
                  leading: Icon(Icons.key_outlined),
                  title: Text('Keep provider keys server-side'),
                  subtitle: Text('Configure NVIDIA, OpenRouter or another supported provider as backend environment variables. Never paste API keys into this APK.'),
                ),
            ]),
          ),
        ),
        if (_busy) const Card(child: Padding(padding: EdgeInsets.all(14), child: Row(children: [
          SizedBox(width: 20, height: 20, child: CircularProgressIndicator(strokeWidth: 2)),
          SizedBox(width: 10),
          Expanded(child: Text('Working… long-running research may take several minutes.')),
        ]))),
        if (_lastAction.isNotEmpty) Padding(padding: const EdgeInsets.symmetric(vertical: 4), child: Text(_lastAction, style: const TextStyle(color: Colors.white70))),
        if (_error != null) Card(color: const Color(0xFF351A1A), child: Padding(padding: const EdgeInsets.all(12), child: Text(_error!))),
        if (_report != null) Card(
          child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Latest multi-agent report', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            SelectableText(_report!),
          ])),
        ),
        if (_backtest != null) Card(
          child: Padding(padding: const EdgeInsets.all(14), child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            const Text('Historical backtest report', style: TextStyle(fontSize: 16, fontWeight: FontWeight.w800)),
            const SizedBox(height: 8),
            SelectableText(_backtest!),
          ])),
        ),
        const Padding(
          padding: EdgeInsets.all(8),
          child: Text('Research only: outputs may vary with model, date, provider quotas and data quality. Historical results do not guarantee future performance.',
              style: TextStyle(fontSize: 12, color: Colors.white60)),
        ),
      ],
    );
  }
}
