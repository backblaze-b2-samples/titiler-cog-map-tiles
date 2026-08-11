import { LayerDetail } from "@/components/layers/layer-detail";

export default async function LayerDetailPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return (
    <div className="animate-fade-in">
      <LayerDetail id={id} />
    </div>
  );
}
