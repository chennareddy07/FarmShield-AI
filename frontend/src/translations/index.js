import en from './en'
import te from './te'

export const dictionaries = { en, te }
export const LANGUAGES = [{ code: 'en', label: 'English' }, { code: 'te', label: 'తెలుగు' }]

/** Translate `key` for `lang`; falls back to English, then to the key itself. Supports {placeholders}. */
export function translate(lang, key, vars) {
  let s = (dictionaries[lang] && dictionaries[lang][key]) ?? dictionaries.en[key] ?? key
  if (vars) for (const [k, v] of Object.entries(vars)) s = s.replaceAll(`{${k}}`, String(v))
  return s
}
