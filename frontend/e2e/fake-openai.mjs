/**
 * A fake of the OpenAI Responses API, for the end-to-end test (#79). The worker reaches it
 * through OPENAI_BASE_URL, which the SDK reads by itself, so the real adapter runs whole:
 * the request, the structured output and its validation. Nothing leaves the machine and
 * nothing is paid.
 *
 * It answers every classification with the expense of the test. Node only, no dependencies.
 */
import { createServer } from 'node:http'

const PORT = 8080
const RESPONSES_PATH = '/v1/responses'

// What the model answers for "gasté 1500 en el súper con Mercado Pago": the strict schema of
// backend/app/adapters/outbound/llm_client/openai_llm.py, every field present.
const CLASSIFICATION = {
  message_class: 'registration',
  registration_type: 'expense',
  amount: '1500',
  account: 'Mercado Pago',
  category: 'Supermercado',
  currency: null,
  currency_words: null,
  transaction_date: null,
  proposed_category: null,
  several_movements: false,
  pending_reply: null,
  accepts_proposal: false,
}

function response() {
  return {
    id: 'resp_e2e',
    object: 'response',
    created_at: Math.floor(Date.now() / 1000),
    status: 'completed',
    model: 'gpt-5.4-mini',
    output: [
      {
        type: 'message',
        id: 'msg_e2e',
        status: 'completed',
        role: 'assistant',
        content: [{ type: 'output_text', text: JSON.stringify(CLASSIFICATION), annotations: [] }],
      },
    ],
    parallel_tool_calls: false,
    tool_choice: 'auto',
    tools: [],
    usage: {
      input_tokens: 812,
      input_tokens_details: { cached_tokens: 0 },
      output_tokens: 64,
      output_tokens_details: { reasoning_tokens: 0 },
      total_tokens: 876,
    },
  }
}

createServer((request, reply) => {
  // The body is read and dropped: the answer does not depend on it.
  request.resume()
  request.on('end', () => {
    if (request.method === 'POST' && request.url === RESPONSES_PATH) {
      reply.writeHead(200, { 'Content-Type': 'application/json' })
      reply.end(JSON.stringify(response()))
      return
    }
    reply.writeHead(404)
    reply.end()
  })
}).listen(PORT)
