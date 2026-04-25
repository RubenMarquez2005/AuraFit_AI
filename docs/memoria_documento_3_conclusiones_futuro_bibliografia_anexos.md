# Memoria TFG - Documento 3

## Conclusiones

### Version breve de conclusiones

El proyecto cumple sus objetivos clave: integra paciente y profesional, aplica seguridad por rol, aporta trazabilidad clinica y mantiene evidencia tecnica reproducible.

### Desarrollo amplio de conclusiones

La realizacion de AuraFit AI ha supuesto una evolucion progresiva desde una base funcional inicial hasta una solucion clinica-formativa con arquitectura robusta, control de seguridad por roles y trazabilidad documental. El resultado no se limita a funcionalidades aisladas: integra en un mismo sistema el registro del paciente, la coordinacion profesional y la capacidad de justificar decisiones en el tiempo.

### 1. Cumplimiento de objetivos

Con base en la implementacion y evidencias disponibles, los objetivos planteados se consideran cubiertos:

- se implemento autenticacion y control por rol,
- se habilito flujo accionable IMC -> cita nutricional,
- se desplego panel profesional con seguimiento de pacientes,
- se implementaron derivaciones entre especialidades,
- se añadieron protocolos, checklist y auditoria versionada,
- se incorporo severidad sugerida explicable,
- se habilito export de informe hospitalario PDF,
- se validaron rutas criticas con pruebas automatizadas.

### 2. Aportacion tecnica del proyecto

Contribuciones relevantes:

- arquitectura por capas mantenible,
- seguridad aplicada en backend como frontera real,
- modelo de dominio con trazabilidad clinica,
- integracion de NLU local con RASA,
- evidencia reproducible de calidad.

### 3. Aportacion funcional y academica

Desde el punto de vista funcional, el proyecto convierte datos en acciones de seguimiento real. Desde el punto de vista academico, permite defender competencias de analisis, diseno, implementacion, validacion y documentacion con un caso aplicado de complejidad media-alta.

### 4. Aprendizajes obtenidos

Aprendizajes tecnicos:

- importancia de diseñar seguridad desde backend,
- valor de tipado y validacion de contratos,
- necesidad de trazabilidad en dominios sensibles,
- utilidad de dividir el proyecto por modulos de dominio.

Aprendizajes de proceso:

- documentar en paralelo reduce deuda de memoria,
- validar por hitos evita regresiones grandes,
- mantener bitacora facilita defensa y coherencia narrativa.

### 5. Valor final defendible

AuraFit AI demuestra una solucion funcional completa y razonablemente madura para entorno de TFG: integra tecnologia, seguridad, usabilidad y evidencia de pruebas en un mismo discurso tecnico.

### 6. Cierre critico (que queda claro tras el proyecto)

- No basta con construir pantallas: la calidad real aparece en la coherencia backend + reglas + trazabilidad.
- No basta con registrar datos: el valor aparece cuando esos datos activan decisiones.
- No basta con una IA "que responda": en salud, la explicabilidad y el control importan tanto como la respuesta.

---

## Lineas de investigacion futuras

### Version breve de lineas futuras

Las prioridades futuras son: ampliar calidad automatizada, profesionalizar despliegue y observabilidad, y profundizar personalizacion clinica y gobernanza IA.

### Desarrollo amplio de lineas futuras

### 1. Calidad y pruebas

- ampliar cobertura de tests en todos los endpoints clinicos,
- incorporar tests de regresion frontend,
- automatizar reportes de cobertura.

### 2. CI/CD y operaciones

- montar pipeline CI para lint + test,
- automatizar checks pre-merge,
- estandarizar despliegue en entornos de prueba.

### 3. Observabilidad y rendimiento

- incorporar metricas de latencia por endpoint,
- integrar logs estructurados con niveles de severidad,
- habilitar alertas basicas de salud de servicio.

### 4. Evolucion de producto

- ampliar modulo de analitica longitudinal,
- mejorar personalizacion de planes por perfiles,
- extender catalogo de recursos clinicos,
- aumentar soporte para nuevos flujos interdisciplinarios.

### 5. IA conversacional y explicabilidad

- ampliar corpus de entrenamiento RASA,
- evaluar metricas de clasificacion por intent,
- versionar sistematicamente modelos y experimentos,
- reforzar control de deriva semantica en expresiones reales de usuarios.

### 6. Escalado funcional

- recuperar plataformas frontend aplazadas,
- estudiar despliegues seguros por entorno,
- formalizar versionado de API para compatibilidad evolutiva.

