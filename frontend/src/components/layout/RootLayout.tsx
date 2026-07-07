import { Outlet } from "react-router-dom";

export default function RootLayout() {
  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <main className="flex-grow">
        <Outlet />
      </main>
    </div>
  );
}
