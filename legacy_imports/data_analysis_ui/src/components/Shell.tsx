import { Outlet } from "react-router-dom";
import { Nav } from "./Nav";

export function Shell() {
  return (
    <div className="h-full flex bg-[#f4f5f7] overflow-hidden">
      <Nav />
      <div className="flex-1 flex flex-col overflow-hidden">
        <Outlet />
      </div>
    </div>
  );
}
