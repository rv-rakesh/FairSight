import 'package:flutter_test/flutter_test.dart';
import 'package:exam_proctor_app/models/telemetry_model.dart';

void main() {
  group('Telemetry Model Unit Tests', () {
    test('TelemetryResult correctly parses from JSON', () {
      final json = {
        'face_count': 1,
        'person_count': 1,
        'mesh_face_count': 1,
        'conditions': {
          'gaze_away': false,
          'head_turned': true,
          'no_face': false,
          'multiple_faces': false,
        },
        'details': {
          'head_turned': 'turned right (yaw -31.2 deg)',
        },
        'gaze': {
          'horizontal_ratio': 0.48,
          'vertical_ratio': 0.52,
          'direction': 'center',
        },
        'head_pose': {
          'yaw': -31.2,
          'pitch': 11.5,
          'roll': 2.1,
          'flag': true,
        },
        'auxiliary_persons': [],
      };

      final result = TelemetryResult.fromJson(json);

      expect(result.faceCount, 1);
      expect(result.personCount, 1);
      expect(result.conditions['head_turned'], true);
      expect(result.conditions['gaze_away'], false);
      expect(result.details['head_turned'], 'turned right (yaw -31.2 deg)');
      expect(result.gaze?.direction, 'center');
      expect(result.headPose?.yaw, -31.2);
      expect(result.headPose?.flag, true);
    });

    test('ExamAuditReport parses dual score and normalized metrics', () {
      final json = {
        'session_id': 'TEST_SESSION_001',
        'duration_sec': 600.0,
        'risk_score': 60,
        'risk_level': 'High',
        'normalized_score': 32,
        'normalized_risk_level': 'Medium',
        'window_analysis': [
          {'window_index': 0, 'window_score': 24}
        ],
        'events': [
          {
            'type': 'gaze_away',
            'start_sec': 10.0,
            'end_sec': 12.0,
            'duration_sec': 2.0,
            'weight': 12,
            'note': 'sustained',
          }
        ],
        'activity_log': [
          {'time_sec': 10.0, 'type': 'gaze_away', 'detail': 'looking left'}
        ],
        'frames_analysed': 240,
      };

      final report = ExamAuditReport.fromJson(json);

      expect(report.sessionId, 'TEST_SESSION_001');
      expect(report.durationSec, 600.0);
      expect(report.riskScore, 60);
      expect(report.riskLevel, 'High');
      expect(report.normalizedScore, 32);
      expect(report.normalizedRiskLevel, 'Medium');
      expect(report.windowAnalysis.length, 1);
      expect(report.events.length, 1);
      expect(report.events[0].type, 'gaze_away');
      expect(report.events[0].weight, 12);
      expect(report.activityLog.length, 1);
      expect(report.framesAnalysed, 240);
    });

    test('ExamAuditReport falls back cleanly if normalized fields are absent', () {
      final legacyJson = {
        'session_id': 'LEGACY_SESSION_002',
        'duration_sec': 30.0,
        'risk_score': 27,
        'risk_level': 'Low',
        'events': [],
        'activity_log': [],
      };

      final report = ExamAuditReport.fromJson(legacyJson);

      expect(report.riskScore, 27);
      expect(report.riskLevel, 'Low');
      expect(report.normalizedScore, 27); // falls back to riskScore
      expect(report.normalizedRiskLevel, 'Low'); // falls back to riskLevel
      expect(report.windowAnalysis, isEmpty);
    });
  });
}
