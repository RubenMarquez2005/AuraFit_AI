import 'package:flutter_test/flutter_test.dart';

import 'package:aurafit_frontend/main.dart';

void main() {
  testWidgets('AuraFit app loads main shell', (WidgetTester tester) async {
    await tester.pumpWidget(const AuraFitApp());

    expect(find.textContaining('AuraFit AI'), findsWidgets);
  });
}
