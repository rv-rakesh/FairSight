import 'package:flutter/material.dart';
import '../models/telemetry_model.dart';

class ReportScreen extends StatelessWidget {
  final ExamAuditReport report;

  const ReportScreen({super.key, required this.report});

  Color _getRiskColor() {
    if (report.riskScore >= 60) return const Color(0xFFDC2626); // Red
    if (report.riskScore >= 25) return const Color(0xFFD97706); // Amber
    return const Color(0xFF059669); // Emerald
  }

  Color _getRiskBg() {
    if (report.riskScore >= 60) return const Color(0xFFFEF2F2);
    if (report.riskScore >= 25) return const Color(0xFFFFFBEB);
    return const Color(0xFFECFDF5);
  }

  Color _getRiskBorder() {
    if (report.riskScore >= 60) return const Color(0xFFFECACA);
    if (report.riskScore >= 25) return const Color(0xFFFDE68A);
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

  @override
  Widget build(BuildContext context) {
    final riskColor = _getRiskColor();
    final riskBg = _getRiskBg();
    final riskBorder = _getRiskBorder();

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Integrity Audit Certificate'),
        leading: IconButton(
          icon: const Icon(Icons.arrow_back),
          onPressed: () => Navigator.pop(context),
        ),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 20),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Minimalist Score Card
                Container(
                  padding: const EdgeInsets.all(28),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(0.02), blurRadius: 10, offset: const Offset(0, 4)),
                    ],
                  ),
                  child: Column(
                    children: [
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
                                '${report.riskScore}',
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
                      const SizedBox(height: 14),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 4),
                        decoration: BoxDecoration(
                          color: riskBg,
                          borderRadius: BorderRadius.circular(20),
                          border: Border.all(color: riskBorder),
                        ),
                        child: Text(
                          '${report.riskLevel.toUpperCase()} RISK SESSION',
                          style: TextStyle(
                            color: riskColor,
                            fontWeight: FontWeight.w700,
                            fontSize: 11.5,
                            letterSpacing: 0.5,
                          ),
                        ),
                      ),
                      const SizedBox(height: 12),
                      Text(
                        report.riskScore >= 60
                            ? 'High-confidence behavioral malpractice confirmed. Immediate proctor review required.'
                            : report.riskScore >= 25
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
                    _buildStatCard('Duration', '${report.durationSec.toStringAsFixed(1)}s', Icons.timer_outlined),
                    const SizedBox(width: 12),
                    _buildStatCard('Violations', '${report.events.length}', Icons.flag_outlined),
                    const SizedBox(width: 12),
                    _buildStatCard('Analyzed Frames', '${report.activityLog.length}', Icons.layers_outlined),
                  ],
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

                if (report.events.isEmpty)
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
                    itemCount: report.events.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 8),
                    itemBuilder: (context, idx) {
                      final e = report.events[idx];
                      return Container(
                        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
                        decoration: BoxDecoration(
                          color: Colors.white,
                          borderRadius: BorderRadius.circular(14),
                          border: Border.all(color: const Color(0xFFE2E8F0)),
                          boxShadow: [
                            BoxShadow(color: Colors.black.withOpacity(0.015), blurRadius: 4, offset: const Offset(0, 2)),
                          ],
                        ),
                        child: Row(
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
                            const SizedBox(width: 14),
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
            BoxShadow(color: Colors.black.withOpacity(0.015), blurRadius: 4, offset: const Offset(0, 2)),
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
