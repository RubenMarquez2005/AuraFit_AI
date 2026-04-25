# Memoria TFG - AuraFit AI (Version separada por documentos)

Esta memoria se ha separado en tres documentos, siguiendo exactamente la estructura indicada por la guia docente.

## Documento 1

Portada, Indice, Resumen/Introduccion, Justificacion del proyecto y Objetivos:

- Incluye formato doble en cada bloque: version breve + desarrollo amplio.
- Incluye trazabilidad objetivo -> evidencia para defensa.

- [docs/memoria_documento_1_portada_indice_resumen_justificacion_objetivos.md](docs/memoria_documento_1_portada_indice_resumen_justificacion_objetivos.md)

## Documento 2

Desarrollo completo: Fundamentacion teorica, Materiales y metodos, Resultados y Analisis:

- Incluye inventario tecnico completo del proyecto (frontend, backend, modelos, endpoints, pruebas).
- Incluye seccion extensa de problemas/incidencias (causa, impacto, solucion y evidencia de cierre).
- Incluye lecciones tecnicas consolidadas y madurez por dimension.

- [docs/memoria_documento_2_desarrollo.md](docs/memoria_documento_2_desarrollo.md)

## Documento 3

Conclusiones, Lineas de investigacion futuras, Bibliografia/Webgrafia en APA, Anexos y Otros puntos:

- Incluye version breve + desarrollo amplio en conclusiones, lineas futuras, anexos y opcionales.
- Incluye plan por fases y checklist operativo de defensa.

- [docs/memoria_documento_3_conclusiones_futuro_bibliografia_anexos.md](docs/memoria_documento_3_conclusiones_futuro_bibliografia_anexos.md)

## Documentacion de apoyo para defensa

- IA principal: modelo configurable tipo ChatGPT con proveedor activo `IA_PROVIDER`.
- Modelos disponibles en el proyecto: `gemini-2.0-flash` y `qwen3-32b-instruct`.
- La respuesta principal sale del modelo, no de plantillas; el fallback local solo actua si falla el proveedor.
- Usuarios: los pacientes se registran desde la app y los usuarios demo profesionales se crean desde el backend al arrancar.
- La base de datos SQL mantiene esquemas, roles y tablas; no es el sitio principal de alta de usuarios.

- [docs/documentacion_tfg_integral_2026.md](docs/documentacion_tfg_integral_2026.md)
- [docs/bitacora_tfg.md](docs/bitacora_tfg.md)
- [RASA_VALIDATION_TFG.md](RASA_VALIDATION_TFG.md)
- [docs/guion_defensa_tfg_completo.md](docs/guion_defensa_tfg_completo.md)
