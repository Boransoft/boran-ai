type Store = Map<string, string>;

type LocalStorageLike = {
  length: number;
  clear: () => void;
  getItem: (key: string) => string | null;
  key: (index: number) => string | null;
  removeItem: (key: string) => void;
  setItem: (key: string, value: string) => void;
};

export function createLocalStorageMock(seed?: Record<string, string>): LocalStorageLike {
  const store: Store = new Map<string, string>(Object.entries(seed || {}));

  return {
    get length() {
      return store.size;
    },
    clear: () => {
      store.clear();
    },
    getItem: (key: string) => {
      return store.has(key) ? (store.get(key) as string) : null;
    },
    key: (index: number) => {
      const keys = Array.from(store.keys());
      return keys[index] ?? null;
    },
    removeItem: (key: string) => {
      store.delete(key);
    },
    setItem: (key: string, value: string) => {
      store.set(key, value);
    },
  };
}

export function installLocalStorageMock(seed?: Record<string, string>): LocalStorageLike {
  const mock = createLocalStorageMock(seed);
  Object.defineProperty(globalThis, "localStorage", {
    value: mock,
    writable: true,
    configurable: true,
  });
  return mock;
}
