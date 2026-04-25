import json
import random
from pathlib import Path

SEED = 20260420
random.seed(SEED)

ROOT = Path("/Users/rubenperez/Documents/AuraFit_AI")
OUT_DIR = ROOT / "datasets" / "health_fitness_wellness_25000"

N_TOTAL = 25000
BUCKETS = {
    "nutricion": 6250,
    "entrenamiento": 6250,
    "psicologia": 6250,
    "combinado": 6250,
}

PROFILES = [
    {"name": "adolescente", "age_min": 14, "age_max": 18},
    {"name": "adulto sedentario", "age_min": 25, "age_max": 55},
    {"name": "deportista", "age_min": 18, "age_max": 40},
    {"name": "principiante en gym", "age_min": 18, "age_max": 45},
    {"name": "persona con sobrepeso", "age_min": 20, "age_max": 60},
    {"name": "persona activa", "age_min": 20, "age_max": 55},
    {"name": "persona con mala alimentacion", "age_min": 18, "age_max": 60},
    {"name": "persona con rutina desordenada", "age_min": 20, "age_max": 50},
]

GOALS_NUTRI = [
    "perder grasa",
    "ganar masa muscular",
    "mantener el peso",
    "comer mejor sin dietas extremas",
    "mejorar la energia diaria",
]

GOALS_TRAIN = [
    "empezar gimnasio desde cero",
    "ganar musculo",
    "perder grasa",
    "mejorar resistencia",
    "crear constancia",
]

PSYCH_TOPICS = [
    "ansiedad",
    "estres",
    "insomnio",
    "falta de motivacion",
    "habitos negativos",
    "organizacion personal",
    "autoestima baja",
    "cansancio mental",
]

NUTRI_TOPICS = [
    "deficit calorico",
    "superavit calorico",
    "proteina diaria",
    "comida real vs ultraprocesada",
    "control de azucar",
    "colesterol",
    "hidratacion",
    "energia y fatiga por alimentacion",
]

TRAIN_TOPICS = [
    "full body",
    "torso pierna",
    "rutina 3 a 5 dias",
    "progresion de cargas",
    "tecnica basica",
    "descanso y recuperacion",
    "errores en el gym",
    "sobreentrenamiento",
    "rutina en casa",
    "cardio para perder grasa",
]

COMBO_CASES = [
    "ansiedad + sobrepeso",
    "estres + mala alimentacion",
    "falta de motivacion + sedentarismo",
    "diabetes + gimnasio (precaucion general)",
    "insomnio + fatiga + mala dieta",
]

DAILY_CONTEXTS = [
    "trabajo por turnos",
    "poco tiempo entre semana",
    "estudio y examenes",
    "cuidado de hijos",
    "presupuesto ajustado",
    "viajes frecuentes",
    "comidas fuera de casa",
    "horarios irregulares",
]

OPENERS = [
    "Te entiendo, vamos a hacerlo simple y sostenible.",
    "Buena pregunta, y se puede resolver sin complicarlo.",
    "Gracias por contarlo con claridad.",
    "Perfecto, vamos paso a paso para que lo puedas mantener.",
    "Tiene sentido lo que te pasa, y hay una forma practica de abordarlo.",
]

CLOSERS = [
    "Si quieres, en el siguiente mensaje te lo convierto en plan semanal detallado.",
    "Si te va bien, te preparo una version aun mas simple para tu rutina real.",
    "Puedes empezar hoy con esto y ajustar en 7 dias segun como te sientas.",
    "Lo importante es continuidad, no perfeccion.",
    "Cuando quieras, lo adaptamos a tu horario exacto.",
]


def pick_profile():
    p = random.choice(PROFILES)
    age = random.randint(p["age_min"], p["age_max"])
    weight = random.randint(48, 115)
    activity = random.choice(["baja", "media", "alta"])
    context = random.choice(DAILY_CONTEXTS)
    return p["name"], age, weight, activity, context


def make_user_nutri():
    profile, age, weight, activity, context = pick_profile()
    goal = random.choice(GOALS_NUTRI)
    topic = random.choice(NUTRI_TOPICS)
    t = random.choice([
        f"Tengo {age} anos, peso {weight} kg, perfil {profile}, actividad {activity}. Quiero {goal} y me cuesta {topic}. Trabajo con {context}. Que me recomiendas?",
        f"Soy {profile}, {age} anos, {weight} kg. Mi objetivo es {goal}. Me pierdo con {topic} y mis horarios son de {context}.",
        f"Necesito ayuda con nutricion: {goal}. Tengo {age} anos, actividad {activity}, y me afecta {topic}. Contexto diario: {context}.",
        f"Estoy intentando {goal}, pero fallo por {topic}. Tengo perfil {profile}, {age} anos, {weight} kg y {context}.",
    ])
    return t, {"topic": topic, "goal": goal}


