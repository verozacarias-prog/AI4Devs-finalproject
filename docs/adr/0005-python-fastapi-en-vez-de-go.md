# 0005 — Python + FastAPI en vez de Go

- Estado: Aceptada
- Fecha: 2026-09-20

## Contexto

La autora tiene 15+ años de experiencia backend y su stack principal es Go con arquitectura
hexagonal, además de NestJS y Java/Kotlin. Python también forma parte de su stack. El producto
tiene un núcleo de IA de primera clase: interpretación de lenguaje natural con LLM, generación
de embeddings y RAG sobre pgvector. Además es un proyecto formativo del máster AI4Devs, donde
parte del objetivo es el aprendizaje.

## Decisión

Python + FastAPI, en vez de Go, que sería la elección por defecto según la experiencia previa de
la autora. Razones:

- El ecosistema de IA es de primera clase en Python. Los SDK de los proveedores de LLM, las
  librerías de embeddings, los clientes de vector stores y las herramientas de RAG nacen y se
  mantienen primero en Python. En Go habría que pagar trabajo de integración y wrappers sin
  obtener nada a cambio en un proyecto cuyo núcleo es exactamente eso.
- FastAPI encaja con la arquitectura hexagonal sin fricción: es un adaptador de entrada delgado,
  con validación en el borde vía Pydantic y OpenAPI generado automáticamente, que es la base del
  mecanismo de reconciliación entre especificación y código previsto para la entrega 2.
- Valor formativo: salir deliberadamente del stack de trabajo diario es parte del objetivo del
  máster, y la arquitectura hexagonal es conocimiento transferible entre lenguajes, de modo que
  la experiencia previa en Go no se pierde, se traslada.

## Consecuencias

### Positivas

- Acceso directo al ecosistema de IA sin capas de adaptación.
- OpenAPI generado por el framework.
- Tipado y validación en el borde con Pydantic.
- Aprendizaje de un stack nuevo con la arquitectura ya dominada.

### Negativas y costos asumidos

- Menor rendimiento y mayor consumo de memoria que Go en el runtime.
- El tipado de Python es opcional y hay que imponerlo por convención y herramientas, no lo
  garantiza el compilador: de ahí la regla de tipado obligatorio y prohibición de `Any` en
  [CLAUDE.md](../../CLAUDE.md).
- Menor velocidad inicial de desarrollo por ser un stack menos frecuente para la autora.
- Gestión de dependencias y entornos virtuales más frágil que el sistema de módulos de Go.

## Alternativas descartadas

- **Go con arquitectura hexagonal:** el stack de mayor dominio de la autora y mejor rendimiento,
  descartado porque el ecosistema de IA en Go es inmaduro y obligaría a construir integraciones
  que en Python ya existen, en un proyecto donde la IA es el núcleo y no un accesorio.
- **NestJS / TypeScript:** buen soporte de IA y tipado fuerte, descartado por estar peor
  posicionado que Python en embeddings, RAG y el tooling de vector stores.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
