import { HTTP_NOT_FOUND, HTTP_UNAUTHORIZED, IDEMPOTENCY_KEY_HEADER } from '../constants'
import { request, type Failure, type Options } from './request'
import { API_ROUTES } from './routes'
import type { components } from './schema'

export type ChatMessage = components['schemas']['ChatMessageItem']
type ChatConversation = components['schemas']['ChatConversation']
type ChatMessageRequest = components['schemas']['ChatMessageRequest']
type StoredChatMessage = components['schemas']['StoredChatMessage']

export type Conversation =
  | { kind: 'loaded'; messages: ChatMessage[]; nextCursor: string | null }
  | { kind: 'no-session' }
  /** The web chat is turned off: its routes do not exist (ADR 0016). */
  | { kind: 'disabled' }
  | Failure

/**
 * The conversation of the web chat (GET /chat/messages, docs/04-api.md). With `after`, only
 * the messages that came after that one: it is what the screen asks every few seconds.
 */
export async function loadConversation(after: string | null, options: Options = {}): Promise<Conversation> {
  const path = after === null ? API_ROUTES.chatMessages : `${API_ROUTES.chatMessages}?${new URLSearchParams({ after })}`
  const answer = await request(path, options)
  if (answer.kind !== 'answered') return answer
  if (answer.status === HTTP_UNAUTHORIZED) return { kind: 'no-session' }
  if (answer.status === HTTP_NOT_FOUND) return { kind: 'disabled' }
  if (!answer.ok) return { kind: 'api-error' }
  const conversation = answer.body as ChatConversation
  return { kind: 'loaded', messages: conversation.messages, nextCursor: conversation.next_cursor }
}

export type Sent = { kind: 'sent'; id: string } | { kind: 'no-session' } | Failure

/**
 * Writes a message to Platita (POST /chat/messages). The API stores it and answers at once;
 * the reply shows up later in the conversation. The key is generated once per message and
 * sent again unchanged on a retry, so a message is never stored twice.
 */
export async function sendMessage(text: string, idempotencyKey: string, options: Options = {}): Promise<Sent> {
  const body: ChatMessageRequest = { text }
  const answer = await request(API_ROUTES.chatMessages, {
    ...options,
    method: 'POST',
    body,
    headers: { [IDEMPOTENCY_KEY_HEADER]: idempotencyKey },
  })
  if (answer.kind !== 'answered') return answer
  if (answer.status === HTTP_UNAUTHORIZED) return { kind: 'no-session' }
  if (!answer.ok) return { kind: 'api-error' }
  return { kind: 'sent', id: (answer.body as StoredChatMessage).id }
}
