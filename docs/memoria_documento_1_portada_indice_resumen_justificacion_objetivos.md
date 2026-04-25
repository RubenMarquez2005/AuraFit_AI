# Memoria TFG - Documento 1

## Portada

- Nombre del alumno/alumnos: Ruben Perez Marquez
- Curso academico: 2025-2026
- Nombre del tutor de FCT: [Completar]
- Nombre del grado: [Completar]
- Centro educativo: [Completar]
- Fecha de entrega: 06-04-2026
- Titulo del proyecto: AuraFit AI - Plataforma clinica integral para seguimiento de pacientes y coordinacion profesional

---

## Indice

Nota de formato: este documento esta redactado en Markdown. Al maquetar en procesador de texto o PDF, sustituir "p. xx" por la pagina real de inicio.

- Portada ................................................................ p. xx
- Indice .................................................................. p. xx
- Resumen / Introduccion .................................................. p. xx
- Justificacion del proyecto .............................................. p. xx
- Objetivos ............................................................... p. xx
- Objetivo general ........................................................ p. xx
- Objetivos especificos ................................................... p. xx
- Criterios de cumplimiento ............................................... p. xx

---

## Resumen / Introduccion

### Version breve del resumen

AuraFit AI es una plataforma de salud digital que conecta seguimiento de paciente y coordinacion profesional en un mismo sistema. Integra Flutter, FastAPI, MySQL y RASA para transformar datos de bienestar en acciones clinicas trazables.

### Desarrollo amplio del resumen

AuraFit AI es una plataforma de salud digital orientada a mejorar la continuidad asistencial entre pacientes y profesionales en un unico ecosistema tecnologico. La solucion integra frontend en Flutter, backend en FastAPI, procesamiento conversacional en lenguaje natural con RASA y persistencia en MySQL mediante SQLAlchemy.

El proyecto surge al detectar un problema recurrente en herramientas de bienestar y salud: la informacion del usuario aparece distribuida en aplicaciones distintas, lo que impide una vision global del caso y reduce la capacidad de actuar a tiempo ante riesgos clinicos o de adherencia. En este escenario, el usuario suele registrar datos de forma aislada, sin que esos datos se conviertan en acciones coordinadas de seguimiento profesional.

AuraFit AI se diseña para resolver esa discontinuidad. El paciente puede registrar metricas corporales, estado emocional y habitos de forma estructurada. El profesional puede consultar informacion consolidada, coordinar derivaciones, aplicar protocolos, registrar checklist clinico y generar informes documentales para revision de caso. De esta manera, la plataforma transforma datos en decisiones operativas y trazables.

Desde el punto de vista academico, el proyecto demuestra competencias de arquitectura full stack, seguridad por roles, diseño de dominio, integracion de IA conversacional y validacion automatizada. La memoria no describe un prototipo conceptual, sino una implementacion funcional con evidencia tecnica reproducible.

Puntos troncales del alcance actual:

- Registro publico restringido al rol paciente.
- Registro privado de especialistas con clave interna.
- Flujo IMC accionable desde interfaz paciente.
- Solicitud de cita nutricional desde el estado IMC.
- Seguimiento emocional y de habitos con series temporales.
- Panel profesional por secciones con bandeja clinica y seguimiento.
- Derivaciones entre especialidades con estados.
- Plan nutricional y medicacion con permisos segun rol.
- Protocolos hospitalarios, checklist versionado y auditoria temporal.
- Severidad sugerida por KPIs con explicabilidad.
- Export de informe hospitalario en PDF.
- Pruebas backend de rutas criticas validadas.

Este proyecto, por tanto, se posiciona como una base robusta para defensa de TFG y como un punto de partida realista para evolucion hacia un producto de salud digital mas amplio.

#### Contexto de alcance real alcanzado

El alcance funcional actual no es teorico: cubre autenticacion, rolado, modulos de seguimiento, coordinacion de especialistas, trazabilidad y evidencia de pruebas automatizadas. Esto permite defender el proyecto desde una perspectiva de implementacion real y no solo de propuesta conceptual.

#### Pregunta de valor que responde el proyecto

La pregunta que estructura este TFG es: "como convertir registro de datos personales de salud en acciones clinicas coordinadas y auditables". AuraFit AI responde esa pregunta integrando:

- captura estructurada,
- interpretacion contextual,
- accion asistencial,
- control de permisos,
- historial verificable.

