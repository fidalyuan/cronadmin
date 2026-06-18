import asyncio
import hashlib
from sqlalchemy import select
from app.database.session import async_session_factory
from app.models.models import User
from app.core.security import get_password_hash

async def reset_admin():
    username = "admin"
    password_plain = "admin123"
    
    # 核心：前端会先对密码进行 SHA256 加密再传输
    # 所以数据库里存储的 bcrypt(password) 实际上是 bcrypt(sha256(password_plain))
    password_sha256 = hashlib.sha256(password_plain.encode()).hexdigest()
    hashed_password = get_password_hash(password_sha256)
    
    async with async_session_factory() as session:
        result = await session.execute(select(User).where(User.username == username))
        user = result.scalars().first()
        
        if user:
            print(f"用户 {username} 已存在，正在重置密码...")
            user.hashed_password = hashed_password
            user.is_active = True
        else:
            print(f"正在创建用户 {username}...")
            user = User(
                username=username,
                hashed_password=hashed_password,
                is_active=True
            )
            session.add(user)
        
        await session.commit()
        print(f"成功！管理员账号: {username}，密码: {password_plain}")
        print(f"SHA256: {password_sha256}")

if __name__ == "__main__":
    asyncio.run(reset_admin())
