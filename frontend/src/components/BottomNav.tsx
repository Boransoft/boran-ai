import { NavLink } from "react-router-dom";

const links = [
  { to: "/chat", label: "Chat" },
  { to: "/voice", label: "Voice" },
  { to: "/documents", label: "Docs" },
  { to: "/learning", label: "Learning" },
  { to: "/settings", label: "Settings" },
];

export default function BottomNav() {
  return (
    <nav className="bottom-nav" aria-label="Main navigation">
      {links.map((link) => (
        <NavLink
          key={link.to}
          to={link.to}
          className={({ isActive }) => `bottom-nav-item ${isActive ? "active" : ""}`}
        >
          {link.label}
        </NavLink>
      ))}
    </nav>
  );
}
