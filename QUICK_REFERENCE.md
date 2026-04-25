# 📚 QUICK REFERENCE - COMPONENTES NUEVOS

## IMPORTACIONES RÁPIDAS

### Para usar TODO junto (Panel integrado)
```dart
import 'package:aurafit_frontend/pages/panel_profesional_integrado.dart';

// Uso
PanelProfesionalIntegrado(
  rolNombre: 'medico',
  authToken: userToken,
)
```

### Componentes individuales

#### 1. Estadísticas con gráficos
```dart
import 'package:aurafit_frontend/widgets/estadisticas_widget.dart';

// Uso
EstadisticasWidget()
```

#### 2. Dashboard ejecutivo (KPIs)
```dart
import 'package:aurafit_frontend/widgets/dashboard_ejecutivo.dart';

// Uso
DashboardEjecutivo(
  totalPacientes: 24,
  derivacionesPendientes: 3,
  alertasActivas: 1,
  especialidades: [
    {'name': 'Nutricionista', 'pacientes': 8, 'derivaciones': 1, 'alertas': 0},
    {'name': 'Psicólogo', 'pacientes': 10, 'derivaciones': 1, 'alertas': 1},
  ],
  onRefresh: () => _recargarDatos(),
)
```

#### 3. Funciones avanzadas para doctores
```dart
import 'package:aurafit_frontend/widgets/funciones_avanzadas_doctor.dart';

// Uso
FuncionesAvanzadasDoctor(
  pacienteId: 1,
  pacienteNombre: 'Juan García',
  especialidad: 'medico',
)
```

#### 4. Componentes base profesionales
```dart
import 'package:aurafit_frontend/widgets/professional_dashboard_widgets.dart';

// PremiumCard
PremiumCard(
  title: 'Mi tarjeta',
  subtitle: 'Descripción',
  icon: Icons.info,
  iconColor: Colors.blue,
  gradient: const LinearGradient(...),
  child: Text('Contenido'),
)

// MetricCard
MetricCard(
  label: 'Ánimo',
  value: '7.2',
  unit: '/10',
  icon: Icons.sentiment_satisfied,
  color: Colors.blue,
  trend: '↑',
  trendColor: Colors.green,
)

// DerivacionStateCard
DerivacionStateCard(
  paciente: 'Juan García',
  derivadoPor: 'Dr. López',
  estado: 'en_proceso', // pendiente, en_proceso, completado
  especialidad: 'Psicología',
  fecha: DateTime.now(),
  onTap: () {},
)

// EspecialidadDashboard
EspecialidadDashboard(
  especialidad: 'Nutricionista',
  pacientesActivos: 8,
  derivacionesPendientes: 1,
  alertas: 0,
  onTap: () {},
)

// AlertaClinica
AlertaClinica(
  titulo: 'Alerta importante',
  descripcion: 'Algo requiere tu atención',
  tipo: 'critica', // leve, moderada, critica
  icon: Icons.warning,
  actionLabel: 'Ver detalles',
  onAction: () {},
  onDismiss: () {},
)
```

---

## 📊 COLORES DISPONIBLES

### Por métrica
```dart
// Ánimo
const Color ánimo = Color(0xFF3b82f6); // Azul

// Energía
const Color energía = Color(0xFF10b981); // Verde

// Estrés
const Color estrés = Color(0xFFf59e0b); // Ámbar

// Sueño
const Color sueño = Color(0xFF8b5cf6); // Púrpura

// Bienestar
const Color bienestar = Color(0xFF06b6d4); // Cian
```

### Por estado
```dart
// Pendiente
const Color pendiente = Color(0xFFf59e0b); // Naranja ⏳

// En proceso
const Color enProceso = Color(0xFF3b82f6); // Azul 🔄

// Completado
const Color completado = Color(0xFF10b981); // Verde ✓

// Crítica
const Color critica = Color(0xFFef4444); // Rojo ⚠️
```

---

## 🎨 GRADIENTES PREDEFINIDOS

```dart
// Premium white (background cards)
const LinearGradient premiumWhite = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFFF8FAFC), Color(0xFFF1F5F9)],
);

// Light blue
const LinearGradient lightBlue = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFFF0F9FF), Color(0xFFF8FAFC)],
);

// Light pink
const LinearGradient lightPink = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFFFEF2F2), Color(0xFFFAF5F5)],
);

// Dark
const LinearGradient darkGradient = LinearGradient(
  begin: Alignment.topLeft,
  end: Alignment.bottomRight,
  colors: [Color(0xFF0F172A), Color(0xFF1E293B), Color(0xFF334155)],
);
```

---

## 🎭 EMOJIS USADOS

```dart
// Estados de bienestar
'😄' // Excelente (ánimo ≥ 7)
'😊' // Bueno (ánimo ≥ 6)
'😐' // Regular (ánimo ≥ 4)
'😟' // Bajo (ánimo < 4)

// Tendencias
'↑'  // Mejorando
'↓'  // Empeorando
'→'  // Sin cambio

// Funciones
'📊' // Reportes
'🚨' // Urgencias
'📝' // Notas
'💊' // Medicación
'📤' // Derivaciones
'🏥' // Panel profesional
'👨‍⚕️' // Doctor
'📈' // Estadísticas

// Estados
'✓'  // Completado
'⚠️'  // Alerta
'🔄' // En proceso
'⏳' // Pendiente
'🎯' // Objetivo
```

