import 'package:flutter_test/flutter_test.dart';
import 'package:exam_proctor_app/main.dart';

void main() {
  testWidgets('FairSight home screen renders proctoring modes', (WidgetTester tester) async {
    await tester.pumpWidget(const ExamProctorApp());
    // Allow initial health-check HTTP microtask in TestWidgetsFlutterBinding to settle.
    await tester.pump(const Duration(milliseconds: 50));

    expect(find.text('Exam Proctor AI'), findsOneWidget);
    expect(find.text('Choose Proctoring Mode'), findsOneWidget);
    expect(find.text('Upload Examination Video File'), findsOneWidget);
    expect(find.text('Live Camera Proctoring Studio'), findsOneWidget);
    expect(find.text('Academic Scenarios Benchmark'), findsOneWidget);
  });
}
