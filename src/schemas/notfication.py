from datetime import datetime
from typing import Optional, List

import strawberry
from sqlalchemy import select, func
from strawberry.types import Info

from conn import get_session, Notification as NotificationModel


# Input class for sending a notification
@strawberry.input
class SendNotificationInput:
    sender_id: int
    receiver_id: int
    message: str


# Type definition for the Notification
@strawberry.type
class NotificationType:
    notification_id: strawberry.ID
    sender_id: strawberry.ID
    receiver_id: strawberry.ID
    message: Optional[str]
    is_read: Optional[bool]
    created_at: Optional[datetime]


# Type definition for the UserNotificationCountType
@strawberry.type
class UserNotificationCountType:
    success: bool
    message: Optional[str] = None
    unread_count: Optional[int] = None
    notifications: Optional[List[NotificationType]] = None


# Type definition for the Notification response
@strawberry.type
class NotificationResponse:
    success: bool
    notification_id: int = None
    message: Optional[str]


# Type definition for the Query class
@strawberry.type
class Query:
    # Query to get user notifications
    @strawberry.field
    async def get_user_notifications(self, info: Info,
                                     unread_only: Optional[bool] = False) -> UserNotificationCountType:
        async with get_session() as session:
            # Fetch the job seeker and project from the database
            try:
                user_id = await info.context.get_current_user
                # if user_id is None:
                #     raise Exception("User not authenticated")
            except Exception as e:
                return UserNotificationCountType(
                    success=False,
                    message=str(e)
                )

            try:
                if user_id:
                    query = select(NotificationModel).where(NotificationModel.receiver_id == user_id)
                    if unread_only:
                        query = query.where(NotificationModel.is_read == False)

                    unread_count = await session.execute(
                        query.where(NotificationModel.is_read == False).with_only_columns(func.count()))

                    notifications = await session.execute(query.order_by(NotificationModel.created_at.desc()))

                    return UserNotificationCountType(
                        success=True,
                        unread_count=unread_count.scalar(),
                        notifications=notifications.scalars().unique().all()
                    )
                else:
                    return UserNotificationCountType(
                        success=False,
                        message="Not able to retrieve notification"
                    )
            except Exception as e:
                return UserNotificationCountType(
                    success=False,
                    message=str(e)
                )


# Type definition for the Mutation class
@strawberry.type
class Mutation:
    # Mutation to send a notification
    @strawberry.mutation
    async def send_notification(self, input: SendNotificationInput) -> NotificationResponse:
        async with get_session() as session:
            try:
                notification = NotificationModel(sender_id=input.sender_id, receiver_id=input.receiver_id,
                                                 message=input.message)
                session.add(notification)
                await session.commit()

                return NotificationResponse(success=True, notification_id=notification.notification_id,
                                            message="Notification is sent")
            except Exception as e:
                return NotificationResponse(success=False, message=str(e))

    # Mutation to mark a notification as read
    @strawberry.mutation
    async def mark_notification_as_read(self, notification_id: int) -> NotificationResponse:
        async with get_session() as session:
            try:
                notification = await session.get(NotificationModel, notification_id)
                if notification:
                    notification.is_read = True
                    await session.commit()

                    return NotificationResponse(success=True, notification_id=notification.notification_id,
                                                message="Notification is read")
            except Exception as e:
                return NotificationResponse(success=False, message=str(e))
