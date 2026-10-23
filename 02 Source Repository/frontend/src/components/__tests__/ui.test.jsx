import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'

import Badge from '../ui/Badge'
import Button from '../ui/Button'
import Pagination from '../ui/Pagination'
import StatCard from '../ui/StatCard'

describe('UI primitives', () => {
  it('renders a button with its label', () => {
    render(<Button>Save claim</Button>)
    expect(screen.getByRole('button', { name: 'Save claim' })).toBeEnabled()
  })

  it('disables a loading button', () => {
    render(<Button loading>Saving</Button>)
    const button = screen.getByRole('button')
    expect(button).toBeDisabled()
    expect(button.querySelector('.animate-spin')).toBeTruthy()
  })

  it('renders badge tones', () => {
    render(<Badge tone="success">Approved</Badge>)
    expect(screen.getByText('Approved')).toHaveClass('text-status-success')
  })

  it('renders stat cards and counts up to the value', async () => {
    render(<StatCard label="Total claims" value={17} hint="All claims" />)
    expect(screen.getByText('Total claims')).toBeInTheDocument()
    expect(screen.getByText('All claims')).toBeInTheDocument()
    await waitFor(() => expect(screen.getByText('17')).toBeInTheDocument())
  })

  it('moves through pages', async () => {
    const onPage = vi.fn()
    render(<Pagination page={2} totalPages={4} total={40} onPage={onPage} />)

    await userEvent.click(screen.getByRole('button', { name: /next/i }))
    await userEvent.click(screen.getByRole('button', { name: /prev/i }))

    expect(onPage).toHaveBeenNthCalledWith(1, 3)
    expect(onPage).toHaveBeenNthCalledWith(2, 1)
  })
})
