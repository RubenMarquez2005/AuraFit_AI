# Dataset Salud, Fitness y Bienestar (JSONL)

Fecha de generacion: 2026-04-20

## Objetivo
Generar un dataset grande y realista para fine-tuning de modelos NLP conversacionales (OpenAI, LLaMA, Mistral) orientado a:
- entrenador personal
- nutricionista basico
- coach de habitos
- asistente de bienestar emocional general (no clinico)

## Formato aplicado
Formato JSONL por linea, con estructura obligatoria:

```json
{
  "messages": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}
```

## Salida generada
- Carpeta dataset: datasets/health_fitness_wellness_25000/
- Script generador: scripts/generate_health_wellness_dataset.py
- Total de ejemplos: 25.000
- Tamano aproximado:
  - all_domains_25000_openai.jsonl: ~22 MB
  - openai_train_22500.jsonl: ~19 MB
  - openai_valid_2500.jsonl: ~2.2 MB

## Cobertura tematica incluida
### Nutricion
- perdida de grasa
- ganancia muscular
- mantenimiento
- habitos alimenticios
- hidratacion
- adolescentes y adultos
- errores comunes
- deficit/superavit calorico
- proteina diaria
- comida real vs ultraprocesada
- control de azucar
- colesterol
- energia y fatiga

### Entrenamiento
- principiante
- avanzado
- casa y gimnasio
- cardio para perdida de grasa
- ganancia muscular
- descanso/recuperacion
- errores frecuentes
- sobreentrenamiento
- full body
- torso/pierna
- rutinas 3-5 dias
- progresion de cargas
- tecnica basica
- constancia

### Psicologia de bienestar general (no clinica)
- ansiedad
- estres
- insomnio
- falta de motivacion
- habitos negativos
- organizacion personal
- autoestima baja
- cansancio mental

Regla aplicada:
- no se hacen diagnosticos medicos
- lenguaje empatico y humano
- consejos generales y de habitos

## Perfiles de usuario incluidos
- adolescente
- adulto sedentario
- deportista
- principiante en gym
- persona con sobrepeso
- persona activa
- persona con mala alimentacion
- persona con rutina desordenada

## Combinaciones realistas incluidas
- ansiedad + sobrepeso
- estres + mala alimentacion
- falta de motivacion + sedentarismo
- diabetes + gimnasio (precaucion general)
- insomnio + fatiga + mala dieta

## Variacion automatica aplicada
Se varian automaticamente:
- edad
- peso
- objetivo
- nivel de actividad
- problema principal
- contexto diario (turnos, poco tiempo, hijos, viajes, etc.)
- formulacion linguistica de preguntas y respuestas

## Distribucion del dataset
Generacion balanceada:
- nutricion: 6.250
- entrenamiento: 6.250
- psicologia bienestar: 6.250
- combinados realistas: 6.250

Total: 25.000

## Archivos generados
- nutricion_6250.jsonl
- entrenamiento_6250.jsonl
- psicologia_6250.jsonl
- combinado_6250.jsonl
- all_domains_25000_openai.jsonl
- openai_train_22500.jsonl
- openai_valid_2500.jsonl

## Uso rapido
Generar de nuevo:

```bash
/Users/rubenperez/Documents/AuraFit_AI/backend/venv/bin/python scripts/generate_health_wellness_dataset.py
```

Verificar lineas:

```bash
wc -l datasets/health_fitness_wellness_25000/*.jsonl
```