---

## 📱 RESPONSIVE BREAKPOINTS

```dart
// Mobile
< 600px: Single column

// Tablet
600px - 900px: 2 columns

// Desktop
> 900px: 3-4 columns, max-width 1440px
```

### Cómo usar en componentes
```dart
GridView.count(
  crossAxisCount: MediaQuery.of(context).size.width > 1200 ? 4 : 2,
  // ...
)
```

---

## 🔧 EJEMPLOS DE USO

### Ejemplo 1: Mostrar estadísticas en página existente
```dart
import 'package:aurafit_frontend/widgets/estadisticas_widget.dart';

class MiPagina extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text('Mi Página')),
      body: SingleChildScrollView(
        child: Column(
          children: [
            SizedBox(height: 20),
            EstadisticasWidget(), // ← Añadir aquí
            SizedBox(height: 20),
          ],
        ),
      ),
    );
  }
}
```

### Ejemplo 2: Dashboard en admin
```dart
import 'package:aurafit_frontend/widgets/dashboard_ejecutivo.dart';

DashboardEjecutivo(
  totalPacientes: _pacientes.length,
  derivacionesPendientes: _derivacionesPendientes,
  alertasActivas: _alertasActivas,
  especialidades: [
    {'name': 'Nutricionista', 'pacientes': 8, 'derivaciones': 1, 'alertas': 0},
    {'name': 'Psicólogo', 'pacientes': 10, 'derivaciones': 1, 'alertas': 1},
    {'name': 'Médico', 'pacientes': 6, 'derivaciones': 1, 'alertas': 0},
  ],
  onRefresh: _recargarDatos,
)
```

### Ejemplo 3: Card personalizada
```dart
import 'package:aurafit_frontend/widgets/professional_dashboard_widgets.dart';

PremiumCard(
  title: 'Seguimiento del paciente',
  subtitle: 'Juan García - Última actualización hace 2 horas',
  icon: Icons.person,
  iconColor: Colors.blue,
  gradient: LinearGradient(
    colors: [Colors.blue.withOpacity(0.08), Colors.grey.withOpacity(0.02)],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  ),
  child: Column(
    children: [
      MetricCard(
        label: 'Ánimo',
        value: '7.2',
        unit: '/10',
        icon: Icons.mood,
        color: Colors.blue,
        trend: '↑',
        trendColor: Colors.green,
      ),
      SizedBox(height: 12),
      MetricCard(
        label: 'Estrés',
        value: '4.1',
        unit: '/10',
        icon: Icons.psychology,
        color: Colors.orange,
        trend: '↓',
        trendColor: Colors.green,
      ),
    ],
  ),
)
```

---

## 🚀 INTEGRACIÓN EN ROUTER

### En `router.dart`
```dart
GoRoute(
  path: '/panel-profesional',
  name: 'panelProfesional',
  builder: (context, state) => PanelProfesionalIntegrado(
    rolNombre: userState.rolNombre,
    authToken: userState.token,
  ),
)
```

### Navegar a la página
```dart
context.goNamed('panelProfesional');
// o
context.go('/panel-profesional');
```

---

## 💡 TIPS Y TRUCOS

### Cambiar temas globalmente
```dart
// En professional_dashboard_widgets.dart, actualiza los const LinearGradient
// para cambiar toda la paleta

const LinearGradient premiumCard = LinearGradient(
  // ← Cambiar colores aquí
);
```

### Usar tus propios colores
```dart
PremiumCard(
  gradient: LinearGradient(
    colors: [Colors.green, Colors.teal],
    begin: Alignment.topLeft,
    end: Alignment.bottomRight,
  ),
  // ...
)
```

### Mostrar/ocultar elementos
```dart
if (_mostrarDetalles)
  EstadisticasWidget()
else
  CircularProgressIndicator()
```

### Conectar a datos reales
```dart
// En lugar de datos simulados, consume del API

final estadisticas = await _apiService.obtenerEstadisticas(pacienteId);
// Luego pasa a los widgets
```

---

## 📖 DOCUMENTACIÓN COMPLETA

Para más detalles, ver:
- `MEJORAS_SESION_5.md` - Resumen completo de cambios
- `GUIA_VISUAL_PANEL.md` - Especificaciones visuales
- `RESUMEN_SESION_5.md` - Vista ejecutiva

---

## ⚡ START RÁPIDO (30 segs)

1. **Copiar import**
   ```dart
   import 'package:aurafit_frontend/pages/panel_profesional_integrado.dart';
   ```

2. **Usar en página**
   ```dart
   PanelProfesionalIntegrado(rolNombre: 'medico', authToken: token)
   ```

3. **Listo** ✅

---

**Componentes listos para usar. ¡Disfrutalos! 🎉**
