# 0001 — Arquitectura hexagonal (ports & adapters)

- Estado: Aceptada
- Fecha: 2026-09-20

## Contexto

Platita depende de varias integraciones externas —WhatsApp, email, LLM, base vectorial,
cotizaciones, REM— que van a cambiar con el tiempo, y donde ya se identificó al menos un
reemplazo probable: el motor de vectores. Además está previsto un dashboard web desacoplado y,
más adelante, la posibilidad de una app móvil sobre la misma API.

## Decisión

Arquitectura hexagonal (ports & adapters), con el dominio —entidades y casos de uso— aislado de
los detalles de infraestructura detrás de puertos. Backend y frontend quedan desacoplados,
comunicados únicamente por API REST.

## Consecuencias

### Positivas

- El dominio no conoce los detalles de cada integración: cada una es un adaptador detrás de un
  puerto, y cambiarla es reemplazar el adaptador, no tocar la lógica de negocio.
- Los casos de uso (registrar un movimiento, evaluar un presupuesto, generar un consejo) se
  pueden testear sin levantar WhatsApp, un LLM real ni una base de datos: se testean contra los
  puertos, con dobles de prueba.
- Separar front de back deja la puerta abierta a una futura app móvil que consuma la misma API
  sin tocar lógica de negocio.
- Es el mismo patrón que ya se usa en otros proyectos propios en Go, así que la disciplina de
  diseño ya es conocida, solo cambia el lenguaje.

### Negativas y costos asumidos

- Más carpetas e indirección que un CRUD directo controlador-a-base de datos. Para un proyecto
  de este tamaño el volumen de casos de uso reales lo justifica.
- Mitigación: mantener los puertos chicos y con una sola responsabilidad cada uno, en vez de una
  interfaz gigante.

## Alternativas descartadas

- **CRUD directo controlador-a-base de datos:** menos carpetas e indirección, descartado porque
  con este número de integraciones externas cambiantes el dominio quedaría acoplado a detalles
  de infraestructura y los casos de uso no serían testeables sin levantar servicios reales.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
