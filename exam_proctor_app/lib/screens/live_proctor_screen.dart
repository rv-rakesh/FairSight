import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import 'package:camera/camera.dart';
import '../services/api_service.dart';
import '../models/telemetry_model.dart';
import 'report_screen.dart';

class LiveProctorScreen extends StatefulWidget {
  const LiveProctorScreen({super.key});

  @override
  State<LiveProctorScreen> createState() => _LiveProctorScreenState();
}

class _LiveProctorScreenState extends State<LiveProctorScreen> {
  CameraController? _cameraController;
  List<CameraDescription> _cameras = [];
  bool _isCameraReady = false;
  bool _isProcessingFrame = false;
  String? _sessionId;
  Timer? _frameTimer;
  Timer? _sessionTimer;
  int _secondsElapsed = 0;

  // Live Telemetry State
  int _currentRiskScore = 0;
  String _currentRiskLevel = "Low";
  TelemetryResult? _latestTelemetry;
  String? _activeWarning;

  @override
  void initState() {
    super.initState();
    _initLiveSession();
  }

  Future<void> _initLiveSession() async {
    final sId = await ApiService.startSession();
    if (!mounted) return;
    setState(() => _sessionId = sId);

    try {
      _cameras = await availableCameras();
      if (_cameras.isNotEmpty) {
        CameraDescription selectedCam = _cameras.firstWhere(
          (c) => c.lensDirection == CameraLensDirection.front,
          orElse: () => _cameras.first,
        );

        _cameraController = CameraController(
          selectedCam,
          ResolutionPreset.medium,
          enableAudio: false,
          imageFormatGroup: ImageFormatGroup.jpeg,
        );

        await _cameraController!.initialize();
        if (mounted) {
          setState(() => _isCameraReady = true);
          _startProctoringLoops();
        }
      }
    } catch (e) {
      debugPrint("Camera error: $e");
    }
  }

  void _startProctoringLoops() {
    _sessionTimer = Timer.periodic(const Duration(seconds: 1), (t) {
      if (mounted) {
        setState(() => _secondsElapsed++);
      }
    });

    _frameTimer = Timer.periodic(const Duration(milliseconds: 700), (_) async {
      if (_isProcessingFrame || _cameraController == null || !_cameraController!.value.isInitialized) {
        return;
      }
      _isProcessingFrame = true;
      try {
        final XFile image = await _cameraController!.takePicture();
        final Uint8List bytes = await image.readAsBytes();
        final String base64Image = base64Encode(bytes);

        if (_sessionId != null) {
          final res = await ApiService.sendSessionFrame(
            _sessionId!,
            base64Image,
            _secondsElapsed.toDouble(),
          );

          if (res != null && mounted) {
            setState(() {
              _currentRiskScore = res['current_risk_score'] ?? _currentRiskScore;
              _currentRiskLevel = res['current_risk_level'] ?? _currentRiskLevel;

              if (res['telemetry'] != null) {
                _latestTelemetry = TelemetryResult.fromJson(res['telemetry']);

                final conds = _latestTelemetry!.conditions;
                final dets = _latestTelemetry!.details;
                if (conds['multiple_faces'] == true) {
                  _activeWarning = dets['multiple_faces'] ?? "Multiple persons/intruder detected!";
                } else if (conds['no_face'] == true) {
                  _activeWarning = "Candidate face missing from frame!";
                } else if (conds['head_turned'] == true) {
                  _activeWarning = "Head turned: ${dets['head_turned'] ?? ''}";
                } else if (conds['gaze_away'] == true) {
                  _activeWarning = "Eyes off-screen: ${dets['gaze_away'] ?? ''}";
                } else {
                  _activeWarning = null;
                }
              }
            });
          }
        }
      } catch (e) {
        debugPrint("Frame error: $e");
      } finally {
        _isProcessingFrame = false;
      }
    });
  }

