import { api, unwrap } from './client'
import { EP, fill } from './endpoints'

export const reviewQueue = (params = {}) =>
  unwrap(api.get(EP.reviewQueue, { params }))

export const reviewStats = () => unwrap(api.get(EP.reviewStats))

export const reviewDecision = (claimId, action, comments) =>
  unwrap(
    api.post(fill(EP.reviewDecision, { claim_id: claimId }), {
      action,
      comments,
    }),
  )
