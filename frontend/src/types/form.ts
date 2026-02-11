import { z } from "zod";
import { strategyFormSchema, adSchema } from "./strategySchema";

export type StrategyFormData = z.infer<typeof strategyFormSchema>;
export type AdFields = z.infer<typeof adSchema>;