  Future<void> _finalizeAndFinishExam() async {
    _frameTimer?.cancel();
    _sessionTimer?.cancel();

    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(24.0),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                CircularProgressIndicator(color: Color(0xFF2563EB)),
                SizedBox(height: 16),
                Text('Finalizing Forensic Audit Report...'),
              ],
            ),
          ),
        ),
      ),
    );

    if (_sessionId != null) {
      final report = await ApiService.finalizeSession(_sessionId!);
      if (mounted) {
        Navigator.pop(context);
        if (report != null) {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(builder: (_) => ReportScreen(report: report)),
          );
          return;
        }
      }
    }

    if (mounted) {
      Navigator.pop(context);
      Navigator.pop(context);
    }
  }

  @override
  void dispose() {
    _frameTimer?.cancel();
    _sessionTimer?.cancel();
    _cameraController?.dispose();
    super.dispose();
  }

  String _formatTime(int sec) {
    final m = (sec ~/ 60).toString().padLeft(2, '0');
    final s = (sec % 60).toString().padLeft(2, '0');
    return '$m:$s';
  }

  Color _getRiskColor() {
    if (_currentRiskScore >= 60) return const Color(0xFFDC2626);
    if (_currentRiskScore >= 25) return const Color(0xFFD97706);
    return const Color(0xFF059669);
  }

  @override
  Widget build(BuildContext context) {
    final riskColor = _getRiskColor();

    return Scaffold(
      backgroundColor: const Color(0xFFF1F5F9),
      appBar: AppBar(
        title: const Text('Live Proctoring Session'),
        actions: [
          Center(
            child: Container(
              padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
              margin: const EdgeInsets.only(right: 14),
              decoration: BoxDecoration(
                color: const Color(0xFFFEF2F2),
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: const Color(0xFFFECACA)),
              ),
              child: Row(
                children: [
                  Container(
                    width: 7,
                    height: 7,
                    decoration: const BoxDecoration(color: Color(0xFFDC2626), shape: BoxShape.circle),
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'REC ${_formatTime(_secondsElapsed)}',
                    style: const TextStyle(color: Color(0xFFDC2626), fontWeight: FontWeight.w700, fontSize: 11.5),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
      body: Stack(
        children: [
          // Camera Stream with Apple-style rounded frame
          Positioned.fill(
            child: Padding(
              padding: const EdgeInsets.all(12),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(20),
                child: _isCameraReady && _cameraController != null
                    ? CameraPreview(_cameraController!)
                    : Container(
                        color: Colors.white,
                        child: const Center(
                          child: Column(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              CircularProgressIndicator(color: Color(0xFF2563EB)),
                              SizedBox(height: 14),
                              Text('Initializing camera stream...', style: TextStyle(color: Color(0xFF64748B), fontSize: 13)),
                            ],
                          ),
                        ),
                      ),
              ),
            ),
          ),

          // Top Apple Frosted HUD Pill (Risk + Persons)
          Positioned(
            top: 24,
            left: 24,
            right: 24,
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                // Frosted Risk Pill
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.92),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 8, offset: const Offset(0, 2)),
                    ],
                  ),
                  child: Row(
                    children: [
                      Icon(Icons.shield_outlined, color: riskColor, size: 17),
                      const SizedBox(width: 8),
                      Text(
                        'Risk: $_currentRiskScore / 100',
                        style: TextStyle(
                          color: const Color(0xFF0F172A),
                          fontWeight: FontWeight.w700,
                          fontSize: 12.5,
                        ),
                      ),
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
                        decoration: BoxDecoration(
                          color: riskColor.withOpacity(0.12),
                          borderRadius: BorderRadius.circular(6),
                        ),
                        child: Text(
                          _currentRiskLevel.toUpperCase(),
                          style: TextStyle(color: riskColor, fontSize: 10, fontWeight: FontWeight.w700),
                        ),
                      ),
                    ],
                  ),
                ),

                // Persons Pill
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
                  decoration: BoxDecoration(
                    color: Colors.white.withOpacity(0.92),
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 8, offset: const Offset(0, 2)),
                    ],
                  ),
                  child: Row(
                    children: [
                      Icon(
                        Icons.person_outline,
                        size: 16,
                        color: (_latestTelemetry?.faceCount ?? 1) > 1 ? const Color(0xFFDC2626) : const Color(0xFF059669),
                      ),
                      const SizedBox(width: 6),
                      Text(
                        '${_latestTelemetry?.faceCount ?? 1} in frame',
                        style: const TextStyle(color: Color(0xFF0F172A), fontWeight: FontWeight.w600, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),

          // Active Warning Banner (If Any Violation Occurs)
          if (_activeWarning != null)
            Positioned(
              top: 76,
              left: 24,
              right: 24,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                decoration: BoxDecoration(
                  color: const Color(0xFFFEF2F2).withOpacity(0.95),
                  borderRadius: BorderRadius.circular(14),
                  border: Border.all(color: const Color(0xFFFECACA)),
                  boxShadow: [
                    BoxShadow(color: Colors.red.withOpacity(0.12), blurRadius: 10, offset: const Offset(0, 4)),
                  ],
                ),
                child: Row(
                  children: [
                    const Icon(Icons.warning_amber_rounded, color: Color(0xFFDC2626), size: 20),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        _activeWarning!,
                        style: const TextStyle(color: Color(0xFF991B1B), fontWeight: FontWeight.w700, fontSize: 12.5),
                      ),
                    ),
                  ],
                ),
              ),
            ),

          // Bottom Telemetry HUD & Finish Button
          Positioned(
            bottom: 24,
            left: 24,
            right: 24,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                if (_latestTelemetry != null)
                  Container(
                    padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    margin: const EdgeInsets.only(bottom: 14),
                    decoration: BoxDecoration(
                      color: Colors.white.withOpacity(0.94),
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withOpacity(0.06), blurRadius: 10, offset: const Offset(0, 3)),
                      ],
                    ),
                    child: Row(
                      mainAxisAlignment: MainAxisAlignment.spaceAround,
                      children: [
                        _buildAppleHudBadge(
                          'Gaze',
                          _latestTelemetry!.gaze?.direction.toUpperCase() ?? 'CENTER',
                          _latestTelemetry!.conditions['gaze_away'] == true ? const Color(0xFFD97706) : const Color(0xFF059669),
                        ),
                        _buildAppleHudBadge(
                          'Head Pose',
                          _latestTelemetry!.headPose?.yaw != null
                              ? 'Yaw: ${_latestTelemetry!.headPose!.yaw!.toStringAsFixed(1)}°'
                              : '0.0°',
                          _latestTelemetry!.conditions['head_turned'] == true ? const Color(0xFFD97706) : const Color(0xFF0F172A),
                        ),
                        _buildAppleHudBadge(
                          'Integrity',
                          _latestTelemetry!.conditions.values.any((v) => v) ? 'FLAGGED' : 'COMPLIANT',
                          _latestTelemetry!.conditions.values.any((v) => v) ? const Color(0xFFDC2626) : const Color(0xFF059669),
                        ),
                      ],
                    ),
                  ),

                // Finish Exam Button
                SizedBox(
                  width: double.infinity,
                  height: 50,
                  child: ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                      foregroundColor: Colors.white,
                      elevation: 2,
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                    ),
                    icon: const Icon(Icons.check_circle_outline, size: 20),
                    label: const Text('FINISH EXAM & VIEW AUDIT REPORT', style: TextStyle(fontWeight: FontWeight.w700, letterSpacing: 0.3)),
                    onPressed: _finalizeAndFinishExam,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildAppleHudBadge(String label, String value, Color valueColor) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(label, style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5, fontWeight: FontWeight.w500)),
        const SizedBox(height: 2),
        Text(value, style: TextStyle(color: valueColor, fontWeight: FontWeight.w700, fontSize: 12.5)),
      ],
    );
  }
}
