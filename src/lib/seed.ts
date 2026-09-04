import type { ShopState } from "./types";

function id(prefix: string, n: number) {
  return `${prefix}-${n}`;
}

const now = Date.now();

function hoursAgo(h: number) {
  return new Date(now - h * 3600_000).toISOString();
}

export const SEED: ShopState = {
  companyName: "Nakasero Mart",
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
  categories: [
    { id: "cat-1", name: "Grains" },
    { id: "cat-2", name: "Oils" },
    { id: "cat-3", name: "Household" },
    { id: "cat-4", name: "Drinks" },
    { id: "cat-5", name: "Dairy" },
  ],
  items: [
    { id: id("it", 1), name: "Rice 25kg", categoryId: "cat-1", buyPrice: 98000, sellPrice: 115000, quantity: 18, reorderLevel: 6 },
    { id: id("it", 2), name: "Maize flour 2kg", categoryId: "cat-1", buyPrice: 4200, sellPrice: 5500, quantity: 42, reorderLevel: 12 },
    { id: id("it", 3), name: "Sugar 1kg", categoryId: "cat-1", buyPrice: 3800, sellPrice: 4800, quantity: 9, reorderLevel: 15 },
    { id: id("it", 4), name: "Cooking oil 5L", categoryId: "cat-2", buyPrice: 22000, sellPrice: 27000, quantity: 11, reorderLevel: 8 },
    { id: id("it", 5), name: "Salt 500g", categoryId: "cat-1", buyPrice: 800, sellPrice: 1200, quantity: 60, reorderLevel: 20 },
    { id: id("it", 6), name: "Bar soap", categoryId: "cat-3", buyPrice: 1500, sellPrice: 2200, quantity: 4, reorderLevel: 10 },
    { id: id("it", 7), name: "Laundry powder 1kg", categoryId: "cat-3", buyPrice: 6500, sellPrice: 8200, quantity: 14, reorderLevel: 6 },
    { id: id("it", 8), name: "Fresh milk 500ml", categoryId: "cat-5", buyPrice: 1800, sellPrice: 2500, quantity: 7, reorderLevel: 12 },
    { id: id("it", 9), name: "Soda crate", categoryId: "cat-4", buyPrice: 18000, sellPrice: 24000, quantity: 6, reorderLevel: 4 },
    { id: id("it", 10), name: "Mineral water 1.5L", categoryId: "cat-4", buyPrice: 1500, sellPrice: 2500, quantity: 28, reorderLevel: 10 },
    { id: id("it", 11), name: "Tea leaves 250g", categoryId: "cat-1", buyPrice: 4500, sellPrice: 6000, quantity: 16, reorderLevel: 6 },
    { id: id("it", 12), name: "Matches pack", categoryId: "cat-3", buyPrice: 400, sellPrice: 700, quantity: 3, reorderLevel: 8 },
  ],
  sales: [
    { id: "sa-1", itemId: "it-3", itemName: "Sugar 1kg", quantity: 4, sellPrice: 4800, costPrice: 3800, createdAt: hoursAgo(1) },
    { id: "sa-2", itemId: "it-8", itemName: "Fresh milk 500ml", quantity: 6, sellPrice: 2500, costPrice: 1800, createdAt: hoursAgo(3) },
    { id: "sa-3", itemId: "it-2", itemName: "Maize flour 2kg", quantity: 3, sellPrice: 5500, costPrice: 4200, createdAt: hoursAgo(5) },
    { id: "sa-4", itemId: "it-6", itemName: "Bar soap", quantity: 2, sellPrice: 2200, costPrice: 1500, createdAt: hoursAgo(8) },
    { id: "sa-5", itemId: "it-10", itemName: "Mineral water 1.5L", quantity: 8, sellPrice: 2500, costPrice: 1500, createdAt: hoursAgo(26) },
    { id: "sa-6", itemId: "it-1", itemName: "Rice 25kg", quantity: 1, sellPrice: 115000, costPrice: 98000, createdAt: hoursAgo(30) },
    { id: "sa-7", itemId: "it-4", itemName: "Cooking oil 5L", quantity: 2, sellPrice: 27000, costPrice: 22000, createdAt: hoursAgo(50) },
    { id: "sa-8", itemId: "it-9", itemName: "Soda crate", quantity: 1, sellPrice: 24000, costPrice: 18000, createdAt: hoursAgo(54) },
  ],
  stockMoves: [
    { id: "st-1", itemId: "it-2", itemName: "Maize flour 2kg", quantity: 20, createdAt: hoursAgo(12) },
    { id: "st-2", itemId: "it-4", itemName: "Cooking oil 5L", quantity: 6, createdAt: hoursAgo(40) },
  ],
  activity: [
    { id: "ac-1", kind: "sale", message: "Sold 4 × Sugar 1kg", createdAt: hoursAgo(1) },
    { id: "ac-2", kind: "sale", message: "Sold 6 × Fresh milk 500ml", createdAt: hoursAgo(3) },
    { id: "ac-3", kind: "sale", message: "Sold 3 × Maize flour 2kg", createdAt: hoursAgo(5) },
    { id: "ac-4", kind: "stock", message: "Added 20 × Maize flour 2kg", createdAt: hoursAgo(12) },
    { id: "ac-5", kind: "sale", message: "Sold 2 × Bar soap", createdAt: hoursAgo(8) },
  ],
};
