# Términos y política de privacidad: qué tienen que cubrir

Este documento **no es** el texto de los términos ni de la política de privacidad. Es el índice
de lo que tienen que cubrir, sacado de las decisiones ya tomadas en la especificación, para que
quien los redacte no deje nada afuera. El texto definitivo lo tiene que escribir o revisar
alguien con conocimiento legal, en particular sobre la Ley 25.326 de protección de datos
personales y la inscripción de bases de datos ante la autoridad de aplicación.

El alta exige aceptarlos antes de guardar nada
([reglas de dominio § 11](reglas-de-dominio.md#11-alta-de-usuario-consentimiento-y-mensajes-proactivos)),
así que bloquean abrir Platita a usuarios reales.

## Política de privacidad

| Tema | Qué tiene que decir | Dónde está la decisión |
|---|---|---|
| Qué datos se guardan | Teléfono, nombre, país, cuentas, movimientos, presupuestos, categorías, mensajes y, si el usuario lo completa, el perfil financiero | [3. Modelo de datos](03-modelo-de-datos.md) |
| Datos sensibles | El perfil financiero (ingresos por rango, deudas, personas a cargo, objetivos) es opcional y se usa solo para los consejos | [Reglas de dominio § 11](reglas-de-dominio.md#11-alta-de-usuario-consentimiento-y-mensajes-proactivos) |
| Procesamiento con IA | Los mensajes se interpretan con un proveedor externo de LLM, sin identificadores, y con un proveedor que por contrato no entrena con esos datos | [ADR 0013](adr/0013-datos-minimos-al-proveedor-de-llm.md) |
| Otros terceros | WhatsApp (Meta) como canal, el proveedor de alojamiento y las fuentes de cotización | [2. Arquitectura](02-arquitectura.md) |
| Dónde se alojan los datos | La región del proveedor de alojamiento, que puede estar fuera del país | [2.4. Infraestructura](02-arquitectura.md#24-infraestructura-y-despliegue) |
| Grupos familiares | Lo que un miembro imputa a un presupuesto familiar lo ven los demás miembros, y sigue visible después de que sale | [Reglas de dominio § 10](reglas-de-dominio.md#10-grupos-familiares-administración-salida-y-visibilidad) |
| Retención | Cuánto se guarda el texto de los mensajes y qué queda después | [Reglas de dominio § 14](reglas-de-dominio.md#14-privacidad-retención-borrado-de-cuenta-y-derechos) |
| Borrado de cuenta | Qué se borra, qué se anonimiza y el plazo de gracia | [Reglas de dominio § 14](reglas-de-dominio.md#14-privacidad-retención-borrado-de-cuenta-y-derechos) |
| Derechos | Acceso, rectificación y supresión, y cómo ejercerlos | [Reglas de dominio § 14](reglas-de-dominio.md#14-privacidad-retención-borrado-de-cuenta-y-derechos) |
| Avisos | Qué mensajes proactivos existen, que requieren permiso y cómo retirarlo | [Reglas de dominio § 11](reglas-de-dominio.md#11-alta-de-usuario-consentimiento-y-mensajes-proactivos) |
| Registros técnicos | Que los logs no guardan teléfono, montos ni texto sin enmascarar | [2.5. Seguridad](02-arquitectura.md#25-seguridad) |

## Términos de uso

| Tema | Qué tiene que decir | Dónde está la decisión |
|---|---|---|
| Qué es y qué no es | Un asistente de registro y educación financiera; no se conecta a bancos ni pide credenciales bancarias | [1. Producto](01-producto.md) |
| Los consejos no son asesoramiento profesional | Son educación financiera general cruzada con los datos del usuario, no una recomendación de inversión personalizada | [1.2. Consejos con RAG](01-producto.md#12-características-y-funcionalidades-principales) |
| Confirmaciones | El usuario confirma cada movimiento; las cotizaciones son sugerencias que él valida | [Reglas de dominio § 1 y § 6](reglas-de-dominio.md) |
| Límites de uso | Cuotas diarias de mensajes y consultas, y qué pasa al superarlas | [Reglas de dominio § 12](reglas-de-dominio.md#12-límites-de-uso-del-asistente) |
| Disponibilidad | Depende de WhatsApp y del proveedor de LLM; puede haber demoras | [ADR 0010](adr/0010-webhook-asincrono-con-tabla-de-entrada.md) |
| Versiones | Que los términos pueden cambiar y cómo se avisa; el alta guarda la versión aceptada | [3. Modelo de datos, USER](03-modelo-de-datos.md#32-descripción-de-entidades-principales) |
