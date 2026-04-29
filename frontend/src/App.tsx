import { NavLink, Route, Routes } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import Preferences from "./pages/Preferences";
import Products from "./pages/Products";
import WeekPlan from "./pages/WeekPlan";
import ShoppingList from "./pages/ShoppingList";
import History from "./pages/History";
import Settings from "./pages/Settings";

const navItems = [
  { to: "/", label: "Dashboard" },
  { to: "/plan", label: "Wochenplan" },
  { to: "/shopping", label: "Einkaufsliste" },
  { to: "/preferences", label: "Vorlieben" },
  { to: "/products", label: "Zutaten" },
  { to: "/history", label: "Historie" },
  { to: "/settings", label: "Einstellungen" },
];

export default function App() {
  return (
    <div className="min-h-full bg-neutral-50 text-neutral-900 dark:bg-neutral-950 dark:text-neutral-100">
      <header className="border-b border-neutral-200 dark:border-neutral-800">
        <nav className="mx-auto flex max-w-5xl flex-wrap gap-4 px-4 py-3 text-sm">
          <span className="font-semibold">🍽️ Meal Planner</span>
          <div className="flex flex-wrap gap-3">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  isActive ? "font-medium underline" : "text-neutral-500 hover:text-neutral-900"
                }
              >
                {item.label}
              </NavLink>
            ))}
          </div>
        </nav>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-6">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/plan" element={<WeekPlan />} />
          <Route path="/shopping" element={<ShoppingList />} />
          <Route path="/preferences" element={<Preferences />} />
          <Route path="/products" element={<Products />} />
          <Route path="/history" element={<History />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}
