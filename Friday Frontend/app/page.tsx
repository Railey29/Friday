"use client";

import HomeView from "./views/HomeView";
import { useHomeController } from "./controllers/useHomeController";

export default function PageClient() {
  const controller = useHomeController();
  return <HomeView controller={controller} />;
}
