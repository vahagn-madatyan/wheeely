import { createClient } from "@/lib/supabase/server";
import { NavLinks } from "@/components/nav-links";
import { LogoutButton } from "@/components/logout-button";

export default async function AppLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="fixed inset-y-0 left-0 z-10 flex w-64 flex-col bg-gray-900 text-white">
        <div className="flex h-16 items-center px-6">
          <span className="text-xl font-bold tracking-tight">Wheeely</span>
        </div>
        <div className="flex-1 overflow-y-auto px-3 py-4">
          <NavLinks />
        </div>
      </aside>

      {/* Main content area */}
      <div className="flex flex-1 flex-col pl-64">
        {/* Top bar */}
        <header className="flex h-16 items-center justify-end gap-4 border-b border-gray-200 bg-white px-6">
          <span className="text-sm text-gray-600">{user?.email}</span>
          <LogoutButton />
        </header>

        {/* Page content */}
        <main className="flex-1 p-6">{children}</main>
      </div>
    </div>
  );
}
