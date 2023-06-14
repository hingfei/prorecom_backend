from datetime import datetime
from typing import Optional, List

import strawberry
from sqlalchemy import select, func
from strawberry.types import Info

from conn import get_session, Notification as NotificationModel


@strawberry.input
class SendNotificationInput:
    sender_id: int
    receiver_id: int
    message: str


@strawberry.type
class NotificationType:
    notification_id: strawberry.ID
    sender_id: strawberry.ID
    receiver_id: strawberry.ID
    message: Optional[str]
    is_read: Optional[bool]
    created_at: Optional[datetime]


@strawberry.type
class UserNotificationCountType:
    unread_count: int
    notifications: List[NotificationType]


@strawberry.type
class NotificationResponse:
    success: bool
    notification_id: int = None
    message: Optional[str]


@strawberry.type
class Query:
    @strawberry.field
    async def get_user_notifications(self, info: Info,
                                     unread_only: Optional[bool] = False) -> UserNotificationCountType:
        async with get_session() as session:
            # Fetch the job seeker and project from the database
            user_id = await info.context.get_current_user
            if user_id is None:
                raise ValueError("User not authenticated")

            query = select(NotificationModel).where(NotificationModel.receiver_id == user_id)
            if unread_only:
                query = query.where(NotificationModel.is_read == False)

            unread_count = await session.execute(
                query.where(NotificationModel.is_read == False).with_only_columns(func.count()))

            notifications = await session.execute(query.order_by(NotificationModel.created_at.desc()))

            # query = query.order_by(NotificationModel.created_at.desc())
            # notifications = await session.execute(query)

            return UserNotificationCountType(
                unread_count=unread_count.scalar(),
                notifications=notifications.scalars().unique().all()
            )


@strawberry.type
class Mutation:
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
