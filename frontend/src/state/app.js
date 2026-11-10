// App-wide state shared by the pages: profile and server health.
import { createContext, useContext } from "react";

export const AppCtx = createContext({ profile: null, health: null, reloadProfile: async () => null, reloadHealth: async () => null });
export const useApp = () => useContext(AppCtx);
