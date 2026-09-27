import { fetchBloodwork } from "@/lib/data";
import { BloodworkClient, type Marker } from "./bloodwork-client";

export const dynamic = "force-dynamic";

export default async function BloodworkPage() {
  const markers = (await fetchBloodwork()) as Marker[];
  return <BloodworkClient markers={markers} />;
}
