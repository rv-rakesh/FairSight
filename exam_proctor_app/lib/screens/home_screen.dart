import 'package:material_ui/material_ui.dart';
import '../services/api_service.dart';
import 'live_proctor_screen.dart';
import 'video_audit_screen.dart';
import 'report_screen.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  bool _isServerOnline = false;
  bool _isChecking = true;

  @override
  void initState() {
    super.initState();
    _checkServer();
  }

  Future<void> _checkServer() async {
    setState(() => _isChecking = true);
    final online = await ApiService.checkHealth();
    if (mounted) {
      setState(() {
        _isServerOnline = online;
        _isChecking = false;
      });
    }
  }

  void _showServerSettingsDialog() {
    final controller = TextEditingController(text: ApiService.baseUrl);
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        backgroundColor: Colors.white,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text(
          'Engine Connection',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 17, color: Color(0xFF0F172A)),
        ),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Configure the AI proctoring backend IP.\n• Laptop PC: http://127.0.0.1:8000\n• Mobile Wi-Fi: http://<PC-LAN-IP>:8000',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B), height: 1.4),
            ),
            const SizedBox(height: 14),
            TextField(
              controller: controller,
              style: const TextStyle(fontSize: 14, fontWeight: FontWeight.w500),
              decoration: InputDecoration(
                filled: true,
                fillColor: const Color(0xFFF8FAFC),
                border: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                ),
                enabledBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFFE2E8F0)),
                ),
                focusedBorder: OutlineInputBorder(
                  borderRadius: BorderRadius.circular(12),
                  borderSide: const BorderSide(color: Color(0xFF2563EB), width: 1.5),
                ),
                labelText: 'Backend URL',
                prefixIcon: const Icon(Icons.dns_outlined, size: 20, color: Color(0xFF64748B)),
              ),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text('Cancel', style: TextStyle(color: Color(0xFF64748B))),
          ),
          ElevatedButton(
            onPressed: () {
              ApiService.setBaseUrl(controller.text);
              Navigator.pop(ctx);
              _checkServer();
            },
            child: const Text('Connect'),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isMobile = MediaQuery.of(context).size.width < 600;

    return Scaffold(
      backgroundColor: const Color(0xFFF8FAFC),
      appBar: AppBar(
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(7),
              decoration: BoxDecoration(
                color: const Color(0xFFEFF6FF),
                borderRadius: BorderRadius.circular(10),
                border: Border.all(color: const Color(0xFFDBEAFE)),
              ),
              child: const Icon(Icons.shield_outlined, color: Color(0xFF2563EB), size: 20),
            ),
            const SizedBox(width: 12),
            const Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Exam Proctor AI',
                  style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16, color: Color(0xFF0F172A), letterSpacing: -0.3),
                ),
                Text(
                  'Assessment Integrity Platform',
                  style: TextStyle(fontSize: 11, fontWeight: FontWeight.w500, color: Color(0xFF64748B)),
                ),
              ],
            ),
          ],
        ),
        actions: [
          IconButton(
            tooltip: 'Server Settings',
            icon: const Icon(Icons.tune_rounded, size: 20, color: Color(0xFF64748B)),
            onPressed: _showServerSettingsDialog,
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: SingleChildScrollView(
        padding: EdgeInsets.symmetric(
          horizontal: isMobile ? 18 : 36,
          vertical: 20,
        ),
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 680),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                // Minimalist Connection Pill Card
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                  decoration: BoxDecoration(
                    color: Colors.white,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFFE2E8F0)),
                    boxShadow: [
                      BoxShadow(color: Colors.black.withValues(alpha: 0.02), blurRadius: 6, offset: const Offset(0, 2)),
                    ],
                  ),
                  child: Row(
                    children: [
                      Container(
                        width: 8,
                        height: 8,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          color: _isServerOnline ? const Color(0xFF10B981) : const Color(0xFFEF4444),
                        ),
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          _isChecking
                              ? 'Connecting to AI proctoring engine...'
                              : _isServerOnline
                                  ? 'Engine Connected: ${ApiService.baseUrl}'
                                  : 'Engine Offline (${ApiService.baseUrl})',
                          style: TextStyle(
                            fontSize: 12.5,
                            fontWeight: FontWeight.w600,
                            color: _isServerOnline ? const Color(0xFF0F172A) : const Color(0xFFDC2626),
                          ),
                          overflow: TextOverflow.ellipsis,
                        ),
                      ),
                      GestureDetector(
                        onTap: _checkServer,
                        child: Container(
                          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                          decoration: BoxDecoration(
                            color: const Color(0xFFF1F5F9),
                            borderRadius: BorderRadius.circular(8),
                          ),
                          child: const Text('Refresh', style: TextStyle(fontSize: 11, fontWeight: FontWeight.w600, color: Color(0xFF475569))),
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 28),

                // Section Title
                const Text(
                  'Choose Proctoring Mode',
                  style: TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: Color(0xFF0F172A), letterSpacing: -0.4),
                ),
                const SizedBox(height: 4),
                const Text(
                  'Monitor a candidate live via camera or upload an existing video recording for forensic AI analysis.',
                  style: TextStyle(fontSize: 13, color: Color(0xFF64748B), height: 1.35),
                ),
                const SizedBox(height: 18),

                // Card 1: Video File Audit (Primary on Mobile)
                _buildAppleCard(
                  title: 'Upload Examination Video File',
                  subtitle: 'Select an exam recording from phone gallery or files. Detects head turns, off-screen gaze, and reaching hands at 4 FPS.',
                  icon: Icons.video_file_outlined,
                  iconTint: const Color(0xFF2563EB),
                  iconBg: const Color(0xFFEFF6FF),
                  badge: 'RECOMMENDED',
                  badgeBg: const Color(0xFFEFF6FF),
                  badgeColor: const Color(0xFF2563EB),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const VideoAuditScreen()),
                    );
                  },
                ),

                const SizedBox(height: 14),

                // Card 2: Live Camera Proctoring Studio
                _buildAppleCard(
                  title: 'Live Camera Proctoring Studio',
                  subtitle: 'Use front selfie camera or webcam for live real-time proctoring with HUD telemetry overlay and violation warnings.',
                  icon: Icons.videocam_outlined,
                  iconTint: const Color(0xFF059669),
                  iconBg: const Color(0xFFECFDF5),
                  badge: 'REAL-TIME HUD',
                  badgeBg: const Color(0xFFECFDF5),
                  badgeColor: const Color(0xFF059669),
                  onTap: () {
                    Navigator.push(
                      context,
                      MaterialPageRoute(builder: (_) => const LiveProctorScreen()),
                    );
                  },
                ),

                const SizedBox(height: 14),

                // Card 3: Academic Scenarios Benchmark
                _buildAppleCard(
                  title: 'Academic Scenarios Benchmark',
                  subtitle: 'Pre-loaded verified ground truth sessions: Honest Candidate (0 pts), Screen Peeking (30 pts), or Unauthorized Person (60+ pts).',
                  icon: Icons.biotech_outlined,
                  iconTint: const Color(0xFF7C3AED),
                  iconBg: const Color(0xFFF5F3FF),
                  badge: 'DEMO DATA',
                  badgeBg: const Color(0xFFF5F3FF),
                  badgeColor: const Color(0xFF7C3AED),
                  onTap: () => _showScenarioDialog(context),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildAppleCard({
    required String title,
    required String subtitle,
    required IconData icon,
    required Color iconTint,
    required Color iconBg,
    required String badge,
    required Color badgeBg,
    required Color badgeColor,
    required VoidCallback onTap,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: const Color(0xFFE2E8F0)),
        boxShadow: [
          BoxShadow(
            color: Colors.black.withValues(alpha: 0.02),
            blurRadius: 8,
            offset: const Offset(0, 2),
          ),
        ],
      ),
      child: Material(
        color: Colors.transparent,
        borderRadius: BorderRadius.circular(16),
        child: InkWell(
          borderRadius: BorderRadius.circular(16),
          onTap: onTap,
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Container(
                  width: 48,
                  height: 48,
                  decoration: BoxDecoration(
                    color: iconBg,
                    borderRadius: BorderRadius.circular(14),
                  ),
                  child: Icon(icon, color: iconTint, size: 24),
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Expanded(
                            child: Text(
                              title,
                              style: const TextStyle(
                                fontSize: 15,
                                fontWeight: FontWeight.w700,
                                color: Color(0xFF0F172A),
                                letterSpacing: -0.3,
                              ),
                            ),
                          ),
                          Container(
                            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2.5),
                            decoration: BoxDecoration(
                              color: badgeBg,
                              borderRadius: BorderRadius.circular(6),
                            ),
                            child: Text(
                              badge,
                              style: TextStyle(
                                fontSize: 9.5,
                                fontWeight: FontWeight.w700,
                                color: badgeColor,
                                letterSpacing: 0.3,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 6),
                      Text(
                        subtitle,
                        style: const TextStyle(fontSize: 12.5, color: Color(0xFF64748B), height: 1.35),
                      ),
                    ],
                  ),
                ),
                const SizedBox(width: 8),
                const Padding(
                  padding: EdgeInsets.only(top: 14),
                  child: Icon(Icons.arrow_forward_ios_rounded, size: 14, color: Color(0xFF94A3B8)),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  void _showScenarioDialog(BuildContext context) {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.white,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(22)),
      ),
      builder: (ctx) => Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text(
              'Select Academic Benchmark',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700, color: Color(0xFF0F172A)),
            ),
            const SizedBox(height: 4),
            const Text(
              'Pre-calibrated test ground truth for evaluator validation.',
              style: TextStyle(fontSize: 12.5, color: Color(0xFF64748B)),
            ),
            const SizedBox(height: 16),
            _buildScenarioItem(
              context,
              'Honest Candidate (Clean)',
              'Zero malpractice score. Normal reading & thinking.',
              'honest_candidate',
              const Color(0xFF059669),
            ),
            _buildScenarioItem(
              context,
              'Screen Peeking (Desk Notes)',
              'Repeated rapid glances. Score: 30+ (Medium Risk).',
              'screen_peeking',
              const Color(0xFFD97706),
            ),
            _buildScenarioItem(
              context,
              'Unauthorized Person (Collusion)',
              'Accomplice enters frame. Score: 60+ (High Risk).',
              'unauthorized_person',
              const Color(0xFFDC2626),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildScenarioItem(BuildContext context, String title, String desc, String key, Color color) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: const Color(0xFFF8FAFC),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: const Color(0xFFE2E8F0)),
      ),
      child: ListTile(
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        leading: Container(
          width: 10,
          height: 10,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13.5)),
        subtitle: Text(desc, style: const TextStyle(fontSize: 11.5, color: Color(0xFF64748B))),
        trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 12, color: Color(0xFF94A3B8)),
        onTap: () => _executeScenario(context, key),
      ),
    );
  }

  Future<void> _executeScenario(BuildContext context, String key) async {
    Navigator.pop(context);
    showDialog(
      context: context,
      barrierDismissible: false,
      builder: (_) => const Center(
        child: Card(
          child: Padding(
            padding: EdgeInsets.all(20),
            child: CircularProgressIndicator(),
          ),
        ),
      ),
    );

    final report = await ApiService.runScenario(key);
    if (context.mounted) {
      Navigator.pop(context);
      if (report != null) {
        Navigator.push(
          context,
          MaterialPageRoute(builder: (_) => ReportScreen(report: report)),
        );
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('Backend unreachable. Start the FastAPI server or check Server Settings.'),
            backgroundColor: Color(0xFFDC2626),
          ),
        );
      }
    }
  }
}
