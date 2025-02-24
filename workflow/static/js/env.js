const Environment = {
  DEBUG_MODE: window.DEBUG_MODE || false,

  isDebugMode() {
    return this.DEBUG_MODE;
  },
};

Object.freeze(Environment);