def make_user_train():
    profile, age, weight, activity, context = pick_profile()
    goal = random.choice(GOALS_TRAIN)
    topic = random.choice(TRAIN_TOPICS)
    t = random.choice([
        f"Quiero {goal}. Tengo {age} anos, peso {weight} kg, soy {profile}, actividad {activity}. Me ayudas con {topic}? Mi contexto: {context}.",
        f"Soy {profile}, {age} anos. Me gustaria {goal} y necesito una guia de {topic}. Tengo {context}.",
        f"Tengo poco orden para entrenar. Perfil {profile}, {age} anos, actividad {activity}. Objetivo: {goal}. Tema: {topic}.",
        f"Quiero mejorar en gym/casa: {goal}. Me cuesta {topic}, tengo {weight} kg y una rutina de {context}.",
    ])
    return t, {"topic": topic, "goal": goal}


def make_user_psych():
    profile, age, weight, activity, context = pick_profile()
    topic = random.choice(PSYCH_TOPICS)
    t = random.choice([
        f"Ultimamente tengo {topic}. Soy {profile}, {age} anos, actividad {activity}, y vivo con {context}. Que habitos me pueden ayudar?",
        f"Me siento bloqueado por {topic}. Tengo {age} anos, perfil {profile}. Mi dia a dia es {context}. Necesito algo practico.",
        f"Quiero mejorar bienestar general, pero me pesa {topic}. Soy {profile}, actividad {activity}.",
        f"No busco diagnostico, solo orientacion general. Tengo {topic}, {age} anos, y una rutina de {context}.",
    ])
    return t, {"topic": topic}


def make_user_combo():
    profile, age, weight, activity, context = pick_profile()
    case = random.choice(COMBO_CASES)
    t = random.choice([
        f"Estoy con {case}. Soy {profile}, {age} anos, {weight} kg, actividad {activity}, y tengo {context}. Que plan simple puedo seguir?",
        f"Necesito una estrategia realista para {case}. Perfil {profile}, {age} anos. Mi contexto diario: {context}.",
        f"Quiero salir de este bucle: {case}. Soy {profile}, peso {weight} kg, y mis horarios son de {context}.",
        f"Me puedes orientar con {case} sin extremos? Tengo {age} anos, actividad {activity}, perfil {profile}.",
    ])
    return t, {"case": case}


def assistant_nutri(meta):
    opener = random.choice(OPENERS)
    topic = meta.get("topic") or random.choice(NUTRI_TOPICS)
    goal = meta.get("goal") or random.choice(GOALS_NUTRI)
    water = random.choice(["1.8 L", "2.0 L", "2.2 L", "2.5 L"])
    meal = random.choice(["3 comidas + 1 snack", "4 comidas simples", "3 comidas estructuradas"])
    return (
        f"{opener} En nutricion, para avanzar hacia {goal} sin agobio te propongo una base: {meal}, prioridad a comida real, "
        f"proteina en cada comida y control de porciones. Sobre {topic}, aplica una regla facil: planifica con antelacion "
        f"dos opciones de comida que puedas repetir entre semana para reducir decisiones impulsivas. "
        f"Tambien cuida hidratacion ({water}/dia) y duerme mejor posible, porque eso afecta hambre y energia. "
        f"Haz seguimiento 7 dias con una escala simple (hambre, energia, adherencia del 1 al 10) y ajusta desde datos reales. "
        f"{random.choice(CLOSERS)}"
    )


def assistant_train(meta):
    opener = random.choice(OPENERS)
    topic = meta.get("topic") or random.choice(TRAIN_TOPICS)
    goal = meta.get("goal") or random.choice(GOALS_TRAIN)
    split = random.choice(["full body 3 dias", "torso/pierna 4 dias", "rutina en casa 3 dias"])
    prog = random.choice([
        "sube 1-2 repeticiones cuando completes todas las series con tecnica limpia",
        "aumenta 2.5-5% de carga de forma gradual",
        "manten carga y mejora ejecucion antes de progresar",
    ])
    return (
        f"{opener} Para entrenamiento con objetivo de {goal}, usa una estructura clara: {split}, calentamiento breve, bloque principal y cierre. "
        f"Como te preocupa {topic}, dedica 5 minutos al inicio a tecnica y ejecucion controlada. "
        f"Enfocate en tecnica y constancia antes de intensidad alta. Para progresar, {prog}. "
        f"Incluye 1-2 dias de recuperacion activa (caminar, movilidad, estiramientos suaves) para evitar sobrecarga. "
        f"Si un dia vas justo de tiempo, haz version minima de 20 minutos en lugar de saltarte todo. "
        f"La clave es sostener semanas, no hacerlo perfecto un solo dia. {random.choice(CLOSERS)}"
    )


