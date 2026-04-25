import { ReactNode } from "react";

import BottomNav from "./BottomNav";

type Props = {
  title: string;
  children: ReactNode;
};

export default function Layout({ title, children }: Props) {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>{title}</h1>
      </header>
      <main className="app-main">{children}</main>
      <BottomNav />
    </div>
  );
}