---

## Justificacion del proyecto

### Version breve de la justificacion

Se justifica el proyecto porque existe fragmentacion en herramientas de bienestar, con baja continuidad entre paciente y profesional. AuraFit AI aporta una solucion integrada, segura y trazable que mejora utilidad real y defendibilidad tecnica.

### Desarrollo amplio de la justificacion

### 1. Problema que se pretende resolver

El ecosistema de salud digital de uso general presenta varias limitaciones cuando se analiza desde la continuidad de cuidados:

- Fragmentacion de la informacion entre aplicaciones de nutricion, fitness y bienestar emocional.
- Falta de interoperabilidad funcional entre registro de datos y accion profesional.
- Escasez de trazabilidad clinica en cambios de seguimiento.
- Ausencia de mecanismos de coordinacion interdisciplinar en la mayoria de herramientas orientadas a consumo.

En la practica, esto implica que el usuario puede registrar muchos datos, pero esos datos no siempre se traducen en decisiones concretas de cuidado.

### 2. Colectivo destinatario

El proyecto esta dirigido a dos perfiles con necesidades complementarias:

1. Paciente.
- Registrar datos clave de salud de forma sencilla.
- Entender su situacion sin lenguaje tecnico excesivo.
- Tener acceso a acciones directas (por ejemplo, solicitar cita).

2. Profesional.
- Disponer de contexto estructurado por paciente.
- Coordinar intervenciones con otros especialistas.
- Documentar acciones y cambios con trazabilidad temporal.

### 3. Utilidad de la herramienta

AuraFit AI es util porque articula un circuito completo:

- captura de datos,
- interpretacion de estado,
- activacion de acciones,
- coordinacion interdisciplinar,
- evidencia documental.

Esto supera la logica de "app de registro" y aproxima el sistema a un modelo de apoyo clinico-formativo.

#### Utilidad concreta por actor

Utilidad para paciente:

- reduce pasos para registrar estado,
- facilita lectura de situacion personal,
- habilita peticion de ayuda profesional sin abandonar flujo.

Utilidad para profesional:

- reduce dispersion de informacion,
- mejora priorizacion de casos,
- mantiene rastro de intervenciones para revision.

Utilidad para evaluacion academica:

- permite demostrar relacion directa entre arquitectura y valor funcional,
- permite enseñar evidencia de seguridad y trazabilidad.

### 4. Competencia y aportacion diferencial

Aunque existen aplicaciones de salud y bienestar muy extendidas, gran parte de ellas priorizan experiencia individual y no integran de forma nativa:

- control de acceso clinico por rol con seguridad server-side,
- derivaciones entre profesionales,
- checklist clinico versionado,
- auditoria temporal,
- informe de caso exportable.

La aportacion diferencial de AuraFit AI se centra en la integracion de estos elementos dentro de una arquitectura coherente y validable.

#### Diferenciacion por capas

- Diferenciacion de producto: integra paciente y profesional.
- Diferenciacion tecnica: seguridad por rol en backend.
- Diferenciacion de proceso: checklist versionado con auditoria.
- Diferenciacion documental: evidencia reproducible en tests y endpoints.

### 5. Razones para elegir este proyecto

Motivos tecnicos y academicos:

- abordar un problema con impacto social,
- construir una solucion full stack de verdad,
- demostrar competencia en seguridad y mantenibilidad,
- entrenar capacidad de documentacion y defensa con evidencia.

Motivos de producto:

- unir bienestar y coordinacion asistencial,
- reducir friccion entre dato y accion,
- facilitar continuidad de seguimiento.

### 6. Valor academico para defensa

Este proyecto permite defender:

- diseño de arquitectura por capas,
- aplicacion de principio de minimo privilegio,
- trazabilidad de decisiones,
- capacidad de validacion automatizada,
- madurez de documentacion tecnica.

#### Contribucion a la rubrica docente

Este documento 1 cubre de forma explicitamente alineada:

- claridad del problema,
- calidad de planteamiento,
- coherencia entre objetivo general y objetivos especificos,
- base argumental para todo el desarrollo tecnico posterior.

---

## Objetivos

### Version breve de objetivos

Objetivo general: construir una plataforma integral de seguimiento y coordinacion asistencial.

Objetivos especificos: implementar seguridad, flujos clinicos accionables, trazabilidad, IA conversacional y validacion tecnica.

