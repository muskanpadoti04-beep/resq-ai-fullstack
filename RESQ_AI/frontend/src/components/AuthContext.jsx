import React, { createContext, useContext } from "react";

const RANK = { viewer: 1, operator: 2, admin: 3 };
const Ctx = createContext({ username: "", role: "viewer" });

export const AuthProvider = Ctx.Provider;
export const useAuth = () => useContext(Ctx);
/** true when `role` is at least `minimum` (viewer < operator < admin) */
export const can = (role, minimum) => (RANK[role] || 0) >= RANK[minimum];
