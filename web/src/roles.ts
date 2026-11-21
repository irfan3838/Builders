// Which screens each role sees. The server enforces the data rules; this only keeps the navigation honest.
import type { View } from "./state/store";

const FINANCE: View[] = ["workspace", "dashboards", "mail", "tasks", "helpdesk", "expenses", "travel", "claims", "payments", "budgets", "reports"];
const BY_ROLE: Record<string, View[]> = {
  admin: FINANCE,
  finance_approver: FINANCE,
  ceo: ["workspace", "dashboards", "mail", "budgets", "reports"],
  hr_admin: ["workspace", "mail", "tasks", "helpdesk", "expenses", "travel", "claims"],
  employee: ["workspace", "mail", "tasks", "helpdesk", "expenses", "travel", "claims"],
};

export const allowedViews = (role: string): View[] => BY_ROLE[role] ?? BY_ROLE.employee;
export const canSee = (role: string, v: View) => allowedViews(role).includes(v);
export const roleLabel = (role: string) =>
  ({ admin: "Admin", finance_approver: "Finance Approver", hr_admin: "HR Admin", ceo: "CEO" } as Record<string, string>)[role] ?? "Employee";
