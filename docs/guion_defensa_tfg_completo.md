# Guion Completo de Defensa TFG - AuraFit AI

Fecha: 06-04-2026

## 1. Mensaje de apertura (30-45 segundos)
AuraFit AI es una plataforma clinica de apoyo al bienestar integral que conecta paciente y profesionales en un unico circuito asistencial. El proyecto combina frontend Flutter, backend FastAPI, NLU local con RASA y persistencia SQL para convertir datos de salud en acciones coordinadas con trazabilidad.

Valor principal: no es solo una app de seguimiento, sino un sistema con control de roles, flujo de derivaciones, checklist clinico versionado, severidad sugerida explicable y export documental hospitalario.

### 1.1 Como "piensa" la IA
- No piensa como una persona ni tiene pensamiento propio.
- Genera respuestas prediciendo el siguiente texto a partir del contexto, el historial del chat y las instrucciones del sistema.
- Por eso se parece a ChatGPT: entiende la consulta, usa memoria de conversacion y adapta la respuesta al caso.
- En AuraFit AI hay una IA principal especializada, con modelos configurables en backend, y un fallback solo si el proveedor falla.

### 1.2 Que hace la app
- Registra datos de salud y seguimiento diario.
- Permite pedir citas y contactar con especialistas desde dentro de la app.
- Resume el estado del paciente para que el profesional lo revise rapido.
- Organiza derivaciones, checklist clinico y trazabilidad.
- Da soporte conversacional para que el paciente no tenga que navegar por pantallas sueltas sin contexto.

## 2. Problema real y propuesta de solucion

### Problema detectado
Las herramientas de salud suelen estar fragmentadas:
- una app para peso,
- otra para habitos,
- otra para salud mental,
- sin continuidad profesional real.

Resultado habitual: datos dispersos y baja accionabilidad.

### Solucion construida
AuraFit AI integra:
- seguimiento diario del paciente,
- interpretacion conversacional,
- coordinacion profesional,
- y salida documental para trabajo clinico.

## 3. Objetivos del proyecto y grado de cumplimiento

### Objetivo general
Crear una plataforma de apoyo clinico integral con base tecnica reproducible para entorno academico-profesional.

### Objetivos especificos cumplidos
1. Autenticacion y roles con frontera de seguridad en backend.
2. Registro de metricas corporales con IMC accionable.
3. Flujo paciente para solicitar cita nutricional.
4. Panel profesional con bandeja y seguimiento por paciente.
5. Derivaciones entre especialidades.
6. Protocolos y checklist hospitalario con historial.
7. Severidad sugerida por KPIs explicables.
8. Export PDF hospitalario.
9. Validacion con pruebas backend en verde.

## 4. Arquitectura explicada para tribunal

### 4.1 Capa de presentacion (Flutter)
- Interfaz para paciente y profesional.
- Layout unificado por secciones para lectura clinica.
- Flujo centrado en accion (ejemplo: IMC -> cita).

### 4.2 Capa API (FastAPI)
- Orquesta negocio, permisos y persistencia.
- Expone endpoints tipados y documentados en Swagger.
- Protege operaciones sensibles por rol.

### 4.3 Capa NLU (RASA)
- Interpreta lenguaje natural en espanol.
- Detecta intenciones y entidades clave.
- Mantiene control local y trazabilidad de entrenamiento.

### 4.4 Capa de datos (MySQL + SQLAlchemy)
- Entidades de usuario, seguimiento, derivacion y auditoria clinica.
- Historial versionado para defensa de decisiones.

### 4.5 IA principal y modelos disponibles
- La IA se explica como un asistente unico, al estilo ChatGPT, con proveedor configurable en backend.
- Modelo principal actual: `Gemini 2.0 Flash`.
- Modelo alternativo disponible: `Qwen3 32B Instruct`.
- El modelo no devuelve respuestas predefinidas en el camino principal: razona sobre el historial, el contexto y la consulta.
- Solo existe fallback local si el proveedor principal falla o no responde.
- Un token no es "pensamiento propio": es una unidad de texto. El comportamiento tipo ChatGPT se consigue porque el modelo generativo predice la siguiente respuesta usando contexto, historial y prompt.
- Si se quisiera mas autonomia, habria que añadir memoria mas avanzada, recuperacion de documentos y un bucle de herramientas, pero para este proyecto no es necesario para explicar la IA de forma clara.

### 4.6 Como entran los usuarios al sistema
- Los pacientes se crean desde el propio proyecto con el registro de la app.
- Los usuarios demo profesionales se crean en el backend durante el arranque en modo desarrollo.
- En SQL quedan la estructura, roles y tablas; no se duplica la semilla de usuarios para no desalinear hashes ni credenciales.

### 4.7 Explicacion corta para la profesora
Si te pregunta por la IA, la explicacion simple es esta: no hay muchas IA sueltas, hay una IA principal con modelos configurables. Esa IA no tiene pensamiento propio, sino que genera la siguiente respuesta con el contexto, el historial y el prompt. Asi consigue parecerse a ChatGPT pero especializada en salud.

## 5. Modulos funcionales clave