### Desarrollo amplio de objetivos

### Objetivo general

- Desarrollar una plataforma clinica integral que convierta datos de seguimiento personal en acciones coordinadas entre paciente y profesionales, con seguridad por roles y trazabilidad de intervenciones.

### Objetivos especificos

- Implementar autenticacion de usuarios con sesion segura.
- Diferenciar perfiles y permisos por rol.
- Restringir registro publico al rol paciente.
- Habilitar alta privada de especialistas con clave de registro.
- Registrar y actualizar perfil antropometrico con calculo de IMC.
- Mostrar lectura de IMC en interfaz accionable para paciente.
- Permitir solicitar cita nutricional desde el estado IMC.
- Implementar seguimiento diario de animo, energia, estres y sueno.
- Mantener historial semanal y rachas de seguimiento.
- Construir panel profesional con pacientes, derivaciones y contexto clinico.
- Permitir derivaciones entre especialidades bajo reglas RBAC.
- Implementar gestion de medicacion para roles autorizados.
- Implementar plan nutricional clinico con permisos de edicion.
- Gestionar protocolos hospitalarios por trastorno y severidad.
- Aplicar checklist clinico por paciente con versionado historico.
- Exponer auditoria temporal de checklist para trazabilidad.
- Calcular severidad sugerida con motivos explicables desde KPIs.
- Generar informe hospitalario PDF para revision de caso.
- Integrar RASA para intenciones y entidades en espanol.
- Validar rutas criticas mediante pruebas automatizadas reproducibles.
- Mantener documentacion extensa y alineada con requisitos docentes.

### Criterios de cumplimiento de objetivos

Un objetivo se considera cubierto cuando concurren los siguientes criterios:

- Existe implementacion funcional en codigo fuente.
- Existe endpoint o interfaz accesible que evidencia la funcionalidad.
- Existe coherencia con reglas de permisos y seguridad.
- Existe trazabilidad documental en memoria/bitacora.
- Existe evidencia de prueba manual o automatizada en funcionalidades criticas.

### Trazabilidad objetivo -> evidencia

Para asegurar que cada objetivo sea defendible, se sigue esta relacion:

1. Objetivo funcional -> endpoint o pantalla equivalente.
2. Objetivo de seguridad -> validacion de rol en servidor.
3. Objetivo de coordinacion -> flujo de derivacion verificable.
4. Objetivo de trazabilidad -> historial/auditoria o salida PDF.
5. Objetivo de calidad -> test automatizado o evidencia de ejecucion.

Este criterio evita objetivos ambiguos y permite justificar cumplimiento con pruebas objetivas.

### Riesgos del planteamiento y como se controlan

Riesgo 1. Objetivos demasiado amplios y poco medibles.

- Control:
	- redactar objetivos en infinitivo,
	- asociar cada objetivo a evidencia concreta (endpoint, pantalla o test).

Riesgo 2. Confundir alcance academico con alcance de producto comercial.

- Control:
	- priorizar flujos troncales defendibles,
	- dejar mejoras avanzadas en lineas futuras.

Riesgo 3. Sobrevalorar funcionalidad visual sin soporte tecnico.

- Control:
	- exigir que cada afirmacion del documento 1 tenga desarrollo en documento 2.

Riesgo 4. Falta de coherencia entre problema y solucion propuesta.

- Control:
	- mantener hilo conductor: dato paciente -> accion profesional -> trazabilidad.

### Mapa de consistencia del documento 1

Para asegurar coherencia interna:

1. Resumen define problema y propuesta.
2. Justificacion explica utilidad y diferenciacion.
3. Objetivos convierten la propuesta en entregables medibles.

Si alguno de estos tres niveles no encaja, el proyecto pierde defendibilidad. Esta comprobacion se ha usado durante toda la redaccion.

### Resumen ejecutivo final del Documento 1

Este documento no solo introduce el proyecto: fija su marco de evaluacion. Deja definida la pregunta de valor, la razon de utilidad y los objetivos que luego se validan tecnicamente. Por ello, funciona como contrato academico del resto de la memoria.

---

## Cierre del Documento 1

Este Documento 1 deja establecidos los fundamentos de la memoria: contexto, razon de ser, utilidad real y objetivos medibles. El Documento 2 desarrolla en profundidad la implementacion tecnica completa y el analisis de resultados.