### 7. Plan por fases recomendado

Fase 1 (corto plazo):

- cobertura de tests en modulos pendientes,
- pipeline CI minimo,
- checklist de regression antes de entrega.

Fase 2 (medio plazo):

- observabilidad basica,
- versionado de API,
- endurecimiento de contratos y errores tipados.

Fase 3 (largo plazo):

- analitica longitudinal avanzada,
- mejora de personalizacion asistencial,
- despliegue multientorno con gobernanza operativa.

---

## Bibliografia / Webgrafia (formato APA)

FastAPI. (2026). FastAPI documentation. https://fastapi.tiangolo.com/

Flutter Team. (2026). Flutter documentation. https://docs.flutter.dev/

Rasa Technologies. (2026). Rasa Open Source documentation. https://rasa.com/docs/

SQLAlchemy Authors. (2026). SQLAlchemy documentation. https://docs.sqlalchemy.org/

Pydantic. (2026). Pydantic documentation. https://docs.pydantic.dev/

Oracle. (2026). MySQL documentation. https://dev.mysql.com/doc/

PyFPDF. (2026). PyFPDF documentation. https://pyfpdf.readthedocs.io/

World Health Organization. (2021). Ethics and governance of artificial intelligence for health. https://www.who.int/publications/i/item/9789240029200

Nielsen, J. (1994). 10 usability heuristics for user interface design. Nielsen Norman Group. https://www.nngroup.com/articles/ten-usability-heuristics/

Fielding, R. T. (2000). Architectural styles and the design of network-based software architectures (Doctoral dissertation, University of California, Irvine). https://www.ics.uci.edu/~fielding/pubs/dissertation/top.htm

---

## Anexos

### Version breve de anexos

Los anexos deben contener evidencia visual, tecnica y de pruebas para sostener cada afirmacion de la memoria.

### Desarrollo amplio de anexos

### Anexo A. Evidencias de interfaz

- capturas de login y registro,
- capturas de home paciente con estado IMC,
- capturas de flujo de solicitud de cita nutricional,
- capturas de seguimiento emocional y habitos,
- capturas de panel profesional y secciones clinicas.

### Anexo B. Evidencias de API

- capturas de Swagger en endpoints troncales,
- ejemplos de payload/response en rutas criticas,
- evidencia de autorizacion por rol en operaciones sensibles.

### Anexo C. Evidencias de trazabilidad

- captura de checklist aplicado,
- captura de auditoria temporal versionada,
- captura de severidad sugerida con motivos,
- captura de informe PDF generado.

### Anexo D. Evidencias de pruebas

- salida de test_rbac_clinico,
- salida de test_cita_nutricion,
- comando ejecutado y estado final en verde.

### Anexo F. Checklist operativo para preparar defensa

1. Capturar login paciente y profesional.
2. Capturar home con tarjeta IMC y CTA.
3. Capturar creacion o reutilizacion de derivacion nutricional.
4. Capturar bandeja profesional con derivacion recibida.
5. Capturar checklist clinico antes y despues de editar.
6. Capturar endpoint de auditoria con versiones.
7. Capturar endpoint de severidad sugerida con motivos.
8. Capturar descarga PDF hospitalario.
9. Capturar ejecucion de test_rbac_clinico.
10. Capturar ejecucion de test_cita_nutricion.

### Anexo G. Mapa requisito -> evidencia (plantilla)

- Requisito: seguridad por rol.
	- Evidencia: endpoint protegido + test RBAC.

- Requisito: accionabilidad paciente.
	- Evidencia: flujo IMC -> solicitud de cita.

- Requisito: coordinacion profesional.
	- Evidencia: derivaciones emitidas/recibidas.

- Requisito: trazabilidad clinica.
	- Evidencia: auditoria versionada de checklist.

- Requisito: documento asistencial.
	- Evidencia: informe hospitalario PDF.

### Anexo E. Documentacion complementaria del proyecto

- [docs/documentacion_tfg_integral_2026.md](docs/documentacion_tfg_integral_2026.md)
- [docs/bitacora_tfg.md](docs/bitacora_tfg.md)
- [RASA_VALIDATION_TFG.md](RASA_VALIDATION_TFG.md)
- [docs/guion_defensa_tfg_completo.md](docs/guion_defensa_tfg_completo.md)

---

## Otros puntos (opcionales)

### Version breve de los apartados opcionales

Estos apartados refuerzan la madurez del trabajo mostrando crecimiento profesional, aprendizaje personal y reconocimiento del apoyo recibido.

### Desarrollo amplio de los apartados opcionales

