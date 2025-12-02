// src/api/base44Client.ts
type AnyRecord = { id?: string; [key: string]: any };

function makeStore<T extends AnyRecord>() {
  let data: T[] = [];
  let nextId = 1;

  return {
    async list(orderBy?: string) {
      // ignoring orderBy for simplicity
      return [...data];
    },
    async filter(query: Partial<T>, _orderBy?: string, limit?: number) {
      let result = data.filter(item =>
        Object.entries(query).every(([k, v]) => (item as any)[k] === v),
      );
      if (limit) result = result.slice(0, limit);
      return result;
    },
    async create(payload: Omit<T, 'id'>) {
      const item = { ...(payload as any), id: String(nextId++) } as T;
      data.push(item);
      return item;
    },
    async update(id: string, payload: Partial<T>) {
      const idx = data.findIndex(i => String(i.id) === String(id));
      if (idx === -1) return null;
      data[idx] = { ...data[idx], ...payload };
      return data[idx];
    },
    async delete(id: string) {
      data = data.filter(i => String(i.id) !== String(id));
      return true;
    },
  };
}

const base44 = {
  entities: {
    UserProfile: makeStore<AnyRecord>(),
    Contact: makeStore<AnyRecord>(),
    Conversation: makeStore<AnyRecord>(),
    Message: makeStore<AnyRecord>(),
  },
};

export { base44 };
export default base44;
