
import { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../features/auth/AuthContext";
import { useTheme } from "../features/theme/ThemeContext";
import ThemeToggle from "../components/ThemeToggle";

const navigation = [
  { label: "Dashboard", path: "/", icon: "⌂" },
  { label: "Habits", path: "/habits", icon: "↻" },
  { label: "Tasks", path: "/tasks", icon: "☑" },
  { label: "Reports", path: "/reports", icon: "▥" },
];

export default function AppLayout() {
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);

  const { user, logout } = useAuth();
  const { isDark } = useTheme();
  const navigate = useNavigate();

  const sidebarStyle = isDark
    ? "bg-[#181818] border-[#303030] text-white"
    : "bg-white border-neutral-200 text-neutral-900";

  const mutedStyle = isDark
    ? "text-neutral-400 hover:bg-[#292929]"
    : "text-neutral-500 hover:bg-neutral-100";

  const activeStyle = isDark
    ? "bg-orange-500 text-black"
    : "bg-neutral-900 text-white";

  async function handleLogout() {
    if (!window.confirm("Are you sure you want to log out?")) return;

    setLoggingOut(true);

    try {
      await logout();
    } finally {
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className={`flex min-h-screen ${
      isDark
        ? "bg-[#111111] text-white"
        : "bg-neutral-50 text-neutral-900"
    }`}>
      {mobileOpen && (
        <button
          type="button"
          aria-label="Close sidebar"
          onClick={() => setMobileOpen(false)}
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
        />
      )}

      <aside
        className={`
          fixed inset-y-0 left-0 z-50 flex flex-col border-r
          transition-all duration-200
          ${sidebarStyle}
          ${collapsed ? "w-20" : "w-64"}
          ${mobileOpen ? "translate-x-0" : "-translate-x-full"}
          md:sticky md:top-0 md:h-screen md:translate-x-0
        `}
      >
        <div className="flex h-20 items-center justify-between border-b border-neutral-500/20 px-4">
          {!collapsed && (
            <h1 className="text-lg font-bold tracking-tight">
              Habit Tracker<span className="text-orange-500">.</span>
            </h1>
          )}

          <button
            type="button"
            onClick={() => {
              setCollapsed((value) => !value);
              setMobileOpen(false);
            }}
            className="hidden rounded-lg p-2 hover:bg-neutral-500/10 md:block"
            aria-label="Toggle sidebar"
            title="Collapse or expand sidebar"
          >
            ☰
          </button>

          <button
            type="button"
            onClick={() => setMobileOpen(false)}
            className="rounded-lg p-2 hover:bg-neutral-500/10 md:hidden"
            aria-label="Close menu"
          >
            ✕
          </button>
        </div>

        <nav className="flex-1 space-y-2 p-3">
          {navigation.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.path === "/"}
              onClick={() => setMobileOpen(false)}
              title={collapsed ? item.label : undefined}
              className={({ isActive }) => `
                flex items-center gap-3 rounded-lg px-4 py-3
                text-sm font-medium transition
                ${isActive ? activeStyle : mutedStyle}
              `}
            >
              <span className="w-5 text-center text-lg">
                {item.icon}
              </span>

              {!collapsed && <span>{item.label}</span>}
            </NavLink>
          ))}
        </nav>

        <div className="space-y-4 border-t border-neutral-500/20 p-4">
          <div className={collapsed ? "flex justify-center" : ""}>
            <ThemeToggle />
          </div>

          {!collapsed && user && (
            <p className="break-all text-xs text-neutral-500">
              {user.email}
            </p>
          )}

          <button
            type="button"
            onClick={handleLogout}
            disabled={loggingOut}
            title="Log out"
            className={`
              flex w-full items-center gap-3 rounded-lg border
              border-neutral-500/30 px-4 py-3 text-sm
              hover:bg-neutral-500/10 disabled:opacity-50
              ${collapsed ? "justify-center" : ""}
            `}
          >
            <span>↪</span>
            {!collapsed && (
              <span>{loggingOut ? "Logging out..." : "Log out"}</span>
            )}
          </button>
        </div>
      </aside>

      <div className="min-w-0 flex-1">
        <header className="sticky top-0 z-30 flex h-14 items-center border-b border-neutral-500/20 bg-inherit px-4 md:hidden">
          <button
            type="button"
            onClick={() => setMobileOpen(true)}
            className="rounded-lg p-2 hover:bg-neutral-500/10"
            aria-label="Open sidebar"
          >
            ☰
          </button>

          <span className="ml-3 font-semibold">
            Habit Tracker<span className="text-orange-500">.</span>
          </span>
        </header>

        <main className="min-w-0 p-5 md:p-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
