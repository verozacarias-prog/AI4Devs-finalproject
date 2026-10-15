/**
 * Every text the dashboard shows, in one place. They are for the end user, so they are in
 * Spanish.
 */
export const MESSAGES = {
  appTitle: 'Platita',
  appTagline: 'Tu plata, en orden',
  nav: {
    label: 'Menú principal',
    accounts: 'Cuentas',
    testing: 'Pruebas',
    status: 'Estado del sistema',
    signedInAs: 'Sesión de',
    logout: 'Cerrar sesión',
    logoutFailed: 'No se pudo cerrar la sesión',
  },
  /** Shared by every screen that asks the API for something. */
  common: {
    retry: 'Reintentar',
    /** Why the API gave no usable answer, by the kind of failure of `api/request.ts`. */
    apiFailures: {
      'api-error': 'La API respondió con un error.',
      'api-timeout': 'La API no respondió a tiempo.',
      'api-unreachable': 'No se puede llegar a la API.',
    },
  },
  status: {
    heading: 'Estado del sistema',
    loading: 'Consultando el estado…',
    connected: 'Todo conectado',
    connectedDetail: 'El dashboard llega a la API, y la API a la base de datos.',
    disconnected: 'Sin conexión',
    databaseUnreachable: 'La API responde, pero no llega a la base de datos.',
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
  },
  accounts: {
    heading: 'Tus cuentas',
    loading: 'Consultando tus cuentas…',
    currencyGroup: (currency: string) => `Cuentas en ${currency}`,
    investmentsHeading: 'Inversiones',
    investmentsDetail: 'Lo aportado neto: lo que pusiste menos lo que sacaste, no lo que vale hoy.',
    netContributed: 'Aportado neto',
    empty: 'Todavía no tenés cuentas',
    emptyDetail: 'Las cuentas se dan de alta conversando con Platita.',
    failed: 'No se pudieron consultar tus cuentas',
    types: {
      bank_account: 'Banco',
      digital_wallet: 'Billetera',
      broker: 'Inversión',
      cash: 'Efectivo',
      credit_card: 'Tarjeta de crédito',
      receivable: 'Me deben',
    },
  },
} as const
