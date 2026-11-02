import { describe, expect, it } from 'vitest'
import en from '../translations/en'
import te from '../translations/te'
import { translate } from '../translations'

describe('translations', () => {
  it('Telugu and English dictionaries have identical keys', () => {
    expect(Object.keys(te).sort()).toEqual(Object.keys(en).sort())
  })
  it('no empty strings', () => {
    for (const d of [en, te]) for (const [k, v] of Object.entries(d)) expect(v.trim().length, k).toBeGreaterThan(0)
  })
  it('placeholders match between languages', () => {
    const ph = (s) => (s.match(/\{\w+\}/g) || []).sort().join()
    for (const k of Object.keys(en)) expect(ph(te[k]), k).toBe(ph(en[k]))
  })
  it('falls back to English then key; replaces variables', () => {
    expect(translate('xx', 'risk.high')).toBe('High')
    expect(translate('te', 'does.not.exist')).toBe('does.not.exist')
    expect(translate('en', 'x', {}) ).toBe('x')
  })
  it('all five risk labels exist in both languages', () => {
    for (const r of ['low', 'moderate', 'high', 'critical', 'insufficient_data']) { expect(en[`risk.${r}`]).toBeTruthy(); expect(te[`risk.${r}`]).toBeTruthy() }
  })
})
