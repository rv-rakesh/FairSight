import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/telemetry_model.dart';

class ApiService {
  // Default URL: If running on Windows desktop, 127.0.0.1 works directly.
  // If running on an Android emulator, 10.0.2.2 routes to the host machine.
  // If running on a physical phone on Wi-Fi, change to your PC's LAN IP (e.g. http://192.168.1.50:8000).
  static const String defaultLocalhost = "http://127.0.0.1:8000";
  static const String defaultEmulator = "http://10.0.2.2:8000";

  static String baseUrl = defaultLocalhost;

  static void setBaseUrl(String url) {
    baseUrl = url.trim().replaceAll(RegExp(r'/+$'), '');
  }

  static Future<bool> checkHealth() async {
    try {
      final res = await http.get(Uri.parse('$baseUrl/health')).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (_) {
      return false;
    }
  }

  static Future<TelemetryResult?> detectFrame(String base64Image, int timestampMs) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/detect-frame'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image_base64': base64Image,
          'timestamp_ms': timestampMs,
        }),
      ).timeout(const Duration(seconds: 5));

      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return TelemetryResult.fromJson(data);
      }
    } catch (e) {
      debugPrint("detectFrame error: $e");
    }
    return null;
  }

  static Future<String?> startSession() async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/session/start')).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        final data = jsonDecode(res.body);
        return data['session_id'];
      }
    } catch (e) {
      debugPrint("startSession error: $e");
    }
    return null;
  }

  static Future<Map<String, dynamic>?> sendSessionFrame(String sessionId, String base64Image, double timestampSec) async {
    try {
      final res = await http.post(
        Uri.parse('$baseUrl/api/session/$sessionId/frame'),
        headers: {'Content-Type': 'application/json'},
        body: jsonEncode({
          'image_base64': base64Image,
          'timestamp_sec': timestampSec,
        }),
      ).timeout(const Duration(seconds: 5));
      if (res.statusCode == 200) {
        return jsonDecode(res.body);
      }
    } catch (e) {
      debugPrint("sendSessionFrame error: $e");
    }
    return null;
  }

  static Future<ExamAuditReport?> finalizeSession(String sessionId) async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/session/$sessionId/finalize')).timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        return ExamAuditReport.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint("finalizeSession error: $e");
    }
    return null;
  }

  static Future<ExamAuditReport?> uploadAndAnalyzeVideo(File videoFile) async {
    try {
      var request = http.MultipartRequest('POST', Uri.parse('$baseUrl/api/analyze-video'));
      request.files.add(await http.MultipartFile.fromPath('file', videoFile.path));

      // Allow adequate time for video upload & MediaPipe 4 FPS CPU processing (up to 120s)
      var streamedResponse = await request.send().timeout(const Duration(seconds: 120));
      var response = await http.Response.fromStream(streamedResponse);

      if (response.statusCode == 200) {
        final Map<String, dynamic> data = jsonDecode(response.body);
        return ExamAuditReport.fromJson(data);
      } else {
        debugPrint("uploadAndAnalyzeVideo server responded with: ${response.statusCode} - ${response.body}");
      }
    } catch (e) {
      debugPrint("uploadAndAnalyzeVideo error: $e");
      rethrow;
    }
    return null;
  }

  static Future<ExamAuditReport?> runScenario(String scenarioKey) async {
    try {
      final res = await http.post(Uri.parse('$baseUrl/api/scenarios/$scenarioKey/run')).timeout(const Duration(seconds: 10));
      if (res.statusCode == 200) {
        return ExamAuditReport.fromJson(jsonDecode(res.body));
      }
    } catch (e) {
      debugPrint("runScenario error: $e");
    }
    return null;
  }
}