### Retos profesionales

- consolidar perfil full stack en salud digital,
- reforzar competencias en arquitectura mantenible,
- mejorar dominio de seguridad aplicada en APIs clinicas,
- profundizar en integracion responsable de IA.

Retos profesionales ampliados:

- dominar diseño de sistemas orientados a dominio con evolucion segura,
- mejorar capacidad de estimacion de esfuerzo en proyectos con multiples frentes,
- profesionalizar procesos de calidad (testing, CI, revision tecnica),
- profundizar en documentacion de arquitectura para equipos multidisciplinares,
- fortalecer competencias de observabilidad y operacion de servicios,
- aprender estrategias de escalado sin degradar mantenibilidad,
- mejorar toma de decisiones tecnicas bajo restricciones de tiempo,
- reforzar comunicacion con perfiles no tecnicos en entornos sanitarios,
- establecer estandares personales de trazabilidad por entrega,
- consolidar criterio de priorizacion entre valor funcional y deuda tecnica.

### Retos personales

- optimizar gestion del tiempo en iteraciones largas,
- mantener disciplina de pruebas continuas,
- mejorar comunicacion oral tecnica para defensa.

Retos personales ampliados:

- sostener constancia en fases de alta carga de trabajo,
- mejorar equilibrio entre perfeccionismo y entrega incremental,
- reforzar tolerancia a bloqueos tecnicos prolongados,
- aumentar capacidad de concentracion en tareas de documentacion extensa,
- mejorar claridad narrativa para exponer decisiones complejas,
- entrenar pensamiento critico para evaluar alternativas con objetividad,
- mantener una rutina de aprendizaje continuo post-defensa,
- mejorar gestion emocional durante entregas y revisiones,
- fortalecer habitos de revision final antes de cada cierre,
- transformar errores de ejecucion en aprendizaje reutilizable.

### Agradecimientos

Agradezco al profesorado y al tutor de practicas su orientacion durante el desarrollo, asi como el feedback tecnico recibido para mejorar el proyecto en cada fase. Tambien agradezco el apoyo personal que ha permitido sostener el proceso de trabajo, validacion y documentacion.

Agradecimientos ampliados:

- A la empresa de practicas, por facilitar un entorno de aprendizaje aplicado donde trasladar conceptos academicos a problemas reales de desarrollo.
- A las personas de la empresa que ofrecieron orientacion tecnica y organizativa durante el proceso.
- Al tutor o tutora de FCT, por la supervision, el seguimiento y la ayuda en la priorizacion de entregables.
- Al profesorado del grado, por su acompañamiento y por el enfoque practico que ha permitido construir una base solida para este TFG.
- A los compañeros y compañeras que compartieron feedback, pruebas y contraste de ideas.
- A la familia y entorno personal, por el apoyo sostenido en momentos de alta carga de trabajo.

Texto formal sugerido para entrega final (editable):

"Deseo expresar mi agradecimiento a la empresa de practicas por brindarme la oportunidad de aprender en un contexto real y por su apoyo durante el desarrollo del proyecto. Agradezco especialmente al tutor de FCT y al profesorado del grado por su orientacion academica y tecnica. Asimismo, agradezco a mis compañeros y a mi entorno personal por su apoyo constante durante todo el proceso de elaboracion del TFG."

### Lecciones personales y profesionales de cierre

Lecciones profesionales:

- un diseño robusto empieza por contratos y permisos,
- la escalabilidad real exige modularidad temprana,
- los tests no son un extra: son evidencia de calidad.

Lecciones personales:

- documentar desde el inicio reduce retrabajo,
- dividir un problema grande en bloques facilita cierre,
- defender un proyecto exige tanto rigor tecnico como claridad narrativa.

Lecciones ampliadas de cierre:

- la calidad percibida por un tribunal depende tanto del producto como de la capacidad de justificar decisiones,
- una memoria extensa sin estructura pierde fuerza; una estructura clara multiplica el valor de la evidencia,
- la trazabilidad (bitacora, test y documentos) reduce incertidumbre en etapas finales,
- convertir incidencias en conocimiento reutilizable mejora futuras entregas,
- el equilibrio entre ambicion funcional y cierre estable es una competencia clave en proyectos reales.

---

## Cierre del Documento 3

Con este Documento 3 se completa la estructura solicitada en la guia docente para la memoria: conclusiones, lineas futuras, bibliografia en formato APA, anexos y apartados opcionales. En conjunto con Documento 1 y Documento 2, la memoria queda separada por documentos y lista para revision, maquetacion final y defensa.
