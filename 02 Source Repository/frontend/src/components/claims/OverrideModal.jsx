import { useState } from 'react'

import { errorMessage } from '../../api/client'
import { reviewDecision } from '../../api/review'
import { REVIEW_ACTIONS } from '../../lib/constants'
import { useToast } from '../../store/toast'
import Button from '../ui/Button'
import { Select, Textarea } from '../ui/Fields'
import Modal from '../ui/Modal'

export default function OverrideModal({ claim, open, onClose, onDone }) {
  const push = useToast((state) => state.push)
  const [action, setAction] = useState('Approved')
  const [comments, setComments] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  const submit = async (event) => {
    event.preventDefault()
    if (!comments.trim()) {
      setError('Reviewer comments are required.')
      return
    }
    setBusy(true)
    setError('')
    try {
      const updated = await reviewDecision(claim.claim_id, action, comments.trim())
      push(`Claim ${claim.claim_id} marked ${updated.status}.`)
      onDone(updated)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Reviewer decision"
      description={claim ? `${claim.claim_id} · ${claim.product?.product_name || claim.product_id}` : ''}
      footer={
        <>
          <Button variant="ghost" onClick={onClose}>Cancel</Button>
          <Button form="override-form" type="submit" loading={busy}>Record decision</Button>
        </>
      }
    >
      <form id="override-form" onSubmit={submit} className="space-y-4">
        <div className="rounded-xl border border-line/70 bg-[#FAFAF8] px-3 py-2 text-xs text-muted">
          Model decision: <span className="text-ink">{claim?.final_decision}</span> ·{' '}
          {claim?.consistency_status}
        </div>
        <Select label="New status" value={action} onChange={(event) => setAction(event.target.value)}>
          {REVIEW_ACTIONS.map((item) => (
            <option key={item} value={item}>{item}</option>
          ))}
        </Select>
        <Textarea
          label="Reviewer comments"
          required
          rows={4}
          value={comments}
          onChange={(event) => setComments(event.target.value)}
          placeholder="Explain the evidence reviewed and the disposition…"
        />
        {error && <p className="text-xs text-status-danger">{error}</p>}
      </form>
    </Modal>
  )
}


