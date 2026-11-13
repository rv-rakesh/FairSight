import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:material_ui/material_ui.dart';
import 'package:file_picker/file_picker.dart';
import 'package:image_picker/image_picker.dart';
import '../services/api_service.dart';
import 'report_screen.dart';

class VideoAuditScreen extends StatefulWidget {
  const VideoAuditScreen({super.key});

  @override
  State<VideoAuditScreen> createState() => _VideoAuditScreenState();
}

class _VideoAuditScreenState extends State<VideoAuditScreen> {
  File? _selectedFile;
  String? _fileName;
  int _fileSizeBytes = 0;
  bool _isAnalyzing = false;
  String _statusText = "Ready to analyze";
  final ImagePicker _imagePicker = ImagePicker();

  // Selected video preview / player state
  bool _isPlayingPreview = false;
  double _previewProgress = 0.0; // 0.0 to 1.0

  Future<void> _pickFromGallery() async {
    try {
      final XFile? video = await _imagePicker.pickVideo(source: ImageSource.gallery);
      if (video != null) {
        final file = File(video.path);
        setState(() {
          _selectedFile = file;
          _fileName = video.name;
          _fileSizeBytes = file.lengthSync();
          _statusText = "Video selected from Gallery";
          _previewProgress = 0.0;
        });
      }
    } catch (e) {
      _showError("Error accessing gallery: $e");
    }
  }

  Future<void> _pickFromFileStorage() async {
    try {
      final picked = await FilePicker.pickFile(type: FileType.video);

      if (picked != null && picked.path != null) {
        final file = File(picked.path!);
        setState(() {
          _selectedFile = file;
          _fileName = picked.name;
          _fileSizeBytes = file.lengthSync();
          _statusText = "Video selected from Storage";
          _previewProgress = 0.0;
        });
      }
    } catch (e) {
      _showError("Error selecting file: $e");
    }
  }

  Future<void> _recordVideo() async {
    try {
      final XFile? video = await _imagePicker.pickVideo(
        source: ImageSource.camera,
        maxDuration: const Duration(minutes: 5),
      );
      if (video != null) {
        final file = File(video.path);
        setState(() {
          _selectedFile = file;
          _fileName = video.name;
          _fileSizeBytes = file.lengthSync();
          _statusText = "Recorded exam video";
          _previewProgress = 0.0;
        });
      }
    } catch (e) {
      _showError("Error accessing camera: $e");
    }
  }

