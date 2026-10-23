export const CATEGORIES = [
  { value: 'electronics', label: 'Electronics' },
  { value: 'appliances', label: 'Home Appliances' },
  { value: 'automotive', label: 'Automotive' },
]

export const INTAKE_ROLES = ['customer', 'service_center', 'admin']

export const WARRANTY_STATUSES = [
  'Active',
  'Expiring Soon',
  'Grace Period Active',
  'Expired',
]

export const WARRANTY_TONE = {
  Active: 'success',
  'Expiring Soon': 'warning',
  'Grace Period Active': 'warning',
  Expired: 'danger',
}

export const DECISION_TONE = {
  'Likely Valid': 'success',
  'Likely Invalid': 'danger',
  'Manual Review Required': 'warning',
  Draft: 'neutral',
}

export const STATUS_TONE = {
  Approved: 'success',
  Rejected: 'danger',
  'Manual Review': 'warning',
  'Request More Info': 'warning',
  Draft: 'neutral',
  Submitted: 'info',
  'Under Evaluation': 'info',
  Closed: 'neutral',
}

export const CLAIM_STATUSES = [
  'Draft',
  'Submitted',
  'Under Evaluation',
  'Manual Review',
  'Approved',
  'Rejected',
  'Request More Info',
  'Closed',
]

export const DOC_TYPES = [
  { value: 'purchase_receipt', label: 'Purchase Receipt' },
  { value: 'warranty_card', label: 'Warranty Card' },
  { value: 'product_image', label: 'Product Photo' },
  { value: 'serial_number_photo', label: 'Serial Number Photo' },
  { value: 'damage_photo', label: 'Damage Photo' },
  { value: 'diagnostic_report', label: 'Diagnostic Report' },
]

export const DOC_TYPE_LABEL = Object.fromEntries(
  DOC_TYPES.map((item) => [item.value, item.label]),
)

export const FAULT_CATEGORIES = [
  { value: 'motherboard_failure', label: 'Motherboard Failure' },
  { value: 'screen_flicker_defect', label: 'Screen Flicker Defect' },
  { value: 'battery_not_charging', label: 'Battery Not Charging' },
  { value: 'general_defect', label: 'General Defect' },
]

export const DAMAGE_TYPES = [
  { value: 'none', label: 'No accidental damage' },
  { value: 'liquid_spill_damage', label: 'Liquid spill damage' },
  { value: 'physical_drop_crack', label: 'Physical drop / crack' },
]

export const REVIEW_ACTIONS = ['Approved', 'Rejected', 'Request More Info', 'Closed']

export const REVIEWER_ROLES = ['reviewer', 'admin']
export const ADMIN_ROLES = ['admin']

export const NAV_ITEMS = [
  { to: '/', label: 'Dashboard', icon: 'dashboard', end: true },
  { to: '/products', label: 'Products', icon: 'box' },
  { to: '/documents', label: 'Documents', icon: 'file' },
  { to: '/claims', label: 'Claims', icon: 'clipboard' },
  { to: '/alerts', label: 'Warranty Alerts', icon: 'bell' },
  { to: '/repairs', label: 'Repairs', icon: 'wrench' },
  { to: '/review', label: 'Review Queue', icon: 'shield', roles: REVIEWER_ROLES },
  { to: '/admin', label: 'Administration', icon: 'settings', roles: ADMIN_ROLES },
]
