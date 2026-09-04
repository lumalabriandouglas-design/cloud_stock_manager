export type Category = {
  id: string;
  name: string;
};

export type Item = {
  id: string;
  name: string;
  categoryId: string | null;
  buyPrice: number;
  sellPrice: number;
  quantity: number;
  reorderLevel: number;
};

export type Sale = {
  id: string;
  itemId: string;
  itemName: string;
  quantity: number;
  sellPrice: number;
  costPrice: number;
  createdAt: string;
};

export type StockMove = {
  id: string;
  itemId: string;
  itemName: string;
  quantity: number;
  createdAt: string;
};

export type Activity = {
  id: string;
  kind: "sale" | "stock" | "edit";
  message: string;
  createdAt: string;
};

export type ShopState = {
  companyName: string;
  companyId: string | null;
  cloud: boolean;
  subActive: boolean;
  subStatus: string;
  isPlatformAdmin: boolean;
  isOwner: boolean;
  canManageStock: boolean;
  canEditItems: boolean;
  canViewReports: boolean;
  canManageCategories: boolean;
  canManageTeam: boolean;
  categories: Category[];
  items: Item[];
  sales: Sale[];
  stockMoves: StockMove[];
  activity: Activity[];
};
