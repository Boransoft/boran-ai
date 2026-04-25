import type { AuthUser } from "../types/auth";

type TopBarProps = {
  user: AuthUser | null;
  onLogout: () => void;
  showAdminSwitch?: boolean;
  adminMode?: boolean;
};

export default function TopBar({ user, onLogout, showAdminSwitch = false, adminMode = false }: TopBarProps) {
  const identity = user?.display_name || user?.username || user?.email || "authenticated user";
  const switchLabel = adminMode ? "Sohbet" : "Admin";
  const switchHref = adminMode ? "/" : "/admin";

  return (
    <header className="sticky top-0 z-30 border-b border-slate-700/80 bg-slate-950/95 px-3 pb-1.5 pt-[calc(0.4rem+env(safe-area-inset-top))] backdrop-blur sm:px-4 sm:pb-2 sm:pt-[calc(0.55rem+env(safe-area-inset-top))]">
      <div className="mx-auto flex w-full max-w-4xl items-center justify-between gap-2">
        <div className="min-w-0">
          <p className="text-sm font-semibold tracking-wide text-white">boranizm</p>
          <p className="truncate text-[10px] text-slate-400 sm:text-xs">{identity}</p>
        </div>
        <div className="flex items-center gap-2">
          {showAdminSwitch ? (
            <a
              href={switchHref}
              className="inline-flex h-8 shrink-0 items-center rounded-lg border border-slate-700 bg-slate-900/70 px-2.5 text-[11px] font-medium text-slate-300 transition hover:border-slate-500 hover:text-slate-100 sm:h-9 sm:px-3"
            >
              {switchLabel}
            </a>
          ) : null}
          <button
            type="button"
            onClick={onLogout}
            className="h-8 shrink-0 rounded-lg border border-slate-700 bg-slate-900/70 px-2.5 text-[11px] font-medium text-slate-300 transition hover:border-slate-500 hover:text-slate-100 active:scale-95 sm:h-9 sm:px-3"
          >
            Cikis
          </button>
        </div>
      </div>
    </header>
  );
}
