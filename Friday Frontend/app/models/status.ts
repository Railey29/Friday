export interface Stats {
  battery: number;
  temperature: number;
  cpu: number;
  connectivity: string;
  uptime: string;
}

export { API_URL, BACKEND_URL } from "@/config/network";
