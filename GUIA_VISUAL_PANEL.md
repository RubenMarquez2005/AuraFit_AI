# 🎨 GUÍA VISUAL - PANEL CLÍNICO PROFESIONAL

## PALETA DE COLORES IMPLEMENTADA

### Colores de métricas (Estadísticas)
- **Ánimo**: #3b82f6 (Azul brillante)
- **Energía**: #10b981 (Verde vivo)
- **Estrés**: #f59e0b (Ámbar vibrante)
- **Sueño**: #8b5cf6 (Púrpura)
- **Bienestar**: #06b6d4 (Cian)

### Colores de estado (Derivaciones)
- **Pendiente**: #f59e0b (Naranja) ⏳
- **En proceso**: #3b82f6 (Azul) 🔄
- **Completado**: #10b981 (Verde) ✓
- **Crítica**: #ef4444 (Rojo) ⚠️

### Fondos y gradientes
- **Premium white**: #F8FAFC - #F1F5F9
- **Light blue**: #F0F9FF - #F8FAFC
- **Light pink**: #FEF2F2 - #FAF5F5
- **Dark**: #0F172A

## COMPONENTES VISUALES

### 1. PremiumCard
```
┌─────────────────────────────────┐
│ [ICON] TÍTULO                   │
│        Subtítulo                │
├─────────────────────────────────┤
│ [CONTENIDO]                     │
└─────────────────────────────────┘
```
- Gradiente suave
- Sombra profesional
- Border blanco translúcido
- Icono con fondo coloreado

### 2. MetricCard
```
┌────────────────────┐
│ [ICON]      [↑]   │  ← Tendencia
│ Label             │
│ 24.5 mg           │  ← Valor + unidad
└────────────────────┘
```
- Fondo gradiente del color
- Icono coloreado
- Indicador de tendencia (↑↓→)
- Valor prominente

### 3. DerivacionStateCard
```
┌─────────────────────────────┐
│ PACIENTE             [STATUS]│ ← Color dinámico
│ Derivado por: ...           │
├─────────────────────────────┤
│ [Especialidad]    [Fecha]   │
└─────────────────────────────┘
```
- Border coloreado (2px)
- Fondo gradiente
- Badge de estado dinámico
- Información compacta

### 4. EspecialidadDashboard
```
┌────────────────────────────┐
│ [ICON]           [ALERTAS] │
│ ESPECIALIDAD               │
├────────────────────────────┤
│ 👥 8 Pacientes             │
│ 📤 2 Derivaciones          │
└────────────────────────────┘
```
- Icono por especialidad
- Indicador de alertas en rojo
- Stats en fila
- Colores específicos por especialidad

## EMOJIS Y SÍMBOLOS

### Estados de bienestar
- 😄 Excelente (ánimo ≥ 7)
- 😊 Bueno (ánimo ≥ 6)  
- 😐 Regular (ánimo ≥ 4)
- 😟 Bajo (ánimo < 4)

### Indicadores de tendencia
- ↑ Mejorando
- ↓ Empeorando
- → Sin cambio

### Funciones
- 📊 Reportes PDF
- 🚨 Urgencias
- 📝 Notas clínicas
- 💊 Medicación
- 📤 Derivaciones

### Estado general
- 🏥 Panel profesional
- ✓ Normal/Completado
- ⚠️ Alerta/Pendiente

## SOMBRAS Y EFECTOS

### BoxShadow light (cards regulares)
```dart
BoxShadow(
  color: Colors.black.withValues(alpha: 0.08),
  blurRadius: 16,
  offset: Offset(0, 4),
)
```

### BoxShadow elevated (headers)
```dart
BoxShadow(
  color: Colors.black.withValues(alpha: 0.1),
  blurRadius: 16,
  offset: Offset(0, 4),
)
```

## TIPOGRAFÍA

### Heading levels
- **Heading 1**: 24px, w700 - Títulos principales
- **Heading 2**: 20px, w700 - Subtítulos
- **Heading 3**: 16px, w700 - Sections
- **Body**: 14px, w500 - Texto normal
- **Body small**: 12px, w500 - Detalles
- **Label**: 11px, w600 - Badges

## ESPACIADO (AppSpacing)
- **xs**: 4px
- **sm**: 8px
- **md**: 12px
- **lg**: 16px
- **xl**: 20px
- **2xl**: 24px

## BORDER RADIUS
- **sm**: 6px - Pequeños elementos
- **md**: 8px - Cards regulares
- **lg**: 12px - Componentes grandes
- **xl**: 16px - Containers principales

## EJEMPLO DE FLUJO VISUAL

### Dashboard Ejecutivo
```
┌─────────────────────────────────────┐
│ 🏥 PANEL PROFESIONAL               │
│ Seguimiento clínico integral        │
├─────────────────────────────────────┤
│ [Dashboard] [Estadísticas] [Funciones]
├─────────────────────────────────────┤
│
│ ┌─────┬─────┬─────┬─────┐
│ │ 📊  │ 🔴  │ ⚠️  │ 👥  │ ← KPIs
│ │ 24  │ 3   │ 1   │ 3   │
│ └─────┴─────┴─────┴─────┘
│
│ ┌─────────────┐ ┌─────────────┐
│ │ Nutrición   │ │ Psicología  │ ← Especialidades
│ │ 8 pac • 1d  │ │ 10 pac • 1d │
│ └─────────────┘ └─────────────┘
```

### Estadísticas Paciente
```
┌─────────────────────────────────────┐
│ 😊 Ánimo: 7.2 ↑ │ Energía: 6.8 ↑   │ ← Tarjeta resumen
│ Estrés: 4.1 ↓  │ Sueño: 7.5 →     │
└─────────────────────────────────────┘
│
│ [Gráfico línea: Ánimo 7 días]      ← 5 gráficos línea
│ [Gráfico radar: Multidimensional]  ← Radar
│ [Gráfico barras: Comparativa]      ← Barras
│
│ [Tabla: Datos diarios]             ← Tabla scroll
```

### Funciones Avanzadas
```
[📊 Reportes] [🚨 Urgencias] [📝 Notas] [💊 Med] [📤 Deriv]
       ↓
   ┌─────────────┐
   │ PDF Mensual │
   │ Resumen Ej. │
   │ Informe Esp.│
   └─────────────┘
```

## PROPIEDADES DE ACCESIBILIDAD

- Contraste mínimo 4.5:1 (WCAG AA)
- Colores principales no-dependientes del color
- Iconos acompañados de texto
- Tamaños de toque mínimo 48x48dp
- Ripple effect en botones

---

**Resultado final**: Panel profesional "flipante" apto para defensa de TFG 🎓
