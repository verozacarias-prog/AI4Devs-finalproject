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
    apiError: 'La API respondió con un error.',
    apiTimeout: 'La API no respondió a tiempo.',
    retry: 'Reintentar',
  },
  devEntry: {
    heading: 'Entrada de desarrollo',
    loading: 'Consultando la sesión…',
    choose: 'Elegí con qué usuario de prueba entrar.',
    enterAs: (name: string) => `Entrar como ${name}`,
    signedInAs: (name: string) => `Entraste como ${name}`,
    signedInDetail: 'La sesión es real: vence a las 12 horas, o a los 30 minutos sin actividad.',
    logout: 'Cerrar sesión',
    empty: 'No hay usuarios de prueba',
    emptyDetail: 'Corré el script de datos de prueba y volvé a consultar:',
    failed: 'No se pudo consultar la sesión',
    apiUnreachable: 'No se puede llegar a la API.',
    apiError: 'La API respondió con un error.',
    apiTimeout: 'La API no respondió a tiempo.',
    retry: 'Reintentar',
  },
} as const
