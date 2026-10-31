# 0030 — El rol de la aplicación en la base

- Estado: Aceptada
- Fecha: 2026-10-31

## Contexto

El [ADR 0015](0015-borrado-logico-de-movimientos.md) decidió que la aplicación no puede eliminar
movimientos, y la migración del esquema crea para eso el rol `platita_app`, sin `DELETE` sobre
`transaction`, `transfer` y `recurring_rule`. El rol no podía iniciar sesión, y dejaba sin decidir
cómo se conecta la aplicación con él.

Por eso la API, el worker y las migraciones entraban con el dueño de las tablas, que puede borrar
cualquier fila. La prohibición existía en la base pero no protegía nada. Lo señaló
`/security-audit` el 19/10/2026.

## Decisión

1. **Cada proceso tiene su conexión.** La API, el worker y los comandos de operación usan
   `DATABASE_URL`, con `platita_app`. Las migraciones usan `MIGRATIONS_DATABASE_URL`, con el dueño
   de las tablas, y nunca usan la otra variable en su lugar.
2. **Las migraciones habilitan el rol.** Cada `alembic upgrade head`, aunque no haya migraciones
   pendientes, le da inicio de sesión a `platita_app` con la contraseña de
   `APPLICATION_DB_PASSWORD`. Si el valor cambió, también cambia la contraseña. Vive en
   `migrations/env.py`, que corre en cada ejecución. Una migración corre una sola vez y no podría
   cambiar la contraseña. Un comando que solo consulta, como `alembic current`, no pide la
   contraseña ni la cambia.
3. **Sin alguna de las dos variables, `alembic upgrade head` falla** y nombra la que falta. Un
   despliegue que las olvide se cancela y no deja a la aplicación sin poder conectarse.
4. **Vale igual en todos los entornos:** Compose y Render corren el mismo paso, solo cambia de
   dónde salen los valores. Los tests siguen conectándose con el dueño, porque crean y borran bases.

## Consecuencias

### Positivas

- La base rechaza un `DELETE` de movimientos aunque venga de un error del código o de un SQL
  inyectado.
- No hay pasos a mano: una base que ya existía queda lista en el siguiente despliegue.

### Negativas y costos asumidos

- Si el `ALTER ROLE` falla, PostgreSQL lo guarda completo en su registro, porque
  `log_min_error_statement` vale `error`. Por eso el comando lleva el hash SCRAM de la contraseña,
  calculado en el cliente, y nunca la contraseña: quien lea el registro no puede entrar con ese
  valor, pero sí intentar adivinarla sin conexión. Con una contraseña larga y al azar, ese riesgo
  se acepta.
- Hay una variable más que cargar en cada entorno.
- El rol no frena a quien logre ejecutar código en el servidor. Si el paso previo al despliegue de
  Render comparte las variables del servicio, ese proceso también puede leer la conexión del dueño.
- Quedan por verificar en el primer despliegue:
  - Que el usuario por defecto de Render Postgres pueda crear el rol y cambiarle la contraseña.
  - Si el paso previo al despliegue comparte las variables del servicio.

## Alternativas descartadas

- **Un usuario creado a mano en cada entorno:** la contraseña no pasaría por las migraciones, pero
  en Compose exige un script que solo corre con la base vacía, así que una base existente dejaría
  de conectarse. En Render suma un paso manual fácil de olvidar.
- **Conectarse como dueño y ejecutar `SET ROLE platita_app`:** no pide otra contraseña, pero no
  protege, porque un SQL inyectado puede deshacerlo con `RESET ROLE`.

---

Mientras no lleve la marca `En producción desde`, este ADR se corrige en este archivo. Con la
marca es inmutable: si la decisión queda sin efecto, no edites este archivo; creá uno nuevo y
cambiá el Estado de este a "Reemplazada por NNNN".
