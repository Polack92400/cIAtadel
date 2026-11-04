"use client";

import { useParams } from "next/navigation";
import { AssistantView } from "@/components/app/assistant-view";

export default function ConversationPage() {
  const { id } = useParams<{ id: string }>();
  return <AssistantView conversationId={id} />;
}
