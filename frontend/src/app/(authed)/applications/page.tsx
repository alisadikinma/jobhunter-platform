"use client";

import {
  closestCenter,
  DndContext,
  type DragEndEvent,
  PointerSensor,
  useDroppable,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import Link from "next/link";

import {
  useKanban,
  useUpdateApplication,
  type Application,
} from "@/hooks/useApplications";

const COLUMNS = [
  "targeting",
  "cv_generating",
  "cv_ready",
  "applied",
  "email_sent",
  "replied",
  "interview_scheduled",
  "interviewed",
  "offered",
  "accepted",
  "rejected",
  "ghosted",
] as const;

export default function ApplicationsPage() {
  const { data, isLoading } = useKanban();
  const update = useUpdateApplication();
  const sensors = useSensors(useSensor(PointerSensor, { activationConstraint: { distance: 5 } }));

  function onDragEnd(e: DragEndEvent) {
    const id = e.active?.id;
    const targetStatus = e.over?.id;
    if (!id || !targetStatus || typeof targetStatus !== "string") return;

    const parsed = String(id).replace(/^app-/, "");
    const numericId = Number(parsed);
    if (Number.isNaN(numericId)) return;

    update.mutate({ id: numericId, patch: { status: targetStatus } });
  }

  if (isLoading) return <div className="text-neutral-500">Loading…</div>;

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">Applications</h1>
      <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={onDragEnd}>
        <div className="flex gap-2 overflow-x-auto pb-4">
          {COLUMNS.map((status) => {
            const items = data?.columns?.[status] ?? [];
            return (
              <KanbanColumn key={status} status={status} items={items} />
            );
          })}
        </div>
      </DndContext>
    </div>
  );
}

function KanbanColumn({ status, items }: { status: string; items: Application[] }) {
  const { setNodeRef, isOver } = useDroppable({ id: status });
  return (
    <div
      ref={setNodeRef}
      className={`flex min-w-[220px] max-w-[240px] flex-col rounded-card border p-2 ${
        isOver ? "border-brand-blue bg-neutral-900" : "border-neutral-800 bg-neutral-950"
      }`}
    >
      <div className="mb-2 flex items-center justify-between px-1">
        <h2 className="text-xs uppercase text-neutral-500">{status.replace(/_/g, " ")}</h2>
        <span className="text-xs text-neutral-600">{items.length}</span>
      </div>
      <SortableContext items={items.map((a) => `app-${a.id}`)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2">
          {items.map((app) => (
            <ApplicationCard key={app.id} application={app} />
          ))}
        </div>
      </SortableContext>
    </div>
  );
}

function ApplicationCard({ application }: { application: Application }) {
  const { setNodeRef, attributes, listeners, transform, transition } = useSortable({
    id: `app-${application.id}`,
  });
  return (
    <div
      ref={setNodeRef}
      {...attributes}
      {...listeners}
      style={{
        transform: CSS.Translate.toString(transform),
        transition,
      }}
      className="card cursor-grab space-y-1 active:cursor-grabbing"
    >
      <Link
        href={`/applications/${application.id}`}
        onClick={(e) => e.stopPropagation()}
        className="block text-sm hover:text-brand-blue"
      >
        App #{application.id}
      </Link>
      <div className="text-xs text-neutral-500">
        Job #{application.job_id ?? "—"}
      </div>
      {application.notes && (
        <p className="line-clamp-2 text-xs text-neutral-400">{application.notes}</p>
      )}
    </div>
  );
}
