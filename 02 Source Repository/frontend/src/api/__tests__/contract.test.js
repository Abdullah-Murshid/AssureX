import fs from 'node:fs'
import path from 'node:path'

import { describe, expect, it } from 'vitest'

import { EP } from '../endpoints'

const spec = JSON.parse(
  fs.readFileSync(path.resolve(process.cwd(), 'openapi.json'), 'utf8'),
)

describe('API contract', () => {
  it('uses the AssureX Claim Engine v2 schema', () => {
    expect(spec.info.title).toBe('AssureX Claim Engine API')
    expect(spec.info.version).toBe('2.0.0')
    expect(Object.keys(spec.paths).length).toBeGreaterThanOrEqual(41)
  })

  it('every frontend endpoint exists in the OpenAPI document', () => {
    const missing = Object.entries(EP)
      .map(([name, template]) => ({ name, path: `/api/v1${template}` }))
      .filter(({ path }) => !spec.paths[path])

    expect(missing).toEqual([])
  })

  it('exposes bearer authentication', () => {
    expect(spec.components.securitySchemes.SessionOrBearerAuth).toMatchObject({
      type: 'http',
      scheme: 'bearer',
    })
  })
})
