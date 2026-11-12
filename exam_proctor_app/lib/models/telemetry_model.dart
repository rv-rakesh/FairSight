class TelemetryResult {
  final int faceCount;
  final int personCount;
  final int meshFaceCount;
  final Map<String, bool> conditions;
  final Map<String, String> details;
  final GazeData? gaze;
  final HeadPoseData? headPose;
  final List<dynamic> auxiliaryPersons;

  TelemetryResult({
    required this.faceCount,
    required this.personCount,
    required this.meshFaceCount,
    required this.conditions,
    required this.details,
    this.gaze,
    this.headPose,
    required this.auxiliaryPersons,
  });

  factory TelemetryResult.fromJson(Map<String, dynamic> json) {
    Map<String, bool> conds = {};
    if (json['conditions'] != null) {
      json['conditions'].forEach((k, v) {
        conds[k] = v == true;
      });
    }

    Map<String, String> dets = {};
    if (json['details'] != null) {
      json['details'].forEach((k, v) {
        dets[k] = v.toString();
      });
    }

    return TelemetryResult(
      faceCount: json['face_count'] ?? 0,
      personCount: json['person_count'] ?? 0,
      meshFaceCount: json['mesh_face_count'] ?? 0,
      conditions: conds,
      details: dets,
      gaze: json['gaze'] != null ? GazeData.fromJson(json['gaze']) : null,
      headPose: json['head_pose'] != null ? HeadPoseData.fromJson(json['head_pose']) : null,
      auxiliaryPersons: json['auxiliary_persons'] ?? [],
    );
  }
}

class GazeData {
  final double horizontalRatio;
  final double verticalRatio;
  final String direction;

  GazeData({
    required this.horizontalRatio,
    required this.verticalRatio,
    required this.direction,
  });

  factory GazeData.fromJson(Map<String, dynamic> json) {
    return GazeData(
      horizontalRatio: (json['horizontal_ratio'] as num?)?.toDouble() ?? 0.5,
      verticalRatio: (json['vertical_ratio'] as num?)?.toDouble() ?? 0.5,
      direction: json['direction'] ?? 'center',
    );
  }
}

class HeadPoseData {
  final double? yaw;
  final double? pitch;
  final double? roll;
  final bool flag;

  HeadPoseData({
    this.yaw,
    this.pitch,
    this.roll,
    required this.flag,
  });

  factory HeadPoseData.fromJson(Map<String, dynamic> json) {
    return HeadPoseData(
      yaw: (json['yaw'] as num?)?.toDouble(),
      pitch: (json['pitch'] as num?)?.toDouble(),
      roll: (json['roll'] as num?)?.toDouble(),
      flag: json['flag'] == true,
    );
  }
}

class ExamViolationEvent {
  final String type;
  final double startSec;
  final double endSec;
  final double durationSec;
  final int weight;
  final String note;

  ExamViolationEvent({
    required this.type,
    required this.startSec,
    required this.endSec,
    required this.durationSec,
    required this.weight,
    required this.note,
  });

  factory ExamViolationEvent.fromJson(Map<String, dynamic> json) {
    return ExamViolationEvent(
      type: json['type'] ?? 'unknown',
      startSec: (json['start_sec'] as num?)?.toDouble() ?? 0.0,
      endSec: (json['end_sec'] as num?)?.toDouble() ?? 0.0,
      durationSec: (json['duration_sec'] as num?)?.toDouble() ?? 0.0,
      weight: json['weight'] ?? 0,
      note: json['note'] ?? '',
    );
  }
}

class ExamAuditReport {
  final String sessionId;
  final double durationSec;
  final int riskScore;
  final String riskLevel;
  final int normalizedScore;
  final String normalizedRiskLevel;
  final List<dynamic> windowAnalysis;
  final List<ExamViolationEvent> events;
  final List<dynamic> activityLog;

  ExamAuditReport({
    required this.sessionId,
    required this.durationSec,
    required this.riskScore,
    required this.riskLevel,
    required this.normalizedScore,
    required this.normalizedRiskLevel,
    required this.windowAnalysis,
    required this.events,
    required this.activityLog,
  });

  factory ExamAuditReport.fromJson(Map<String, dynamic> json) {
    List<ExamViolationEvent> evs = [];
    if (json['events'] != null) {
      for (var e in json['events']) {
        evs.add(ExamViolationEvent.fromJson(e));
      }
    }
    return ExamAuditReport(
      sessionId: json['session_id'] ?? 'VIDEO_ANALYSIS',
      durationSec: (json['duration_sec'] as num?)?.toDouble() ?? (json['video_duration_sec'] as num?)?.toDouble() ?? 0.0,
      riskScore: json['risk_score'] ?? 0,
      riskLevel: json['risk_level'] ?? 'Low',
      normalizedScore: json['normalized_score'] ?? json['risk_score'] ?? 0,
      normalizedRiskLevel: json['normalized_risk_level'] ?? json['risk_level'] ?? 'Low',
      windowAnalysis: json['window_analysis'] ?? [],
      events: evs,
      activityLog: json['activity_log'] ?? [],
    );
  }
}
