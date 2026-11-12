import 'dart:io';
import 'package:flutter/material.dart';
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
        });
      }
    } catch (e) {
      _showError("Error accessing gallery: $e");
    }
  }

  Future<void> _pickFromFileStorage() async {
    try {
      final result = await FilePicker.platform.pickFiles(
        type: FileType.video,
        allowMultiple: false,
      );

      if (result != null && result.files.single.path != null) {
        final file = File(result.files.single.path!);
        setState(() {
          _selectedFile = file;
          _fileName = result.files.single.name;
          _fileSizeBytes = file.lengthSync();
          _statusText = "Video selected from Storage";
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
        });
      }
    } catch (e) {
      _showError("Error accessing camera: $e");
    }
  }

  void _showPickerOptions() {
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
                subtitle: const Text('Choose .mp4 or .webm from storage', style: TextStyle(fontSize: 12, color: Color(0xFF64748B))),
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
            MaterialPageRoute(builder: (_) => ReportScreen(report: report)),
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

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: const Text('Upload & Audit Video'),
      ),
      body: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 520),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                // Clean Apple Card Dropzone
                GestureDetector(
                  onTap: _isAnalyzing ? null : _showPickerOptions,
                  child: Container(
                    padding: const EdgeInsets.symmetric(vertical: 36, horizontal: 24),
                    decoration: BoxDecoration(
                      color: Colors.white,
                      borderRadius: BorderRadius.circular(20),
                      border: Border.all(
                        color: _selectedFile != null ? const Color(0xFF2563EB) : const Color(0xFFE2E8F0),
                        width: _selectedFile != null ? 1.5 : 1,
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: Colors.black.withOpacity(0.02),
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
                        const SizedBox(height: 18),
                        Text(
                          _selectedFile != null ? _fileName! : 'Select Exam Video Recording',
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
                              ? '${(_fileSizeBytes / (1024 * 1024)).toStringAsFixed(2)} MB • Ready for Forensic Audit'
                              : 'Tap to choose from Gallery, Files, or Camera',
                          style: const TextStyle(fontSize: 13, color: Color(0xFF64748B)),
                          textAlign: TextAlign.center,
                        ),
                        const SizedBox(height: 20),
                        OutlinedButton.icon(
                          style: OutlinedButton.styleFrom(
                            foregroundColor: const Color(0xFF0F172A),
                            side: const BorderSide(color: Color(0xFFCBD5E1)),
                            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
                            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
                          ),
                          onPressed: _isAnalyzing ? null : _showPickerOptions,
                          icon: const Icon(Icons.add_photo_alternate_outlined, size: 16),
                          label: Text(_selectedFile != null ? 'Change Video' : 'Browse Videos', style: const TextStyle(fontSize: 13)),
                        ),
                      ],
                    ),
                  ),
                ),

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
                      shadowColor: const Color(0xFF2563EB).withOpacity(0.3),
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
