import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'

import tr from './locales/tr.json'
import en from './locales/en.json'
import de from './locales/de.json'

export const LANGUAGES = [
  { code: 'tr', label: 'Türkçe', flag: '🇹🇷' },
  { code: 'en', label: 'English', flag: '🇬🇧' },
  { code: 'de', label: 'Deutsch', flag: '🇩🇪' },
]

// Language is stored in users.locale (DB). Fall back to browser language or 'tr'.
const browserLang = navigator.language?.slice(0, 2) || 'tr'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      tr: { translation: tr },
      en: { translation: en },
      de: { translation: de },
    },
    lng: browserLang,
    fallbackLng: 'tr',
    defaultNS: 'translation',
    interpolation: {
      escapeValue: false,
    },
  })

i18n.on('languageChanged', (lng) => {
  document.documentElement.setAttribute('lang', lng)
})

export default i18n
