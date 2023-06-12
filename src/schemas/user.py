import strawberry
from sqlalchemy import select, delete
from typing import Optional, List
from conn import get_session, User as UserModel
from strawberry.types import Info
from jwt import encode, decode, InvalidTokenError
from datetime import datetime, timedelta
from decouple import config
import bcrypt

JWT_SECRET = config('secret')
JWT_ALGORITHM = config('algorithm')
EXPIRATION_TIME = timedelta(minutes=60)


def decode_token(token: str):
    try:
        payload = decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except InvalidTokenError:
        raise Exception("Invalid token")


@strawberry.type
class UserType:
    user_id: strawberry.ID
    user_name: str
    user_email: str
    password: str
    user_type: str

    # This method generates a JWT token for the user
    def generate_token(self):
        payload = {
            "user_id": self.user_id,
            "exp": datetime.utcnow() + EXPIRATION_TIME
        }
        token = encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
        return token


@strawberry.type
class User:
    user_id: strawberry.ID
    user_name: str
    user_email: str
    password: str
    user_type: str

    @classmethod
    def marshal(cls, model: UserModel) -> "User":
        return cls(
            user_id=strawberry.ID(str(model.user_id)),
            user_name=model.user_name,
            user_email=model.user_email,
            password=model.password,
            user_type=model.user_type
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


@strawberry.type
class UserResponse:
    success: bool
    user: Optional[UserType] = None
    message: Optional[str]


@strawberry.type
class AuthResponse:
    success: bool
    token: Optional[str]
    user: Optional[UserType] = None
    message: Optional[str]


# Responses
AddUserResponse = strawberry.union("AddUserResponse", (User, UserExists))
UpdateUserResponse = strawberry.union("UpdateUserResponse", (UserUpdateMessage, UserNotFound))
DeleteUserResponse = strawberry.union("DeleteUserResponse", (UserDeleteMessage, UserNotFound))


@strawberry.type
class Query:
    @strawberry.field
    async def me(self, info: Info) -> UserType:
        async with get_session() as session:
            user_id = await info.context.get_current_user
            if user_id is None:
                raise ValueError("User not authenticated")
            from src.controllers.index import SessionExpired
            try:
                user_query = select(UserModel).where(UserModel.user_id == user_id)
                user = (await session.execute(user_query)).scalars().first()
                if not user:
                    raise ValueError("User not found")

                return UserType(
                    user_id=user.user_id,
                    user_name=user.user_name,
                    user_email=user.user_email,
                    user_type=user.user_type,
                    password=user.password
                )
            except SessionExpired:
                raise ValueError("Session has expired")

    @strawberry.field
    async def user_detail(self, info: Info, user_id: int) -> Optional[User]:
        async with get_session() as s:
            user_query = select(UserModel).where(UserModel.user_id == user_id)
            db_user = (await s.execute(user_query)).scalars().first()
            return User.marshal(db_user) if db_user else None

    @strawberry.field
    async def user_listing(self) -> List[User]:
        async with get_session() as s:
            sql = select(UserModel).order_by(UserModel.user_id)
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
    async def update_user(self, user_id: int, user_name: Optional[str] = None, user_email: Optional[str] = None,
                          password: Optional[str] = None) -> UpdateUserResponse:
        async with get_session() as s:
            db_user = await s.get(UserModel, user_id)
            if db_user is None:
                return UserNotFound()

            if user_name is not None:
                db_user.user_name = user_name
            if user_email is not None:
                db_user.user_email = user_email
            if password is not None:
                db_user.password = password

            await s.commit()

        return UserUpdateMessage(message=f"User with id {user_id} updated successfully")

    @strawberry.mutation
    async def delete_user(self, user_id: int) -> DeleteUserResponse:
        async with get_session() as s:
            sql = delete(UserModel).where(UserModel.user_id == user_id)
            db_user = await s.execute(sql)
            # db_user = await s.get(user.User, id)
            if db_user.rowcount == 0:
                return UserNotFound()

            # s.delete(db_user)
            await s.commit()

        return UserDeleteMessage

    @strawberry.mutation
    async def login(self, user_name: str, password: str) -> AuthResponse:
        async with get_session() as s:
            try:
                user_query = select(UserModel).where(UserModel.user_name == user_name)
                db_user = (await s.execute(user_query)).scalars().first()
                if db_user is None:
                    return AuthResponse(success=False, token=None, user=None, message='Account not found')
                if not bcrypt.checkpw(password.encode('utf-8'), db_user.password.encode('utf-8')):
                    return AuthResponse(success=False, token=None, user=None, message='Password is incorrect')
                
                user = UserType(
                    user_id=db_user.user_id,
                    user_name=db_user.user_name,
                    user_email=db_user.user_email,
                    password=db_user.password,
                    user_type=db_user.user_type
                )
                token = user.generate_token()
                return AuthResponse(success=True, token=token, user=user, message='Login successfully')

            except Exception as e:
                return AuthResponse(success=False, token=None, user=None, message=str(e))