### 5.1 Paciente
- Registro/login.
- Actualizacion de metricas IMC.
- Solicitud de cita nutricional desde home.
- Consulta de derivaciones.
- Seguimiento emocional diario.

### 5.2 Profesional
- Visualizacion de pacientes.
- Medicacion (roles autorizados).
- Plan nutricional clinico.
- Derivaciones y bandeja recibida.
- Protocolos, checklist y auditoria.
- PDF hospitalario descargable.

### 5.3 IA y apoyo a decision
- RASA para interpretacion conversacional.
- Heuristica de severidad sugerida por KPIs.
- Explicabilidad con motivos, no caja negra opaca.

## 6. Seguridad y control de acceso

### 6.1 Principio aplicado
Todo permiso se valida en backend.

### 6.2 Medidas implementadas
- Registro publico restringido a paciente.
- Registro profesional con clave privada.
- Operaciones clinicas protegidas por rol.
- Restricciones para medicacion, protocolos y checklist.

### 6.3 Beneficio defendible
Evita escalado de privilegios por manipulacion del frontend.

## 7. Trazabilidad clinica (diferencial del proyecto)

### 7.1 Checklist versionado
Cada actualizacion clinica genera snapshot historico con:
- version,
- fecha,
- profesional,
- contenido,
- escalado,
- observaciones.

### 7.2 Severidad sugerida explicable
La salida incluye:
- severidad sugerida,
- puntuacion,
- motivos.

### 7.3 Informe hospitalario PDF
Consolida protocolo, checklist y ruta de escalado para revision de caso.

## 8. Inventario de endpoints (resumen para exposicion)

### Endpoints principales
- Chat y NLU: /chat, /chat/rasa
- Perfil/IMC: /perfil/completar, /perfil/metricas-imc, /perfil/resumen
- Seguimiento: /seguimiento/checkin, /seguimiento/resumen-semanal, /seguimiento/historico
- Derivaciones: /profesionales/derivaciones, /pacientes/solicitar-cita-nutricion, /pacientes/derivaciones
- Hospitalario: /profesionales/protocolos-hospitalarios, /profesionales/pacientes/{id}/checklist-clinico, /profesionales/pacientes/{id}/checklist-clinico/auditoria, /profesionales/pacientes/{id}/informe-hospitalario-pdf

## 9. Demostracion en vivo recomendada (8-10 minutos)

1. Iniciar backend y abrir /docs.
2. Iniciar frontend y entrar como paciente.
3. Actualizar peso/altura y mostrar tarjeta IMC.
4. Solicitar cita de nutricion desde CTA.
5. Cambiar a perfil profesional y abrir panel clinico.
6. Revisar derivacion recibida.
7. Mostrar checklist clinico y guardar actualizacion.
8. Abrir endpoint de auditoria para ver versionado.
9. Consultar severidad sugerida.
10. Descargar informe hospitalario PDF.
11. Cerrar con ejecucion de pruebas backend.

## 10. Evidencia de calidad tecnica

### Comando de pruebas ejecutado
/Users/rubenperez/Documents/AuraFit_AI/backend/venv/bin/python -m unittest tests.test_rbac_clinico tests.test_cita_nutricion -v

### Resultado
9 pruebas en total, 9 superadas.

Interpretacion:
- permisos por rol validados,
- flujo IMC -> cita nutricional validado,
- integracion backend robusta en rutas criticas.

## 11. Riesgos y mitigaciones

### Riesgo 1: crecimiento de reglas clinicas
Mitigacion:
- modularidad por dominio,
- evolucion incremental con tests.

### Riesgo 2: interpretacion NLU incompleta
Mitigacion:
- mejora continua de ejemplos NLU,
- versionado de modelos RASA.

### Riesgo 3: confundir apoyo IA con diagnostico
Mitigacion:
- framing explicito de apoyo,
- decision final siempre profesional.

## 12. Preguntas habituales del tribunal (y respuesta corta)

1. Por que esta arquitectura y no una app monolitica simple.
- Porque separa seguridad, UI, NLU y persistencia, facilitando escalabilidad y mantenimiento.

2. Que aporta RASA frente a solo usar un LLM externo.
- Privacidad local, reproducibilidad, control de entrenamiento y explicabilidad.

3. Donde esta la evidencia objetiva de calidad.
- En pruebas backend reproducibles, contratos API tipados y trazabilidad documental.

4. Cual es el diferencial frente a una app de habitos convencional.
- Circuito clinico completo: derivacion, checklist versionado, severidad sugerida y PDF hospitalario.

5. Que mejorarias tras la defensa.
- CI/CD, mas cobertura automatica, monitorizacion y versionado formal de API.

## 13. Cierre final sugerido para exposicion
AuraFit AI demuestra una implementacion full stack con criterio clinico, seguridad por diseno y evidencia tecnica verificable. El proyecto no se queda en prototipo visual: articula datos, decisiones y coordinacion profesional con trazabilidad apta para contexto hospitalario formativo.

El resultado es defendible tanto desde ingenieria de software como desde aplicacion practica en salud digital.