def assistant_psych(meta):
    opener = random.choice(OPENERS)
    topic = meta.get("topic") or random.choice(PSYCH_TOPICS)
    tech = random.choice([
        "respiracion 4-4-6 por 3 minutos",
        "descarga mental de 5 minutos en papel",
        "bloques de enfoque de 25 minutos + pausa breve",
        "caminar 10-15 minutos sin pantalla",
    ])
    return (
        f"{opener} Con {topic}, no hace falta hacerlo perfecto: empieza con una accion pequena y repetible. "
        f"Hoy prueba {tech} y define una sola tarea prioritaria para cerrar el dia con sensacion de avance. "
        f"A nivel de habitos, intenta horario regular de sueno, menos estimulos por la noche y micro-rutinas cortas por la manana. "
        f"Si notas que te cuesta sostenerlo, simplifica aun mas: objetivo minimo diario de 10 minutos. "
        f"Esto es orientacion general de bienestar y habitos, no diagnostico clinico. {random.choice(CLOSERS)}"
    )


def assistant_combo():
    opener = random.choice(OPENERS)
    case = random.choice(COMBO_CASES)
    return (
        f"{opener} En casos como {case}, funciona mejor un plan combinado y realista: 1) comida estructurada sin extremos, "
        "2) movimiento breve diario, 3) rutina de sueno mas estable, y 4) gestion del estres con tecnica corta de regulacion. "
        "No intentes cambiar todo de golpe; elige dos prioridades para esta semana y mide adherencia diaria. "
        "Si hay una condicion medica conocida, adapta con precaucion general y seguimiento profesional cuando corresponda. "
        "La consistencia pequena gana al plan perfecto imposible. "
        f"{random.choice(CLOSERS)}"
    )


def assistant_combo_with_case(meta):
    opener = random.choice(OPENERS)
    case = meta.get("case") or random.choice(COMBO_CASES)
    return (
        f"{opener} En casos como {case}, funciona mejor un plan combinado y realista: 1) comida estructurada sin extremos, "
        "2) movimiento breve diario, 3) rutina de sueno mas estable, y 4) gestion del estres con tecnica corta de regulacion. "
        "No intentes cambiar todo de golpe; elige dos prioridades para esta semana y mide adherencia diaria. "
        "Si hay una condicion medica conocida, adapta con precaucion general y seguimiento profesional cuando corresponda. "
        "La consistencia pequena gana al plan perfecto imposible. "
        f"{random.choice(CLOSERS)}"
    )


def make_pair(bucket):
    if bucket == "nutricion":
        user_msg, meta = make_user_nutri()
        return user_msg, assistant_nutri(meta)
    if bucket == "entrenamiento":
        user_msg, meta = make_user_train()
        return user_msg, assistant_train(meta)
    if bucket == "psicologia":
        user_msg, meta = make_user_psych()
        return user_msg, assistant_psych(meta)
    user_msg, meta = make_user_combo()
    return user_msg, assistant_combo_with_case(meta)


def generate_examples():
    seen = set()
    by_bucket = {k: [] for k in BUCKETS}

    for bucket, target in BUCKETS.items():
        created = 0
        attempts = 0
        while created < target:
            attempts += 1
            user_msg, assistant_msg = make_pair(bucket)
            key = (user_msg, assistant_msg)
            if key in seen:
                if attempts > target * 30:
                    break
                continue
            seen.add(key)

            obj = {
                "messages": [
                    {"role": "user", "content": user_msg},
                    {"role": "assistant", "content": assistant_msg},
                ]
            }
            by_bucket[bucket].append(obj)
            created += 1

    return by_bucket


def write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    by_bucket = generate_examples()
    all_rows = []

    # 1) Archivos separados por dominio
    for bucket, rows in by_bucket.items():
        out = OUT_DIR / f"{bucket}_6250.jsonl"
        write_jsonl(out, rows)
        all_rows.extend(rows)

    # 2) Dataset combinado (formato OpenAI chat fine-tuning)
    combined_path = OUT_DIR / "all_domains_25000_openai.jsonl"
    write_jsonl(combined_path, all_rows)

    # 3) Particion train/valid automatica
    random.shuffle(all_rows)
    split_idx = int(len(all_rows) * 0.9)
    train_rows = all_rows[:split_idx]
    valid_rows = all_rows[split_idx:]

    train_path = OUT_DIR / "openai_train_22500.jsonl"
    valid_path = OUT_DIR / "openai_valid_2500.jsonl"
    write_jsonl(train_path, train_rows)
    write_jsonl(valid_path, valid_rows)

    print(f"Dataset base: {combined_path}")
    print(f"Total ejemplos: {len(all_rows)}")
    print(f"Train: {train_path} -> {len(train_rows)}")
    print(f"Valid: {valid_path} -> {len(valid_rows)}")
    for bucket, rows in by_bucket.items():
        print(f"{bucket}: {len(rows)}")


if __name__ == "__main__":
    main()
