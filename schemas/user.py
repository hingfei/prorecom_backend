import strawberry
from sqlalchemy import select, delete
from typing import Optional
# from models import user
from conn import get_session, User as UserModel
from strawberry.types import Info


@strawberry.type
class User:
    id: strawberry.ID
    user_name: str
    user_email: str
    password: str

    @classmethod
    def marshal(cls, model: UserModel) -> "User":
        return cls(
            id=strawberry.ID(str(model.id)),
            user_name=model.user_name,
            user_email=model.user_email,
            password=model.password
        )


@strawberry.type
class UserExists:
    message: str = "User with this name already exist"


@strawberry.type
class UserUpdateMessage:
    message: str


@strawberry.type
class UserNotFound:
    message: str = "User not found"


@strawberry.type
class UserDeleteMessage:
    message: str = "User deleted successfully"


# Responses
AddUserResponse = strawberry.union("AddUserResponse", (User, UserExists))
UpdateUserResponse = strawberry.union("UpdateUserResponse", (UserUpdateMessage, UserNotFound))
DeleteUserResponse = strawberry.union("DeleteUserResponse", (UserDeleteMessage, UserNotFound))


@strawberry.type
class Query:
    @strawberry.field
    async def user_detail(self, info: Info, id: int) -> Optional[User]:
        async with get_session() as s:
            user_query = select(UserModel).where(UserModel.id == id)
            db_user = (await s.execute(user_query)).scalars().first()
            return User.marshal(db_user) if db_user else None

    @strawberry.field
    async def user_listing(self) -> list[User]:
        async with get_session() as s:
            sql = select(UserModel).order_by(UserModel.id)
            db_user = (await s.execute(sql)).scalars().unique().all()
        return [User.marshal(loc) for loc in db_user]


@strawberry.type
class Mutation:
    @strawberry.mutation
    async def create_user(self, user_name: str, user_email: str, password: str) -> AddUserResponse:
        async with get_session() as s:
            sql = select(UserModel).where(UserModel.user_name == user_name)
            db_user = (await s.execute(sql)).first()
            if db_user is not None:
                return UserExists()
            db_user = UserModel(user_name=user_name, user_email=user_email, password=password)
            s.add(db_user)
            await s.commit()
        return User.marshal(db_user)

    @strawberry.mutation
    async def update_user(self, id: int, user_name: Optional[str] = None, user_email: Optional[str] = None,
                          password: Optional[str] = None) -> UpdateUserResponse:
        async with get_session() as s:
            db_user = await s.get(UserModel, id)
            if db_user is None:
                return UserNotFound()

            if user_name is not None:
                db_user.user_name = user_name
            if user_email is not None:
                db_user.user_email = user_email
            if password is not None:
                db_user.password = password

            await s.commit()

        return UserUpdateMessage(message=f"User with id {id} updated successfully")

    @strawberry.mutation
    async def delete_user(self, id: int) -> DeleteUserResponse:
        async with get_session() as s:
            sql = delete(UserModel).where(UserModel.id == id)
            db_user = await s.execute(sql)
            # db_user = await s.get(user.User, id)
            if db_user.rowcount == 0:
                return UserNotFound()

            # s.delete(db_user)
            await s.commit()

        return UserDeleteMessage
