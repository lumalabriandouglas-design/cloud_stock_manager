import { create } from "zustand";
import { persist } from "zustand/middleware";
import { SEED } from "./seed";
import type { Activity, Category, Item, Sale, ShopState } from "./types";

function uid(prefix: string) {
  return `${prefix}-${Math.random().toString(36).slice(2, 9)}`;
}

function titleCase(name: string) {
  return name.trim().replace(/\s+/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

type Actions = {
  setCompanyName: (name: string) => void;
  addCategory: (name: string) => string | null;
  removeCategory: (id: string) => void;
  upsertItem: (draft: {
    id?: string;
    name: string;
    categoryId: string | null;
    buyPrice: number;
    sellPrice: number;
    quantity?: number;
    reorderLevel: number;
  }) => { ok: true } | { ok: false; error: string };
  receiveStock: (input: {
    itemId?: string;
    name: string;
    quantity: number;
    buyPrice?: number;
    sellPrice?: number;
    categoryId?: string | null;
  }) => { ok: true } | { ok: false; error: string };
  recordSale: (input: {
    itemId: string;
    quantity: number;
    sellPrice?: number;
  }) => { ok: true } | { ok: false; error: string };
  deleteItem: (id: string) => void;
  resetDemo: () => void;
  applyWorkspace: (ws: {
    companyId: string;
    companyName: string;
    isPlatformAdmin: boolean;
    membership: {
      role: "owner" | "staff";
      canManageStock: boolean;
      canEditItems: boolean;
      canViewReports: boolean;
      canManageCategories: boolean;
      canManageTeam: boolean;
    };
    subscription: { active: boolean; status: string };
    categories: Category[];
    items: Item[];
    sales: Sale[];
    activity: Activity[];
  }) => void;
};

export const useShop = create<ShopState & Actions>()(
  persist(
    (set, get) => ({
      ...SEED,
      companyId: null,
      cloud: false,
      subActive: true,
      subStatus: "trial",
      isPlatformAdmin: false,
      isOwner: true,
      canManageStock: true,
      canEditItems: true,
      canViewReports: true,
      canManageCategories: true,
      canManageTeam: true,
      setCompanyName: (name) => set({ companyName: name.trim() || get().companyName }),
      addCategory: (name) => {
        const trimmed = titleCase(name);
        if (!trimmed) return null;
        const exists = get().categories.some(
          (c) => c.name.toLowerCase() === trimmed.toLowerCase(),
        );
        if (exists) return get().categories.find((c) => c.name.toLowerCase() === trimmed.toLowerCase())!.id;
        const id = uid("cat");
        set({ categories: [...get().categories, { id, name: trimmed }] });
        return id;
      },
      removeCategory: (id) =>
        set({
          categories: get().categories.filter((c) => c.id !== id),
          items: get().items.map((it) =>
            it.categoryId === id ? { ...it, categoryId: null } : it,
          ),
        }),
      upsertItem: (draft) => {
        const name = titleCase(draft.name);
        if (!name) return { ok: false, error: "Give the product a name." };
        const items = get().items;
        const clash = items.find(
          (it) =>
            it.name.toLowerCase() === name.toLowerCase() && it.id !== draft.id,
        );
        if (clash) return { ok: false, error: "That product already exists." };
        const now = new Date().toISOString();
        if (draft.id) {
          const existing = items.find((it) => it.id === draft.id);
          if (!existing) return { ok: false, error: "Product not found." };
          set({
            items: items.map((it) =>
              it.id === draft.id
                ? {
                    ...it,
                    name,
                    categoryId: draft.categoryId,
                    buyPrice: draft.buyPrice,
                    sellPrice: draft.sellPrice,
                    reorderLevel: draft.reorderLevel,
                    quantity:
                      draft.quantity === undefined ? it.quantity : draft.quantity,
                  }
                : it,
            ),
            activity: [
              {
                id: uid("ac"),
                kind: "edit" as const,
                message: `Updated ${name}`,
                createdAt: now,
              },
              ...get().activity,
            ].slice(0, 40),
          });
          return { ok: true };
        }
        const item: Item = {
          id: uid("it"),
          name,
          categoryId: draft.categoryId,
          buyPrice: draft.buyPrice,
          sellPrice: draft.sellPrice,
          quantity: draft.quantity ?? 0,
          reorderLevel: draft.reorderLevel,
        };
        set({ items: [...items, item] });
        return { ok: true };
      },
      receiveStock: (input) => {
        const qty = Math.floor(input.quantity);
        if (qty < 1) return { ok: false, error: "Quantity must be at least 1." };
        const name = titleCase(input.name);
        if (!name) return { ok: false, error: "Choose or name a product." };
        const now = new Date().toISOString();
        let items = [...get().items];
        let item = input.itemId
          ? items.find((it) => it.id === input.itemId)
          : items.find((it) => it.name.toLowerCase() === name.toLowerCase());
        if (!item) {
          item = {
            id: uid("it"),
            name,
            categoryId: input.categoryId ?? null,
            buyPrice: input.buyPrice ?? 0,
            sellPrice: input.sellPrice ?? 0,
            quantity: 0,
            reorderLevel: 5,
          };
          items = [...items, item];
        }
        const next: Item = {
          ...item,
          quantity: item.quantity + qty,
          buyPrice: input.buyPrice ?? item.buyPrice,
          sellPrice: input.sellPrice ?? item.sellPrice,
          categoryId: input.categoryId ?? item.categoryId,
        };
        set({
          items: items.map((it) => (it.id === next.id ? next : it)),
          stockMoves: [
            {
              id: uid("st"),
              itemId: next.id,
              itemName: next.name,
              quantity: qty,
              createdAt: now,
            },
            ...get().stockMoves,
          ],
          activity: [
            {
              id: uid("ac"),
              kind: "stock" as const,
              message: `Added ${qty} × ${next.name}`,
              createdAt: now,
            },
            ...get().activity,
          ].slice(0, 40),
        });
        return { ok: true };
      },
      recordSale: (input) => {
        const qty = Math.floor(input.quantity);
        if (qty < 1) return { ok: false, error: "Quantity must be at least 1." };
        const item = get().items.find((it) => it.id === input.itemId);
        if (!item) return { ok: false, error: "Product not found." };
        if (item.quantity < qty) {
          return { ok: false, error: `Only ${item.quantity} in stock.` };
        }
        const price = input.sellPrice ?? item.sellPrice;
        const now = new Date().toISOString();
        set({
          items: get().items.map((it) =>
            it.id === item.id ? { ...it, quantity: it.quantity - qty } : it,
          ),
          sales: [
            {
              id: uid("sa"),
              itemId: item.id,
              itemName: item.name,
              quantity: qty,
              sellPrice: price,
              costPrice: item.buyPrice,
              createdAt: now,
            },
            ...get().sales,
          ],
          activity: [
            {
              id: uid("ac"),
              kind: "sale" as const,
              message: `Sold ${qty} × ${item.name}`,
              createdAt: now,
            },
            ...get().activity,
          ].slice(0, 40),
        });
        return { ok: true };
      },
      deleteItem: (id) =>
        set({ items: get().items.filter((it) => it.id !== id) }),
      resetDemo: () => set({ ...SEED }),
      applyWorkspace: (ws: {
        companyId: string;
        companyName: string;
        isPlatformAdmin: boolean;
        membership: {
          role: "owner" | "staff";
          canManageStock: boolean;
          canEditItems: boolean;
          canViewReports: boolean;
          canManageCategories: boolean;
          canManageTeam: boolean;
        };
        subscription: { active: boolean; status: string };
        categories: Category[];
        items: Item[];
        sales: Sale[];
        activity: Activity[];
      }) =>
        set({
          cloud: true,
          companyId: ws.companyId,
          companyName: ws.companyName,
          isPlatformAdmin: ws.isPlatformAdmin,
          isOwner: ws.membership.role === "owner",
          canManageStock: ws.membership.role === "owner" || ws.membership.canManageStock,
          canEditItems: ws.membership.role === "owner" || ws.membership.canEditItems,
          canViewReports: ws.membership.role === "owner" || ws.membership.canViewReports,
          canManageCategories: ws.membership.role === "owner" || ws.membership.canManageCategories,
          canManageTeam: ws.membership.role === "owner" || ws.membership.canManageTeam,
          subActive: ws.subscription.active,
          subStatus: ws.subscription.status,
          categories: ws.categories,
          items: ws.items,
          sales: ws.sales,
          activity: ws.activity,
        }),
    }),
    { name: "csm-shop-v1" },
  ),
);

