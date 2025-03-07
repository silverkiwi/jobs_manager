export const Environment = {
  DEBUG_MODE: window.DEBUG_MODE || false,

  isDebugMode() {
    return this.DEBUG_MODE;
  },
};

export function debugLog(...args) {
  if (Environment.isDebugMode()) {
    console.log(...args);
  }
}

Object.freeze(Environment);
