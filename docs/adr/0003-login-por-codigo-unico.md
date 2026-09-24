# 0003 — Login por código de un solo uso, sin contraseñas

- Estado: Reemplazada por 0016
- Fecha: 2026-09-20

## Contexto

El dashboard web necesita acceso protegido. El sistema ya valida la identidad del usuario por
otro lado: el número de teléfono con el que conversa por WhatsApp, que es además la clave de
entrada del canal conversacional y es único por usuario.

## Decisión

Login sin contraseñas: el usuario pide acceder al dashboard, recibe un código de un solo uso por
WhatsApp —el mismo canal ya verificado— y lo intercambia por un JWT de corta duración.

## Consecuencias

### Positivas

- Se evita almacenar y gestionar contraseñas.
- Se reutiliza la identidad que el sistema ya valida por otro lado, sin agregar un segundo
  mecanismo de identidad que mantener sincronizado.
- No hace falta flujo de recuperación de contraseña.

### Negativas y costos asumidos

- Hace falta rate limiting sobre el endpoint de login para evitar fuerza bruta sobre el código.
- El acceso al dashboard queda atado a la disponibilidad del canal de WhatsApp: si el canal
  falla, no hay login alternativo.
- El JWT es de corta duración, así que el usuario reautentica con más frecuencia.

## Alternativas descartadas

- **Usuario y contraseña:** descartado por el costo de almacenarlas y gestionarlas de forma
  segura, y porque duplicaría una identidad que el sistema ya valida por WhatsApp.

---

Los ADR son inmutables. Si esta decisión queda sin efecto, no edites este archivo: creá uno nuevo
y cambiá el Estado de este a "Reemplazada por NNNN".