  void _showPickerOptions() {
    final bool isDesktop = defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.linux ||
        defaultTargetPlatform == TargetPlatform.macOS;

    // On Windows desktop, bypass phone camera and open native file dialog directly
    if (isDesktop) {
      _pickFromFileStorage();
      return;
    }

    // On Mobile (Android / iOS): show appropriate source options
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 20, horizontal: 16),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const Padding(
                padding: EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                child: Text(
                  'Select Video Source',
                  style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: Color(0xFF0F172A), letterSpacing: -0.3),
                ),
              ),
              const Divider(color: Color(0xFFE2E8F0)),
              ListTile(
                leading: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: const Color(0xFFEFF6FF), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.photo_library_outlined, color: Color(0xFF2563EB), size: 20),
                ),
                title: const Text('Phone Gallery / Photos', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                subtitle: const Text('Select existing exam video recording', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                onTap: () {
                  Navigator.pop(ctx);
                  _pickFromGallery();
                },
              ),
              ListTile(
                leading: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: const Color(0xFFECFDF5), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.folder_open_outlined, color: Color(0xFF059669), size: 20),
                ),
                title: const Text('Files & Downloads', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                subtitle: const Text('Choose .mp4, .webm or .mkv from storage', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                onTap: () {
                  Navigator.pop(ctx);
                  _pickFromFileStorage();
                },
              ),
              ListTile(
                leading: Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(color: const Color(0xFFF5F3FF), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.videocam_outlined, color: Color(0xFF7C3AED), size: 20),
                ),
                title: const Text('Record with Phone Camera', style: TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
                subtitle: const Text('Capture live session now', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
                onTap: () {
                  Navigator.pop(ctx);
                  _recordVideo();
                },
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _runVideoAnalysis() async {
    if (_selectedFile == null) return;

    setState(() {
      _isAnalyzing = true;
      _statusText = "Streaming video to AI engine...";
    });

    try {
      final report = await ApiService.uploadAndAnalyzeVideo(_selectedFile!);
      if (mounted) {
        setState(() => _isAnalyzing = false);
        if (report != null) {
          Navigator.pushReplacement(
            context,
            MaterialPageRoute(
              builder: (_) => ReportScreen(
                report: report,
                videoFile: _selectedFile,
                videoPath: _selectedFile?.path,
              ),
            ),
          );
        } else {
          _showError("Analysis failed. Verify your connection to the AI backend.");
        }
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isAnalyzing = false);
        _showError("Error: $e");
      }
    }
  }

  void _showError(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: const Color(0xFFDC2626),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  String _formatFileSize(int bytes) {
    if (bytes >= 1024 * 1024) {
      return '${(bytes / (1024 * 1024)).toStringAsFixed(2)} MB';
    }
    return '${(bytes / 1024).toStringAsFixed(1)} KB';
  }

  @override
  Widget build(BuildContext context) {
    final bool isDesktop = defaultTargetPlatform == TargetPlatform.windows ||
        defaultTargetPlatform == TargetPlatform.linux ||
        defaultTargetPlatform == TargetPlatform.macOS;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Upload & Audit Video'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 540),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Clean Apple Card Dropzone
                GestureDetector(
                  onTap: _isAnalyzing ? null : _showPickerOptions,
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 28, horizontal: 24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _selectedFile != null ? const Color(0xFF2563EB) : const Color(0xFFE2E8F0),
                        width: _selectedFile != null ? 1.5 : 1,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withValues(alpha: 0.02),
                          blurRadius: 10,
                          offset: const Offset(0, 4),
                        ),
                      ],
                    ),
                    child: Column(
                      children: [
                        Container(
                          width: 64,
                          height: 64,
                          decoration: BoxDecoration(
                            color: _selectedFile != null ? const Color(0xFFEFF6FF) : const Color(0xFFF8FAFC),
                            shape: BoxShape.circle,
                            border: Border.all(color: _selectedFile != null ? const Color(0xFFDBEAFE) : const Color(0xFFE2E8F0)),
                          ),
                          child: Icon(
                            _selectedFile != null ? Icons.movie_outlined : Icons.cloud_upload_outlined,
                            size: 28,
                            color: _selectedFile != null ? const Color(0xFF2563EB) : const Color(0xFF64748B),
                          ),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _selectedFile != null ? _fileName! : (isDesktop ? 'Choose Video File from Computer' : 'Select Exam Video Recording'),
                          style: const TextStyle(
                            fontWeight: FontWeight.w700,
                            fontSize: 16,
                            color: Color(0xFF0F172A),
                            letterSpacing: -0.3,
                          ),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 6),
                        Text(
                          _selectedFile != null
                              ? '${_formatFileSize(_fileSizeBytes)} • Ready for Forensic Audit'
                              : (isDesktop ? 'Click to open file browser (.mp4, .webm, .mkv, .avi)' : 'Tap to choose from Gallery, Files, or Camera'),
                          style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 18),
                        Wrap(
                          spacing: 10,
                          children: [
                            OutlinedButton.icon(
                              style: OutlinedButton.styleFrom(
                                foregroundColor: const Color(0xFF0F172A),
                                side: const BorderSide(color: Color(0xFFCBD5E1)),
                                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                              ),
                              onPressed: _isAnalyzing ? null : _showPickerOptions,
                              icon: Icon(_selectedFile != null ? Icons.folder_open : Icons.add_photo_alternate_outlined, size: 16),
                              label: Text(_selectedFile != null ? 'Change Video' : (isDesktop ? 'Browse File System' : 'Browse Videos'), style: const TextStyle(fontSize: 13)),
                            ),
                            if (_selectedFile != null)
                              TextButton.icon(
                                style: TextButton.styleFrom(
                                  foregroundColor: const Color(0xFFDC2626),
                                  shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                                  padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
                                ),
                                onPressed: _isAnalyzing
                                    ? null
                                    : () {
                                        setState(() {
                                          _selectedFile = null;
                                          _fileName = null;
                                          _fileSizeBytes = 0;
                                          _statusText = "Ready to analyze";
                                        });
                                      },
                                icon: const Icon(Icons.close, size: 16),
                                label: const Text('Clear', style: TextStyle(fontSize: 13)),
                              ),
                          ],
                        ),
                      ],
                    ),
                  ),
                ),

                // Selected Video Inspector & Playback Preview Card
                if (_selectedFile != null) ...[
                  const SizedBox(height: 16),
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                      boxShadow: [
                        BoxShadow(color: Colors.black.withValues(alpha: 0.015), blurRadius: 6, offset: const Offset(0, 2)),
                      ],
                    ),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Row(
                          children: [
                            const Icon(Icons.play_circle_outline, color: Color(0xFF2563EB), size: 20),
                            const SizedBox(width: 8),
                            const Text(
                              'Selected Video Preview & Inspector',
                              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13.5, color: Color(0xFF0F172A)),
                            ),
                            const Spacer(),
                            Container(
                              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
                              decoration: BoxDecoration(
                                color: const Color(0xFFEFF6FF),
                                borderRadius: BorderRadius.circular(6),
                              ),
                              child: Text(
                                _fileName != null ? _fileName!.split('.').last.toUpperCase() : 'MP4',
                                style: const TextStyle(color: Color(0xFF2563EB), fontSize: 10.5, fontWeight: FontWeight.w700),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(height: 12),
                        // Interactive Video Player / Scrubber Preview Bar
                        Container(
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: const Color(0xFF0F172A),
                            borderRadius: BorderRadius.circular(10),
                          ),
                          child: Column(
                            children: [
                              Row(
                                children: [
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(),
                                    icon: Icon(
                                      _isPlayingPreview ? Icons.pause_circle_filled : Icons.play_circle_filled,
                                      color: Colors.white,
                                      size: 28,
                                    ),
                                    onPressed: () {
                                      setState(() {
                                        _isPlayingPreview = !_isPlayingPreview;
                                      });
                                    },
                                  ),
                                  const SizedBox(width: 10),
                                  Expanded(
                                    child: SliderTheme(
                                      data: SliderTheme.of(context).copyWith(
                                        thumbShape: const RoundSliderThumbShape(enabledThumbRadius: 6),
                                        trackHeight: 3,
                                        activeTrackColor: const Color(0xFF38BDF8),
                                        inactiveTrackColor: const Color(0xFF334155),
                                        thumbColor: Colors.white,
                                      ),
                                      child: Slider(
                                        value: _previewProgress,
                                        min: 0.0,
                                        max: 1.0,
                                        onChanged: (v) {
                                          setState(() => _previewProgress = v);
                                        },
                                      ),
                                    ),
                                  ),
                                  const SizedBox(width: 8),
                                  IconButton(
                                    padding: EdgeInsets.zero,
                                    constraints: const BoxConstraints(),
                                    icon: const Icon(Icons.replay, color: Color(0xFF94A3B8), size: 20),
                                    onPressed: () {
                                      setState(() {
                                        _previewProgress = 0.0;
                                        _isPlayingPreview = false;
                                      });
                                    },
                                  ),
                                ],
                              ),
                              Padding(
                                padding: const EdgeInsets.symmetric(horizontal: 4),
                                child: Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text(
                                      'Position: ${(_previewProgress * 100).toInt()}%',
                                      style: const TextStyle(color: Color(0xFF94A3B8), fontSize: 11),
                                    ),
                                    Text(
                                      'Path: ${_selectedFile!.path.length > 32 ? "...${_selectedFile!.path.substring(_selectedFile!.path.length - 30)}" : _selectedFile!.path}',
                                      style: const TextStyle(color: Color(0xFF64748B), fontSize: 10.5),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ],

                const SizedBox(height: 24),

                // Analysis State / Button
                if (_isAnalyzing)
                  Container(
                    padding: const EdgeInsets.all(22),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(16),
                      border: Border.all(color: const Color(0xFFE2E8F0)),
                    ),
                    child: Column(
                      children: [
                        const SizedBox(
                          width: 32,
                          height: 32,
                          child: CircularProgressIndicator(strokeWidth: 3, color: Color(0xFF2563EB)),
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _statusText,
                          style: const TextStyle(fontWeight: FontWeight.w700, fontSize: 14, color: Color(0xFF0F172A)),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 6),
                        const Text(
                          'MediaPipe Vision extracting 3D head yaw/pitch, iris ratios, multi-person faces, and reaching arms at 4 FPS...',
                          style: TextStyle(fontSize: 12, color: Color(0xFF64748B), height: 1.35),
                          textAlign: TextAlign.center,
                        ),
                      ],
                    ),
                  )
                else
                  ElevatedButton.icon(
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF2563EB),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(14)),
                      shadowColor: const Color(0xFF2563EB).withValues(alpha: 0.3),
                      elevation: _selectedFile != null ? 3 : 0,
                    ),
                    icon: const Icon(Icons.analytics_outlined, size: 20),
                    label: const Text(
                      'START FORENSIC AI AUDIT',
                      style: TextStyle(fontWeight: FontWeight.w700, fontSize: 14.5, letterSpacing: 0.3),
                    ),
                    onPressed: _selectedFile != null ? _runVideoAnalysis : null,
                  ),

                const SizedBox(height: 20),

                // Clean Note Card
                Container(
                  padding: const EdgeInsets.all(14),
                  decoration: BoxDecoration(
                    color: const Color(0xFFEFF6FF),
                    borderRadius: BorderRadius.circular(12),
                    border: Border.all(color: const Color(0xFFDBEAFE)),
                  ),
                  child: const Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Icon(Icons.info_outline, color: Color(0xFF2563EB), size: 18),
                      SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          'The AI pipeline samples 4 frames per second, ensuring brief glances (700ms) and accomplice reaching hands are reliably caught without skipping.',
                          style: TextStyle(fontSize: 12, color: Color(0xFF1E40AF), height: 1.35),
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}


