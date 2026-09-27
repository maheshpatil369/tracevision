import { NavLink, Outlet } from "react-router-dom";

const navItems = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/cases", label: "Cases" },
  { to: "/models", label: "Models" },
  { to: "/settings", label: "Settings" },
];

export default function Layout() {
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 bg-ink text-white flex flex-col">
        <div className="px-4 py-5 border-b border-white/10">
          <div className="font-semibold tracking-wide text-lg">TRACEVISION</div>
          <div className="text-xs text-white/50">Forensic video analysis</div>
        </div>
        <nav className="flex-1 py-3">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) =>
                `block px-4 py-2 text-sm ${isActive ? "bg-white/10 font-medium" : "text-white/80 hover:bg-white/5"}`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-4 py-3 text-[11px] text-white/40 border-t border-white/10">
          Investigative decision-support tool.
          <br />
          Not an automatic legal determination.
        </div>
      </aside>
      <main className="flex-1 min-w-0">
        <Outlet />
      </main>
    </div>
  );
}
