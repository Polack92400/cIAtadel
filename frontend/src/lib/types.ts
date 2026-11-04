export type Role = "owner" | "admin" | "member" | "viewer";

export interface MembershipSummary {
  tenant_id: string;
  tenant_name: string;
  tenant_slug: string;
  role: Role;
}

export interface Me {
  id: string;
  email: string;
  full_name: string;
  memberships: MembershipSummary[];
}

export type DocumentStatus = "pending" | "processing" | "ready" | "failed";

export interface DocumentItem {
  id: string;
  title: string;
  original_filename: string;
  size_bytes: number;
  status: DocumentStatus;
  error_code: string;
  error_message: string;
  page_count: number | null;
  chunk_count: number;
  matter: string | null;
  matter_name: string | null;
  uploaded_by_email: string | null;
  created_at: string;
  processed_at: string | null;
}

export interface Paginated<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}

export interface Matter {
  id: string;
  name: string;
  reference: string;
  description: string;
  is_restricted: boolean;
  allowed_members: string[];
  document_count: number;
  created_at: string;
}

export interface Citation {
  number: number;
  used: boolean;
  document: string | null;
  document_title: string;
  page_number: number | null;
  score: number | null;
  excerpt: string | null;
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  insufficient_context: boolean;
  model_name: string;
  latency_ms: number | null;
  created_at: string;
  citations: Citation[];
}

export interface Conversation {
  id: string;
  title: string;
  matter: string | null;
  matter_name: string | null;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface Member {
  id: string;
  user_id: string;
  email: string;
  full_name: string;
  role: Role;
  is_active: boolean;
  created_at: string;
  last_login: string | null;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  member_count: number;
}

export interface AuditEvent {
  id: string;
  created_at: string;
  actor_email: string;
  category: "security" | "document" | "conversation" | "admin";
  action: string;
  outcome: string;
  target_type: string;
  target_id: string;
  target_label: string;
  metadata: Record<string, unknown>;
  ip_address: string | null;
  request_id: string;
}

export interface Dashboard {
  tenant: { id: string; name: string };
  role: Role;
  documents_by_status: Record<DocumentStatus, number>;
  document_total: number;
  matter_count: number;
  conversation_count: number;
  recent_documents: DocumentItem[];
  recent_conversations: Conversation[];
}
