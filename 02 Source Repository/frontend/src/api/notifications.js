import { api, unwrap } from './client'
import { EP, fill } from './endpoints'

export const listNotifications = (params = {}) =>
  unwrap(api.get(EP.notifications, { params }))

export const getUnreadCount = () => unwrap(api.get(EP.notificationsUnread))

export const markNotificationRead = (notificationId) =>
  unwrap(api.post(fill(EP.notificationRead, { notification_id: notificationId })))

export const markAllNotificationsRead = () =>
  unwrap(api.post(EP.notificationsReadAll))
