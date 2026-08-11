"use client";

import type { ReactNode } from "react";
import { toast } from "sonner";

import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "@/components/ui/alert-dialog";
import { useDeleteLayer } from "@/lib/queries";

export function DeleteLayerDialog({
  layerId,
  layerName,
  trigger,
  onDeleted,
}: {
  layerId: string;
  layerName: string;
  trigger: ReactNode;
  onDeleted?: () => void;
}) {
  const remove = useDeleteLayer();

  const onConfirm = () => {
    remove.mutate(layerId, {
      onSuccess: () => {
        toast.success(`Deleted “${layerName}”`, {
          description: "The COG and its sidecar were removed from B2.",
        });
        onDeleted?.();
      },
      onError: (error) => toast.error("Delete failed", { description: error.message }),
    });
  };

  return (
    <AlertDialog>
      <AlertDialogTrigger asChild>{trigger}</AlertDialogTrigger>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Delete this layer?</AlertDialogTitle>
          <AlertDialogDescription>
            This permanently deletes the COG and its render sidecar for{" "}
            <strong>{layerName}</strong> from your B2 bucket. This can’t be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancel</AlertDialogCancel>
          <AlertDialogAction
            onClick={onConfirm}
            disabled={remove.isPending}
            className="bg-destructive text-white hover:bg-destructive/90"
          >
            {remove.isPending ? "Deleting…" : "Delete layer"}
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );
}
