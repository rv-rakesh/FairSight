import 'dart:io';
import 'dart:async';
import 'dart:convert';
import 'package:flutter/foundation.dart';
import 'package:material_ui/material_ui.dart';
import '../models/telemetry_model.dart';
import '../services/api_service.dart';

class ReportScreen extends StatefulWidget {
  final ExamAuditReport report;
  final File? videoFile;
  final String? videoPath;

  const ReportScreen({
    super.key,
    required this.report,
    this.videoFile,
    this.videoPath,
  });

  @override
  State<ReportScreen> createState() => _ReportScreenState();
}

class _ReportScreenState extends State<ReportScreen> {
  double _playerCurrentSec = 0.0;
  bool _isPlaying = false;
  Timer? _playbackTimer;
  int? _selectedEventIdx;

  @override
  void initState() {
    super.initState();
    if (widget.report.events.isNotEmpty) {
      _playerCurrentSec = widget.report.events.first.startSec;
      _selectedEventIdx = 0;
    }
  }

  @override
  void dispose() {
    _playbackTimer?.cancel();
    super.dispose();
  }

  void _togglePlayback() {
    if (_isPlaying) {
      _playbackTimer?.cancel();
      setState(() => _isPlaying = false);
    } else {
      setState(() => _isPlaying = true);
      _playbackTimer = Timer.periodic(const Duration(milliseconds: 250), (t) {
        if (!mounted) return;
        setState(() {
          final maxSec = widget.report.durationSec > 0 ? widget.report.durationSec : 10.0;
          _playerCurrentSec += 0.25;
          if (_playerCurrentSec >= maxSec) {
            _playerCurrentSec = maxSec;
            _isPlaying = false;
            _playbackTimer?.cancel();
          }
        });
      });
    }
  }

  void _seekTo(double sec) {
    setState(() {
      final maxSec = widget.report.durationSec > 0 ? widget.report.durationSec : 10.0;
      _playerCurrentSec = sec.clamp(0.0, maxSec);
    });
  }

  void _seekToViolation(int idx) {
    if (idx < 0 || idx >= widget.report.events.length) return;
    final ev = widget.report.events[idx];
    setState(() {
      _selectedEventIdx = idx;
      _seekTo(ev.startSec);
    });
    _showEvidenceDialog(ev, idx + 1);
  }

  String _formatTime(double totalSec) {
    final s = totalSec.toInt();
    final m = (s ~/ 60).toString().padLeft(2, '0');
    final remS = (s % 60).toString().padLeft(2, '0');
    return '$m:$remS';
  }

  Color _getRiskColor() {
    if (widget.report.riskScore >= 60) return const Color(0xFFDC2626); // Red
    if (widget.report.riskScore >= 25) return const Color(0xFFD97706); // Amber
    return const Color(0xFF059669); // Emerald
  }

  Color _getRiskBg() {
    if (widget.report.riskScore >= 60) return const Color(0xFFFEF2F2);
    if (widget.report.riskScore >= 25) return const Color(0xFFFFFBEB);
    return const Color(0xFFECFDF5);
  }

  Color _getRiskBorder() {
    if (widget.report.riskScore >= 60) return const Color(0xFFFECACA);
    if (widget.report.riskScore >= 25) return const Color(0xFFFDE68A);
    return const Color(0xFFA7F3D0);
  }

  String _formatEventTitle(String type) {
    switch (type) {
      case 'multiple_faces':
        return 'Unauthorized Person / Reaching Limb';
      case 'head_turned':
        return 'Head Turned Away from Screen';
      case 'gaze_away':
        return 'Eyes Glanced Off-Screen';
      case 'frequent_gaze_away':
        return 'Frequent Quick Glance Pattern';
      case 'frequent_head_turned':
        return 'Frequent Rapid Head Checks';
      case 'no_face':
        return 'Candidate Left Camera Frame';
      default:
        return type.replaceAll('_', ' ').toUpperCase();
    }
  }

