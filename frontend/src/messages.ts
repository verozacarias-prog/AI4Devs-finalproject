/**
 * Every text the dashboard shows, in one place. They are for the end user, so they are in
 * Spanish.
 */
export const MESSAGES = {
  appTitle: 'Platita',
  status: {
    heading: 'Estado del sistema',
    loading: 'Consultando el estado…',
    connected: 'Todo conectado',
    connectedDetail: 'El dashboard llega a la API, y la API a la base de datos.',
    disconnected: 'Sin conexión',
    databaseUnreachable: 'La API responde, pero no llega a la base de datos.',
    apiUnreachable: 'No se puede llegar a la API.',
    retry: 'Reintentar',
  },
} as const
