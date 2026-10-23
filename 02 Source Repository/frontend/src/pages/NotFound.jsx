import { Link } from 'react-router-dom'

import { buttonClasses } from '../components/ui/Button'
import { EmptyState } from '../components/ui/Feedback'

export default function NotFound() {
  return (
    <div className="py-10">
      <EmptyState
        icon="search"
        title="Page not found"
        description="The page you were looking for does not exist or was moved."
        action={
          <Link to="/" className={buttonClasses({ size: 'sm' })}>
            Back to dashboard
          </Link>
        }
      />
    </div>
  )
}