  void _showEvidenceDialog(ExamViolationEvent ev, int number) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(10),
              ),
              child: const Icon(Icons.videocam_outlined, color: Color(0xFFDC2626), size: 22),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Violation #$number Evidence',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                  ),
                  Text(
                    _formatEventTitle(ev.type),
                    style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                  ),
                ],
              ),
            ),
          ],
        ),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              // Real Evidence Frame
              if (ev.evidenceFrameB64 != null && ev.evidenceFrameB64!.isNotEmpty)
                ClipRRect(
                  borderRadius: BorderRadius.circular(12),
                  child: Container(
                    decoration: BoxDecoration(
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                      color: Colors.black,
                    ),
                    child: Image.memory(
                      base64Decode(ev.evidenceFrameB64!),
                      fit: BoxFit.contain,
                      height: 180,
                    ),
                  ),
                )
              else
                Container(
                  height: 120,
                  decoration: BoxDecoration(
                    color: const Color(0xFFF1F5F9),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                  ),
                  child: const Center(
                    child: Column(
                      mainAxisSize: MainAxisSize.min,
                      children: [
                        Icon(Icons.camera_alt_outlined, size: 28, color: Color(0xFF94A3B8)),
                        SizedBox(height: 6),
                        Text('Forensic Frame Logged in Telemetry Stream', style: TextStyle(fontSize: 11.5, color: Color(0xFF64748B))),
                      ],
                    ),
                  ),
                ),
              const SizedBox(height: 16),
              // Metadata
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  children: [
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Timestamp Range:', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                        Text(
                          '${_formatTime(ev.startSec)} – ${_formatTime(ev.endSec)} (${ev.durationSec.toStringAsFixed(1)}s)',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        const Text('Penalty Added:', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                        Text(
                          '+${ev.weight} pts',
                          style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: Color(0xFFDC2626)),
                        ),
                      ],
                    ),
                    if (ev.note.isNotEmpty) ...[
                      const SizedBox(height: 6),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text('Algorithmic Trace:', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                          Flexible(
                            child: Text(
                              ev.note,
                              style: const TextStyle(fontSize: 11.5, fontStyle: FontStyle.italic, color: Color(0xFF334155)),
                              textAlign: TextAlign.end,
                            ),
                          ),
                        ],
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Close'),
          ),
        ],
      ),
    );
  }

  void _showExportDialog() {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: const Row(
          children: [
            Icon(Icons.print_outlined, color: Color(0xFF2563EB), size: 24),
            SizedBox(width: 10),
            Text('Export Forensic Certificate', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
          ],
        ),
        content: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 420),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Text(
                'FairSight Integrity Certificate has been generated with complete timestamp traces, dual risk scoring, and evidence frames.',
                style: TextStyle(fontSize: 13, color: Color(0xFF475569), height: 1.4),
              ),
              const SizedBox(height: 14),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: const Color(0xFFF8FAFC),
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: const Color(0xFFE2E8F0)),
                ),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text('Candidate: ${widget.report.candidateName}', style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 12.5)),
                    const SizedBox(height: 4),
                    Text('Exam: ${widget.report.examTitle}', style: const TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                    const SizedBox(height: 4),
                    Text('Final Score: ${widget.report.riskScore} / 100 (${widget.report.riskLevel})', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: _getRiskColor())),
                    const SizedBox(height: 4),
                    Text('10-Min Norm: ${widget.report.normalizedScore} / 100 (${widget.report.normalizedRiskLevel})', style: const TextStyle(fontSize: 12, color: Color(0xFF334155))),
                  ],
                ),
              ),
              const SizedBox(height: 12),
              const Text(
                'Printable HTML & PDF export is available via the backend /api/report/html endpoint.',
                style: TextStyle(fontSize: 11.5, color: Color(0xFF94A3B8)),
              ),
            ],
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Done'),
          ),
          ElevatedButton.icon(
            style: ElevatedButton.styleFrom(backgroundColor: const Color(0xFF2563EB), foregroundColor: Colors.white),
            onPressed: () {
              Navigator.pop(ctx);
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Audit certificate logged. Ready for institutional review.')),
              );
            },
            icon: const Icon(Icons.check, size: 16),
            label: const Text('Confirm Record'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final riskColor = _getRiskColor();
    final riskBg = _getRiskBg();
    final riskBorder = _getRiskBorder();
    final maxSec = widget.report.durationSec > 0 ? widget.report.durationSec : 10.0;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Integrity Audit Certificate'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
        actions: [
          IconButton(
            tooltip: 'Export Certificate',
            icon: const Icon(Icons.print_outlined),
            onPressed: _showExportDialog,
          ),
        ],
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 640),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Minimalist Score Card & Examination Summary Header
                Container(
                  padding: const EdgeInsets.all(24),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 10, offset: const Offset(0, 4)),
                    ],
                  ),
                  child: Column(
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                widget.report.candidateName,
                                style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Color(0xFF0F172A)),
                              ),
                              const SizedBox(height: 2),
                              Text(
                                widget.report.examTitle,
                                style: const TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
                              ),
                            ],
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                            decoration: BoxDecoration(
                              color: riskBg,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(color: riskBorder),
                            ),
                            child: Text(
                              '${widget.report.riskLevel.toUpperCase()} RISK',
                              style: TextStyle(color: riskColor, fontWeight: FontWeight.w700, fontSize: 11),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 18),
                      Container(
                        width: 96,
                        height: 96,
                        decoration: BoxDecoration(
                          color: riskBg,
                          shape: BoxShape.circle,
                          border: Border.all(color: riskColor, width: 3),
                        ),
                        child: Center(
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Text(
                                '${widget.report.riskScore}',
                                style: TextStyle(
                                  fontSize: 32,
                                  fontWeight: FontWeight.w800,
                                  color: riskColor,
                                  letterSpacing: -1,
                                ),
                              ),
                              const Text(
                                '/ 100',
                                style: TextStyle(fontSize: 10, fontWeight: FontWeight.w600, color: Color(0xFF94A3B8)),
                              ),
                            ],
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                        decoration: BoxDecoration(
                          color: const Color(0xFFF8FAFC),
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                        ),
                        child: Text(
                          '10-Min Normalized Score: ${widget.report.normalizedScore} / 100 (${widget.report.normalizedRiskLevel})',
                          style: const TextStyle(
                            fontSize: 11.5,
                            fontWeight: FontWeight.w600,
                            color: Color(0xFF334155),
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        widget.report.riskScore >= 60
                            ? 'High-confidence behavioral malpractice confirmed. Immediate proctor review required.'
                            : widget.report.riskScore >= 25
                                ? 'Moderate infractions observed. Video review recommended before final grading.'
                                : 'Session verified compliant. Natural candidate behavior observed throughout.',
                        textAlign: TextAlign.center,
                        style: const TextStyle(fontSize: 13, color: Color(0xFF64748B), height: 1.4),
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 16),

                // Metrics Strip
                Row(
                  children: [
                    _buildStatCard('Duration', '${widget.report.durationSec.toStringAsFixed(1)}s', Icons.timer_outlined),
                    const SizedBox(width: 12),
                    _buildStatCard('Violations', '${widget.report.events.length}', Icons.flag_outlined),
                    const SizedBox(width: 12),
                    _buildStatCard(
                      widget.report.framesAnalysed > 0 ? 'Analyzed Frames' : 'Flagged Moments',
                      widget.report.framesAnalysed > 0 ? '${widget.report.framesAnalysed}' : '${widget.report.activityLog.length}',
                      Icons.layers_outlined,
                    ),
                  ],
                ),

                const SizedBox(height: 20),

                // Forensic Video Evidence Player Component
                Container(
                  padding: const EdgeInsets.all(18),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(18),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.015), blurRadius: 6, offset: const Offset(0, 2)),
                    ],
                  ),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Row(
                            children: [
                              Icon(Icons.video_library_outlined, color: Color(0xFF2563EB), size: 19),
                              SizedBox(width: 8),
                              Text(
                                'Forensic Video Review Player',
                                style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF0F172A)),
                              ),
                            ],
                          ),
                          Text(
                            '${_formatTime(_playerCurrentSec)} / ${_formatTime(maxSec)}',
                            style: const TextStyle(fontFamily: 'monospace', fontSize: 12.5, fontWeight: FontWeight.w700, color: Color(0xFF2563EB)),
                          ),
                        ],
                      ),
                      const SizedBox(height: 14),

                      // Player Viewport / Frame Preview
                      Container(
                        height: 160,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: const Color(0xFF0F172A),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Stack(
                          alignment: Alignment.center,
                          children: [
                            // If an event matches current timestamp, show its evidence thumbnail
                            if (_selectedEventIdx != null &&
                                _selectedEventIdx! < widget.report.events.length &&
                                widget.report.events[_selectedEventIdx!].evidenceFrameB64 != null)
                              ClipRRect(
                                borderRadius: BorderRadius.circular(12),
                                child: Image.memory(
                                  base64Decode(widget.report.events[_selectedEventIdx!].evidenceFrameB64!),
                                  fit: BoxFit.contain,
                                  width: double.infinity,
                                  height: 160,
                                ),
                              )
                            else
                              Column(
                                mainAxisAlignment: MainAxisAlignment.center,
                                children: [
                                  const Icon(Icons.ondemand_video, color: Color(0xFF64748B), size: 40),
                                  const SizedBox(height: 8),
                                  Text(
                                    widget.videoFile != null
                                        ? 'Video Source: ${widget.videoFile!.path.split(Platform.pathSeparator).last}'
                                        : 'Exam Session Telemetry Stream',
                                    style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 12),
                                  ),
                                  const SizedBox(height: 4),
                                  Text(
                                    'Scrub slider below to inspect timestamps (${_formatTime(_playerCurrentSec)})',
                                    style: const TextStyle(color: Color(0xFF475569), fontSize: 11),
                                  ),
                                ],
                              ),

                            // Top Pill on Player
                            Positioned(
                              top: 8,
                              right: 8,
                              child: Container(
                                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                                decoration: BoxDecoration(
                                  color: Colors.black.withValues(alpha: 0.7),
                                  borderRadius: BorderRadius.circular(6),
                                ),
                                child: Text(
                                  _isPlaying ? 'PLAYING' : 'PAUSED',
                                  style: TextStyle(
                                    color: _isPlaying ? const Color(0xFF34D399) : const Color(0xFF94A3B8),
                                    fontSize: 9.5,
                                    fontWeight: FontWeight.w700,
                                  ),
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: 12),

                      // Scrubber Slider
                      SliderTheme(
                        data: SliderTheme.of(context).copyWith(
                          trackHeight: 4,
                          activeTrackColor: const Color(0xFF2563EB),
                          inactiveTrackColor: const Color(0xFFE2E8F0),
                          thumbColor: const Color(0xFF2563EB),
                          thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 7),
                        ),
                        child: Slider(
                          value: _playerCurrentSec.clamp(0.0, maxSec),
                          min: 0.0,
                          max: maxSec,
                          onChanged: (v) => _seekTo(v),
                        ),
                      ),

                      // Player Controls
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          IconButton(
                            icon: const Icon(Icons.replay, size: 20, color: Color(0xFF475569)),
                            tooltip: 'Replay from 00:00',
                            onPressed: () => _seekTo(0.0),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            icon: const Icon(Icons.replay_5, size: 22, color: Color(0xFF475569)),
                            tooltip: 'Step Back 5s',
                            onPressed: () => _seekTo(_playerCurrentSec - 5.0),
                          ),
                          const SizedBox(width: 8),
                          ElevatedButton(
                            style: ElevatedButton.styleFrom(
                              shape: const CircleBorder(),
                              padding: const EdgeInsets.all(12),
                              backgroundColor: const Color(0xFF2563EB),
                              foregroundColor: Colors.white,
                              elevation: 2,
                            ),
                            onPressed: _togglePlayback,
                            child: Icon(_isPlaying ? Icons.pause : Icons.play_arrow, size: 24),
                          ),
                          const SizedBox(width: 8),
                          IconButton(
                            icon: const Icon(Icons.forward_5, size: 22, color: Color(0xFF475569)),
                            tooltip: 'Step Forward 5s',
                            onPressed: () => _seekTo(_playerCurrentSec + 5.0),
                          ),
                          if (widget.videoFile != null && !kIsWeb && defaultTargetPlatform == TargetPlatform.windows) ...[
                            const SizedBox(width: 8),
                            IconButton(
                              icon: const Icon(Icons.open_in_new, size: 20, color: Color(0xFF2563EB)),
                              tooltip: 'Open in System Video Player',
                              onPressed: () {
                                try {
                                  Process.run('explorer.exe', [widget.videoFile!.path]);
                                } catch (e) {
                                  debugPrint("Launch player error: $e");
                                }
                              },
                            ),
                          ],
                        ],
                      ),
                    ],
                  ),
                ),

                const SizedBox(height: 24),

                // Infractions Title
                const Text(
                  'Confirmed Infractions Timeline',
                  style: TextStyle(fontSize: 16, fontWeight: FontWeight.w700, color: Color(0xFF0F172A), letterSpacing: -0.3),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Events exceeding sustained duration thresholds or rapid frequency gates.',
                  style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                ),
                const SizedBox(height: 12),

                if (widget.report.events.isEmpty)
                  Container(
                    padding: const EdgeInsets.all(28),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: const Column(
                      children: [
                        Icon(Icons.check_circle_outline, color: Color(0xFF059669), size: 36),
                        SizedBox(height: 8),
                        Text(
                          'Clean Assessment Session',
                          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF0F172A)),
                        ),
                        SizedBox(height: 2),
                        Text(
                          'Zero confirmed behavioral anomalies detected.',
                          style: TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                        ),
                      ],
                    ),
                  )
                else
                  ListView.separated(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: widget.report.events.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder: (context, idx) {
                      final e = widget.report.events[idx];
                      final isSelected = _selectedEventIdx == idx;

                      return Container(
                        padding: const EdgeInsets.all(14),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(
                            color: isSelected ? const Color(0xFF2563EB) : const Color(0xFFE2E8F0),
                            width: isSelected ? 1.5 : 1,
                          ),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withValues(alpha: 0.015), blurRadius: 4, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Row(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Container(
                                  width: 36,
                                  height: 36,
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFFEF2F2),
                                    borderRadius: BorderRadius.circular(10),
                                  ),
                                  child: const Icon(Icons.warning_amber_rounded, color: Color(0xFFDC2626), size: 18),
                                ),
                                const SizedBox(width: 12),
                                Expanded(
                                  child: Column(
                                    crossAxisAlignment: CrossAxisAlignment.start,
                                    children: [
                                      Text(
                                        _formatEventTitle(e.type),
                                        style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: Color(0xFF0F172A)),
                                      ),
                                      const SizedBox(height: 3),
                                      Text(
                                        'Time: ${e.startSec.toStringAsFixed(1)}s – ${e.endSec.toStringAsFixed(1)}s (${e.durationSec.toStringAsFixed(1)}s duration)',
                                        style: const TextStyle(fontSize: 12, color: Color(0xFF64748B)),
                                      ),
                                      if (e.note.isNotEmpty) ...[
                                        const SizedBox(height: 2),
                                        Text(
                                          e.note,
                                          style: const TextStyle(fontSize: 11, fontStyle: FontStyle.italic, color: Color(0xFF94A3B8)),
                                        ),
                                      ],
                                    ],
                                  ),
                                ),
                                Container(
                                  padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3.5),
                                  decoration: BoxDecoration(
                                    color: const Color(0xFFFEF2F2),
                                    borderRadius: BorderRadius.circular(6),
                                    border: Border.all(color: const Color(0xFFFECACA)),
                                  ),
                                  child: Text(
                                    '+${e.weight} pts',
                                    style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 11.5, color: Color(0xFFDC2626)),
                                  ),
                                ),
                              ],
                            ),
                            const SizedBox(height: 10),
                            Row(
                              mainAxisAlignment: MainAxisAlignment.spaceBetween,
                              children: [
                                // Thumbnail mini preview if available
                                if (e.evidenceFrameB64 != null && e.evidenceFrameB64!.isNotEmpty)
                                  ClipRRect(
                                    borderRadius: BorderRadius.circular(6),
                                    child: Image.memory(
                                      base64Decode(e.evidenceFrameB64!),
                                      width: 48,
                                      height: 32,
                                      fit: BoxFit.cover,
                                    ),
                                  )
                                else
                                  const SizedBox.shrink(),
                                OutlinedButton.icon(
                                  style: OutlinedButton.styleFrom(
                                    foregroundColor: const Color(0xFF2563EB),
                                    side: const BorderSide(color: Color(0xFFDBEAFE)),
                                    padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                    shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                                  ),
                                  onPressed: () => _seekToViolation(idx),
                                  icon: const Icon(Icons.visibility_outlined, size: 15),
                                  label: const Text('View Evidence', style: TextStyle(fontSize: 12, fontWeight: FontWeight.w600)),
                                ),
                              ],
                            ),
                          ],
                        ),
                      );
                    },
                  ),

                const SizedBox(height: 28),

                // Return to Dashboard Button
                SizedBox(
                  height: 48,
                  child: ElevatedButton(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                      foregroundColor: Colors.white,
                      elevation: 0,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
                    ),
                    onPressed: () => Navigator.popUntil(context, (route) => route.isFirst),
                    child: const Text('RETURN TO DASHBOARD', style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.3)),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildStatCard(String label, String value, IconData icon) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: const Color(0xFFE2E8F0)),
          boxShadow: [
            BoxShadow(color: Colors.black.withValues(alpha: 0.015), blurRadius: 4, offset: const Offset(0, 2)),
          ],
        ),
        child: Column(
          children: [
            Icon(icon, size: 18, color: const Color(0xFF2563EB)),
            const SizedBox(height: 6),
            Text(value, style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 15, color: Color(0xFF0F172A))),
            const SizedBox(height: 2),
            Text(label, style: const TextStyle(fontSize: 11, color: Color(0xFF64748B))),
          ],
        ),
      ),
    );
  }
}
