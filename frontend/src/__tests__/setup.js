import '@testing-library/jest-dom/vitest'

globalThis.ResizeObserver = class {
  constructor(callback) {
    this.callback = callback
  }
  observe(target) {
    this.callback([{ target, contentRect: { width: 800, height: 220 } }])
  }
  unobserve() {}
  disconnect() {}
}
